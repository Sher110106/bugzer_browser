"""
Test Flow Actions System for Test Flow Management.

This module provides programmatic actions for managing test flows,
including starting, pausing, resuming, and completing test flows
with comprehensive error handling and validation.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta

from ..schemas import (
    TestFlowRequest, TestFlowResponse, TestFlowStatus,
    TestFlow, TestStepData
)
from .test_flow_manager import test_flow_manager
from .step_capture import step_data_capture

logger = logging.getLogger(__name__)


class TestFlowActions:
    """
    Comprehensive test flow actions system.
    
    This class provides:
    - Test flow lifecycle management
    - Step validation and error handling
    - Flow timeout and retry mechanisms
    - Bulk operations and batch processing
    """
    
    def __init__(self):
        self.default_timeout = 300  # 5 minutes
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
    
    async def start_test_flow(
        self, 
        session_id: str, 
        flow_name: str, 
        user_request: str,
        test_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        timeout: Optional[int] = None
    ) -> TestFlowResponse:
        """
        Start a new test flow with comprehensive validation.
        
        Args:
            session_id: The session ID to start the flow for
            flow_name: Name of the test flow
            user_request: Original user request that triggered the test
            test_id: Optional test identifier
            user_id: Optional user identifier
            tags: Optional tags for categorization
            timeout: Optional timeout in seconds
            
        Returns:
            TestFlowResponse with operation status
        """
        try:
            # Validate inputs
            if not session_id or not flow_name or not user_request:
                return TestFlowResponse(
                    status="error",
                    message="session_id, flow_name, and user_request are required"
                )
            
            # Check if session already has an active flow
            existing_flow = await test_flow_manager.get_test_flow_summary(session_id)
            if existing_flow and existing_flow.metadata.status in [TestFlowStatus.RUNNING, TestFlowStatus.PAUSED]:
                return TestFlowResponse(
                    status="warning",
                    message=f"Session {session_id} already has an active test flow: {existing_flow.metadata.name}",
                    flow_id=existing_flow.metadata.name,
                    data={"existing_flow": existing_flow.metadata.name}
                )
            
            # Create test flow request
            request = TestFlowRequest(
                session_id=session_id,
                flow_name=flow_name,
                user_request=user_request,
                test_id=test_id,
                user_id=user_id,
                tags=tags or []
            )
            
            # Start the test flow
            result = await test_flow_manager.start_test_flow(request)
            
            if result.status == "success":
                logger.info(f"Test flow '{flow_name}' started successfully for session {session_id}")
                
                # Set up timeout monitoring if specified
                if timeout:
                    asyncio.create_task(self._monitor_flow_timeout(session_id, timeout))
                
                return result
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error starting test flow: {str(e)}")
            return TestFlowResponse(
                status="error",
                message=f"Failed to start test flow: {str(e)}"
            )
    
    async def pause_test_flow(self, session_id: str, reason: str = None) -> TestFlowResponse:
        """
        Pause an active test flow.
        
        Args:
            session_id: The session ID to pause
            reason: Optional reason for pausing
            
        Returns:
            TestFlowResponse with operation status
        """
        try:
            if not session_id:
                return TestFlowResponse(
                    status="error",
                    message="session_id is required"
                )
            
            # Get current flow status
            flow = await test_flow_manager.get_test_flow_summary(session_id)
            if not flow:
                return TestFlowResponse(
                    status="error",
                    message=f"No test flow found for session {session_id}"
                )
            
            if flow.metadata.status != TestFlowStatus.RUNNING:
                return TestFlowResponse(
                    status="warning",
                    message=f"Test flow is not running (current status: {flow.metadata.status.value})"
                )
            
            # Pause the flow
            result = await test_flow_manager.pause_test_flow(session_id)
            
            if result.status == "success":
                logger.info(f"Test flow paused for session {session_id}. Reason: {reason or 'User requested'}")
                
                # Add pause reason to flow metadata if provided
                if reason and flow.metadata.summary:
                    flow.metadata.summary += f" [Paused: {reason}]"
                
                return result
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error pausing test flow: {str(e)}")
            return TestFlowResponse(
                status="error",
                message=f"Failed to pause test flow: {str(e)}"
            )
    
    async def resume_test_flow(self, session_id: str) -> TestFlowResponse:
        """
        Resume a paused test flow.
        
        Args:
            session_id: The session ID to resume
            
        Returns:
            TestFlowResponse with operation status
        """
        try:
            if not session_id:
                return TestFlowResponse(
                    status="error",
                    message="session_id is required"
                )
            
            # Get current flow status
            flow = await test_flow_manager.get_test_flow_summary(session_id)
            if not flow:
                return TestFlowResponse(
                    status="error",
                    message=f"No test flow found for session {session_id}"
                )
            
            if flow.metadata.status != TestFlowStatus.PAUSED:
                return TestFlowResponse(
                    status="warning",
                    message=f"Test flow is not paused (current status: {flow.metadata.status.value})"
                )
            
            # Resume the flow
            result = await test_flow_manager.resume_test_flow(session_id)
            
            if result.status == "success":
                logger.info(f"Test flow resumed for session {session_id}")
                return result
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error resuming test flow: {str(e)}")
            return TestFlowResponse(
                status="error",
                message=f"Failed to resume test flow: {str(e)}"
            )
    
    async def complete_test_flow(
        self, 
        session_id: str, 
        success: bool, 
        summary: str = None,
        force: bool = False
    ) -> TestFlowResponse:
        """
        Complete a test flow with validation.
        
        Args:
            session_id: The session ID to complete
            success: Whether the test flow was successful
            summary: Optional summary of the test flow
            force: Force completion even if flow is paused
            
        Returns:
            TestFlowResponse with operation status
        """
        try:
            if not session_id:
                return TestFlowResponse(
                    status="error",
                    message="session_id is required"
                )
            
            # Get current flow status
            flow = await test_flow_manager.get_test_flow_summary(session_id)
            if not flow:
                return TestFlowResponse(
                    status="error",
                    message=f"No test flow found for session {session_id}"
                )
            
            # Check if flow can be completed
            if not force and flow.metadata.status == TestFlowStatus.PAUSED:
                return TestFlowResponse(
                    status="warning",
                    message=f"Test flow is paused. Use force=True to complete anyway."
                )
            
            # Complete the flow
            result = await test_flow_manager.complete_test_flow(session_id, success, summary)
            
            if result.status == "success":
                status_text = "completed successfully" if success else "completed with failures"
                logger.info(f"Test flow {status_text} for session {session_id}")
                return result
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error completing test flow: {str(e)}")
            return TestFlowResponse(
                status="error",
                message=f"Failed to complete test flow: {str(e)}"
            )
    
    async def record_test_step(
        self,
        session_id: str,
        url: str,
        action: str = None,
        metrics: Optional[Dict[str, Any]] = None,
        errors: Optional[List[str]] = None,
        capture_options: Optional[Dict[str, bool]] = None
    ) -> TestFlowResponse:
        """
        Record a test step with comprehensive data capture.
        
        Args:
            session_id: The session ID to record the step for
            url: The URL of the current page
            action: The action being performed
            metrics: Optional metrics to override captured ones
            errors: Optional errors to record
            capture_options: Override default capture options
            
        Returns:
            TestFlowResponse with operation status
        """
        try:
            if not session_id or not url:
                return TestFlowResponse(
                    status="error",
                    message="session_id and url are required"
                )
            
            # Check if flow exists and is active
            flow = await test_flow_manager.get_test_flow_summary(session_id)
            if not flow:
                return TestFlowResponse(
                    status="error",
                    message=f"No test flow found for session {session_id}"
                )
            
            if flow.metadata.status not in [TestFlowStatus.RUNNING, TestFlowStatus.PAUSED]:
                return TestFlowResponse(
                    status="warning",
                    message=f"Test flow is not active (current status: {flow.metadata.status.value})"
                )
            
            # Capture step metrics
            step_data, start_time = await step_data_capture.capture_step_metrics(
                session_id, url, action, capture_options
            )
            
            # Override with provided metrics/errors
            if metrics:
                step_data.metrics = metrics
            
            if errors:
                step_data.errors = errors
            
            # Complete the step capture
            success = await step_data_capture.complete_step_capture(
                session_id, step_data, start_time, metrics, errors
            )
            
            if success:
                return TestFlowResponse(
                    status="success",
                    message=f"Test step recorded successfully for {url}",
                    data={"step_count": flow.metadata.total_steps + 1}
                )
            else:
                return TestFlowResponse(
                    status="error",
                    message="Failed to record test step"
                )
                
        except Exception as e:
            logger.error(f"Error recording test step: {str(e)}")
            return TestFlowResponse(
                status="error",
                message=f"Failed to record test step: {str(e)}"
            )
    
    async def get_test_flow_summary(self, session_id: str) -> TestFlowResponse:
        """
        Get comprehensive test flow summary.
        
        Args:
            session_id: The session ID to get summary for
            
        Returns:
            TestFlowResponse with flow data
        """
        try:
            if not session_id:
                return TestFlowResponse(
                    status="error",
                    message="session_id is required"
                )
            
            flow = await test_flow_manager.get_test_flow_summary(session_id)
            
            if not flow:
                return TestFlowResponse(
                    status="not_found",
                    message=f"No test flow found for session {session_id}"
                )
            
            return TestFlowResponse(
                status="success",
                message="Test flow summary retrieved successfully",
                data={"flow": flow}
            )
            
        except Exception as e:
            logger.error(f"Error getting test flow summary: {str(e)}")
            return TestFlowResponse(
                status="error",
                message=f"Failed to get test flow summary: {str(e)}"
            )
    
    async def export_test_report(
        self, 
        session_id: str, 
        format: str = "json",
        include_screenshots: bool = True
    ) -> TestFlowResponse:
        """
        Export test flow report with options.
        
        Args:
            session_id: The session ID to export
            format: Export format (json, html, markdown)
            include_screenshots: Whether to include screenshots in export
            
        Returns:
            TestFlowResponse with export data
        """
        try:
            if not session_id:
                return TestFlowResponse(
                    status="error",
                    message="session_id is required"
                )
            
            if format not in ["json", "html", "markdown"]:
                return TestFlowResponse(
                    status="error",
                    message=f"Unsupported format: {format}. Use: json, html, markdown"
                )
            
            # Get the flow to check if screenshots should be included
            flow = await test_flow_manager.get_test_flow_summary(session_id)
            if not flow:
                return TestFlowResponse(
                    status="not_found",
                    message=f"No test flow found for session {session_id}"
                )
            
            # Export the report
            report_content = await test_flow_manager.export_test_report(session_id, format)
            
            return TestFlowResponse(
                status="success",
                message=f"Test report exported successfully in {format.upper()} format",
                data={
                    "format": format,
                    "content": report_content,
                    "content_length": len(report_content),
                    "flow_name": flow.metadata.name
                }
            )
            
        except Exception as e:
            logger.error(f"Error exporting test report: {str(e)}")
            return TestFlowResponse(
                status="error",
                message=f"Failed to export test report: {str(e)}"
            )
    
    async def bulk_operations(
        self, 
        operations: List[Dict[str, Any]]
    ) -> List[TestFlowResponse]:
        """
        Perform multiple test flow operations in batch.
        
        Args:
            operations: List of operation dictionaries
            
        Returns:
            List of TestFlowResponse objects
        """
        results = []
        
        for operation in operations:
            try:
                op_type = operation.get("type")
                session_id = operation.get("session_id")
                
                if not op_type or not session_id:
                    results.append(TestFlowResponse(
                        status="error",
                        message="Operation type and session_id are required"
                    ))
                    continue
                
                # Execute operation based on type
                if op_type == "start":
                    result = await self.start_test_flow(
                        session_id=session_id,
                        flow_name=operation.get("flow_name"),
                        user_request=operation.get("user_request"),
                        test_id=operation.get("test_id"),
                        user_id=operation.get("user_id"),
                        tags=operation.get("tags")
                    )
                elif op_type == "pause":
                    result = await self.pause_test_flow(
                        session_id=session_id,
                        reason=operation.get("reason")
                    )
                elif op_type == "resume":
                    result = await self.resume_test_flow(session_id)
                elif op_type == "complete":
                    result = await self.complete_test_flow(
                        session_id=session_id,
                        success=operation.get("success", True),
                        summary=operation.get("summary"),
                        force=operation.get("force", False)
                    )
                elif op_type == "record_step":
                    result = await self.record_test_step(
                        session_id=session_id,
                        url=operation.get("url"),
                        action=operation.get("action"),
                        metrics=operation.get("metrics"),
                        errors=operation.get("errors")
                    )
                else:
                    result = TestFlowResponse(
                        status="error",
                        message=f"Unknown operation type: {op_type}"
                    )
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error in bulk operation: {str(e)}")
                results.append(TestFlowResponse(
                    status="error",
                    message=f"Operation failed: {str(e)}"
                ))
        
        return results
    
    async def _monitor_flow_timeout(self, session_id: str, timeout: int) -> None:
        """
        Monitor a test flow for timeout and auto-complete if needed.
        
        Args:
            session_id: The session ID to monitor
            timeout: Timeout in seconds
        """
        try:
            await asyncio.sleep(timeout)
            
            # Check if flow is still running
            flow = await test_flow_manager.get_test_flow_summary(session_id)
            if flow and flow.metadata.status == TestFlowStatus.RUNNING:
                logger.warning(f"Test flow for session {session_id} timed out after {timeout} seconds")
                
                # Auto-complete the flow with timeout status
                await test_flow_manager.complete_test_flow(
                    session_id, 
                    success=False, 
                    summary=f"Test flow timed out after {timeout} seconds"
                )
                
        except Exception as e:
            logger.error(f"Error monitoring flow timeout: {str(e)}")
    
    async def cleanup_expired_flows(self, max_age_hours: int = 24) -> TestFlowResponse:
        """
        Clean up expired test flows.
        
        Args:
            max_age_hours: Maximum age in hours to keep flows
            
        Returns:
            TestFlowResponse with cleanup results
        """
        try:
            cleaned_count = await test_flow_manager.cleanup_old_flows(max_age_hours)
            
            return TestFlowResponse(
                status="success",
                message=f"Cleaned up {cleaned_count} expired test flows",
                data={"cleaned_count": cleaned_count}
            )
            
        except Exception as e:
            logger.error(f"Error cleaning up expired flows: {str(e)}")
            return TestFlowResponse(
                status="error",
                message=f"Failed to cleanup expired flows: {str(e)}"
            )
    
    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status.
        
        Returns:
            Dict containing system status information
        """
        try:
            active_flows = test_flow_manager.get_active_flows_count()
            completed_flows = test_flow_manager.get_completed_flows_count()
            
            # Get some sample flow information
            sample_flows = []
            for session_id, flow in list(test_flow_manager.active_flows.items())[:5]:
                sample_flows.append({
                    "session_id": session_id,
                    "name": flow.metadata.name,
                    "status": flow.metadata.status.value,
                    "steps": flow.metadata.total_steps,
                    "start_time": flow.metadata.start_time.isoformat()
                })
            
            return {
                "status": "healthy",
                "active_flows": active_flows,
                "completed_flows": completed_flows,
                "sample_active_flows": sample_flows,
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0"
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Global instance for use across the application
test_flow_actions = TestFlowActions()
