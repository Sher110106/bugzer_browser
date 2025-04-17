# Final Detailed Roadmap for Batch Browser Agent Implementation

## 1. Create New Agent Function: `browser_use_agent_batch`

Create a new version of the browser agent that returns a complete report rather than streaming results:

```python
async def browser_use_agent_batch(
    model_config: ModelConfig,
    agent_settings: AgentSettings,
    history: List[Mapping[str, Any]],
    session_id: str,
) -> str:
    """
    Non-streaming version of browser_use_agent that runs autonomously
    and returns the final report as a single string.
    """
    # Implementation will be similar to browser_use_agent but without streaming
    # ...
```

## 2. Modify Agent Execution Flow

### 2.1 Replace Async Generator with Async Function
- Change return type from `AsyncIterator[str]` to `str` for the final report

### 2.2 Replace Queue-based Stream Processing with Data Collection
- Remove the `asyncio.Queue` usage
- Create a container to collect important data during execution:
```python
collected_data = {
    "metrics": {},
    "anomalies": {},
    "screenshots": {},
    "final_report": None
}
```

### 2.3 Modify the Agent Callbacks
- Update `yield_data` to store important data in the container instead of queueing:
```python
def batch_yield_data(browser_state, agent_output, step_number):
    # Store data but don't queue for streaming
    if agent_output.current_state.memory:
        collected_data["memory"] = agent_output.current_state.memory
    # Process other important data...
```

- Update `yield_done` to generate the final report and store it:
```python
def batch_yield_done(history):
    # Generate the final report
    report = display_performance_report()
    collected_data["final_report"] = report
```

### 2.4 Modify Agent Execution Logic
- Wait for agent to complete using `await`:
```python
try:
    agent_task = asyncio.create_task(agent.run(steps))
    await agent_task
    
    # After agent completes, ensure we have a final report
    if not collected_data["final_report"]:
        collected_data["final_report"] = force_display_report()
        
    return collected_data["final_report"]
except Exception as e:
    logger.error(f"Error during batch execution: {str(e)}")
    return f"Error: {str(e)}\n\n{force_display_report()}"
```

## 3. Create a New API Endpoint with Test/Report Integration

Add a new endpoint in `api/index.py` for batch processing that integrates with the test and report creation workflow:

```python
class BatchAgentRequest(BaseModel):
    url: str  # The URL to test
    description: Optional[str] = None
    provider: str
    model_settings: ModelConfig
    agent_settings: Optional[AgentSettings] = None
    timeout: Optional[int] = 300
    user_id: str  # Authenticated user ID

@app.post("/api/batch/browser_agent", tags=["Agents"])
async def run_browser_agent_batch(
    request: BatchAgentRequest,
    user_id: str = Depends(get_current_user)
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
            supabase.table("tests") \
                .update({"status": "running"}) \
                .eq("id", test_id) \
                .execute()
                
            # Run the agent
            report = await asyncio.wait_for(
                browser_use_agent_batch(
                    model_config=model_config,
                    agent_settings=agent_settings,
                    history=chat_messages,
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
            supabase.table("tests") \
                .update({"status": "completed"}) \
                .eq("id", test_id) \
                .execute()
                
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
            
            # Update test status to "failed"
            supabase.table("tests") \
                .update({"status": "failed", "error": error_message}) \
                .eq("id", test_id) \
                .execute()
                
            # Still create a report with the error
            report_data = ReportCreate(
                test_id=test_id,
                content=f"ERROR: {error_message}",
                status="failed"
            )
            
            await create_report(report_data, user_id)
            
            # Update batch job status
            batch_job_status[test_id] = {
                "status": "failed",
                "message": error_message,
                "completed_at": datetime.now().isoformat()
            }
            
            return {
                "status": "error",
                "test_id": test_id,
                "message": error_message
            }
            
        except Exception as e:
            # Handle other exceptions
            error_message = f"Error during agent execution: {str(e)}"
            
            # Update test status to "failed"
            supabase.table("tests") \
                .update({"status": "failed", "error": error_message}) \
                .eq("id", test_id) \
                .execute()
                
            # Still create a report with the error
            report_data = ReportCreate(
                test_id=test_id,
                content=f"ERROR: {error_message}",
                status="failed"
            )
            
            await create_report(report_data, user_id)
            
            # Update batch job status
            batch_job_status[test_id] = {
                "status": "failed",
                "message": error_message,
                "completed_at": datetime.now().isoformat()
            }
            
            return {
                "status": "error",
                "test_id": test_id,
                "message": error_message
            }
            
    except Exception as e:
        logger.error(f"Error in batch browser agent: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }
```

## 4. Implement Resource Cleanup

Ensure proper resource cleanup in the batch agent function:

```python
finally:
    # Close browser and clean up resources
    if browser:
        try:
            await browser.close()
            logger.info(f"Browser closed for session {session_id}")
        except Exception as e:
            logger.error(f"Error closing browser: {str(e)}")
    
    # Remove from active browsers dictionary
    if session_id in active_browsers:
        del active_browsers[session_id]
    if session_id in active_browser_contexts:
        del active_browser_contexts[session_id]
    
    # Clean up session metrics
    if session_id in session_metrics_storage:
        # Optionally persist metrics somewhere
        # ...
        # Then clean up
        del session_metrics_storage[session_id]
```

## 5. Status Check Endpoint

Create a status check endpoint for monitoring batch jobs:

