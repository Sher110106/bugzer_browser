from dotenv import load_dotenv
from fastapi import FastAPI, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from .schemas import ChatRequest, SessionRequest, TestFlowRequest, TestFlowResponse
from .utils.prompt import convert_to_chat_messages
from .models import ModelConfig
from .plugins import WebAgentType, get_web_agent, AGENT_CONFIGS
from .streamer import stream_vercel_format, empty_stream
from api.middleware.profiling_middleware import ProfilingMiddleware
from .utils.test_flow_manager import test_flow_manager
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import asyncio
import subprocess
import re
import time
import logging
from datetime import datetime
from .schemas import TestFlowStatus

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
        
        # Extract test_id and user_id from agent_settings if available
        # We need to use hasattr/getattr as AgentSettings is a Pydantic model, not a dict
        test_id = getattr(request.agent_settings, 'test_id', None) 
        
        if test_id:
            logger.info(f"Test ID received in request: {test_id}")
            # Store test_id in session metrics for reporting
            from .plugins.browser_use.agent import session_metrics_storage
            if request.session_id in session_metrics_storage:
                session_metrics_storage[request.session_id]['test_id'] = test_id
                
       

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
    Returns available agent configurations.
    """
    return {"agents": AGENT_CONFIGS}

@app.get("/api/ollama/models", tags=["Ollama"])
async def get_ollama_models():
    """
    Returns available Ollama models.
    """
    try:
        # Try to connect to local Ollama instance
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                data = response.json()
                return {"models": data.get("models", [])}
            else:
                return {"models": [], "error": "Ollama not running"}
    except Exception as e:
        logger.warning(f"Failed to fetch Ollama models: {e}")
        return {"models": [], "error": "Ollama not available"}


@app.get("/healthcheck", tags=["System"])
async def healthcheck():
    """
    Simple health check endpoint to verify the API is running.
    """
    return {"status": "ok"}


# Test Flow Management Endpoints
@app.post("/api/test-flows/start", tags=["Test Flows"])
async def start_test_flow(request: TestFlowRequest):
    """
    Start a new test flow for a session.
    """
    try:
        result = await test_flow_manager.start_test_flow(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test-flows/{session_id}/pause", tags=["Test Flows"])
async def pause_test_flow(session_id: str):
    """
    Pause an active test flow.
    """
    try:
        result = await test_flow_manager.pause_test_flow(session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test-flows/{session_id}/resume", tags=["Test Flows"])
async def resume_test_flow(session_id: str):
    """
    Resume a paused test flow.
    """
    try:
        result = await test_flow_manager.resume_test_flow(session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test-flows/{session_id}/complete", tags=["Test Flows"])
async def complete_test_flow(session_id: str, success: bool = True, summary: str = None):
    """
    Complete a test flow.
    """
    try:
        result = await test_flow_manager.complete_test_flow(session_id, success, summary)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/test-flows/{session_id}/summary", tags=["Test Flows"])
async def get_test_flow_summary(session_id: str):
    """
    Get the current test flow summary for a session.
    """
    try:
        flow = await test_flow_manager.get_test_flow_summary(session_id)
        if not flow:
            return {"status": "not_found", "message": f"No test flow found for session {session_id}"}
        return flow
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/test-flows/{session_id}/export", tags=["Test Flows"])
async def export_test_report(session_id: str, format: str = "json"):
    """
    Export a test flow report in the specified format.
    """
    try:
        if format not in ["json", "html", "markdown"]:
            raise HTTPException(status_code=400, detail="Unsupported format. Use: json, html, markdown")
        
        report = await test_flow_manager.export_test_report(session_id, format)
        return {"format": format, "content": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/test-flows/status", tags=["Test Flows"])
async def get_test_flows_status():
    """
    Get overall status of test flows.
    """
    try:
        return {
            "active_flows": test_flow_manager.get_active_flows_count(),
            "completed_flows": test_flow_manager.get_completed_flows_count(),
            "status": "healthy"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test-flows/cleanup", tags=["Test Flows"])
async def cleanup_old_test_flows(max_age_hours: int = 24):
    """
    Clean up old completed test flows.
    """
    try:
        cleaned_count = await test_flow_manager.cleanup_old_flows(max_age_hours)
        return {
            "status": "success",
            "message": f"Cleaned up {cleaned_count} old test flows",
            "cleaned_count": cleaned_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Enhanced Test Flow Endpoints
@app.post("/api/test-flows/bulk", tags=["Test Flows"])
async def bulk_test_flow_operations(operations: List[Dict[str, Any]]):
    """
    Perform multiple test flow operations in batch.
    """
    try:
        from .utils.test_flow_actions import test_flow_actions
        
        results = await test_flow_actions.bulk_operations(operations)
        return {
            "status": "success",
            "message": f"Processed {len(operations)} operations",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/test-flows/{session_id}/state", tags=["Test Flows"])
async def get_test_flow_state(session_id: str):
    """
    Get detailed state information for a test flow.
    """
    try:
        from .utils.flow_state_manager import flow_state_manager
        
        state = await flow_state_manager.get_flow_state(session_id)
        if not state:
            return {"status": "not_found", "message": f"No flow state found for session {session_id}"}
        
        return {
            "status": "success",
            "data": state
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test-flows/{session_id}/validate", tags=["Test Flows"])
async def validate_test_flow_state(session_id: str, level: str = "standard"):
    """
    Validate the state of a test flow.
    """
    try:
        from .utils.flow_state_manager import flow_state_manager, FlowValidationLevel
        
        # Parse validation level
        try:
            validation_level = FlowValidationLevel(level)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid validation level: {level}. Use: basic, standard, strict")
        
        validation_result = await flow_state_manager.validate_flow_state(session_id, validation_level)
        
        return {
            "status": "success",
            "data": validation_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test-flows/{session_id}/retry", tags=["Test Flows"])
async def retry_test_flow(session_id: str):
    """
    Manually retry a failed test flow.
    """
    try:
        from .utils.flow_state_manager import flow_state_manager
        
        # Get current flow
        flow = await test_flow_manager.get_test_flow_summary(session_id)
        if not flow:
            raise HTTPException(status_code=404, detail=f"No test flow found for session {session_id}")
        
        if flow.metadata.status not in [TestFlowStatus.FAILED, TestFlowStatus.TIMEOUT]:
            raise HTTPException(status_code=400, detail=f"Cannot retry flow with status: {flow.metadata.status.value}")
        
        # Reset flow status and trigger retry
        flow.metadata.status = TestFlowStatus.RUNNING
        flow.metadata.summary = f"Manually retried at {datetime.utcnow().isoformat()}"
        
        # Update state manager
        await flow_state_manager.update_flow_state(session_id, {
            "status": TestFlowStatus.RUNNING,
            "last_activity": datetime.utcnow()
        })
        
        return {
            "status": "success",
            "message": f"Test flow retry initiated for session {session_id}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/test-flows/health", tags=["Test Flows"])
async def get_test_flows_health():
    """
    Get comprehensive health status of the test flow system.
    """
    try:
        from .utils.flow_state_manager import flow_state_manager
        from .utils.test_flow_actions import test_flow_actions
        
        # Get system health from state manager
        state_health = await flow_state_manager.get_system_health()
        
        # Get system status from actions
        actions_status = await test_flow_actions.get_system_status()
        
        # Combine health information
        health_data = {
            "overall_status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "state_manager": state_health,
            "actions_system": actions_status,
            "test_flow_manager": {
                "active_flows": test_flow_manager.get_active_flows_count(),
                "completed_flows": test_flow_manager.get_completed_flows_count()
            }
        }
        
        # Determine overall status
        if (state_health.get("status") == "error" or 
            actions_status.get("status") == "error"):
            health_data["overall_status"] = "error"
        elif (state_health.get("status") == "warning" or 
              actions_status.get("status") == "warning"):
            health_data["overall_status"] = "warning"
        
        return health_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test-flows/{session_id}/timeout", tags=["Test Flows"])
async def set_test_flow_timeout(session_id: str, timeout_seconds: int):
    """
    Set custom timeout for a test flow.
    """
    try:
        from .utils.flow_state_manager import flow_state_manager
        
        if timeout_seconds < 60 or timeout_seconds > 3600:
            raise HTTPException(status_code=400, detail="Timeout must be between 60 and 3600 seconds")
        
        # Update timeout in state manager
        success = await flow_state_manager.update_flow_state(session_id, {
            "timeout_seconds": timeout_seconds
        })
        
        if not success:
            raise HTTPException(status_code=404, detail=f"No flow state found for session {session_id}")
        
        return {
            "status": "success",
            "message": f"Timeout set to {timeout_seconds} seconds for session {session_id}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test-flows/{session_id}/capture", tags=["Test Flows"])
async def capture_test_step_data(
    session_id: str,
    url: str,
    action: str = None,
    capture_options: Dict[str, bool] = None
):
    """
    Capture comprehensive data for a test step.
    """
    try:
        from .utils.test_flow_actions import test_flow_actions
        
        result = await test_flow_actions.record_test_step(
            session_id=session_id,
            url=url,
            action=action,
            capture_options=capture_options
        )
        
        if result.status == "success":
            return result
        else:
            raise HTTPException(status_code=400, detail=result.message)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/test-flows/analytics", tags=["Test Flows"])
async def get_test_flows_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tags: Optional[List[str]] = None
):
    """
    Get analytics and insights about test flows.
    """
    try:
        from .utils.test_flow_actions import test_flow_actions
        
        # Get all flows for analysis
        all_flows = []
        
        # Combine active and completed flows
        for session_id in test_flow_manager.active_flows:
            flow = await test_flow_manager.get_test_flow_summary(session_id)
            if flow:
                all_flows.append(flow)
        
        for session_id in test_flow_manager.completed_flows:
            flow = await test_flow_manager.get_test_flow_summary(session_id)
            if flow:
                all_flows.append(flow)
        
        # Filter by date range if provided
        if start_date or end_date:
            filtered_flows = []
            for flow in all_flows:
                flow_start = flow.metadata.start_time
                
                if start_date:
                    start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    if flow_start < start_dt:
                        continue
                
                if end_date:
                    end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    if flow_start > end_dt:
                        continue
                
                filtered_flows.append(flow)
            
            all_flows = filtered_flows
        
        # Filter by tags if provided
        if tags:
            filtered_flows = []
            for flow in all_flows:
                if any(tag in (flow.metadata.tags or []) for tag in tags):
                    filtered_flows.append(flow)
            
            all_flows = filtered_flows
        
        # Calculate analytics
        total_flows = len(all_flows)
        if total_flows == 0:
            return {
                "status": "success",
                "message": "No flows found for the specified criteria",
                "data": {
                    "total_flows": 0,
                    "analytics": {}
                }
            }
        
        # Status distribution
        status_counts = {}
        for flow in all_flows:
            status = flow.metadata.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Performance metrics
        total_steps = sum(flow.metadata.total_steps for flow in all_flows)
        avg_steps_per_flow = total_steps / total_flows if total_flows > 0 else 0
        
        # Success rate
        successful_flows = sum(1 for flow in all_flows if flow.metadata.status == TestFlowStatus.COMPLETED)
        success_rate = (successful_flows / total_flows) * 100 if total_flows > 0 else 0
        
        # Duration analysis
        durations = []
        for flow in all_flows:
            if flow.metadata.end_time and flow.metadata.start_time:
                duration = (flow.metadata.end_time - flow.metadata.start_time).total_seconds()
                durations.append(duration)
        
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        analytics = {
            "total_flows": total_flows,
            "status_distribution": status_counts,
            "performance_metrics": {
                "total_steps": total_steps,
                "average_steps_per_flow": round(avg_steps_per_flow, 2),
                "success_rate": round(success_rate, 2)
            },
            "duration_analysis": {
                "average_duration_seconds": round(avg_duration, 2),
                "flows_with_duration": len(durations)
            },
            "date_range": {
                "start_date": start_date,
                "end_date": end_date
            },
            "tags_filter": tags
        }
        
        return {
            "status": "success",
            "message": f"Analytics generated for {total_flows} flows",
            "data": analytics
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
