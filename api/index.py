from dotenv import load_dotenv
from fastapi import FastAPI, Response, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from .schemas import ChatRequest, SessionRequest, TestCreate, TestResponse, ReportCreate, ReportResponse, BatchAgentRequest
from .utils.prompt import convert_to_chat_messages
from .models import ModelConfig
from .plugins import WebAgentType, get_web_agent, AGENT_CONFIGS
from .streamer import stream_vercel_format
from api.middleware.profiling_middleware import ProfilingMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union
import os
import asyncio
import subprocess
import re
import time
import logging
from datetime import datetime
from .utils.types import AgentSettings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1) Import the Steel client
try:
    from steel import Steel
except ImportError:
    raise ImportError("Please install the steel package: pip install steel")


load_dotenv(".env.local")

# Log the environment variables for debugging (excluding sensitive info)
port = os.environ.get("PORT", "8000")
logger.info(f"Starting server on port: {port}")

app = FastAPI()
app.add_middleware(ProfilingMiddleware) # Uncomment this when profiling is not needed
STEEL_API_KEY = os.getenv("STEEL_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
STEEL_API_URL = os.getenv("STEEL_API_URL")

# 2) Initialize the Steel client
#    Make sure your STEEL_API_KEY is set as an environment variable
steel_client = Steel(steel_api_key=STEEL_API_KEY, base_url=STEEL_API_URL)

# Add a session locks mechanism to prevent multiple resume requests
session_locks: Dict[str, asyncio.Lock] = {}
session_last_resume: Dict[str, float] = {}
RESUME_COOLDOWN = 1.0  # seconds

# Keep track of batch job status
batch_job_status: Dict[str, Dict[str, Any]] = {}

origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8080",
    "https://bugzer.bugzer.workers.dev",
    "http://localhost:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Health"])
async def root_health_check():
    """
    Root health check endpoint for Cloud Run
    """
    logger.info("Health check endpoint called")
    return {"status": "ok", "message": "API is running"}

@app.post("/api/sessions", tags=["Sessions"])
async def create_session(request: SessionRequest):
    """
    Creates a new session.
    """
    # Create a regular session for all agent types (since CLAUDE_COMPUTER_USE was removed)
    return steel_client.sessions.create(
        api_timeout=request.timeout * 1000,
    )


@app.post("/api/sessions/{session_id}/release", tags=["Sessions"])
async def release_session(session_id: str):
    """
    Releases a session. Returns success even if session is already released.
    """
    try:
        return steel_client.sessions.release(session_id)
    except Exception as e:
        # Return success response even if session was already released
        if "Session already stopped" in str(e):
            return {"status": "success", "message": "Session released"}
        raise e

