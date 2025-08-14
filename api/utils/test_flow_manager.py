"""
Test Flow Manager for structured browser automation testing.

This module provides a comprehensive system for managing test flows,
capturing step-by-step data, and generating detailed test reports.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, AsyncIterator
from pydantic import BaseModel

from ..schemas import (
    TestFlow, TestFlowMetadata, TestStepData, TestFlowStatus,
    TestFlowRequest, TestFlowResponse
)

logger = logging.getLogger(__name__)


class TestFlowManager:
    """
    Manages test flows for browser automation testing.
    
    This class handles:
    - Test flow lifecycle (start, pause, resume, complete)
    - Step-by-step data collection
    - Performance metrics aggregation
    - Test flow reporting and export
    """
    
    def __init__(self):
        self.active_flows: Dict[str, TestFlow] = {}
        self.completed_flows: Dict[str, TestFlow] = {}
        self.flow_locks: Dict[str, asyncio.Lock] = {}
        
    async def start_test_flow(self, request: TestFlowRequest) -> TestFlowResponse:
        """
        Start a new test flow for a session.
        
        Args:
            request: TestFlowRequest containing flow initialization data
            
        Returns:
            TestFlowResponse with flow status and ID
        """
        try:
            # Check if session already has an active flow
            if request.session_id in self.active_flows:
                existing_flow = self.active_flows[request.session_id]
                if existing_flow.metadata.status == TestFlowStatus.RUNNING:
                    return TestFlowResponse(
                        status="error",
                        message=f"Session {request.session_id} already has an active test flow: {existing_flow.metadata.name}",
                        flow_id=existing_flow.metadata.name
                    )
            
            # Create new test flow
            flow_id = str(uuid.uuid4())
            metadata = TestFlowMetadata(
                name=request.flow_name,
                user_request=request.user_request,
                test_id=request.test_id,
                user_id=request.user_id,
                tags=request.tags or []
            )
            
            test_flow = TestFlow(
                session_id=request.session_id,
                metadata=metadata
            )
            
            # Store the flow and create a lock for it
            self.active_flows[request.session_id] = test_flow
            self.flow_locks[request.session_id] = asyncio.Lock()
            
            logger.info(f"Started test flow '{request.flow_name}' for session {request.session_id}")
            
            return TestFlowResponse(
                status="success",
                message=f"Test flow '{request.flow_name}' started successfully",
                flow_id=flow_id,
                data={"flow_name": request.flow_name}
            )
            
        except Exception as e:
            logger.error(f"Failed to start test flow: {str(e)}")
            return TestFlowResponse(
                status="error",
                message=f"Failed to start test flow: {str(e)}"
            )
    
    async def record_step(self, session_id: str, step_data: TestStepData) -> bool:
        """
        Record a step in the active test flow.
        
        Args:
            session_id: The session ID to record the step for
            step_data: TestStepData containing step information
            
        Returns:
            bool: True if step was recorded successfully, False otherwise
        """
        try:
            if session_id not in self.active_flows:
                logger.warning(f"No active test flow found for session {session_id}")
                return False
            
            flow = self.active_flows[session_id]
            
            # Update step count
            flow.metadata.total_steps += 1
            
            # Add step to flow
            flow.steps.append(step_data)
            
            # Update success/failure counts
            if step_data.errors and len(step_data.errors) > 0:
                flow.metadata.failed_steps += 1
            else:
                flow.metadata.successful_steps += 1
            
            logger.debug(f"Recorded step {len(flow.steps)} for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to record step for session {session_id}: {str(e)}")
            return False
    
    async def complete_test_flow(self, session_id: str, success: bool, summary: str = None) -> TestFlowResponse:
        """
        Complete a test flow and move it to completed flows.
        
        Args:
            session_id: The session ID to complete
            success: Whether the test flow was successful
            summary: Optional summary of the test flow
            
        Returns:
            TestFlowResponse with completion status
        """
        try:
            if session_id not in self.active_flows:
                return TestFlowResponse(
                    status="error",
                    message=f"No active test flow found for session {session_id}"
                )
            
            flow = self.active_flows[session_id]
            
            # Update flow metadata
            flow.metadata.end_time = datetime.utcnow()
            flow.metadata.status = TestFlowStatus.COMPLETED if success else TestFlowStatus.FAILED
            flow.metadata.summary = summary
            
            # Generate performance summary
            await self._generate_performance_summary(flow)
            
            # Move to completed flows
            self.completed_flows[session_id] = flow
            del self.active_flows[session_id]
            
            # Clean up lock
            if session_id in self.flow_locks:
                del self.flow_locks[session_id]
            
            logger.info(f"Completed test flow '{flow.metadata.name}' for session {session_id}")
            
            return TestFlowResponse(
                status="success",
                message=f"Test flow completed successfully",
                flow_id=flow.metadata.name,
                data={"status": flow.metadata.status.value}
            )
            
        except Exception as e:
            logger.error(f"Failed to complete test flow for session {session_id}: {str(e)}")
            return TestFlowResponse(
                status="error",
                message=f"Failed to complete test flow: {str(e)}"
            )
    
    async def pause_test_flow(self, session_id: str) -> TestFlowResponse:
        """
        Pause an active test flow.
        
        Args:
            session_id: The session ID to pause
            
        Returns:
            TestFlowResponse with pause status
        """
        try:
            if session_id not in self.active_flows:
                return TestFlowResponse(
                    status="error",
                    message=f"No active test flow found for session {session_id}"
                )
            
            flow = self.active_flows[session_id]
            flow.metadata.status = TestFlowStatus.PAUSED
            
            logger.info(f"Paused test flow '{flow.metadata.name}' for session {session_id}")
            
            return TestFlowResponse(
                status="success",
                message="Test flow paused successfully",
                flow_id=flow.metadata.name
            )
            
        except Exception as e:
            logger.error(f"Failed to pause test flow for session {session_id}: {str(e)}")
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
            TestFlowResponse with resume status
        """
        try:
            if session_id not in self.active_flows:
                return TestFlowResponse(
                    status="error",
                    message=f"No active test flow found for session {session_id}"
                )
            
            flow = self.active_flows[session_id]
            if flow.metadata.status != TestFlowStatus.PAUSED:
                return TestFlowResponse(
                    status="error",
                    message=f"Test flow is not paused (current status: {flow.metadata.status.value})"
                )
            
            flow.metadata.status = TestFlowStatus.RUNNING
            
            logger.info(f"Resumed test flow '{flow.metadata.name}' for session {session_id}")
            
            return TestFlowResponse(
                status="success",
                message="Test flow resumed successfully",
                flow_id=flow.metadata.name
            )
            
        except Exception as e:
            logger.error(f"Failed to resume test flow for session {session_id}: {str(e)}")
            return TestFlowResponse(
                status="error",
                message=f"Failed to resume test flow: {str(e)}"
            )
    
    async def get_test_flow_summary(self, session_id: str) -> Optional[TestFlow]:
        """
        Get the current test flow summary for a session.
        
        Args:
            session_id: The session ID to get summary for
            
        Returns:
            TestFlow if found, None otherwise
        """
        # Check active flows first
        if session_id in self.active_flows:
            return self.active_flows[session_id]
        
        # Check completed flows
        if session_id in self.completed_flows:
            return self.completed_flows[session_id]
        
        return None
    
    async def export_test_report(self, session_id: str, format: str = "json") -> str:
        """
        Export a test flow report in the specified format.
        
        Args:
            session_id: The session ID to export
            format: Export format ("json", "html", "markdown")
            
        Returns:
            str: Exported report content
        """
        try:
            flow = await self.get_test_flow_summary(session_id)
            if not flow:
                return f"No test flow found for session {session_id}"
            
            if format.lower() == "json":
                return flow.model_dump_json(indent=2)
            elif format.lower() == "html":
                return await self._generate_html_report(flow)
            elif format.lower() == "markdown":
                return await self._generate_markdown_report(flow)
            else:
                return f"Unsupported format: {format}. Supported formats: json, html, markdown"
                
        except Exception as e:
            logger.error(f"Failed to export test report for session {session_id}: {str(e)}")
            return f"Failed to export report: {str(e)}"
    
    async def _generate_performance_summary(self, flow: TestFlow) -> None:
        """Generate a performance summary for the test flow."""
        try:
            if not flow.steps:
                return
            
            # Aggregate performance metrics across all steps
            total_duration = 0
            total_load_time = 0
            total_paint_time = 0
            step_count = 0
            
            for step in flow.steps:
                if step.metrics:
                    if step.duration_ms:
                        total_duration += step.duration_ms
                    
                    # Extract performance metrics if available
                    if isinstance(step.metrics, dict):
                        if 'pageLoadTime' in step.metrics and step.metrics['pageLoadTime'] != 'N/A':
                            total_load_time += step.metrics['pageLoadTime']
                        if 'firstPaint' in step.metrics and step.metrics['firstPaint'] != 'N/A':
                            total_paint_time += step.metrics['firstPaint']
                    
                    step_count += 1
            
            if step_count > 0:
                flow.performance_summary = {
                    "total_steps": step_count,
                    "average_step_duration_ms": total_duration / step_count if total_duration > 0 else 0,
                    "average_load_time_ms": total_load_time / step_count if total_load_time > 0 else 0,
                    "average_paint_time_ms": total_paint_time / step_count if total_paint_time > 0 else 0,
                    "total_duration_ms": total_duration,
                    "success_rate": (flow.metadata.successful_steps / flow.metadata.total_steps) * 100 if flow.metadata.total_steps > 0 else 0
                }
                
        except Exception as e:
            logger.error(f"Failed to generate performance summary: {str(e)}")
    
    async def _generate_html_report(self, flow: TestFlow) -> str:
        """Generate an HTML report for the test flow."""
        try:
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Test Flow Report - {flow.metadata.name}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                    .step {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }}
                    .metrics {{ background-color: #f9f9f9; padding: 10px; margin: 10px 0; border-radius: 3px; }}
                    .error {{ color: red; }}
                    .success {{ color: green; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Test Flow Report: {flow.metadata.name}</h1>
                    <p><strong>User Request:</strong> {flow.metadata.user_request}</p>
                    <p><strong>Status:</strong> <span class="{'success' if flow.metadata.status == TestFlowStatus.COMPLETED else 'error'}">{flow.metadata.status.value}</span></p>
                    <p><strong>Start Time:</strong> {flow.metadata.start_time}</p>
                    <p><strong>Total Steps:</strong> {flow.metadata.total_steps}</p>
                    <p><strong>Success Rate:</strong> {flow.metadata.successful_steps}/{flow.metadata.total_steps}</p>
                </div>
            """
            
            if flow.performance_summary:
                html += f"""
                <div class="metrics">
                    <h2>Performance Summary</h2>
                    <p><strong>Average Step Duration:</strong> {flow.performance_summary.get('average_step_duration_ms', 0):.2f}ms</p>
                    <p><strong>Average Load Time:</strong> {flow.performance_summary.get('average_load_time_ms', 0):.2f}ms</p>
                    <p><strong>Success Rate:</strong> {flow.performance_summary.get('success_rate', 0):.1f}%</p>
                </div>
                """
            
            html += "<h2>Test Steps</h2>"
            
            for i, step in enumerate(flow.steps, 1):
                html += f"""
                <div class="step">
                    <h3>Step {i}: {step.url}</h3>
                    <p><strong>Timestamp:</strong> {step.timestamp}</p>
                    <p><strong>Action:</strong> {step.action or 'N/A'}</p>
                    <p><strong>Duration:</strong> {step.duration_ms or 'N/A'}ms</p>
                """
                
                if step.errors:
                    html += f'<p class="error"><strong>Errors:</strong> {", ".join(step.errors)}</p>'
                
                html += "</div>"
            
            html += """
            </body>
            </html>
            """
            
            return html
            
        except Exception as e:
            logger.error(f"Failed to generate HTML report: {str(e)}")
            return f"Failed to generate HTML report: {str(e)}"
    
    async def _generate_markdown_report(self, flow: TestFlow) -> str:
        """Generate a markdown report for the test flow."""
        try:
            md = f"""# Test Flow Report: {flow.metadata.name}

## Overview
- **User Request**: {flow.metadata.user_request}
- **Status**: {flow.metadata.status.value}
- **Start Time**: {flow.metadata.start_time}
- **Total Steps**: {flow.metadata.total_steps}
- **Success Rate**: {flow.metadata.successful_steps}/{flow.metadata.total_steps}

"""
            
            if flow.performance_summary:
                md += f"""## Performance Summary
- **Average Step Duration**: {flow.performance_summary.get('average_step_duration_ms', 0):.2f}ms
- **Average Load Time**: {flow.performance_summary.get('average_load_time_ms', 0):.2f}ms
- **Success Rate**: {flow.performance_summary.get('success_rate', 0):.1f}%

"""
            
            md += "## Test Steps\n\n"
            
            for i, step in enumerate(flow.steps, 1):
                md += f"""### Step {i}: {step.url}
- **Timestamp**: {step.timestamp}
- **Action**: {step.action or 'N/A'}
- **Duration**: {step.duration_ms or 'N/A'}ms
"""
                
                if step.errors:
                    md += f"- **Errors**: {', '.join(step.errors)}\n"
                
                md += "\n"
            
            return md
            
        except Exception as e:
            logger.error(f"Failed to generate markdown report: {str(e)}")
            return f"Failed to generate markdown report: {str(e)}"
    
    def get_active_flows_count(self) -> int:
        """Get the number of currently active test flows."""
        return len(self.active_flows)
    
    def get_completed_flows_count(self) -> int:
        """Get the number of completed test flows."""
        return len(self.completed_flows)
    
    async def cleanup_old_flows(self, max_age_hours: int = 24) -> int:
        """
        Clean up old completed flows to prevent memory bloat.
        
        Args:
            max_age_hours: Maximum age in hours to keep flows
            
        Returns:
            int: Number of flows cleaned up
        """
        try:
            cutoff_time = datetime.utcnow().replace(hour=datetime.utcnow().hour - max_age_hours)
            flows_to_remove = []
            
            for session_id, flow in self.completed_flows.items():
                if flow.metadata.end_time and flow.metadata.end_time < cutoff_time:
                    flows_to_remove.append(session_id)
            
            for session_id in flows_to_remove:
                del self.completed_flows[session_id]
            
            logger.info(f"Cleaned up {len(flows_to_remove)} old test flows")
            return len(flows_to_remove)
            
        except Exception as e:
            logger.error(f"Failed to cleanup old flows: {str(e)}")
            return 0


# Global instance for use across the application
test_flow_manager = TestFlowManager()