```python
# Keep track of batch job status
batch_job_status = {}

@app.get("/api/batch/status/{test_id}", tags=["Agents"])
async def check_batch_status(
    test_id: str,
    user_id: str = Depends(get_current_user)
):
    """
    Check the status of a batch browser agent job.
    """
    # Verify that the test belongs to the user
    test_result = supabase.table("tests") \
        .select("*") \
        .eq("id", test_id) \
        .eq("user_id", user_id) \
        .execute()
    
    if not test_result.data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test ID does not exist or does not belong to you"
        )
    
    # Get the test data
    test_data = test_result.data[0]
    
    # Return from batch_job_status if available, otherwise reconstruct from DB
    if test_id in batch_job_status:
        status_data = batch_job_status[test_id]
    else:
        # Reconstruct status from database
        status_data = {
            "status": test_data.get("status", "unknown"),
            "message": test_data.get("error") or f"Test status: {test_data.get('status', 'unknown')}",
            "created_at": test_data.get("created_at")
        }
    
    # Add test data to the response
    status_data["test"] = test_data
    
    # Get report data if available
    report_result = supabase.table("reports") \
        .select("*") \
        .eq("test_id", test_id) \
        .execute()
    
    if report_result.data:
        status_data["report"] = report_result.data[0]
    
    return status_data
```

## 6. Code Changes Summary

### 6.1 New Files to Create:
- `api/plugins/browser_use/batch_agent.py` (Optionally separate the batch implementation)
- Define `TestCreate`, `TestResponse`, `ReportCreate`, `ReportResponse` models

### 6.2 Files to Modify:
- `api/plugins/browser_use/agent.py` (Add batch functionality or import from it)
- `api/plugins/browser_use/__init__.py` (Export new batch function)
- `api/index.py` (Add new batch endpoint with test/report integration)
- `api/plugins/__init__.py` (Update WebAgentType to include batch if needed)

### 6.3 Changes to Existing Functions:
- Create batch versions of `yield_data` and `yield_done`
- Implement proper session cleanup
- Create timeout management
- Integrate with test and report creation functions

## 7. Implementation Steps

1. Define the data models for Test and Report if not already defined
2. Create the batch version of the browser agent function
3. Implement non-streaming data collection and reporting
4. Add the new API endpoint with test/report integration
5. Implement status tracking endpoint
6. Test with increasing timeouts (start small, then increase)
7. Add proper error handling and resource cleanup
8. Add documentation

## 8. Error Handling and Concurrency Considerations

- Ensure errors within `browser_use_agent_batch` are properly propagated or included in the report
- Implement transaction management for database operations (create test → create report)
- Use the session_id/test_id as unique keys in shared dictionaries for concurrency safety
- Add timeouts for database operations to prevent hanging
- Implement rate limiting if needed to prevent overloading the system
- Consider using a background job queue for very long-running jobs

This roadmap provides a comprehensive plan for implementing a non-streaming version of the browser agent that integrates with the test and report creation workflow. The agent runs to completion, and the results are stored in a database for future reference and analysis.

# Implementation Notes

## Step 1: Adding the Batch Agent Function
- Added `browser_use_agent_batch` to `api/plugins/browser_use/agent.py`
- Implemented non-streaming callbacks (`batch_yield_data` and `batch_yield_done`)
- Added proper resource cleanup in the finally block
- Used `collected_data` dictionary to store agent state instead of yielding
- Made sure to reuse existing report generation functions (`display_performance_report` and `force_display_report`)

## Step 2: Updating Plugin Exports
- Updated `api/plugins/browser_use/__init__.py` to export the new function
- Added the function to `__all__` list

## Step 3: Updating Agent Types
- Added `BROWSER_USE_BATCH` to the `WebAgentType` enum in `api/plugins/__init__.py`
- Updated the `get_web_agent` function to handle the new type
- Updated the return type annotation to include non-streaming returns
- Added a configuration for the batch agent in `AGENT_CONFIGS`

## Step 4: Creating Data Models
- Added Pydantic models to `api/schemas.py`:
  - `TestCreate` - For creating new test records
  - `TestResponse` - For test responses
  - `ReportCreate` - For creating new report records
  - `ReportResponse` - For report responses
  - `BatchAgentRequest` - For batch agent requests

## Step 5: Creating API Endpoints
- Added `batch_job_status` dictionary to track batch job status
- Added `/api/tests` endpoint for creating test records
- Added `/api/reports` endpoint for creating report records
- Added `/api/batch/browser_agent` endpoint for running the batch agent
- Added `/api/batch/status/{test_id}` endpoint for checking batch job status

## Key Differences from Streaming Version
1. Return type is `str` rather than `AsyncIterator[str]`
2. No use of `asyncio.Queue` or yielding results
3. Custom callbacks that store data instead of yielding
4. Direct `await agent.run(steps)` instead of handling via a queue
5. Properly closing browser resources in the finally block
6. Integration with test/report creation flow

## Testing Notes
1. Would need to test with increasing timeouts to ensure it works for longer jobs
2. Should verify resource cleanup works correctly
3. Need to ensure reports are generated consistently even on errors

## Things to Watch Out For
1. Make sure model imports are correct (had to add AgentSettings import)
2. Ensure timeouts are appropriate for the expected operation time
3. Resource cleanup is critical since there's no client keeping the connection alive
4. Error handling needs to be robust to capture and store all errors

## Future Improvements
1. Add proper database integration (currently using in-memory storage for demo)
2. Add background job processing for very long-running tasks
3. Add more detailed status reporting during the run
4. Improve error reporting and recovery
5. Add rate limiting to prevent system overload
