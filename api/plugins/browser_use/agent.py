import logging
from browser_use import Agent, Browser, BrowserConfig, Controller
from typing import Any, List, Mapping, AsyncIterator, Optional, Dict
from ...providers import create_llm
from ...models import ModelConfig
from langchain.schema import AIMessage
from langchain_core.messages import ToolMessage
import os
from dotenv import load_dotenv
from ...utils.types import AgentSettings
from browser_use.browser.views import BrowserState
from browser_use.browser.context import BrowserContext
from browser_use.agent.views import (
    AgentHistoryList,
    AgentOutput,
)
import asyncio
from pydantic import BaseModel
import uuid
from .system_prompt import ExtendedSystemPrompt
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(".env.local")
os.environ["ANONYMIZED_TELEMETRY"] = "false"

STEEL_API_KEY = os.getenv("STEEL_API_KEY")
STEEL_CONNECT_URL = os.getenv("STEEL_CONNECT_URL")

# Dictionary to store active browser instances by session_id
active_browsers: Dict[str, Browser] = {}
active_browser_contexts: Dict[str, BrowserContext] = {}

# Global variable to track resume state
_agent_resumed = False

# Session storage for metrics
session_metrics_storage: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(lambda: {"pages": {}})

# Initialize the controller
class SessionAwareController(Controller):
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__init__(*args, **kwargs)
        return cls._instance
        
    def __init__(self, *args, **kwargs):
        if not hasattr(self, 'session_id'):  # Only initialize if not already initialized
            super().__init__(*args, **kwargs)
            self.session_id = None
            self.agent = None
            self.finished = False  # Track if agent has finished executing its task

    def set_session_id(self, session_id: str):
        self.session_id = session_id
        # Ensure session entry exists when ID is set
        session_metrics_storage[session_id] # Access to initialize via defaultdict
        # Reset finished state on new session
        self.finished = False
        logger.info(f"🔄 Controller finished state reset for session: {session_id}")

    def set_agent(self, agent: Agent):
        self.agent = agent

    def _get_current_session_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Helper to get the metrics dictionary for the current session."""
        if not self.session_id:
            return {"pages": {}} # Should not happen if set_session_id is called
        return session_metrics_storage[self.session_id]

    def _store_metric(self, page_url: str, metric_type: str, data: Any):
        """Helper to store a specific metric for a page in the session."""
        if not self.session_id:
            logger.warning("Attempted to store metric without session_id")
            return
        session_data = self._get_current_session_metrics()
        if page_url not in session_data["pages"]:
            session_data["pages"][page_url] = {}
        session_data["pages"][page_url][metric_type] = data
        logger.debug(f"Stored {metric_type} for {page_url} in session {self.session_id}")

controller = SessionAwareController(exclude_actions=["open_tab", "switch_tab"])

@controller.action('Print a message')
def print_call(message: str) -> str:
    """Print a message when the tool is called."""
    print(f"🔔 Tool call: {message}")
    return f"Printed: {message}"

@controller.action('Capture page performance metrics')
async def capture_performance_metrics() -> str:
    """Captures page performance metrics including latency, load time, and other timing information. Stores data for session summary."""
    if not controller.agent or not controller.agent.browser_context:
        return "No active browser context found"
    
    page = None # Initialize page to None
    try:
        # Get the current page
        page = await controller.agent.browser_context.get_current_page()
        page_url = page.url # Capture URL early
        
        # Use JavaScript to get detailed performance metrics
        perf_metrics = await page.evaluate("""() => {
            const perfData = window.performance.timing;
            const navStart = perfData.navigationStart;
            
            // Create an object with all the relevant timing metrics
            const metrics = {
                // Page load metrics
                pageLoadTime: perfData.loadEventEnd - navStart,
                domContentLoaded: perfData.domContentLoadedEventEnd - navStart,
                firstPaint: performance.getEntriesByType('paint').find(entry => entry.name === 'first-paint')?.startTime || 0,
                firstContentfulPaint: performance.getEntriesByType('paint').find(entry => entry.name === 'first-contentful-paint')?.startTime || 0,
                
                // Connection metrics
                dnsLookupTime: perfData.domainLookupEnd - perfData.domainLookupStart,
                tcpConnectionTime: perfData.connectEnd - perfData.connectStart,
                serverResponseTime: perfData.responseEnd - perfData.responseStart,
                
                // Processing metrics
                domProcessingTime: perfData.domComplete - perfData.domLoading,
                resourceLoadTime: perfData.loadEventEnd - perfData.responseEnd,
                
                // Resource metrics
                resourceStats: {
                    totalResources: performance.getEntriesByType('resource').length,
                    totalSize: performance.getEntriesByType('resource').reduce((total, resource) => total + (resource.transferSize || 0), 0),
                    totalDuration: performance.getEntriesByType('resource').reduce((total, resource) => total + resource.duration, 0)
                }
            };
            
            // Add resource data
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
        
        # Store the raw data
        controller._store_metric(page_url, "performance", perf_metrics)

        # Format the results for better readability
        formatted_result = f"""
        📊 Page Performance Metrics for {page_url}:
        
        ⏱️ Timing Metrics:
        - Page Load Time: {perf_metrics['pageLoadTime']}ms
        - DOM Content Loaded: {perf_metrics['domContentLoaded']}ms
        - First Paint: {perf_metrics['firstPaint']}ms
        - First Contentful Paint: {perf_metrics['firstContentfulPaint']}ms
        
        🔄 Connection Metrics:
        - DNS Lookup: {perf_metrics['dnsLookupTime']}ms
        - TCP Connection: {perf_metrics['tcpConnectionTime']}ms
        - Server Response: {perf_metrics['serverResponseTime']}ms
        
        ⚙️ Processing Metrics:
        - DOM Processing: {perf_metrics['domProcessingTime']}ms
        - Resource Loading: {perf_metrics['resourceLoadTime']}ms
        
        📦 Resource Stats:
        - Total Resources: {perf_metrics['resourceStats']['totalResources']}
        - Total Size: {perf_metrics['resourceStats']['totalSize'] / 1024:.2f} KB
        - Total Resource Duration: {perf_metrics['resourceStats']['totalDuration']}ms
        
        🐢 Top 5 Slowest Resources:"""
        
        # Add slowest resources to the output
        for idx, resource in enumerate(perf_metrics['slowestResources']):
            formatted_result += f"""
        {idx+1}. {resource['url']} 
           - Duration: {resource['duration']}ms
           - Size: {resource['size'] / 1024:.2f} KB
           - Type: {resource['type']}"""
            
        return formatted_result
        
    except Exception as e:
        logger.error(f"❌ Error capturing performance metrics: {str(e)}")
        # Try to get URL even on error if page object exists
        error_url = page.url if page else "unknown page"
        return f"Failed to capture performance metrics for {error_url}: {str(e)}"

@controller.action('Capture network requests')
async def capture_network_requests() -> str:
    """Captures all network requests made by the page using performance API and summarizes them. Stores data for session summary."""
    if not controller.agent or not controller.agent.browser_context:
        return "No active browser context found"
    
    page = None
    try:
        # Get the current page
        page = await controller.agent.browser_context.get_current_page()
        page_url = page.url

        # Use JavaScript to get detailed network requests
        network_data = await page.evaluate("""() => {
            // Get all resource entries
            const resources = performance.getEntriesByType('resource');
            
            // Organize by type
            const resourcesByType = {};
            resources.forEach(resource => {
                const type = resource.initiatorType || 'other';
                if (!resourcesByType[type]) {
                    resourcesByType[type] = [];
                }
                resourcesByType[type].push({
                    url: resource.name,
                    duration: resource.duration,
                    size: resource.transferSize || 0,
                    startTime: resource.startTime
                });
            });
            
            // Get failed resources from our monitoring namespace
            const possibleErrors = window.__BROWSER_USE_MONITOR ? window.__BROWSER_USE_MONITOR.networkErrors : [];
            
            return {
                totalRequests: resources.length,
                byType: resourcesByType,
                possibleErrors: possibleErrors
            };
        }""")
        
        # Store the raw data
        controller._store_metric(page_url, "network", network_data)

        # Format the results for better readability
        formatted_result = f"""
        🌐 Network Request Summary for {page_url}:
        
        📊 Overview:
        - Total Requests: {network_data['totalRequests']}
        """
        
        # Add resource types
        formatted_result += "\n        📑 Requests by Type:"
        for resource_type, resources in network_data['byType'].items():
            total_size = sum(r['size'] for r in resources) / 1024
            formatted_result += f"\n        - {resource_type.capitalize()}: {len(resources)} requests ({total_size:.2f} KB)"
        
        # Add most significant requests
        formatted_result += "\n\n        📋 Largest Requests:"
        largest_requests = sorted(
            [r for t in network_data['byType'].values() for r in t], 
            key=lambda r: r['size'], 
            reverse=True
        )[:5]
        
        for idx, request in enumerate(largest_requests):
            formatted_result += f"""
        {idx+1}. {request['url']} 
           - Size: {request['size'] / 1024:.2f} KB
           - Duration: {request['duration']}ms"""
        
        # Check for potential network errors
        if network_data['possibleErrors']:
            formatted_result += "\n\n        ⚠️ Possible Network Errors:"
            for idx, error in enumerate(network_data['possibleErrors']):
                formatted_result += f"\n        {idx+1}. {error}"
        
        return formatted_result
        
    except Exception as e:
        logger.error(f"❌ Error capturing network requests: {str(e)}")
        error_url = page.url if page else "unknown page"
        return f"Failed to capture network requests for {error_url}: {str(e)}"

@controller.action('Detect page anomalies')
async def detect_page_anomalies() -> str:
    """Detects potential anomalies on the page including layout issues, console errors, and network problems. Stores data for session summary."""
    if not controller.agent or not controller.agent.browser_context:
        return "No active browser context found"
    
    page = None
    try:
        # Get the current page
        page = await controller.agent.browser_context.get_current_page()
        page_url = page.url

        # Try to take a full-page screenshot with scrolling and timeout
        screenshot_b64 = None
        try:
            # Add JavaScript to capture a full-page screenshot by scrolling
            screenshot_b64 = await page.evaluate("""async () => {
                // Function to scroll down the page in increments
                const scrollPageAndCapture = async () => {
                    // Get the initial page dimensions
                    const fullHeight = Math.max(
                        document.body.scrollHeight,
                        document.documentElement.scrollHeight,
                        document.body.offsetHeight,
                        document.documentElement.offsetHeight,
                        document.body.clientHeight,
                        document.documentElement.clientHeight
                    );
                    
                    // Scroll down in increments
                    const scrollStep = window.innerHeight / 2; // Half a viewport
                    let currentScroll = 0;
                    
                    // First scroll to top to ensure we start from the beginning
                    window.scrollTo(0, 0);
                    await new Promise(r => setTimeout(r, 200)); // Small delay
                    
                    // Continue scrolling until we reach the bottom
                    while (currentScroll < fullHeight) {
                        window.scrollTo(0, currentScroll);
                        await new Promise(r => setTimeout(r, 200)); // Wait for content to load
                        currentScroll += scrollStep;
                    }
                    
                    // Final scroll to the bottom to make sure we've seen everything
                    window.scrollTo(0, fullHeight);
                    await new Promise(r => setTimeout(r, 300)); // Final delay
                    
                    // Scroll back to top
                    window.scrollTo(0, 0);
                    await new Promise(r => setTimeout(r, 200));
                    
                    // Signal to the browser-use system that we've done the scrolling
                    return true;
                };
                
                // Execute the scrolling function
                return await scrollPageAndCapture();
            }""")
            
            # Now capture the screenshot after scrolling
            screenshot_task = asyncio.create_task(controller.agent.browser_context.take_screenshot())
            screenshot_b64 = await asyncio.wait_for(screenshot_task, timeout=15.0)  # 15 second timeout
            logger.info(f"📸 Full-page screenshot captured successfully for {page_url}")
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ Screenshot capture timed out for {page_url}, continuing without screenshot")
        except Exception as screenshot_error:
            logger.warning(f"⚠️ Screenshot capture failed for {page_url}: {str(screenshot_error)}")
        
        # Store screenshot only if successfully captured
        if screenshot_b64:
            controller._store_metric(page_url, "screenshot_b64", screenshot_b64)
        
        # Use JavaScript to detect various anomalies
        anomalies = await page.evaluate("""() => {
            const anomalies = {
                consoleErrors: window.__BROWSER_USE_MONITOR ? window.__BROWSER_USE_MONITOR.consoleErrors : [],
                layoutIssues: [],
                networkIssues: [],
                performanceIssues: [],
                accessibilityIssues: []
            };
            
            // Check for layout issues (elements offscreen or overlapping)
            const allElements = Array.from(document.querySelectorAll('*'));
            const viewportWidth = window.innerWidth;
            const viewportHeight = window.innerHeight;
            
            // Check for offscreen elements that might be important
            allElements.forEach(el => {
                if (el.tagName === 'BUTTON' || el.tagName === 'A' || el.tagName === 'INPUT' || el.tagName === 'SELECT') {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        if (rect.right < 0 || rect.bottom < 0 || rect.left > viewportWidth || rect.top > viewportHeight) {
                            const text = el.textContent || el.value || el.id || el.className || el.tagName;
                            anomalies.layoutIssues.push(`Interactive element offscreen: ${text.trim().substring(0, 50)}`);
                        }
                    }
                }
            });
            
            // Check for network timing anomalies
            const resources = performance.getEntriesByType('resource');
            resources.forEach(resource => {
                if (resource.duration > 2000) {
                    anomalies.networkIssues.push(`Slow resource (${resource.duration.toFixed(0)}ms): ${resource.name}`);
                }
            });
            
            // Check for performance issues
            const timing = performance.timing;
            if (timing.loadEventEnd - timing.navigationStart > 5000) {
                anomalies.performanceIssues.push(`Page load time exceeds 5 seconds (${(timing.loadEventEnd - timing.navigationStart)}ms)`);
            }
            
            if (timing.domInteractive - timing.navigationStart > 3000) {
                anomalies.performanceIssues.push(`Time to interactive exceeds 3 seconds (${(timing.domInteractive - timing.navigationStart)}ms)`);
            }
            
            // Basic accessibility check
            allElements.forEach(el => {
                if (el.tagName === 'IMG' && (!el.alt || el.alt === '')) {
                    anomalies.accessibilityIssues.push(`Image missing alt text: ${el.src}`);
                }
            });
            
            const inputElements = document.querySelectorAll('input, select, textarea');
            inputElements.forEach(input => {
                const label = document.querySelector(`label[for="${input.id}"]`);
                if (!label && !input.getAttribute('aria-label')) {
                    const desc = input.id || input.name || input.placeholder || input.tagName;
                    anomalies.accessibilityIssues.push(`Form control missing label: ${desc}`);
                }
            });
            
            return anomalies;
        }""")
        
        # Add JavaScript to listen for console errors and network errors for future captures
        await page.evaluate("""() => {
            // Initialize our monitoring namespace if not present
            if (!window.__BROWSER_USE_MONITOR) {
                window.__BROWSER_USE_MONITOR = {
                    networkRequests: [],
                    networkErrors: [],
                    consoleErrors: [],
                    initialized: false
                };
            }
            
            // Set up console error tracking if not already set up
            if (!window.__BROWSER_USE_MONITOR.initialized) {
                window.addEventListener('error', (e) => {
                    window.__BROWSER_USE_MONITOR.consoleErrors.push(`${e.message} at ${e.filename}:${e.lineno}`);
                });
                
                // Override console.error to capture error messages
                const originalConsoleError = console.error;
                console.error = function() {
                    window.__BROWSER_USE_MONITOR.consoleErrors.push(Array.from(arguments).join(' '));
                    originalConsoleError.apply(console, arguments);
                };
                
                window.__BROWSER_USE_MONITOR.initialized = true;
            }
        }""")
        
        # Store the raw data
        controller._store_metric(page_url, "anomalies", anomalies)

        # Format the results
        formatted_result = f"""
        🔍 Anomaly Detection for {page_url}:
        """
        
        # Add screenshot status
        if screenshot_b64:
            formatted_result += "\n        📸 Screenshot captured for visual inspection (stored in agent state)"
        else:
            formatted_result += "\n        ⚠️ Screenshot capture was skipped or failed"
        
        # Count total anomalies
        total_anomalies = sum(len(issues) for issues in anomalies.values())
        
        if total_anomalies == 0:
            formatted_result += "\n        ✅ No anomalies detected! Page appears to be functioning normally."
        else:
            formatted_result += f"\n        ⚠️ {total_anomalies} potential issues detected:"
            
            # Add console errors
            if anomalies['consoleErrors']:
                formatted_result += "\n\n        🛑 Console Errors:"
                for idx, error in enumerate(anomalies['consoleErrors']):
                    formatted_result += f"\n        {idx+1}. {error}"
            
            # Add layout issues
            if anomalies['layoutIssues']:
                formatted_result += "\n\n        📐 Layout Issues:"
                for idx, issue in enumerate(anomalies['layoutIssues']):
                    formatted_result += f"\n        {idx+1}. {issue}"
            
            # Add network issues
            if anomalies['networkIssues']:
                formatted_result += "\n\n        🌐 Network Issues:"
                for idx, issue in enumerate(anomalies['networkIssues']):
                    formatted_result += f"\n        {idx+1}. {issue}"
            
            # Add performance issues
            if anomalies['performanceIssues']:
                formatted_result += "\n\n        ⏱️ Performance Issues:"
                for idx, issue in enumerate(anomalies['performanceIssues']):
                    formatted_result += f"\n        {idx+1}. {issue}"
            
            # Add accessibility issues
            if anomalies['accessibilityIssues']:
                formatted_result += "\n\n        ♿ Accessibility Issues:"
                for idx, issue in enumerate(anomalies['accessibilityIssues']):
                    formatted_result += f"\n        {idx+1}. {issue}"
                    
        return formatted_result
        
    except Exception as e:
        logger.error(f"❌ Error detecting page anomalies: {str(e)}")
        error_url = page.url if page else "unknown page"
        return f"Failed to detect page anomalies for {error_url}: {str(e)}"

@controller.action('Pause execution')
async def pause_execution(reason: str) -> str:
    """Pause execution using agent's pause mechanism."""
    global _agent_resumed
    
    if not controller.agent:
        raise ValueError("No agent set in controller")
        
    print(f"⏸️ Pausing execution: {reason}")
    logger.info(f"⏸️ Pausing execution: {reason}")
    
    # Store current browser state before pausing (to prevent about:blank issue)
    browser_context = None
    browser = None
    if controller.session_id in active_browser_contexts:
        browser_context = active_browser_contexts[controller.session_id]
    if controller.session_id in active_browsers:
        browser = active_browsers[controller.session_id]
    
    # Log the current state for debugging
    if browser:
        logger.info(f"📊 Current browser state before pause - session_id: {controller.session_id}")
    
    # Set _agent_resumed to False to indicate we're paused
    _agent_resumed = False
    logger.info(f"⏸️ Set _agent_resumed = False for session: {controller.session_id}")
    
    # IMPORTANT: Make sure the message doesn't contain multiple pause prefixes
    clean_reason = reason.replace("⏸️ ", "").strip()
    if clean_reason.startswith("CONFIRMATION REQUIRED:"):
        clean_reason = clean_reason.replace("CONFIRMATION REQUIRED:", "").strip()
    formatted_reason = f"⏸️ {clean_reason}"
    
    # Pause the agent but ensure browser state is preserved
    controller.agent.pause()
    logger.info(f"⏸️ Agent paused for session: {controller.session_id}")
    
    # Make sure browser and context remain active and are not reset
    if controller.session_id:
        active_browser_contexts[controller.session_id] = browser_context
        active_browsers[controller.session_id] = browser
    
    # Return a clean message for the frontend
    return formatted_reason

class ResumeRequest(BaseModel):
    session_id: str

async def resume_execution(request: ResumeRequest) -> dict:
    """API endpoint to resume agent execution."""
    global _agent_resumed
    if not controller.agent:
        return {"status": "error", "message": "No agent found"}
    
    # Ensure browser state is preserved
    session_id = request.session_id
    if session_id in active_browsers and session_id in active_browser_contexts:
        logger.info(f"📊 Preserving browser state for session on resume: {session_id}")
        browser = active_browsers[session_id]
        browser_context = active_browser_contexts[session_id]
        
        # Make sure we're still using the same browser instances
        if controller.agent.browser != browser:
            logger.info(f"🔄 Restoring browser instance for session: {session_id}")
            controller.agent.browser = browser
            
        if controller.agent.browser_context != browser_context:
            logger.info(f"🔄 Restoring browser context for session: {session_id}")
            controller.agent.browser_context = browser_context
    
    # First set the flag to true so ongoing processes know we're resumed
    _agent_resumed = True
    logger.info(f"✅ Set _agent_resumed = True for session: {session_id}")
    
    # Then resume the agent
    try:
        logger.info(f"▶️ Resuming agent for session: {session_id}")
        controller.agent.resume()
        logger.info(f"✅ Agent resumed successfully for session: {session_id}")
        
        # Small delay to allow agent to process the resume
        await asyncio.sleep(0.2)
        
        # Verify the agent is really resumed
        if controller.agent._paused:
            logger.warning(f"⚠️ Agent still shows as paused after resume for session: {session_id}")
            # Force the paused state to false
            controller.agent._paused = False
            logger.info(f"🔧 Forced agent._paused = False for session: {session_id}")
    except Exception as e:
        logger.error(f"❌ Error resuming agent: {str(e)}")
        # Even if resume fails, keep _agent_resumed = True so UI can recover
        return {"status": "error", "message": f"Failed to resume agent: {str(e)}"}
    
    return {"status": "success", "message": "Agent resumed"}

class PauseRequest(BaseModel):
    session_id: str

async def pause_execution_manually(request: PauseRequest) -> dict:
    """API endpoint to manually pause agent execution."""
    global _agent_resumed
    
    logger.info(f"🖐️ Manual pause requested for session: {request.session_id}")
    
    if not controller.agent:
        return {"status": "error", "message": "No agent found"}
    
    if controller.session_id != request.session_id:
        return {"status": "error", "message": "Session ID mismatch"}
    
    # Store current browser state before pausing
    browser_context = None
    browser = None
    if controller.session_id in active_browser_contexts:
        browser_context = active_browser_contexts[controller.session_id]
    if controller.session_id in active_browsers:
        browser = active_browsers[controller.session_id]
    
    # Log the current state for debugging
    if browser:
        logger.info(f"📊 Preserving browser state on manual pause - session_id: {controller.session_id}")
    
    # Set _agent_resumed to false to indicate pause state
    _agent_resumed = False
    logger.info(f"⏸️ Set _agent_resumed = False for manual pause - session_id: {controller.session_id}")
    
    # Pause the agent but ensure browser state is preserved
    controller.agent.pause()
    logger.info(f"⏸️ Agent manually paused for session: {controller.session_id}")
    
    # Make sure browser and context remain active and are not reset
    if controller.session_id:
        active_browser_contexts[controller.session_id] = browser_context
        active_browsers[controller.session_id] = browser
    
    return {"status": "success", "message": "Agent manually paused for user control"}

@controller.action('Get session exploration summary')
async def get_session_summary() -> str:
    """Retrieves all collected metrics for the current page and session by automatically calling all monitoring tools first."""
    if not controller.agent or not controller.agent.browser_context:
        return "No active browser context found"
    
    if not controller.session_id:
        return "No active session ID found."

    try:
        # Get the current page
        page = await controller.agent.browser_context.get_current_page()
        current_url = page.url

        # First call all the monitoring tools to collect fresh data
        # Use try/except for each tool to ensure one failure doesn't stop the entire process
        
        print(f"📊 Collecting performance metrics for {current_url}")
        try:
            await capture_performance_metrics()
        except Exception as e:
            logger.error(f"❌ Error collecting performance metrics: {str(e)}")
        
        print(f"🌐 Collecting network requests for {current_url}")
        try:
            await capture_network_requests()
        except Exception as e:
            logger.error(f"❌ Error collecting network requests: {str(e)}")
        
        print(f"🔍 Running anomaly detection for {current_url}")
        try:
            await detect_page_anomalies()
        except Exception as e:
            logger.error(f"❌ Error during anomaly detection: {str(e)}")
        
        print(f"🔄 Checking real-time network activity for {current_url}")
        try:
            await get_real_time_network_activity()
        except Exception as e:
            logger.error(f"❌ Error checking real-time network activity: {str(e)}")
        
        # Short delay to ensure all data is properly stored
        await asyncio.sleep(0.5)
        
        # Get the session data
        session_data = controller._get_current_session_metrics()
        pages_visited = session_data.get("pages", {})

        # Initialize a default structure to ensure we always follow the exact format
        perf_data = {
            'pageLoadTime': 'N/A',
            'domContentLoaded': 'N/A',
            'firstPaint': 'N/A',
            'firstContentfulPaint': 'N/A',
            'dnsLookupTime': 'N/A',
            'tcpConnectionTime': 'N/A',
            'serverResponseTime': 'N/A',
            'domProcessingTime': 'N/A',
            'resourceLoadTime': 'N/A',
            'resourceStats': {
                'totalResources': 'N/A',
                'totalSize': 0,
                'totalDuration': 'N/A'
            },
            'slowestResources': []
        }
        
        network_data = {
            'totalRequests': 'N/A',
            'byType': {},
            'largestRequests': []
        }
        
        anomalies_data = {
            'consoleErrors': [],
            'layoutIssues': [],
            'networkIssues': [],
            'performanceIssues': [],
            'accessibilityIssues': []
        }
        
        # Extract actual data if available
        if current_url in pages_visited:
            page_metrics = pages_visited[current_url]
            
            if "performance" in page_metrics:
                actual_perf = page_metrics["performance"]
                # Update perf_data with actual values where available
                for key in perf_data:
                    if key in actual_perf:
                        if key == 'resourceStats':
                            for stat_key in perf_data['resourceStats']:
                                if stat_key in actual_perf['resourceStats']:
                                    perf_data['resourceStats'][stat_key] = actual_perf['resourceStats'][stat_key]
                        else:
                            perf_data[key] = actual_perf[key]
                
                # Handle slowest resources separately
                if 'slowestResources' in actual_perf:
                    perf_data['slowestResources'] = actual_perf['slowestResources']
            
            if "network" in page_metrics:
                actual_network = page_metrics["network"]
                if 'totalRequests' in actual_network:
                    network_data['totalRequests'] = actual_network['totalRequests']
                if 'byType' in actual_network:
                    network_data['byType'] = actual_network['byType']
                
                # Get largest requests
                largest_requests = []
                if 'byType' in actual_network:
                    for type_data in actual_network['byType'].values():
                        largest_requests.extend(type_data)
                    largest_requests.sort(key=lambda r: r.get('size', 0), reverse=True)
                    network_data['largestRequests'] = largest_requests[:5]  # Top 5
            
            if "anomalies" in page_metrics:
                actual_anomalies = page_metrics["anomalies"]
                for key in anomalies_data:
                    if key in actual_anomalies and isinstance(actual_anomalies[key], list):
                        anomalies_data[key] = actual_anomalies[key]
        
        # Now format the results in the exact specified structure
        summary = f"""📊 Page Performance Metrics for {current_url}:

⏱️ Timing Metrics:
- Page Load Time: {perf_data['pageLoadTime']}ms
- DOM Content Loaded: {perf_data['domContentLoaded']}ms
- First Paint: {perf_data['firstPaint']}ms
- First Contentful Paint: {perf_data['firstContentfulPaint']}ms

🔄 Connection Metrics:
- DNS Lookup: {perf_data['dnsLookupTime']}ms
- TCP Connection: {perf_data['tcpConnectionTime']}ms
- Server Response: {perf_data['serverResponseTime']}ms

⚙️ Processing Metrics:
- DOM Processing: {perf_data['domProcessingTime']}ms
- Resource Loading: {perf_data['resourceLoadTime']}ms

📦 Resource Stats:
- Total Resources: {perf_data['resourceStats']['totalResources']}
- Total Size: {float(perf_data['resourceStats']['totalSize']) / 1024 if isinstance(perf_data['resourceStats']['totalSize'], (int, float)) else 0:.2f} KB
- Total Resource Duration: {perf_data['resourceStats']['totalDuration']}ms

🐢 Top 5 Slowest Resources:"""

        # Add slowest resources
        if perf_data['slowestResources']:
            for idx, resource in enumerate(perf_data['slowestResources'][:5]):
                summary += f"""
{idx+1}. {resource.get('url', 'N/A')} 
   - Duration: {resource.get('duration', 'N/A')}ms
   - Size: {resource.get('size', 0) / 1024:.2f} KB
   - Type: {resource.get('type', 'N/A')}"""
        else:
            summary += "\n- No resource data available"
        
        # Network summary
        summary += f"""

🌐 Network Request Summary for {current_url}:

📊 Overview:
- Total Requests: {network_data['totalRequests']}

📑 Requests by Type:"""

        # Add request types
        if network_data['byType']:
            for type_name, type_data in network_data['byType'].items():
                total_size = sum(r.get('size', 0) for r in type_data) / 1024
                summary += f"\n- {type_name.capitalize()}: {len(type_data)} requests ({total_size:.2f} KB)"
        else:
            summary += "\n- No request type data available"
        
        summary += "\n\n📋 Largest Requests:"
        
        # Add largest requests
        if network_data['largestRequests']:
            for idx, request in enumerate(network_data['largestRequests']):
                summary += f"""
{idx+1}. {request.get('url', 'N/A')} 
   - Size: {request.get('size', 0) / 1024:.2f} KB
   - Duration: {request.get('duration', 'N/A')}ms"""
        else:
            summary += "\n- No largest request data available"
        
        # Anomalies section
        summary += f"""

🔍 Top Anomalies for {current_url}:"""
        
        # Count total anomalies
        total_anomalies = sum(len(issues) for issues in anomalies_data.values())
        
        if total_anomalies > 0:
            # Add console errors
            if anomalies_data['consoleErrors']:
                summary += "\n\n🛑 Console Errors:"
                for idx, error in enumerate(anomalies_data['consoleErrors'][:5]):
                    summary += f"\n{idx+1}. {error}"
            
            # Add layout issues
            if anomalies_data['layoutIssues']:
                summary += "\n\n📐 Layout Issues:"
                for idx, issue in enumerate(anomalies_data['layoutIssues'][:5]):
                    summary += f"\n{idx+1}. {issue}"
            
            # Add network issues
            if anomalies_data['networkIssues']:
                summary += "\n\n🌐 Network Issues:"
                for idx, issue in enumerate(anomalies_data['networkIssues'][:5]):
                    summary += f"\n{idx+1}. {issue}"
            
            # Add performance issues
            if anomalies_data['performanceIssues']:
                summary += "\n\n⏱️ Performance Issues:"
                for idx, issue in enumerate(anomalies_data['performanceIssues'][:5]):
                    summary += f"\n{idx+1}. {issue}"
            
            # Add accessibility issues
            if anomalies_data['accessibilityIssues']:
                summary += "\n\n♿ Accessibility Issues:"
                for idx, issue in enumerate(anomalies_data['accessibilityIssues'][:5]):
                    summary += f"\n{idx+1}. {issue}"
        else:
            summary += "\n\n✅ No anomalies detected on this page!"
        
        # Store the generated report in the session metrics for later access
        controller._store_metric(current_url, "full_report", summary)
        
        # Print the full report for debugging
        print(f"\n==== FULL PERFORMANCE REPORT ====\n{summary}\n================================")
        
        # Format with clear visual markers to ensure it displays well in the UI
        formatted_summary = f"""
============ PERFORMANCE METRICS REPORT ============

{summary}

=================================================="""
        
        return formatted_summary
        
    except Exception as e:
        logger.error(f"❌ Error generating session summary: {str(e)}")
        # Even on error, return a formatted response with placeholders
        error_report = f"""📊 Page Performance Metrics for {page.url if page else "unknown"}:

⏱️ Timing Metrics:
- Page Load Time: N/A (Error occurred)
- DOM Content Loaded: N/A
- First Paint: N/A
- First Contentful Paint: N/A

🔄 Connection Metrics:
- DNS Lookup: N/A
- TCP Connection: N/A
- Server Response: N/A

⚙️ Processing Metrics:
- DOM Processing: N/A
- Resource Loading: N/A

📦 Resource Stats:
- Total Resources: N/A
- Total Size: 0.00 KB
- Total Resource Duration: N/A

🐢 Top 5 Slowest Resources:
- No resource data available

🌐 Network Request Summary:
📊 Overview:
- Total Requests: N/A

📑 Requests by Type:
- No request type data available

📋 Largest Requests:
- No largest request data available

🔍 Top Anomalies:
⚠️ Error generating report: {str(e)}"""
        
        # Store the error report for consistency
        if page:
            controller._store_metric(page.url, "full_report", error_report)
            
        return error_report

@controller.action('Show performance metrics')
def show_performance_metrics() -> str:
    """Forces the display of performance metrics for the current page, bypassing any async issues."""
    logger.info("🔍 User explicitly requested to show performance metrics")
    try:
        # First try to get any existing full report from the session data
        session_data = controller._get_current_session_metrics()
        pages = session_data.get("pages", {})
        
        # Look for any existing reports
        for url, page_data in pages.items():
            if "full_report" in page_data:
                logger.info(f"✅ Found existing performance report for {url}")
                return page_data["full_report"]
        
        # If we don't have a full report, try to create a basic report from available data
        best_url = None
        best_metrics = None
        
        # Find the page with the most metrics
        for url, page_data in pages.items():
            metric_count = len(page_data)
            if best_url is None or metric_count > len(best_metrics):
                best_url = url
                best_metrics = page_data
        
        if best_url and best_metrics:
            logger.info(f"📊 Creating basic report for {best_url} from available metrics")
            
            # Create a formatted report from whatever metrics we have
            report = f"""📊 Page Performance Metrics for {best_url}:

"""
            
            # Add performance data if available
            if "performance" in best_metrics:
                perf = best_metrics["performance"]
                report += """⏱️ Timing Metrics:
"""
                # Add whatever performance metrics are available
                if "pageLoadTime" in perf:
                    report += f"- Page Load Time: {perf['pageLoadTime']}ms\n"
                if "domContentLoaded" in perf:
                    report += f"- DOM Content Loaded: {perf['domContentLoaded']}ms\n"
                if "firstPaint" in perf:
                    report += f"- First Paint: {perf['firstPaint']}ms\n"
                if "firstContentfulPaint" in perf:
                    report += f"- First Contentful Paint: {perf['firstContentfulPaint']}ms\n"
                
                # Add resource info if available
                if "resourceStats" in perf:
                    stats = perf["resourceStats"]
                    report += f"""
📦 Resource Stats:
- Total Resources: {stats.get('totalResources', 'N/A')}
- Total Size: {float(stats.get('totalSize', 0)) / 1024:.2f} KB
- Total Duration: {stats.get('totalDuration', 'N/A')}ms
"""
            
            # Add network data if available
            if "network" in best_metrics:
                network = best_metrics["network"]
                report += f"""
🌐 Network Request Summary:
- Total Requests: {network.get('totalRequests', 'N/A')}
"""
            
            # Add anomalies if available
            if "anomalies" in best_metrics:
                anomalies = best_metrics["anomalies"]
                total_issues = sum(len(issues) for k, issues in anomalies.items() if isinstance(issues, list))
                
                report += f"""
🔍 Anomalies Detected: {total_issues}
"""
                
                # Add some details about the anomalies
                for category, issues in anomalies.items():
                    if isinstance(issues, list) and len(issues) > 0:
                        report += f"- {len(issues)} {category}\n"
            
            # Store this report for future reference
            controller._store_metric(best_url, "full_report", report)
            return report
        
        # If we have no metrics at all, return a message
        return """📊 Performance Metrics:

No performance data has been collected yet.

To collect detailed metrics, please try:
1. "Generate performance report"
2. "Get session exploration summary"

These commands will analyze the current page and gather performance data."""
        
    except Exception as e:
        logger.error(f"❌ Error in show_performance_metrics: {str(e)}")
        return f"""📊 Performance Metrics:

⚠️ Error retrieving performance data: {str(e)}

To collect detailed metrics, please try again with:
"Generate performance report" """

def yield_data(
    browser_state: "BrowserState", agent_output: "AgentOutput", step_number: int
):
    """Callback function for each step - modified to ensure action memory appears"""
    try:
        # Always log for debugging
        logger.info(f"🔄 yield_data called for step {step_number}")
        
        # Add a local static variable to track if we've already processed a done action
        if not hasattr(yield_data, "_done_processed"):
            yield_data._done_processed = False
        
        # Format Previous Goal (only for steps after the first few)
        if step_number > 2 and agent_output.current_state.evaluation_previous_goal:
            message = AIMessage(content=f"*Previous Goal*:\n{agent_output.current_state.evaluation_previous_goal}")
            asyncio.get_event_loop().call_soon_threadsafe(queue.put_nowait, message)
            asyncio.get_event_loop().call_soon_threadsafe(queue.put_nowait, {"stop": True})
            logger.info("✅ Sent Previous Goal")
        
        # Format Memory - Always show this
        if agent_output.current_state.memory:
            message = AIMessage(content=f"*Memory*:\n{agent_output.current_state.memory}")
            asyncio.get_event_loop().call_soon_threadsafe(queue.put_nowait, message)
            asyncio.get_event_loop().call_soon_threadsafe(queue.put_nowait, {"stop": True})
            logger.info("✅ Sent Memory")
        
        # Format Next Goal - Always show this
        if agent_output.current_state.next_goal:
            message = AIMessage(content=f"*Next Goal*:\n{agent_output.current_state.next_goal}")
            asyncio.get_event_loop().call_soon_threadsafe(queue.put_nowait, message)
            asyncio.get_event_loop().call_soon_threadsafe(queue.put_nowait, {"stop": True})
            logger.info("✅ Sent Next Goal")
        
        # Format Tool calls (from actions)
        tool_calls = []
        tool_outputs = []
        
        # First check if any 'done' action is in the current step
        has_done_action = False
        for action_model in agent_output.action:
            for key, value in action_model.model_dump().items():
                if key == "done" and value:
                    has_done_action = True
                    break
            if has_done_action:
                break
                
        # If we have a done action and already processed one before, skip processing this entire step
        if has_done_action and (yield_data._done_processed or controller.finished):
            logger.info("🛑 Skipping duplicate done action in step processing")
            return
            
        # Process each action model
        for action_model in agent_output.action:
            logger.info(f"🔧 Processing action: {action_model}")
            for key, value in action_model.model_dump().items():
                if value:
                    if key == "done":
                        # When the agent is done, show the completion message
                        logger.info(f"✅ Agent completed task: {value['text']}")
                        
                        # Check if controller is already finished to prevent multiple reports
                        if controller.finished or yield_data._done_processed:
                            logger.info("⏭️ Controller already finished, skipping report generation")
                            # Just send the done message without additional report
                            done_message = f"<div style='font-size:16px;padding:10px;'>✅ {value['text']}</div>"
                            asyncio.get_event_loop().call_soon_threadsafe(
                                queue.put_nowait, AIMessage(content=done_message)
                            )
                            logger.info(f"✅ Sent basic done message: {done_message[:100]}...")
                            asyncio.get_event_loop().call_soon_threadsafe(
                                queue.put_nowait, {"stop": True}
                            )
                            continue
                            
                        # Set controller as finished before generating report
                        controller.finished = True
                        yield_data._done_processed = True
                        
                        # Try to get a performance report to combine with the done message
                        try:
                            report = show_performance_metrics()
                            if report:
                                # Create a visually prominent message for UI display
                                logger.info("📊 Combining done message with performance report")
                                done_message = f"<div style='font-size:16px;padding:10px;background:#f0f0f0;border-radius:8px;margin:10px 0;'>✅ {value['text']}</div>"
                                report_message = f"<div style='font-size:15px;padding:15px;background:#f8f8f8;border-radius:8px;border:2px solid #ddd;margin:15px 0;white-space:pre-wrap;'>{report}</div>"
                                combined_message = f"{done_message}\n\n{report_message}"
                                
                                # Log the combined message length for debugging
                                logger.info(f"📏 Combined message length: {len(combined_message)}")
                                logger.info(f"📄 First 100 chars: {combined_message[:100]}...")
                                
                                # Send the combined message
                                asyncio.get_event_loop().call_soon_threadsafe(
                                    queue.put_nowait, AIMessage(content=combined_message)
                                )
                                asyncio.get_event_loop().call_soon_threadsafe(
                                    queue.put_nowait, {"stop": True}
                                )
                                return
                        except Exception as e:
                            logger.error(f"❌ Error generating report in done action: {str(e)}")
                        
                        # If we couldn't generate a report, just send the done message
                        asyncio.get_event_loop().call_soon_threadsafe(
                            queue.put_nowait, AIMessage(content=value["text"])
                        )
                        asyncio.get_event_loop().call_soon_threadsafe(
                            queue.put_nowait, {"stop": True}
                        )
                            
                    else:
                        # For other actions, create a tool call
                        id = str(uuid.uuid4())
                        logger.info(f"🔧 Creating tool call for {key} with ID {id}")
                        value = {k: v for k, v in value.items() if v is not None}
                        tool_calls.append(
                            {"name": key, "args": value, "id": f"tool_call_{id}"}
                        )
                        tool_outputs.append(
                            ToolMessage(content="", tool_call_id=f"tool_call_{id}")
                        )
        
        # Send tool calls if there are any
        if tool_calls:
            logger.info(f"🔧 Sending {len(tool_calls)} tool calls")
            asyncio.get_event_loop().call_soon_threadsafe(
                queue.put_nowait, AIMessage(content="", tool_calls=tool_calls)
            )
            for tool_output in tool_outputs:
                asyncio.get_event_loop().call_soon_threadsafe(queue.put_nowait, tool_output)
    
    except Exception as e:
        logger.error(f"❌ Error in yield_data: {str(e)}")
        # Try to recover by sending a basic message
        try:
            asyncio.get_event_loop().call_soon_threadsafe(
                queue.put_nowait, AIMessage(content=f"Error processing agent step: {str(e)}")
            )
        except:
            pass

def yield_done(history: "AgentHistoryList"):
    """Callback when the agent completes its task."""
    try:
        # Always log for debugging
        logger.info(f"🔄 yield_done called, task completed")
        
        # Check if we've already processed a done action via the yield_data function
        if hasattr(yield_data, "_done_processed") and yield_data._done_processed:
            logger.info("⏭️ Done action already processed in yield_data, skipping yield_done processing")
            
            # Don't send END signal here - let the main loop handle that
            # This prevents cutting off the report that might still be in the queue
            logger.info("⏸️ Not sending END signal immediately to allow report processing")
            return
        
        # Check if controller is already finished - if so, skip duplicate report
        if controller.finished:
            logger.info("⏭️ Controller already finished, skipping duplicate report in yield_done")
            
            # Still signal the end of the agent's work, but with a small delay
            try:
                # Use a small delay to ensure any pending messages are processed first
                loop = asyncio.get_event_loop()
                loop.call_later(1.0, lambda: asyncio.get_event_loop().call_soon_threadsafe(
                    queue.put_nowait, "END"))
                logger.info("✅ Scheduled END signal in yield_done with delay")
            except Exception as e:
                logger.error(f"❌ Error scheduling END signal in yield_done: {str(e)}")
            return
        
        # Mark controller as finished and the done action as processed
        controller.finished = True
        if hasattr(yield_data, "_done_processed"):
            yield_data._done_processed = True
            logger.info("✅ Marked yield_data._done_processed = True from yield_done")
        
        # Try to get the performance report using our specialized function
        try:
            # Use the display_performance_report function to get a nicely formatted report
            report = display_performance_report()
            
            # Create a basic completion message
            completion_message = "Task completed successfully."
            
            # Combine with the report
            combined_message = f"{completion_message}\n\n{report}"
            
            # Log what we're sending
            logger.info(f"📊 Sending combined completion message with performance report (length: {len(combined_message)})")
            print(f"🚨 YIELD_DONE SENDING COMBINED MESSAGE WITH REPORT (LENGTH: {len(combined_message)})")
            
            # Send the combined message
            asyncio.get_event_loop().call_soon_threadsafe(
                queue.put_nowait, AIMessage(content=combined_message)
            )
            
            # Add a delay before sending END
            loop = asyncio.get_event_loop()
            loop.call_later(1.0, lambda: asyncio.get_event_loop().call_soon_threadsafe(
                queue.put_nowait, "END"))
            logger.info("⏱️ Scheduled END signal after report with 1s delay")
            return
        except Exception as e:
            logger.error(f"❌ Error generating report in yield_done: {str(e)}")
            
            # If report generation fails, send a basic message
            basic_message = """
<div style="padding:20px; background:#f5f5f5; border:2px solid #ccc; border-radius:10px; margin:20px 0;">
    <h2 style="color:#2c3e50; text-align:center; border-bottom:1px solid #ccc; padding-bottom:10px; margin-bottom:15px;">✅ TASK COMPLETED</h2>
    <p style="font-size:16px; line-height:1.5; text-align:center;">
        Task completed successfully.<br/>
        Try "Display performance report" to see metrics.
    </p>
</div>
"""
            asyncio.get_event_loop().call_soon_threadsafe(
                queue.put_nowait, AIMessage(content=basic_message)
            )
            
            # Send END with a small delay
            loop = asyncio.get_event_loop()
            loop.call_later(0.5, lambda: asyncio.get_event_loop().call_soon_threadsafe(
                queue.put_nowait, "END"))
            logger.info("⏱️ Scheduled END signal after basic message with 0.5s delay")
            return
            
    except Exception as e:
        logger.error(f"❌ Error in yield_done: {str(e)}")
    
    # If we reached here, something went wrong, still signal the end of the agent's work
    try:
        asyncio.get_event_loop().call_soon_threadsafe(queue.put_nowait, "END")
        logger.info("✅ Sent END signal in yield_done (fallback)")
    except Exception as e:
        logger.error(f"❌ Error sending END signal in yield_done: {str(e)}")

async def browser_use_agent(
    model_config: ModelConfig,
    agent_settings: AgentSettings,
    history: List[Mapping[str, Any]],
    session_id: str,
    cancel_event: Optional[asyncio.Event] = None,
) -> AsyncIterator[str]:
    global _agent_resumed
    global session_metrics_storage # Access global storage
    global queue  # Make sure queue is accessible globally

    logger.info("🚀 Starting browser_use_agent with session_id: %s", session_id)
    logger.info("🔧 Model config: %s", model_config)
    logger.info("⚙️ Agent settings: %s", agent_settings)

    # Reset static variables for yield_data function
    if hasattr(yield_data, "_done_processed"):
        yield_data._done_processed = False
        logger.info("🔄 Reset yield_data._done_processed flag")

    # Clear previous metrics for this session ID at the start of a new run
    if session_id in session_metrics_storage:
        logger.info("🧹 Clearing previous session metrics for session_id: %s", session_id)
        del session_metrics_storage[session_id]
    # Re-initialize defaultdict entry
    session_metrics_storage[session_id]

    llm, use_vision = create_llm(model_config)
    logger.info("🤖 Created LLM instance")

    # Set the session_id in the controller
    controller.set_session_id(session_id) # This will also ensure the session exists in storage
    
    # Explicitly reset the finished flag for this run
    controller.finished = False
    logger.info("🔄 Explicitly reset controller.finished flag for new agent run")
    
    # Reset the resumed flag at the start of a new session
    _agent_resumed = False

    browser = None
    browser_context = None
    queue = asyncio.Queue()  # Create a new queue for this session

    # Check if we already have a browser for this session
    if session_id in active_browsers:
        logger.info("🔄 Reusing existing browser for session: %s", session_id)
        browser = active_browsers[session_id]
        browser_context = active_browser_contexts[session_id]
    else:
        # Create a new browser instance
        logger.info("🌐 Creating new browser for session: %s", session_id)
        browser = Browser(
            BrowserConfig(
                cdp_url=f"{STEEL_CONNECT_URL}?apiKey={STEEL_API_KEY}&sessionId={session_id}"
            )
        )
        # Use our custom browser context instead of the default one.
        browser_context = BrowserContext(browser=browser)
        
        # Store for future use
        active_browsers[session_id] = browser
        active_browser_contexts[session_id] = browser_context
        
        # Set up monitoring hooks
        await setup_browser_monitoring_hooks(browser_context)

    agent = Agent(
        llm=llm,
        task=history[-1]["content"],
        controller=controller,
        browser=browser,
        browser_context=browser_context,
        generate_gif=False,
        use_vision=use_vision,
        register_new_step_callback=yield_data,
        register_done_callback=yield_done,
        system_prompt_class=ExtendedSystemPrompt,
    )
    logger.info("🌐 Created Agent with browser instance (use_vision=%s)", use_vision)

    # Set the agent in the controller
    controller.set_agent(agent)

    steps = agent_settings.steps or 25
    
    # Add a flag to track if done was called
    done_called = False
    # Add a variable to store the final report
    final_report = None

    agent_task = asyncio.create_task(agent.run(steps))
    logger.info("▶️ Started agent task with %d steps", steps)

    # Store special messages until agent is resumed
    pending_special_messages = []
    
    # Add a flag to track whether we've stored messages while paused
    has_pending_messages = False
    
    try:
        while True:
            if cancel_event and cancel_event.is_set():
                agent.stop()
                agent_task.cancel()
                break
            if agent._too_many_failures():
                break
                
            # Wait for data from the queue
            try:
                # Use a timeout to regularly check the _agent_resumed flag
                data = await asyncio.wait_for(queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                # Check if agent was resumed while we were waiting
                if _agent_resumed and has_pending_messages:
                    logger.info("🔄 Agent was resumed while waiting for queue data, releasing pending messages")
                    for msg in pending_special_messages:
                        yield msg
                    pending_special_messages = []
                    has_pending_messages = False
                continue
                
            if data == "END":  # You'll need to send this when done
                break
            
            # Check if agent was resumed - if so, release any pending special messages
            if _agent_resumed and pending_special_messages:
                logger.info(f"🔄 Agent resumed, releasing {len(pending_special_messages)} pending messages")
                # First yield all pending special messages
                for msg in pending_special_messages:
                    yield msg
                pending_special_messages = []  # Clear the pending messages
                has_pending_messages = False
            
            # Check if this is a completion ('done' action) message or a combined report message
            is_done_or_report_message = (
                isinstance(data, AIMessage) and 
                not data.tool_calls and
                (controller.finished or 
                 (data.content and ("📊" in data.content or "<div" in data.content or "PERFORMANCE REPORT" in data.content)))
            )
            
            # Log details about the message for debugging
            if isinstance(data, AIMessage) and data.content:
                content_preview = data.content[:100] + "..." if len(data.content) > 100 else data.content
                print(f"🚨 PROCESSING MESSAGE: {content_preview}")
                print(f"🚨 IS DONE/REPORT: {is_done_or_report_message}, HAS HTML: {'<div' in data.content}, HAS EMOJI: {'📊' in data.content}")
                
            # If we've already seen a done message, and this is another one, skip it
            if is_done_or_report_message and done_called:
                logger.info("🛑 Skipping duplicate done/report message, agent already completed")
                continue
                
            # If this is a done or report message, mark that we've seen one
            if is_done_or_report_message:
                done_called = True
                logger.info("✅ Detected done/report message, will prevent further processing")
                
                # Save as final_report if it contains performance metrics
                if data.content and "📊" in data.content:
                    final_report = data
                    logger.info("📊 Saved message as final report")
                
                # Yield this message
                yield data
                
                # Wait for a short time to ensure any report messages get processed
                # This is crucial to allow the performance report to be displayed
                logger.info("⏳ Waiting a short time before stopping agent...")
                await asyncio.sleep(0.5)
                
                # Now force stop agent
                try:
                    logger.info("🛑 Forcing agent to stop after yielding report")
                    # Terminate the task after yielding the message
                    agent.stop()
                    agent_task.cancel()
                    break
                except Exception as e:
                    logger.error(f"❌ Error stopping agent task: {str(e)}")
                continue
            
            # If this is a special message (Memory, Next Goal, etc)
            is_special_message = (
                isinstance(data, AIMessage) and 
                data.content and (
                    "*Memory*:" in data.content or 
                    "*Next Goal*:" in data.content or 
                    "*Previous Goal*:" in data.content
                )
            )
            
            if is_special_message:
                if _agent_resumed or agent._paused == False:
                    # If agent is resumed or was never paused, send the message immediately
                    yield data
                else:
                    # Otherwise, store it for later
                    logger.info("📊 Storing special message for later delivery (agent is paused)")
                    pending_special_messages.append(data)
                    has_pending_messages = True
            else:
                # For non-special messages, always yield them unless we already called done
                if not (done_called and controller.finished):
                    yield data
    finally:
        # Make sure to yield the final report if we have one and haven't sent it yet
        if final_report:
            try:
                logger.info("📊 Yielding final performance report before exit")
                # Check if it's already a well-formatted report
                if not (isinstance(final_report, AIMessage) and final_report.content and "PERFORMANCE REPORT" in final_report.content):
                    # Format it more clearly if it's not already formatted
                    content = final_report.content if isinstance(final_report, AIMessage) else str(final_report)
                    # Create a new message with better formatting
                    formatted_message = AIMessage(content=f"""
----------- FINAL PERFORMANCE REPORT -----------

{content}

---------------------------------------""")
                    yield formatted_message
                else:
                    # If it's already well-formatted, just yield it as is
                    yield final_report
            except Exception as e:
                logger.error(f"❌ Error yielding final report: {str(e)}")
                # Try one more time with simplified formatting
                try:
                    yield AIMessage(content=f"⚠️ Final Report: {str(final_report)}")
                except:
                    pass
        
        # Always display the final report at the end, no matter what
        try:
            logger.info("📊 Generating final HTML performance report")
            # Get the HTML report directly
            html_report = force_display_report()
            
            # Send it to the queue directly
            if queue:
                logger.info("📊 Sending final HTML performance report to queue")
                # Use the current event loop which we know exists in this context
                asyncio.get_event_loop().call_soon_threadsafe(
                    queue.put_nowait, AIMessage(content=html_report)
                )
                # Short delay to ensure report is processed
                await asyncio.sleep(0.5)
                # Then queue the END signal
                asyncio.get_event_loop().call_soon_threadsafe(
                    queue.put_nowait, "END"
                )
                logger.info("⏱️ Scheduled END signal after HTML report")
            else:
                logger.warning("⚠️ Queue not available for final report display")
        except Exception as e:
            logger.error(f"❌ Error generating final report: {str(e)}")
            # Try to send END even on error
            if queue:
                try:
                    asyncio.get_event_loop().call_soon_threadsafe(
                        queue.put_nowait, "END"
                    )
                except Exception:
                    pass
        
        # Reset the done_processed flag in finally block
        if hasattr(yield_data, "_done_processed"):
            yield_data._done_processed = False
            logger.info("🔄 Reset yield_data._done_processed flag in finally block")
        
        # We're intentionally not closing the browser instance here to allow for resuming
        # The browser instances will be managed by the Steel API and cleaned up when the session expires
        pass

async def setup_browser_monitoring_hooks(browser_context: BrowserContext):
    """Setup event listeners for monitoring page navigation and network activity."""
    try:
        # Monitor for new pages and navigation events
        async def on_page_created(page):
            logger.info(f"📄 New page created: {page.url}")
            await inject_monitoring_scripts(page)
            
            # Set up page event listeners
            await page.add_event_listener("load", lambda: asyncio.create_task(on_page_load(page)))
            
        # Handle page load events
        async def on_page_load(page):
            logger.info(f"📄 Page loaded: {page.url}")
            await inject_monitoring_scripts(page)
        
        # Attach the event listeners to browser context
        browser_context.on_page_created(on_page_created)
        
        logger.info("✅ Successfully set up browser monitoring hooks")
    except Exception as e:
        logger.error(f"❌ Error setting up browser monitoring hooks: {str(e)}")

async def inject_monitoring_scripts(page):
    """Injects JavaScript into the page to track network requests and console errors."""
    try:
        await page.evaluate("""() => {
            // Create a namespace for the browser-use monitoring tools
            // Only initialize if it doesn't exist yet
            if (!window.__BROWSER_USE_MONITOR) {
                window.__BROWSER_USE_MONITOR = {
                    networkRequests: [],
                    networkErrors: [],
                    consoleErrors: [],
                    initialized: false
                };
                
                console.log('[browser-use] Initializing performance monitoring');
                
                // Track XHR requests
                const originalXhrOpen = XMLHttpRequest.prototype.open;
                const originalXhrSend = XMLHttpRequest.prototype.send;
                
                XMLHttpRequest.prototype.open = function(method, url) {
                    this.__requestData = { method, url, type: 'xhr', startTime: performance.now(), status: 'pending' };
                    window.__BROWSER_USE_MONITOR.networkRequests.push(this.__requestData);
                    return originalXhrOpen.apply(this, arguments);
                };
                
                XMLHttpRequest.prototype.send = function() {
                    if (this.__requestData) {
                        const request = this.__requestData;
                        
                        this.addEventListener('load', function() {
                            request.status = this.status;
                            request.duration = performance.now() - request.startTime;
                            request.size = parseInt(this.getResponseHeader('Content-Length') || '0');
                        });
                        
                        this.addEventListener('error', function() {
                            request.status = 'failed';
                            request.duration = performance.now() - request.startTime;
                            const errorMsg = `XHR failed: ${request.method} ${request.url}`;
                            window.__BROWSER_USE_MONITOR.networkErrors.push(errorMsg);
                        });
                        
                        this.addEventListener('timeout', function() {
                            request.status = 'timeout';
                            request.duration = performance.now() - request.startTime;
                            const errorMsg = `XHR timeout: ${request.method} ${request.url}`;
                            window.__BROWSER_USE_MONITOR.networkErrors.push(errorMsg);
                        });
                    }
                    return originalXhrSend.apply(this, arguments);
                };
                
                // Track fetch requests
                const originalFetch = window.fetch;
                window.fetch = function(resource, init) {
                    const url = typeof resource === 'string' ? resource : resource.url;
                    const method = init?.method || (typeof resource === 'string' ? 'GET' : resource.method || 'GET');
                    
                    const requestData = { 
                        method, 
                        url, 
                        type: 'fetch', 
                        startTime: performance.now(), 
                        status: 'pending' 
                    };
                    
                    window.__BROWSER_USE_MONITOR.networkRequests.push(requestData);
                    
                    return originalFetch.apply(this, arguments)
                        .then(response => {
                            requestData.status = response.status;
                            requestData.duration = performance.now() - requestData.startTime;
                            
                            if (!response.ok) {
                                const errorMsg = `Fetch error ${response.status}: ${method} ${url}`;
                                window.__BROWSER_USE_MONITOR.networkErrors.push(errorMsg);
                            }
                            
                            return response;
                        })
                        .catch(error => {
                            requestData.status = 'failed';
                            requestData.duration = performance.now() - requestData.startTime;
                            
                            const errorMsg = `Fetch failed: ${method} ${url} - ${error.message}`;
                            window.__BROWSER_USE_MONITOR.networkErrors.push(errorMsg);
                            
                            throw error;
                        });
                };
                
                // Track console errors
                window.addEventListener('error', (e) => {
                    window.__BROWSER_USE_MONITOR.consoleErrors.push(`${e.message} at ${e.filename}:${e.lineno}`);
                });
                
                // Override console.error to capture error messages
                const originalConsoleError = console.error;
                console.error = function() {
                    window.__BROWSER_USE_MONITOR.consoleErrors.push(Array.from(arguments).join(' '));
                    originalConsoleError.apply(console, arguments);
                };
                
                window.__BROWSER_USE_MONITOR.initialized = true;
                console.log('[browser-use] Performance monitoring initialized');
            } else {
                console.log('[browser-use] Performance monitoring already initialized');
            }
        }""")
        logger.info("Successfully injected monitoring scripts")
    except Exception as e:
        logger.error(f"Error injecting monitoring scripts: {str(e)}")

@controller.action('Get real-time network activity')
async def get_real_time_network_activity() -> str:
    """Gets the most recent network requests and activities that have occurred on the page."""
    if not controller.agent or not controller.agent.browser_context:
        return "No active browser context found"
    
    try:
        # Get the current page
        page = await controller.agent.browser_context.get_current_page()
        
        # Get the real-time network data
        network_data = await page.evaluate("""() => {
            // Make sure our namespace is initialized
            if (!window.__BROWSER_USE_MONITOR) {
                window.__BROWSER_USE_MONITOR = {
                    networkRequests: [],
                    networkErrors: [],
                    consoleErrors: [],
                    initialized: false
                };
            }
            
            // Get the most recent requests (last 20)
            const recentRequests = window.__BROWSER_USE_MONITOR.networkRequests
                .slice(-20)
                .map(req => ({
                    url: req.url,
                    method: req.method,
                    type: req.type,
                    status: req.status,
                    duration: req.duration || 0,
                    startTime: req.startTime
                }));
                
            // Calculate some stats
            const inProgressRequests = window.__BROWSER_USE_MONITOR.networkRequests.filter(req => req.status === 'pending').length;
            const completedRequests = window.__BROWSER_USE_MONITOR.networkRequests.filter(req => req.status !== 'pending').length;
            const failedRequests = window.__BROWSER_USE_MONITOR.networkRequests.filter(req => req.status === 'failed' || 
                (typeof req.status === 'number' && (req.status < 200 || req.status >= 400))).length;
            
            // Get errors
            const errors = window.__BROWSER_USE_MONITOR.networkErrors.slice(-10); // Last 10 errors
            
            return {
                recentRequests,
                stats: {
                    totalTracked: window.__BROWSER_USE_MONITOR.networkRequests.length,
                    inProgress: inProgressRequests,
                    completed: completedRequests,
                    failed: failedRequests
                },
                errors
            };
        }""")
        
        # Format the results
        formatted_result = f"""
        🌐 Real-time Network Activity for {page.url}:
        
        📊 Current Stats:
        - Total Tracked Requests: {network_data['stats']['totalTracked']}
        - In Progress: {network_data['stats']['inProgress']}
        - Completed: {network_data['stats']['completed']}
        - Failed: {network_data['stats']['failed']}
        """
        
        # Add recent requests
        if network_data['recentRequests']:
            formatted_result += "\n        📋 Most Recent Requests:"
            for idx, req in enumerate(reversed(network_data['recentRequests'][:10])):  # Show last 10 in reverse order
                status_emoji = "✅" if req['status'] >= 200 and req['status'] < 400 else "❌" if req['status'] != 'pending' else "⏳"
                formatted_result += f"""
        {idx+1}. {status_emoji} {req['method']} {req['url']} 
           - Status: {req['status']}
           - Type: {req['type']}
           - Duration: {req['duration']:.2f}ms"""
        
        # Add errors if any
        if network_data['errors']:
            formatted_result += "\n\n        ⚠️ Recent Network Errors:"
            for idx, error in enumerate(network_data['errors']):
                formatted_result += f"\n        {idx+1}. {error}"
        
        return formatted_result
        
    except Exception as e:
        logger.error(f"❌ Error getting real-time network activity: {str(e)}")
        return f"Failed to get real-time network activity: {str(e)}"

@controller.action('Done')
def done(text: str) -> str:
    """Marks the task as complete and returns any final information."""
    
    # Always print the raw text for debugging
    print(f"🚨 DONE ACTION CALLED WITH TEXT: {text}")
    
    # Get the completion message ready
    completion_message = f"✅ {text}"
    
    # First mark the controller as finished (regardless of if it was already finished)
    controller.finished = True
    logger.info("✅ Marked controller as finished in done action")
    
    # Now call display_performance_report to get the report
    try:
        report = display_performance_report()
        
        # Combine completion message with report
        combined_message = f"{completion_message}\n\n{report}"
        
        # Log for debugging
        print(f"🚨 RETURNING COMBINED COMPLETION MESSAGE AND REPORT (LENGTH: {len(combined_message)})")
        logger.info(f"📊 Successfully combined completion message with performance report (length: {len(combined_message)})")
        
        return combined_message
    except Exception as e:
        logger.error(f"❌ Error calling display_performance_report in done action: {str(e)}")
        # Even if report fails, still return completion message
        return completion_message

# Create a function to run get_session_summary with a timeout
async def run_get_session_summary_with_timeout(timeout=20):
    """Try to run get_session_summary with a timeout"""
    try:
        # Use asyncio.wait_for to implement the timeout
        return await asyncio.wait_for(get_session_summary(), timeout)
    except asyncio.TimeoutError:
        logger.error(f"❌ Timeout running get_session_summary after {timeout} seconds")
        return None
    except Exception as e:
        logger.error(f"❌ Error running get_session_summary: {str(e)}")
        return None

# Add action to explicitly run the session summary
@controller.action('Generate performance report')
async def generate_performance_report() -> str:
    """Generate a complete performance report for the current page."""
    logger.info("🔍 Explicitly generating performance report")
    try:
        # Run get_session_summary with a timeout
        result = await run_get_session_summary_with_timeout()
        if result:
            return result
        else:
            # Fallback to get_latest_report if get_session_summary fails
            return get_latest_report()
    except Exception as e:
        logger.error(f"❌ Error in generate_performance_report: {str(e)}")
        return f"""📊 Page Performance Summary:

⚠️ Error generating performance report: {str(e)}

🔍 Please try running "Get session exploration summary" directly."""

# Add a direct action to get the latest report without async operations
@controller.action('Get latest report')
def get_latest_report() -> str:
    """Gets the most recent full report from session data."""
    try:
        session_data = controller._get_current_session_metrics()
        pages = session_data.get("pages", {})
        
        # Try to find any report
        for url, page_data in pages.items():
            if "full_report" in page_data:
                logger.info(f"✅ Found and returning existing report for {url}")
                return page_data["full_report"]
        
        # If no report found, generate a basic one
        return f"""📊 Page Performance Summary:

No detailed performance metrics available.

🔍 Please run "Get session exploration summary" to generate detailed metrics."""
    
    except Exception as e:
        logger.error(f"❌ Error in get_latest_report: {str(e)}")
        return f"""📊 Page Performance Summary:

⚠️ Error retrieving performance data: {str(e)}

🔍 Please try running "Get session exploration summary" again."""

@controller.action('Show complete performance report')
def show_complete_performance_report() -> str:
    """Retrieves or generates a complete performance report to show the user."""
    logger.info("🔍 User explicitly requested to show complete performance report")
    
    try:
        # Step 1: Try to find an existing report
        session_data = controller._get_current_session_metrics()
        pages = session_data.get("pages", {})
        
        # Check if we already have a report in any page
        for url, page_data in pages.items():
            if "full_report" in page_data:
                logger.info(f"✅ Found existing full report for {url}")
                return f"""--- COMPLETE PERFORMANCE REPORT ---

{page_data['full_report']}

--- END OF REPORT ---

This is the full performance report for {url}."""
        
        # Step 2: If no report exists, tell the user what to do
        logger.info("⚠️ No existing report found, providing instructions")
        return """--- PERFORMANCE REPORT INSTRUCTIONS ---

No performance report has been generated yet. To generate a detailed report:

1. Use the "Generate performance report" action to create a complete report.
2. Or use the "Get session exploration summary" action for detailed metrics.

These will analyze the current page's performance, network activity, and potential issues."""
        
    except Exception as e:
        logger.error(f"❌ Error in show_complete_performance_report: {str(e)}")
        return f"""⚠️ Error retrieving performance report: {str(e)}

To generate a performance report, please try:
1. "Generate performance report" 
2. "Get session exploration summary"

These commands will analyze the current page and gather detailed metrics."""

@controller.action('Display performance report') 
def display_performance_report() -> str:
    """Force-displays the performance report with special formatting to ensure it's visible in the UI."""
    logger.info("🚨 FORCE-DISPLAYING PERFORMANCE REPORT")
    
    try:
        # First try to find an existing report
        session_data = controller._get_current_session_metrics()
        pages = session_data.get("pages", {})
        
        # Look for any report
        for url, page_data in pages.items():
            if "full_report" in page_data:
                full_report = page_data["full_report"]
                logger.info(f"✅ Found existing report for {url} to force-display")
                
                # Use special formatting that should be visible in the UI
                report_message = f"""
<div style="padding:20px; background:#f5f5f5; border:2px solid #ccc; border-radius:10px; margin:20px 0;">
    <h2 style="color:#2c3e50; text-align:center; border-bottom:1px solid #ccc; padding-bottom:10px; margin-bottom:15px;">🚀 PERFORMANCE REPORT 🚀</h2>
    <pre style="white-space:pre-wrap; font-family:monospace; background:#fff; padding:15px; border-radius:5px; font-size:14px; line-height:1.4;">
{full_report}
    </pre>
</div>
"""
                # Print for debugging
                print(f"🚨 FORCE-DISPLAYING REPORT WITH LENGTH: {len(report_message)}")
                return report_message
        
        # Try to generate a report if none exists
        try:
            report = show_performance_metrics()
            if report:
                # Use special formatting that should be visible in the UI
                report_message = f"""
<div style="padding:20px; background:#f5f5f5; border:2px solid #ccc; border-radius:10px; margin:20px 0;">
    <h2 style="color:#2c3e50; text-align:center; border-bottom:1px solid #ccc; padding-bottom:10px; margin-bottom:15px;">🚀 PERFORMANCE REPORT 🚀</h2>
    <pre style="white-space:pre-wrap; font-family:monospace; background:#fff; padding:15px; border-radius:5px; font-size:14px; line-height:1.4;">
{report}
    </pre>
</div>
"""
                print(f"🚨 FORCE-DISPLAYING GENERATED REPORT WITH LENGTH: {len(report_message)}")
                return report_message
        except Exception as e:
            logger.error(f"❌ Error generating report for force-display: {str(e)}")
        
        # Return a basic message if no report found
        return """
<div style="padding:20px; background:#f5f5f5; border:2px solid #ccc; border-radius:10px; margin:20px 0;">
    <h2 style="color:#2c3e50; text-align:center; border-bottom:1px solid #ccc; padding-bottom:10px; margin-bottom:15px;">🚀 PERFORMANCE REPORT 🚀</h2>
    <p style="font-size:16px; line-height:1.5; text-align:center;">
        No performance report has been generated yet.<br/>
        Try running "Get session exploration summary" to generate metrics.
    </p>
</div>
"""
        
    except Exception as e:
        logger.error(f"❌ Error in display_performance_report: {str(e)}")
        return f"""
<div style="padding:20px; background:#f5f5f5; border:2px solid #ccc; border-radius:10px; margin:20px 0;">
    <h2 style="color:#2c3e50; text-align:center; border-bottom:1px solid #ccc; padding-bottom:10px; margin-bottom:15px;">🚀 ERROR DISPLAYING REPORT 🚀</h2>
    <p style="color:#e74c3c; font-size:16px; line-height:1.5;">
        Error: {str(e)}
    </p>
    <p style="font-size:16px; line-height:1.5;">
        Try running "Get session exploration summary" again.
    </p>
</div>
"""

def force_display_report():
    """Special function to force the display of a performance report to the UI. Called at the very end of execution."""
    try:
        # Get the most recent report
        report = None
        report_content = "No performance data available"
        
        # Try to find any existing report
        session_data = controller._get_current_session_metrics()
        pages = session_data.get("pages", {})
        
        # Look for reports
        for url, page_data in pages.items():
            if "full_report" in page_data:
                report = page_data["full_report"]
                logger.info(f"✅ Found report for {url} in force_display_report")
                break
        
        # If we have a report, format it for display
        if report:
            report_content = report
        
        # Create HTML content for better visibility
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        .report-container {{
            padding: 20px;
            background: #f5f5f5;
            border: 2px solid #ccc;
            border-radius: 10px;
            margin: 20px 0;
            font-family: Arial, sans-serif;
        }}
        .report-title {{
            color: #2c3e50;
            text-align: center;
            border-bottom: 1px solid #ccc;
            padding-bottom: 10px;
            margin-bottom: 15px;
            font-size: 20px;
            font-weight: bold;
        }}
        .report-content {{
            white-space: pre-wrap;
            font-family: monospace;
            background: #fff;
            padding: 15px;
            border-radius: 5px;
            font-size: 14px;
            line-height: 1.4;
            overflow-x: auto;
        }}
    </style>
</head>
<body>
    <div class="report-container">
        <div class="report-title">🚀 PERFORMANCE REPORT 🚀</div>
        <div class="report-content">
{report_content}
        </div>
    </div>
</body>
</html>
"""
        
        # Print the HTML for debugging
        print(f"🚨 FORCE DISPLAY REPORT HTML (LENGTH: {len(html_content)})")
        print(f"🚨 FIRST 200 CHARS: {html_content[:200]}...")
        
        # Return the formatted HTML
        return html_content
        
    except Exception as e:
        logger.error(f"❌ Error in force_display_report: {str(e)}")
        return f"Error displaying performance report: {str(e)}"

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
    global _agent_resumed
    global session_metrics_storage
    
    logger.info("🚀 Starting browser_use_agent_batch with session_id: %s", session_id)
    logger.info("🔧 Model config: %s", model_config)
    logger.info("⚙️ Agent settings: %s", agent_settings)

    # Data collection container instead of a queue
    collected_data = {
        "metrics": {},
        "anomalies": {},
        "screenshots": {},
        "final_report": None,
        "memory": None,
        "goals": []
    }

    # --- Robust History Check ---
    if not history:
        logger.error("❌ Error in browser_use_agent_batch: History list is empty.")
        return "Error: Task history is empty."
    if not isinstance(history[-1], dict):
        logger.error(f"❌ Error in browser_use_agent_batch: Last history item is not a dictionary. Got: {type(history[-1])}")
        return f"Error: Invalid history format (last item type: {type(history[-1])})."
    if "content" not in history[-1]:
        logger.error(f"❌ Error in browser_use_agent_batch: Last history item is missing 'content' key. Got keys: {history[-1].keys()}")
        return "Error: Invalid history format (missing 'content' key)."
    if not isinstance(history[-1]["content"], str):
        logger.error(f"❌ Error in browser_use_agent_batch: History 'content' is not a string. Got type: {type(history[-1]['content'])}")
        return f"Error: Invalid history format (content type: {type(history[-1]['content'])})."

    task_description = history[-1]["content"]
    logger.info(f"✅ Extracted task description: {task_description[:100]}...")
    # --- End Robust History Check ---

    # Reset static variables for yield_data function
    if hasattr(yield_data, "_done_processed"):
        yield_data._done_processed = False
        logger.info("🔄 Reset yield_data._done_processed flag")

    # Clear previous metrics for this session ID at the start of a new run
    if session_id in session_metrics_storage:
        logger.info("🧹 Clearing previous session metrics for session_id: %s", session_id)
        del session_metrics_storage[session_id]
    # Re-initialize defaultdict entry
    session_metrics_storage[session_id]

    llm, use_vision = create_llm(model_config)
    logger.info("🤖 Created LLM instance")

    # Set the session_id in the controller
    controller.set_session_id(session_id) # This will also ensure the session exists in storage
    
    # Explicitly reset the finished flag for this run
    controller.finished = False
    logger.info("🔄 Explicitly reset controller.finished flag for new agent run")
    
    # Reset the resumed flag at the start of a new session
    _agent_resumed = False

    browser = None
    browser_context = None

    try:
        # Create a new browser instance (always new for batch mode)
        logger.info("🌐 Creating new browser for batch session: %s", session_id)
        browser = Browser(
            BrowserConfig(
                cdp_url=f"{STEEL_CONNECT_URL}?apiKey={STEEL_API_KEY}&sessionId={session_id}"
            )
        )
        # Use our custom browser context
        browser_context = BrowserContext(browser=browser)
        
        # Store for use during this batch session
        active_browsers[session_id] = browser
        active_browser_contexts[session_id] = browser_context
        
        # Set up monitoring hooks
        await setup_browser_monitoring_hooks(browser_context)

        # Define batch-specific callbacks
        def batch_yield_data(browser_state, agent_output, step_number):
            """Callback for each step - store data instead of yielding"""
            try:
                logger.info(f"🔄 batch_yield_data called for step {step_number}")
                
                # Store memory if available
                if agent_output.current_state.memory:
                    collected_data["memory"] = agent_output.current_state.memory
                    logger.info("✅ Stored memory")
                
                # Store previous goal
                if step_number > 2 and agent_output.current_state.evaluation_previous_goal:
                    collected_data["goals"].append({
                        "type": "previous",
                        "content": agent_output.current_state.evaluation_previous_goal,
                        "step": step_number
                    })
                    logger.info("✅ Stored previous goal")
                
                # Store next goal
                if agent_output.current_state.next_goal:
                    collected_data["goals"].append({
                        "type": "next",
                        "content": agent_output.current_state.next_goal,
                        "step": step_number
                    })
                    logger.info("✅ Stored next goal")
                
                # Check for done action
                for action_model in agent_output.action:
                    for key, value in action_model.model_dump().items():
                        if key == "done" and value:
                            # Set controller as finished
                            controller.finished = True
                            logger.info("✅ Marked agent as finished from batch_yield_data")
                
            except Exception as e:
                logger.error(f"❌ Error in batch_yield_data: {str(e)}")

        def batch_yield_done(history):
            """Callback when the agent completes - generate and store final report"""
            try:
                logger.info("✅ Agent completed task, generating final report")
                
                # Mark controller as finished
                controller.finished = True
                
                # Generate the report
                try:
                    report = display_performance_report()
                    collected_data["final_report"] = report
                    logger.info("📊 Generated and stored final performance report")
                except Exception as e:
                    logger.error(f"❌ Error generating report in batch_yield_done: {str(e)}")
                    # Create a basic report on error
                    collected_data["final_report"] = f"Error generating final report: {str(e)}"
                
            except Exception as e:
                logger.error(f"❌ Error in batch_yield_done: {str(e)}")

        # Create agent with batch callbacks
        agent = Agent(
            llm=llm,
            task=history[-1]["content"],
            controller=controller,
            browser=browser,
            browser_context=browser_context,
            generate_gif=False,
            use_vision=use_vision,
            register_new_step_callback=batch_yield_data,
            register_done_callback=batch_yield_done,
            system_prompt_class=ExtendedSystemPrompt,
        )
        logger.info("🌐 Created Agent with browser instance for batch mode (use_vision=%s)", use_vision)

        # Set the agent in the controller
        controller.set_agent(agent)

        # Get steps from settings
        steps = agent_settings.steps or 25
        logger.info(f"▶️ Running batch agent with {steps} steps using task: {task_description[:100]}...") # Log task usage

        # Run the agent and wait for completion
        await agent.run(steps)
        logger.info("✅ Agent run completed")
        
        # Ensure we have a final report
        if not collected_data["final_report"]:
            logger.info("📊 Generating final report after agent completion")
            try:
                # Use our existing report generation function
                collected_data["final_report"] = force_display_report()
            except Exception as e:
                logger.error(f"❌ Error generating force_display_report: {str(e)}")
                collected_data["final_report"] = "Error generating performance report after completion."
        
        # Return the final report
        logger.info("📄 Returning final report (length: %d)", 
                    len(collected_data["final_report"]) if collected_data["final_report"] else 0)
        return collected_data["final_report"]
        
    except Exception as e:
        logger.error(f"❌ Error in browser_use_agent_batch: {str(e)}")
        error_report = f"Error during batch execution: {str(e)}\n\n"
        
        # Try to get a basic report even on error
        try:
            basic_report = force_display_report()
            error_report += basic_report
        except Exception as report_error:
            error_report += f"Additionally, failed to generate error report: {str(report_error)}"
        
        return error_report
        
    finally:
        # Close browser and clean up resources
        try:
            if browser:
                await browser.close()
                logger.info(f"✅ Browser closed for batch session {session_id}")
        except Exception as e:
            logger.error(f"❌ Error closing browser: {str(e)}")
        
        # Remove from active browsers dictionary
        if session_id in active_browsers:
            del active_browsers[session_id]
            logger.info(f"✅ Removed session {session_id} from active_browsers")
            
        if session_id in active_browser_contexts:
            del active_browser_contexts[session_id]
            logger.info(f"✅ Removed session {session_id} from active_browser_contexts")
        
        # Reset controller status for this session
        if controller.session_id == session_id:
            controller.finished = False
            logger.info(f"✅ Reset controller.finished for session {session_id}")
        
        logger.info(f"✅ Batch agent execution complete for session {session_id}")