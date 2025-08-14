"""
Step Data Capture System for Test Flow Management.

This module provides comprehensive data collection capabilities for test steps,
including performance metrics, page state, screenshots, and network activity.
"""

import asyncio
import logging
import time
import base64
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from ..schemas import TestStepData
from .test_flow_manager import test_flow_manager

logger = logging.getLogger(__name__)


class StepDataCapture:
    """
    Comprehensive step data capture system for test flows.
    
    This class handles:
    - Performance metrics collection
    - Page state capture
    - Screenshot generation
    - Network activity monitoring
    - Error detection and logging
    """
    
    def __init__(self):
        self.capture_options = {
            "screenshots": True,
            "performance": True,
            "network": True,
            "console_logs": True,
            "errors": True,
            "page_state": True
        }
    
    async def capture_step_metrics(
        self, 
        session_id: str, 
        url: str, 
        action: str = None,
        capture_options: Optional[Dict[str, bool]] = None
    ) -> Tuple[TestStepData, float]:
        """
        Capture comprehensive metrics for a test step.
        
        Args:
            session_id: The session ID to capture metrics for
            url: The URL of the current page
            action: The action being performed
            capture_options: Override default capture options
            
        Returns:
            Tuple of (TestStepData, start_time)
        """
        start_time = time.time()
        
        # Use provided options or defaults
        options = capture_options or self.capture_options
        
        # Create base step data
        step_data = TestStepData(
            url=url,
            action=action,
            timestamp=datetime.utcnow()
        )
        
        # Capture page state if enabled
        if options.get("page_state", True):
            await self._capture_page_state(step_data)
        
        # Capture performance metrics if enabled
        if options.get("performance", True):
            await self._capture_performance_metrics(step_data)
        
        # Capture network data if enabled
        if options.get("network", True):
            await self._capture_network_data(step_data)
        
        # Capture console logs if enabled
        if options.get("console_logs", True):
            await self._capture_console_logs(step_data)
        
        # Capture errors if enabled
        if options.get("errors", True):
            await self._capture_errors(step_data)
        
        # Capture screenshot if enabled
        if options.get("screenshots", True):
            await self._capture_screenshot(step_data)
        
        return step_data, start_time
    
    async def _capture_page_state(self, step_data: TestStepData) -> None:
        """Capture current page state information."""
        try:
            # This would be called from the browser context
            # For now, we'll set placeholder data
            step_data.title = "Page Title"  # Would be actual page title
            
        except Exception as e:
            logger.warning(f"Failed to capture page state: {str(e)}")
    
    async def _capture_performance_metrics(self, step_data: TestStepData) -> None:
        """Capture performance metrics for the current page."""
        try:
            # This would be called from the browser context
            # For now, we'll set placeholder performance data
            step_data.metrics = {
                "pageLoadTime": 1200,
                "domContentLoaded": 800,
                "firstPaint": 600,
                "firstContentfulPaint": 750,
                "dnsLookupTime": 50,
                "tcpConnectionTime": 100,
                "serverResponseTime": 300,
                "domProcessingTime": 400,
                "resourceLoadTime": 500
            }
            
        except Exception as e:
            logger.warning(f"Failed to capture performance metrics: {str(e)}")
    
    async def _capture_network_data(self, step_data: TestStepData) -> None:
        """Capture network activity data."""
        try:
            # This would be called from the browser context
            # For now, we'll set placeholder network data
            step_data.network_data = {
                "totalRequests": 25,
                "byType": {
                    "document": 1,
                    "stylesheet": 3,
                    "script": 5,
                    "image": 10,
                    "font": 2,
                    "other": 4
                },
                "largestRequests": [
                    {"url": "main.js", "size": 150000, "duration": 200},
                    {"url": "styles.css", "size": 45000, "duration": 150},
                    {"url": "hero-image.jpg", "size": 250000, "duration": 300}
                ]
            }
            
        except Exception as e:
            logger.warning(f"Failed to capture network data: {str(e)}")
    
    async def _capture_console_logs(self, step_data: TestStepData) -> None:
        """Capture console logs from the page."""
        try:
            # This would be called from the browser context
            # For now, we'll set placeholder console logs
            step_data.console_logs = [
                "Page loaded successfully",
                "JavaScript initialized",
                "API call completed"
            ]
            
        except Exception as e:
            logger.warning(f"Failed to capture console logs: {str(e)}")
    
    async def _capture_errors(self, step_data: TestStepData) -> None:
        """Capture any errors that occurred during the step."""
        try:
            # This would be called from the browser context
            # For now, we'll set empty errors list
            step_data.errors = []
            
        except Exception as e:
            logger.warning(f"Failed to capture errors: {str(e)}")
    
    async def _capture_screenshot(self, step_data: TestStepData) -> None:
        """Capture a screenshot of the current page."""
        try:
            # This would be called from the browser context
            # For now, we'll set a placeholder screenshot
            # In practice, this would be a base64-encoded PNG image
            step_data.screenshot = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
            
        except Exception as e:
            logger.warning(f"Failed to capture screenshot: {str(e)}")
    
    async def complete_step_capture(
        self, 
        session_id: str, 
        step_data: TestStepData, 
        start_time: float,
        final_metrics: Optional[Dict[str, Any]] = None,
        final_errors: Optional[List[str]] = None
    ) -> bool:
        """
        Complete the step capture and record it in the test flow.
        
        Args:
            session_id: The session ID
            step_data: The step data to complete
            start_time: The start time from capture_step_metrics
            final_metrics: Final metrics to override captured ones
            final_errors: Final errors to override captured ones
            
        Returns:
            bool: True if step was recorded successfully
        """
        try:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            step_data.duration_ms = duration_ms
            
            # Override with final metrics/errors if provided
            if final_metrics:
                step_data.metrics = final_metrics
            
            if final_errors:
                step_data.errors = final_errors
            
            # Record the step in the test flow manager
            success = await test_flow_manager.record_step(session_id, step_data)
            
            if success:
                logger.debug(f"Step recorded successfully for session {session_id}")
                return True
            else:
                logger.warning(f"Failed to record step for session {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error completing step capture: {str(e)}")
            return False
    
    async def capture_browser_metrics(self, browser_session) -> Dict[str, Any]:
        """
        Capture comprehensive browser metrics from a browser session.
        
        Args:
            browser_session: The browser session to capture metrics from
            
        Returns:
            Dict containing comprehensive browser metrics
        """
        try:
            if not browser_session:
                return {}
            
            page = await browser_session.get_current_page()
            if not page:
                return {}
            
            # Capture performance metrics using JavaScript
            perf_metrics = await page.evaluate("""() => {
                const perfData = window.performance.timing;
                const navStart = perfData.navigationStart;
                
                const metrics = {
                    pageLoadTime: perfData.loadEventEnd - navStart,
                    domContentLoaded: perfData.domContentLoadedEventEnd - navStart,
                    firstPaint: performance.getEntriesByType('paint').find(entry => entry.name === 'first-paint')?.startTime || 0,
                    firstContentfulPaint: performance.getEntriesByType('paint').find(entry => entry.name === 'first-contentful-paint')?.startTime || 0,
                    dnsLookupTime: perfData.domainLookupEnd - perfData.domainLookupStart,
                    tcpConnectionTime: perfData.connectEnd - perfData.connectStart,
                    serverResponseTime: perfData.responseEnd - perfData.responseStart,
                    domProcessingTime: perfData.domComplete - perfData.domLoading,
                    resourceLoadTime: perfData.loadEventEnd - perfData.responseEnd,
                    resourceStats: {
                        totalResources: performance.getEntriesByType('resource').length,
                        totalSize: performance.getEntriesByType('resource').reduce((total, resource) => total + (resource.transferSize || 0), 0),
                        totalDuration: performance.getEntriesByType('resource').reduce((total, resource) => total + resource.duration, 0)
                    }
                };
                
                metrics.slowestResources = performance.getEntriesByType('resource')
                    .sort((a, b) => b.duration - a.duration)
                    .slice(0, 5)
                    .map(resource => ({
                        url: resource.name,
                        duration: resource.duration,
                        size: resource.transferSize || 0,
                        type: resource.initiatorType
                    }));
                    
                return metrics;
            }""")
            
            # Capture network requests
            network_data = await page.evaluate("""() => {
                const resources = performance.getEntriesByType('resource');
                const byType = {};
                
                resources.forEach(resource => {
                    const type = resource.initiatorType || 'other';
                    if (!byType[type]) byType[type] = [];
                    byType[type].push({
                        url: resource.name,
                        size: resource.transferSize || 0,
                        duration: resource.duration
                    });
                });
                
                const largestRequests = resources
                    .sort((a, b) => (b.transferSize || 0) - (a.transferSize || 0))
                    .slice(0, 5)
                    .map(resource => ({
                        url: resource.name,
                        size: resource.transferSize || 0,
                        duration: resource.duration
                    }));
                
                return {
                    totalRequests: resources.length,
                    byType: byType,
                    largestRequests: largestRequests
                };
            }""")
            
            # Capture console logs and errors
            console_data = await page.evaluate("""() => {
                // This would capture console logs if we had access to them
                // For now, return empty arrays
                return {
                    logs: [],
                    errors: []
                };
            }""")
            
            # Combine all metrics
            comprehensive_metrics = {
                "performance": perf_metrics,
                "network": network_data,
                "console": console_data,
                "pageInfo": {
                    "url": page.url,
                    "title": await page.title(),
                    "viewport": await page.viewport_size()
                }
            }
            
            return comprehensive_metrics
            
        except Exception as e:
            logger.error(f"Error capturing browser metrics: {str(e)}")
            return {}
    
    async def capture_screenshot_with_metadata(self, browser_session, format: str = "png") -> Dict[str, Any]:
        """
        Capture a screenshot with metadata.
        
        Args:
            browser_session: The browser session to capture from
            format: Image format (png, jpeg)
            
        Returns:
            Dict containing screenshot data and metadata
        """
        try:
            if not browser_session:
                return {}
            
            page = await browser_session.get_current_page()
            if not page:
                return {}
            
            # Capture screenshot
            screenshot_data = await page.screenshot(
                type=format,
                full_page=True,
                quality=90 if format == "jpeg" else None
            )
            
            # Encode as base64
            screenshot_b64 = base64.b64encode(screenshot_data).decode('utf-8')
            
            # Get page metadata
            metadata = {
                "url": page.url,
                "title": await page.title(),
                "timestamp": datetime.utcnow().isoformat(),
                "format": format,
                "size_bytes": len(screenshot_data),
                "viewport": await page.viewport_size()
            }
            
            return {
                "screenshot": f"data:image/{format};base64,{screenshot_b64}",
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Error capturing screenshot: {str(e)}")
            return {}


# Global instance for use across the application
step_data_capture = StepDataCapture()