@app.post("/api/sessions/{session_id}/resume", tags=["Sessions"])
async def resume_session(session_id: str):
    """
    Resume execution for a paused session.
    """
    from .plugins.browser_use.agent import resume_execution, ResumeRequest

    # Check if this session was recently resumed
    now = time.time()
    if session_id in session_last_resume:
        time_since_last_resume = now - session_last_resume[session_id]
        if time_since_last_resume < RESUME_COOLDOWN:
            # Too soon - return success but don't actually resume again
            return {
                "status": "success", 
                "message": f"Resume already in progress", 
                "is_resumed": True, 
                "timestamp": now
            }

    # Create a lock for this session if it doesn't exist
    if session_id not in session_locks:
        session_locks[session_id] = asyncio.Lock()
    
    # Try to acquire the lock with a timeout
    try:
        # Use a timeout to prevent deadlocks
        lock_acquired = await asyncio.wait_for(
            session_locks[session_id].acquire(), 
            timeout=0.5
        )
        
        if not lock_acquired:
            # If we couldn't acquire the lock, someone else is already processing
            return {
                "status": "success", 
                "message": "Resume already in progress", 
                "is_resumed": True, 
                "timestamp": now
            }
            
        # Update last resume timestamp
        session_last_resume[session_id] = now
            
        try:
            # Make multiple attempts to resume the session in case the first one fails
            max_attempts = 2
            last_error = None
            
            for attempt in range(max_attempts):
                try:
                    result = await resume_execution(ResumeRequest(session_id=session_id))
                    if result.get("status") == "success":
                        result["is_resumed"] = True
                        result["timestamp"] = now
                        # If we were successful after a retry, log it
                        if attempt > 0:
                            print(f"Successfully resumed session {session_id} on attempt {attempt+1}")
                        return result
                    elif attempt < max_attempts - 1:
                        # Wait briefly before retry
                        await asyncio.sleep(0.2)
                except Exception as e:
                    last_error = e
                    # Only sleep before retry if not the last attempt
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(0.2)
            
            # If we got here, all attempts failed
            if last_error:
                raise last_error
            return {
                "status": "error",
                "message": "Failed to resume session after multiple attempts",
                "is_resumed": False
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            # Always release the lock
            session_locks[session_id].release()
    except asyncio.TimeoutError:
        # If we timed out waiting for the lock
        return {
            "status": "success", 
            "message": "Resume already in progress", 
            "is_resumed": True, 
            "timestamp": now
        }


@app.post("/api/sessions/{session_id}/pause", tags=["Sessions"])
async def pause_session(session_id: str):
    """
    Manually pause execution for a session to take control.
    """
    from .plugins.browser_use.agent import pause_execution_manually, PauseRequest

    try:
        result = await pause_execution_manually(PauseRequest(session_id=session_id))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat", tags=["Chat"])
async def handle_chat(request: ChatRequest):
    """
    This endpoint accepts a chat request, instantiates an agent,
    and then streams the response in the Vercel AI Data Stream Protocol format.
    """
    try:
        messages = request.messages
        chat_messages = convert_to_chat_messages(messages)

        # Check for empty message, which might be causing the duplicated agent creation
        if not messages or (len(messages) > 0 and messages[-1].content == ""):
            logger.info("Received empty message request - not creating a new agent")
            return StreamingResponse(
                stream_vercel_format(empty_stream()),
                media_type="text/event-stream",
            )

        if not request.session_id:
            return Response(
                status_code=400,
                content="Session ID is required",
                media_type="text/plain",
            )
            
        # Import the controller here to avoid circular imports
        from .plugins.browser_use.agent import controller
        
        # Check if this session has a controller with a completed task
        if controller.session_id == request.session_id and controller.finished:
            logger.info(f"Agent already completed task for session {request.session_id} - not creating a new agent")
            return StreamingResponse(
                stream_vercel_format(empty_stream()),
                media_type="text/event-stream",
            )
            
        # Set the session ID on the controller
        controller.session_id = request.session_id
        controller.finished = False

        model_config_args = {
            "provider": request.provider,
            "model_name": request.model_settings.model_choice,
            "api_key": request.api_key,
        }

        if hasattr(request.model_settings, "temperature"):
            model_config_args["temperature"] = request.model_settings.temperature
        if hasattr(request.model_settings, "max_tokens"):
            model_config_args["max_tokens"] = request.model_settings.max_tokens
        if hasattr(request.model_settings, "top_p"):
            model_config_args["top_p"] = request.model_settings.top_p
        if hasattr(request.model_settings, "top_k"):
            model_config_args["top_k"] = request.model_settings.top_k
        if hasattr(request.model_settings, "frequency_penalty"):
            model_config_args["frequency_penalty"] = (
                request.model_settings.frequency_penalty
            )
        if hasattr(request.model_settings, "presence_penalty"):
            model_config_args["presence_penalty"] = (
                request.model_settings.presence_penalty
            )

        model_config = ModelConfig(**model_config_args)

        web_agent = get_web_agent(request.agent_type)

        # Create a FastAPI-level cancel event
        cancel_event = asyncio.Event()

        async def on_disconnect():
            # When the client disconnects, set cancel_event
            cancel_event.set()

        # Pass cancel_event explicitly to the agent only if you want cancellation support
        web_agent_stream = web_agent(
            model_config=model_config,
            agent_settings=request.agent_settings,
            history=chat_messages,
            session_id=request.session_id,
            # Only base_agent really uses it for now
            cancel_event=cancel_event,
        )

        # Directly wrap the agent stream with the Vercel AI format
        streaming_response = stream_vercel_format(
            stream=web_agent_stream,
        )

        # Use background=on_disconnect to catch client-aborted requests
        response = StreamingResponse(
            streaming_response, background=on_disconnect)
        response.headers["x-vercel-ai-data-stream"] = "v1"
        # response.headers["model_used"] = request.model_name
        return response
    except Exception as e:
        # Format error for frontend consumption
        error_response = {
            "error": {
                "message": str(e),
                "type": type(e).__name__,
                "code": getattr(e, "code", 500),
            }
        }
        raise HTTPException(status_code=getattr(
            e, "code", 500), detail=error_response)


@app.get("/api/agents", tags=["Agents"])
async def get_available_agents():
    """
    Returns all available agents and their configurations.
    """
    return AGENT_CONFIGS


@app.get("/healthcheck", tags=["System"])
async def healthcheck():
    """
    Simple health check endpoint to verify the API is running.
    """
    return {"status": "ok"}

@app.post("/api/tests", response_model=TestResponse, tags=["Tests"])
async def create_test(
    test_data: TestCreate,
    user_id: str # In production this would use Depends(get_current_user)
):
    """
    Create a new test for the authenticated user.
    """
    try:
        # Create test data dictionary
        test_dict = test_data.model_dump()
        test_dict["user_id"] = user_id
        test_dict["created_at"] = datetime.now().isoformat()
        test_dict["updated_at"] = test_dict["created_at"]
        
        # Generate a unique ID (in production this would be handled by the database)
        test_id = f"test_{int(time.time())}_{user_id[:8]}"
        test_dict["id"] = test_id
        
        # In a real implementation, this would be a database insert
        # For demo purposes, we'll just return the test data
        result = {"data": [test_dict]}
        
        logger.info(f"Created test: {test_id}")
        
        return TestResponse(**result["data"][0])
    except Exception as e:
        logger.error(f"Failed to create test: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create test: {str(e)}"
        )

@app.post("/api/reports", response_model=ReportResponse, tags=["Reports"])
async def create_report(
    report_data: ReportCreate,
    user_id: str # In production this would use Depends(get_current_user)
):
    """
    Create a new report for the authenticated user.
    """
    try:
        # In a real implementation, we would verify the test belongs to the user
        # For demo purposes, we'll just create the report
        
        # Create the report dictionary
        report_dict = report_data.model_dump()
        report_dict["user_id"] = user_id
        report_dict["created_at"] = datetime.now().isoformat()
        report_dict["updated_at"] = report_dict["created_at"]
        
        # Generate a unique ID (in production this would be handled by the database)
        report_id = f"report_{int(time.time())}_{user_id[:8]}"
        report_dict["id"] = report_id
        
        # In a real implementation, this would be a database insert
        # For demo purposes, we'll just return the report data
        result = {"data": [report_dict]}
        
        logger.info(f"Created report: {report_id} for test: {report_data.test_id}")
        
        return ReportResponse(**result["data"][0])
    except Exception as e:
        logger.error(f"Failed to create report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create report: {str(e)}"
        )

@app.post("/api/batch/browser_agent", tags=["Agents"])
async def run_browser_agent_batch(
    request: BatchAgentRequest,
    user_id: str = "demo_user" # In production this would use Depends(get_current_user)
):
    """
    Run the browser agent in batch mode without streaming.
    Creates a test record, runs the agent, and stores the report.
    """
    try:
        # 1. Create a test record first
        test_data = TestCreate(
            url=request.url,
            description=request.description or f"Automated test for {request.url}",
            status="pending"
        )
        
        # Create the test record
        test_result = await create_test(test_data, user_id)
        test_id = test_result.id
        
        # Update batch job status
        batch_job_status[test_id] = {
            "status": "running",
            "message": "Test initialized, running browser agent",
            "started_at": datetime.now().isoformat()
        }
        
        # 2. Prepare agent execution
        # Create a message with the URL as the content
        messages = [{"role": "user", "content": f"Analyze the website at {request.url} and provide a detailed performance report."}]
        chat_messages = convert_to_chat_messages(messages)
        
        # Set up model and agent settings
        model_config = ModelConfig(
            provider=request.provider,
            model_name=request.model_settings.model_choice,
            temperature=request.model_settings.temperature
        )
        
        agent_settings = request.agent_settings or AgentSettings(steps=100)
        
        # Create a unique session ID from the test ID
        session_id = f"batch_{test_id}"
        
        # Create a timeout mechanism
        timeout = request.timeout or 300  # default 5 minutes
        
        # 3. Run the agent with timeout
        try:
            # Update test status to "running"
            # In a real implementation, this would update the database
            logger.info(f"Starting batch agent for test: {test_id}")
            
            # Import the batch agent function
            from .plugins.browser_use import browser_use_agent_batch
            
            # Run the agent
            report = await asyncio.wait_for(
                browser_use_agent_batch(
                    model_config=model_config,
                    agent_settings=agent_settings,
                    history=[{"role": "user", "content": request.description}],
                    session_id=session_id,
                ),
                timeout=timeout
            )
            
            # 4. Create the report record
            report_data = ReportCreate(
                test_id=test_id,
                content=report,
                status="completed"
            )
            
            report_result = await create_report(report_data, user_id)
            
            # 5. Update test status to "completed"
            # In a real implementation, this would update the database
            logger.info(f"Batch agent completed successfully for test: {test_id}")
            
            # Update batch job status
            batch_job_status[test_id] = {
                "status": "completed",
                "message": "Test completed successfully",
                "completed_at": datetime.now().isoformat()
            }
            
            return {
                "status": "success",
                "test_id": test_id,
                "report_id": report_result.id,
                "report": report
            }
            
        except asyncio.TimeoutError:
            # Handle timeout
            error_message = f"Agent execution timed out after {timeout} seconds"
            logger.error(f"Timeout for test: {test_id} - {error_message}")
            
            # Update test status to "failed"
            # In a real implementation, this would update the database
            
            # Still create a report with the error
            report_data = ReportCreate(
                test_id=test_id,
                content=f"ERROR: {error_message}",
                status="failed"
            )
            
            report_result = await create_report(report_data, user_id)
            
            # Update batch job status
            batch_job_status[test_id] = {
                "status": "failed",
                "message": error_message,
                "completed_at": datetime.now().isoformat()
            }
            
            return {
                "status": "error",
                "test_id": test_id,
                "report_id": report_result.id,
                "message": error_message
            }
            
        except Exception as e:
            # Handle other exceptions
            error_message = f"Error during agent execution: {str(e)}"
            logger.error(f"Error for test: {test_id} - {error_message}")
            
            # Update test status to "failed"
            # In a real implementation, this would update the database
            
            # Still create a report with the error
            report_data = ReportCreate(
                test_id=test_id,
                content=f"ERROR: {error_message}",
                status="failed"
            )
            
            report_result = await create_report(report_data, user_id)
            
            # Update batch job status
            batch_job_status[test_id] = {
                "status": "failed",
                "message": error_message,
                "completed_at": datetime.now().isoformat()
            }
            
            return {
                "status": "error",
                "test_id": test_id,
                "report_id": report_result.id,
                "message": error_message
            }
            
    except Exception as e:
        logger.error(f"Error in batch browser agent: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/api/batch/status/{test_id}", tags=["Agents"])
async def check_batch_status(
    test_id: str,
    user_id: str = "demo_user" # In production this would use Depends(get_current_user)
):
    """
    Check the status of a batch browser agent job.
    """
    # In a real implementation, we would verify that the test belongs to the user
    # For demo purposes, we'll just check if the test exists in our status dictionary
    
    if test_id not in batch_job_status:
        return {
            "status": "unknown",
            "message": "No batch job found for this test ID"
        }
    
    status_data = batch_job_status[test_id]
    
    # In a real implementation, we would include test and report data from the database
    
    return status_data
