"""
Flow State Management System for Test Flow Management.

This module provides comprehensive state management for test flows,
including status tracking, validation, error handling, and recovery mechanisms.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from enum import Enum

from ..schemas import TestFlow, TestFlowStatus, TestStepData
from .test_flow_manager import test_flow_manager

logger = logging.getLogger(__name__)


class FlowValidationLevel(str, Enum):
    """Levels of validation for test flows."""
    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"


class FlowStateManager:
    """
    Comprehensive flow state management system.
    
    This class handles:
    - Flow state tracking and validation
    - Error detection and recovery
    - Flow timeout and retry mechanisms
    - State consistency checks
    """
    
    def __init__(self):
        self.flow_states: Dict[str, Dict[str, Any]] = {}
        self.flow_locks: Dict[str, asyncio.Lock] = {}
        self.flow_timeouts: Dict[str, asyncio.Task] = {}
        self.retry_counts: Dict[str, int] = {}
        self.max_retries = 3
        self.default_timeout = 300  # 5 minutes
        self.cleanup_interval = 60  # 1 minute
        self._cleanup_task = None
    
    async def initialize_flow_state(self, session_id: str, flow: TestFlow) -> bool:
        """
        Initialize state tracking for a new test flow.
        
        Args:
            session_id: The session ID
            flow: The test flow object
            
        Returns:
            bool: True if initialization was successful
        """
        try:
            # Create flow state entry
            self.flow_states[session_id] = {
                "flow": flow,
                "status": flow.metadata.status,
                "start_time": datetime.utcnow(),
                "last_activity": datetime.utcnow(),
                "step_count": 0,
                "error_count": 0,
                "retry_count": 0,
                "validation_level": FlowValidationLevel.STANDARD,
                "timeout_seconds": self.default_timeout,
                "is_monitored": True
            }
            
            # Create lock for this flow
            self.flow_locks[session_id] = asyncio.Lock()
            
            # Initialize retry count
            self.retry_counts[session_id] = 0
            
            # Set up timeout monitoring
            await self._setup_flow_timeout(session_id)
            
            # Start cleanup task if not already running
            if self._cleanup_task is None:
                self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            
            logger.info(f"Flow state initialized for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing flow state: {str(e)}")
            return False
    
    async def update_flow_state(
        self, 
        session_id: str, 
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update the state of a test flow.
        
        Args:
            session_id: The session ID
            updates: Dictionary of updates to apply
            
        Returns:
            bool: True if update was successful
        """
        try:
            if session_id not in self.flow_states:
                logger.warning(f"No flow state found for session {session_id}")
                return False
            
            # Acquire lock for thread-safe updates
            async with self.flow_locks[session_id]:
                state = self.flow_states[session_id]
                
                # Apply updates
                for key, value in updates.items():
                    if key in state:
                        state[key] = value
                    else:
                        logger.warning(f"Unknown state key: {key}")
                
                # Update last activity
                state["last_activity"] = datetime.utcnow()
                
                # Update step count if flow object exists
                if "flow" in state and state["flow"]:
                    state["step_count"] = state["flow"].metadata.total_steps
                
                logger.debug(f"Flow state updated for session {session_id}: {updates}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating flow state: {str(e)}")
            return False
    
    async def get_flow_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current state of a test flow.
        
        Args:
            session_id: The session ID
            
        Returns:
            Dict containing flow state or None if not found
        """
        try:
            return self.flow_states.get(session_id)
        except Exception as e:
            logger.error(f"Error getting flow state: {str(e)}")
            return None
    
    async def validate_flow_state(self, session_id: str, level: FlowValidationLevel = None) -> Dict[str, Any]:
        """
        Validate the current state of a test flow.
        
        Args:
            session_id: The session ID
            level: Validation level to use
            
        Returns:
            Dict containing validation results
        """
        try:
            if session_id not in self.flow_states:
                return {
                    "valid": False,
                    "errors": ["No flow state found"],
                    "warnings": []
                }
            
            state = self.flow_states[session_id]
            validation_level = level or state.get("validation_level", FlowValidationLevel.STANDARD)
            
            errors = []
            warnings = []
            
            # Basic validation (always performed)
            if not state.get("flow"):
                errors.append("No flow object in state")
            
            if not state.get("start_time"):
                errors.append("No start time recorded")
            
            # Standard validation
            if validation_level in [FlowValidationLevel.STANDARD, FlowValidationLevel.STRICT]:
                if state.get("error_count", 0) > 10:
                    warnings.append("High error count detected")
                
                if state.get("retry_count", 0) > self.max_retries:
                    errors.append("Maximum retry count exceeded")
                
                # Check for stale flows
                last_activity = state.get("last_activity")
                if last_activity:
                    time_since_activity = datetime.utcnow() - last_activity
                    if time_since_activity > timedelta(minutes=30):
                        warnings.append("Flow appears to be stale (no activity for 30+ minutes)")
            
            # Strict validation
            if validation_level == FlowValidationLevel.STRICT:
                flow = state.get("flow")
                if flow:
                    if flow.metadata.total_steps == 0:
                        warnings.append("Flow has no recorded steps")
                    
                    # Check if flow has been running too long (handle both enum and string)
                    flow_status = flow.metadata.status
                    if (hasattr(flow_status, 'value') and flow_status.value == TestFlowStatus.RUNNING.value) or \
                       (isinstance(flow_status, str) and flow_status == TestFlowStatus.RUNNING.value):
                        start_time = state.get("start_time")
                        if start_time:
                            running_time = datetime.utcnow() - start_time
                            if running_time > timedelta(hours=2):
                                warnings.append("Flow has been running for over 2 hours")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "validation_level": validation_level.value,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error validating flow state: {str(e)}")
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": []
            }
    
    async def handle_flow_error(
        self, 
        session_id: str, 
        error: Exception, 
        context: str = None
    ) -> Dict[str, Any]:
        """
        Handle errors that occur during test flow execution.
        
        Args:
            session_id: The session ID
            error: The error that occurred
            context: Context where the error occurred
            
        Returns:
            Dict containing error handling results
        """
        try:
            if session_id not in self.flow_states:
                return {
                    "handled": False,
                    "error": "No flow state found"
                }
            
            async with self.flow_locks[session_id]:
                state = self.flow_states[session_id]
                
                # Increment error count
                state["error_count"] = state.get("error_count", 0) + 1
                
                # Log the error
                error_msg = f"Error in {context or 'unknown context'}: {str(error)}"
                logger.error(f"Session {session_id}: {error_msg}")
                
                # Determine if we should retry
                should_retry = await self._should_retry_flow(session_id, error)
                
                if should_retry:
                    # Increment retry count
                    state["retry_count"] = state.get("retry_count", 0) + 1
                    self.retry_counts[session_id] = state["retry_count"]
                    
                    # Schedule retry
                    await self._schedule_flow_retry(session_id, error)
                    
                    return {
                        "handled": True,
                        "action": "retry_scheduled",
                        "retry_count": state["retry_count"],
                        "max_retries": self.max_retries
                    }
                else:
                    # Mark flow as failed
                    if state.get("flow"):
                        state["flow"].metadata.status = TestFlowStatus.FAILED
                        state["flow"].metadata.summary = f"Test failed: {error_msg}"
                    
                    return {
                        "handled": True,
                        "action": "flow_marked_failed",
                        "error": error_msg
                    }
                
        except Exception as e:
            logger.error(f"Error handling flow error: {str(e)}")
            return {
                "handled": False,
                "error": f"Error handling error: {str(e)}"
            }
    
    async def _should_retry_flow(self, session_id: str, error: Exception) -> bool:
        """
        Determine if a flow should be retried based on error type and retry count.
        
        Args:
            session_id: The session ID
            error: The error that occurred
            
        Returns:
            bool: True if flow should be retried
        """
        try:
            current_retries = self.retry_counts.get(session_id, 0)
            
            # Don't retry if we've exceeded max retries
            if current_retries >= self.max_retries:
                return False
            
            # Don't retry certain types of errors
            error_str = str(error).lower()
            non_retryable_errors = [
                "authentication failed",
                "permission denied",
                "invalid session",
                "flow not found"
            ]
            
            for non_retryable in non_retryable_errors:
                if non_retryable in error_str:
                    return False
            
            # Retry for transient errors
            transient_errors = [
                "timeout",
                "connection error",
                "temporary failure",
                "rate limit exceeded"
            ]
            
            for transient in transient_errors:
                if transient in error_str:
                    return True
            
            # Default to retrying for other errors
            return True
            
        except Exception as e:
            logger.error(f"Error determining retry decision: {str(e)}")
            return False
    
    async def _schedule_flow_retry(self, session_id: str, error: Exception) -> None:
        """
        Schedule a retry for a failed flow.
        
        Args:
            session_id: The session ID
            error: The error that occurred
        """
        try:
            # Calculate retry delay (exponential backoff)
            retry_count = self.retry_counts.get(session_id, 0)
            delay = min(2 ** retry_count, 60)  # Max 60 seconds
            
            logger.info(f"Scheduling retry {retry_count + 1} for session {session_id} in {delay} seconds")
            
            # Schedule the retry
            asyncio.create_task(self._execute_flow_retry(session_id, delay))
            
        except Exception as e:
            logger.error(f"Error scheduling flow retry: {str(e)}")
    
    async def _execute_flow_retry(self, session_id: str, delay: int) -> None:
        """
        Execute a scheduled flow retry.
        
        Args:
            session_id: The session ID
            delay: Delay before retry in seconds
        """
        try:
            # Wait for the delay
            await asyncio.sleep(delay)
            
            # Check if flow still exists and should be retried
            if session_id not in self.flow_states:
                return
            
            state = self.flow_states[session_id]
            if not state.get("is_monitored", True):
                return
            
            # Attempt to resume the flow
            flow = state.get("flow")
            if flow and flow.metadata.status == TestFlowStatus.FAILED:
                logger.info(f"Executing retry for session {session_id}")
                
                # Reset status to running
                flow.metadata.status = TestFlowStatus.RUNNING
                
                # Update state
                await self.update_flow_state(session_id, {
                    "status": TestFlowStatus.RUNNING,
                    "last_activity": datetime.utcnow()
                })
                
        except Exception as e:
            logger.error(f"Error executing flow retry: {str(e)}")
    
    async def _setup_flow_timeout(self, session_id: str) -> None:
        """
        Set up timeout monitoring for a flow.
        
        Args:
            session_id: The session ID
        """
        try:
            state = self.flow_states.get(session_id)
            if not state:
                return
            
            timeout_seconds = state.get("timeout_seconds", self.default_timeout)
            
            # Create timeout task
            timeout_task = asyncio.create_task(self._monitor_flow_timeout(session_id, timeout_seconds))
            self.flow_timeouts[session_id] = timeout_task
            
        except Exception as e:
            logger.error(f"Error setting up flow timeout: {str(e)}")
    
    async def _monitor_flow_timeout(self, session_id: str, timeout_seconds: int) -> None:
        """
        Monitor a flow for timeout.
        
        Args:
            session_id: The session ID
            timeout_seconds: Timeout in seconds
        """
        try:
            await asyncio.sleep(timeout_seconds)
            
            # Check if flow is still running
            if session_id in self.flow_states:
                state = self.flow_states[session_id]
                flow = state.get("flow")
                
                if flow:
                    # Check if flow is running (handle both enum and string)
                    flow_status = flow.metadata.status
                    is_running = (hasattr(flow_status, 'value') and flow_status.value == TestFlowStatus.RUNNING.value) or \
                               (isinstance(flow_status, str) and flow_status == TestFlowStatus.RUNNING.value)
                    
                    if is_running:
                        logger.warning(f"Flow for session {session_id} timed out after {timeout_seconds} seconds")
                        
                        # Mark flow as failed due to timeout
                        flow.metadata.status = TestFlowStatus.TIMEOUT
                        flow.metadata.summary = f"Test flow timed out after {timeout_seconds} seconds"
                        
                        # Update state
                        await self.update_flow_state(session_id, {
                            "status": TestFlowStatus.TIMEOUT
                        })
                    
        except Exception as e:
            logger.error(f"Error monitoring flow timeout: {str(e)}")
    
    async def _periodic_cleanup(self) -> None:
        """Periodically clean up expired and completed flows."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired_flows()
                
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {str(e)}")
    
    async def _cleanup_expired_flows(self) -> None:
        """Clean up expired and completed flows."""
        try:
            current_time = datetime.utcnow()
            flows_to_remove = []
            
            for session_id, state in self.flow_states.items():
                try:
                    # Remove flows that have been completed for more than 1 hour
                    if state.get("status") in [TestFlowStatus.COMPLETED, TestFlowStatus.FAILED, TestFlowStatus.TIMEOUT]:
                        last_activity = state.get("last_activity")
                        if last_activity and (current_time - last_activity) > timedelta(hours=1):
                            flows_to_remove.append(session_id)
                    
                    # Remove flows that have been stale for more than 2 hours
                    elif state.get("status") == TestFlowStatus.RUNNING:
                        start_time = state.get("start_time")
                        if start_time and (current_time - start_time) > timedelta(hours=2):
                            flows_to_remove.append(session_id)
                
                except Exception as e:
                    logger.warning(f"Error checking flow {session_id} for cleanup: {str(e)}")
                    flows_to_remove.append(session_id)
            
            # Remove expired flows
            for session_id in flows_to_remove:
                await self._remove_flow_state(session_id)
                
            if flows_to_remove:
                logger.info(f"Cleaned up {len(flows_to_remove)} expired flows")
                
        except Exception as e:
            logger.error(f"Error cleaning up expired flows: {str(e)}")
    
    async def _remove_flow_state(self, session_id: str) -> None:
        """
        Remove a flow state and clean up associated resources.
        
        Args:
            session_id: The session ID
        """
        try:
            # Cancel timeout task if it exists
            if session_id in self.flow_timeouts:
                timeout_task = self.flow_timeouts[session_id]
                if not timeout_task.done():
                    timeout_task.cancel()
                del self.flow_timeouts[session_id]
            
            # Remove retry count
            if session_id in self.retry_counts:
                del self.retry_counts[session_id]
            
            # Remove lock
            if session_id in self.flow_locks:
                del self.flow_locks[session_id]
            
            # Remove state
            if session_id in self.flow_states:
                del self.flow_states[session_id]
                
        except Exception as e:
            logger.error(f"Error removing flow state: {str(e)}")
    
    async def get_system_health(self) -> Dict[str, Any]:
        """
        Get overall system health information.
        
        Returns:
            Dict containing system health data
        """
        try:
            total_flows = len(self.flow_states)
            active_flows = sum(1 for state in self.flow_states.values() 
                             if state.get("status") == TestFlowStatus.RUNNING)
            failed_flows = sum(1 for state in self.flow_states.values() 
                             if state.get("status") in [TestFlowStatus.FAILED, TestFlowStatus.TIMEOUT])
            
            # Check for potential issues
            warnings = []
            if failed_flows > total_flows * 0.2:  # More than 20% failure rate
                warnings.append("High failure rate detected")
            
            if total_flows > 100:  # Too many flows
                warnings.append("High number of flows may impact performance")
            
            return {
                "status": "healthy" if len(warnings) == 0 else "warning",
                "total_flows": total_flows,
                "active_flows": active_flows,
                "failed_flows": failed_flows,
                "warnings": warnings,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system health: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Global instance for use across the application
flow_state_manager = FlowStateManager()
