"""
Lifecycle Hooks for Test Flow Management.

This module provides a clean, structured way to hook into the browser automation
process at key points to capture test flow data and manage the testing lifecycle.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Awaitable
from functools import wraps
from datetime import datetime

from ..schemas import TestStepData, TestFlowStatus
from .test_flow_manager import test_flow_manager

logger = logging.getLogger(__name__)


class LifecycleHook:
    """Base class for lifecycle hooks."""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.hooks: List[Callable[..., Awaitable[Any]]] = []
    
    def register(self, func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        """Register a hook function."""
        self.hooks.append(func)
        return func
    
    async def execute(self, *args, **kwargs) -> List[Any]:
        """Execute all registered hooks."""
        results = []
        for hook in self.hooks:
            try:
                result = await hook(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Error executing hook {hook.__name__} in {self.name}: {str(e)}")
                results.append(None)
        return results


class TestFlowLifecycle:
    """
    Manages the lifecycle of test flows with hooks for key events.
    
    This class provides a clean interface for:
    - Starting test flows
    - Recording test steps
    - Handling step completion
    - Managing test flow state
    """
    
    def __init__(self):
        self.hooks = {
            'on_step_start': LifecycleHook('on_step_start', 'Called when a test step begins'),
            'on_step_end': LifecycleHook('on_step_end', 'Called when a test step completes'),
            'on_flow_start': LifecycleHook('on_flow_start', 'Called when a test flow begins'),
            'on_flow_end': LifecycleHook('on_flow_end', 'Called when a test flow completes'),
            'on_error': LifecycleHook('on_error', 'Called when an error occurs'),
            'on_metrics_capture': LifecycleHook('on_metrics_capture', 'Called when metrics are captured')
        }
        
        # Register default hooks
        self._register_default_hooks()
    
    def _register_default_hooks(self):
        """Register default hooks for test flow management."""
        
        @self.hooks['on_step_start'].register
        async def default_step_start_hook(session_id: str, url: str, action: str = None) -> Dict[str, Any]:
            """Default hook for step start - records step beginning."""
            try:
                logger.info(f"Step started for session {session_id}: {url} - {action}")
                return {
                    "timestamp": datetime.utcnow(),
                    "url": url,
                    "action": action,
                    "status": "started"
                }
            except Exception as e:
                logger.error(f"Error in default step start hook: {str(e)}")
                return {"error": str(e)}
        
        @self.hooks['on_step_end'].register
        async def default_step_end_hook(session_id: str, step_data: TestStepData) -> Dict[str, Any]:
            """Default hook for step end - records step completion and stores in test flow."""
            try:
                # Record the step in the test flow manager
                success = await test_flow_manager.record_step(session_id, step_data)
                
                if success:
                    logger.debug(f"Step recorded successfully for session {session_id}")
                    return {"status": "recorded", "step_count": 1}
                else:
                    logger.warning(f"Failed to record step for session {session_id}")
                    return {"status": "failed", "error": "Failed to record step"}
                    
            except Exception as e:
                logger.error(f"Error in default step end hook: {str(e)}")
                return {"error": str(e)}
        
        @self.hooks['on_flow_start'].register
        async def default_flow_start_hook(session_id: str, flow_name: str, user_request: str) -> Dict[str, Any]:
            """Default hook for flow start - initializes test flow."""
            try:
                from ..schemas import TestFlowRequest
                
                request = TestFlowRequest(
                    session_id=session_id,
                    flow_name=flow_name,
                    user_request=user_request
                )
                
                result = await test_flow_manager.start_test_flow(request)
                
                if result.status == "success":
                    logger.info(f"Test flow started for session {session_id}: {flow_name}")
                    return {"status": "started", "flow_name": flow_name}
                else:
                    logger.warning(f"Failed to start test flow for session {session_id}: {result.message}")
                    return {"status": "failed", "error": result.message}
                    
            except Exception as e:
                logger.error(f"Error in default flow start hook: {str(e)}")
                return {"error": str(e)}
        
        @self.hooks['on_flow_end'].register
        async def default_flow_end_hook(session_id: str, success: bool, summary: str = None) -> Dict[str, Any]:
            """Default hook for flow end - completes test flow."""
            try:
                result = await test_flow_manager.complete_test_flow(session_id, success, summary)
                
                if result.status == "success":
                    logger.info(f"Test flow completed for session {session_id}")
                    return {"status": "completed", "success": success}
                else:
                    logger.warning(f"Failed to complete test flow for session {session_id}: {result.message}")
                    return {"status": "failed", "error": result.message}
                    
            except Exception as e:
                logger.error(f"Error in default flow end hook: {str(e)}")
                return {"error": str(e)}
        
        @self.hooks['on_error'].register
        async def default_error_hook(session_id: str, error: Exception, context: str = None) -> Dict[str, Any]:
            """Default hook for error handling - logs and records errors."""
            try:
                error_msg = f"Error in {context or 'unknown context'}: {str(error)}"
                logger.error(f"Session {session_id}: {error_msg}")
                
                # Record error in test flow if available
                if session_id in test_flow_manager.active_flows:
                    flow = test_flow_manager.active_flows[session_id]
                    flow.metadata.status = TestFlowStatus.FAILED
                    flow.metadata.summary = f"Test failed: {error_msg}"
                
                return {"status": "error_recorded", "error": str(error)}
                
            except Exception as e:
                logger.error(f"Error in default error hook: {str(e)}")
                return {"error": str(e)}
    
    async def step_start(self, session_id: str, url: str, action: str = None) -> List[Any]:
        """Trigger step start hooks."""
        return await self.hooks['on_step_start'].execute(session_id, url, action)
    
    async def step_end(self, session_id: str, step_data: TestStepData) -> List[Any]:
        """Trigger step end hooks."""
        return await self.hooks['on_step_end'].execute(session_id, step_data)
    
    async def flow_start(self, session_id: str, flow_name: str, user_request: str) -> List[Any]:
        """Trigger flow start hooks."""
        return await self.hooks['on_flow_start'].execute(session_id, flow_name, user_request)
    
    async def flow_end(self, session_id: str, success: bool, summary: str = None) -> List[Any]:
        """Trigger flow end hooks."""
        return await self.hooks['on_flow_end'].execute(session_id, success, summary)
    
    async def error(self, session_id: str, error: Exception, context: str = None) -> List[Any]:
        """Trigger error hooks."""
        return await self.hooks['on_error'].execute(session_id, error, context)
    
    async def metrics_capture(self, session_id: str, metrics: Dict[str, Any]) -> List[Any]:
        """Trigger metrics capture hooks."""
        return await self.hooks['on_metrics_capture'].execute(session_id, metrics)


# Decorator for easy hook registration
def lifecycle_hook(hook_name: str):
    """
    Decorator to register a function as a lifecycle hook.
    
    Usage:
        @lifecycle_hook('on_step_start')
        async def my_step_start_hook(session_id: str, url: str, action: str):
            # Custom logic here
            pass
    """
    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        if hasattr(test_flow_lifecycle, 'hooks') and hook_name in test_flow_lifecycle.hooks:
            test_flow_lifecycle.hooks[hook_name].register(func)
        else:
            logger.warning(f"Unknown hook name: {hook_name}")
        return func
    return decorator


# Global instance for use across the application
test_flow_lifecycle = TestFlowLifecycle()


# Utility functions for common lifecycle operations
async def capture_step_metrics(session_id: str, url: str, action: str = None) -> TestStepData:
    """
    Capture metrics for a test step.
    
    This function should be called at the beginning of each test step
    to capture the current state and prepare for metrics collection.
    """
    start_time = time.time()
    
    step_data = TestStepData(
        url=url,
        action=action,
        timestamp=datetime.utcnow()
    )
    
    # Trigger step start hooks
    await test_flow_lifecycle.step_start(session_id, url, action)
    
    return step_data, start_time


async def complete_step_metrics(session_id: str, step_data: TestStepData, start_time: float, 
                               metrics: Dict[str, Any] = None, errors: List[str] = None) -> bool:
    """
    Complete metrics collection for a test step.
    
    This function should be called at the end of each test step
    to finalize the step data and record it in the test flow.
    """
    try:
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        step_data.duration_ms = duration_ms
        
        # Add metrics and errors
        if metrics:
            step_data.metrics = metrics
        if errors:
            step_data.errors = errors
        
        # Trigger step end hooks
        await test_flow_lifecycle.step_end(session_id, step_data)
        
        return True
        
    except Exception as e:
        logger.error(f"Error completing step metrics: {str(e)}")
        return False


async def start_test_flow(session_id: str, flow_name: str, user_request: str) -> bool:
    """
    Start a new test flow for a session.
    
    This function should be called when beginning a new test sequence.
    """
    try:
        await test_flow_lifecycle.flow_start(session_id, flow_name, user_request)
        return True
    except Exception as e:
        logger.error(f"Error starting test flow: {str(e)}")
        return False


async def end_test_flow(session_id: str, success: bool, summary: str = None) -> bool:
    """
    End a test flow for a session.
    
    This function should be called when completing a test sequence.
    """
    try:
        await test_flow_lifecycle.flow_end(session_id, success, summary)
        return True
    except Exception as e:
        logger.error(f"Error ending test flow: {str(e)}")
        return False


async def handle_test_error(session_id: str, error: Exception, context: str = None) -> None:
    """
    Handle errors during test execution.
    
    This function should be called when errors occur during testing.
    """
    try:
        await test_flow_lifecycle.error(session_id, error, context)
    except Exception as e:
        logger.error(f"Error handling test error: {str(e)}")


# Context manager for automatic test step management
class TestStepContext:
    """
    Context manager for automatic test step metrics collection.
    
    Usage:
        async with TestStepContext(session_id, url, "click_button") as step_data:
            # Perform test action here
            await page.click("#button")
            # Step will be automatically recorded when context exits
    """
    
    def __init__(self, session_id: str, url: str, action: str = None):
        self.session_id = session_id
        self.url = url
        self.action = action
        self.step_data = None
        self.start_time = None
    
    async def __aenter__(self):
        self.step_data, self.start_time = await capture_step_metrics(
            self.session_id, self.url, self.action
        )
        return self.step_data
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            # Error occurred, record it
            errors = [str(exc_val)] if exc_val else ["Unknown error"]
            await complete_step_metrics(
                self.session_id, self.step_data, self.start_time, errors=errors
            )
        else:
            # Success, complete normally
            await complete_step_metrics(
                self.session_id, self.step_data, self.start_time
            )
