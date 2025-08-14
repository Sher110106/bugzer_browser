# Test Flow Management System

## Overview

The Test Flow Management System transforms the browser automation system from random behavior to a structured, predictable testing framework that captures entire user flows as requested in chat conversations.

## Key Features

- **Structured Testing**: Every request becomes a structured test with clear lifecycle
- **Complete Flow Capture**: Track entire user journeys, not just single pages
- **Test Metadata**: Store test context, user requests, and execution details
- **Step-by-Step Analysis**: Provide comprehensive view of what happened during the test
- **Performance Tracking**: Monitor performance across entire flows
- **Multiple Export Formats**: JSON, HTML, and Markdown reports

## Architecture

### Core Components

1. **TestFlowManager** (`api/utils/test_flow_manager.py`)
   - Manages test flow lifecycle
   - Stores test data and metadata
   - Generates performance summaries
   - Exports reports in multiple formats

2. **Lifecycle Hooks** (`api/utils/lifecycle_hooks.py`)
   - Provides clean integration points for test automation
   - Replaces complex yield_data/yield_done logic
   - Supports custom hook registration
   - Automatic step tracking with context managers

3. **Schemas** (`api/schemas.py`)
   - Defines data structures for test flows
   - Includes TestFlow, TestStepData, and related models
   - Supports extensible metadata and tagging

4. **API Endpoints** (`api/index.py`)
   - RESTful API for test flow management
   - Start, pause, resume, and complete test flows
   - Export reports and get summaries

## Usage

### Starting a Test Flow

```python
from api.utils.lifecycle_hooks import start_test_flow

# Start a new test flow
success = await start_test_flow(
    session_id="my_session",
    flow_name="checkout_flow",
    user_request="Test the complete checkout process"
)
```

### Recording Test Steps

#### Method 1: Context Manager (Recommended)

```python
from api.utils.lifecycle_hooks import TestStepContext

async with TestStepContext(session_id, url, "click_button") as step_data:
    # Perform test action
    await page.click("#button")
    
    # Add metrics
    step_data.metrics = {
        "pageLoadTime": 1200,
        "firstPaint": 800
    }
    
    # Step is automatically recorded when context exits
```

#### Method 2: Manual Recording

```python
from api.utils.lifecycle_hooks import capture_step_metrics, complete_step_metrics

# Start step
step_data, start_time = await capture_step_metrics(session_id, url, "navigate_page")

# Perform test action
await page.goto(url)

# Complete step
await complete_step_metrics(session_id, step_data, start_time, metrics=page_metrics)
```

### Completing a Test Flow

```python
from api.utils.lifecycle_hooks import end_test_flow

# Complete the test flow
success = await end_test_flow(
    session_id="my_session",
    success=True,
    summary="Checkout flow completed successfully"
)
```

### Getting Test Flow Summary

```python
from api.utils.test_flow_manager import test_flow_manager

# Get current test flow summary
flow = await test_flow_manager.get_test_flow_summary(session_id)

if flow:
    print(f"Flow: {flow.metadata.name}")
    print(f"Status: {flow.metadata.status.value}")
    print(f"Steps: {flow.metadata.total_steps}")
    print(f"Success Rate: {flow.metadata.successful_steps}/{flow.metadata.total_steps}")
```

### Exporting Reports

```python
# Export in different formats
json_report = await test_flow_manager.export_test_report(session_id, "json")
html_report = await test_flow_manager.export_test_report(session_id, "html")
md_report = await test_flow_manager.export_test_report(session_id, "markdown")
```

## API Endpoints

### Test Flow Management

- `POST /api/test-flows/start` - Start a new test flow
- `POST /api/test-flows/{session_id}/pause` - Pause an active test flow
- `POST /api/test-flows/{session_id}/resume` - Resume a paused test flow
- `POST /api/test-flows/{session_id}/complete` - Complete a test flow
- `GET /api/test-flows/{session_id}/summary` - Get test flow summary
- `GET /api/test-flows/{session_id}/export` - Export test report
- `GET /api/test-flows/status` - Get overall test flows status
- `POST /api/test-flows/cleanup` - Clean up old completed flows

### Agent Actions

The system adds new actions to the browser automation agent:

- `Start test flow` - Begin a new test sequence
- `End test flow` - Complete the current test sequence
- `Record test step` - Manually record a test step
- `Get test flow summary` - View current test flow status
- `Export test report` - Generate reports in various formats

## Integration with Existing System

### Session Summary Integration

The existing `get_session_summary()` function now includes test flow information:

```
🧪 Test Flow Integration:
   - Flow Name: checkout_flow
   - Status: running
   - Total Steps: 3
   - Success Rate: 3/3
```

### Backward Compatibility

- All existing functionality remains unchanged
- New test flow features are additive
- Existing performance metrics continue to work
- Gradual migration path available

## Data Structures

### TestFlow

```python
class TestFlow:
    session_id: str
    metadata: TestFlowMetadata
    steps: List[TestStepData]
    performance_summary: Optional[Dict[str, Any]]
    error_summary: Optional[Dict[str, Any]]
```

### TestStepData

```python
class TestStepData:
    timestamp: datetime
    url: str
    title: Optional[str]
    action: Optional[str]
    metrics: Optional[Dict[str, Any]]
    screenshot: Optional[str]  # base64 encoded
    network_data: Optional[Dict[str, Any]]
    console_logs: Optional[List[str]]
    errors: Optional[List[str]]
    duration_ms: Optional[float]
```

### TestFlowMetadata

```python
class TestFlowMetadata:
    name: str
    user_request: str
    test_id: Optional[str]
    user_id: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    status: TestFlowStatus
    total_steps: int
    successful_steps: int
    failed_steps: int
    summary: Optional[str]
    tags: Optional[List[str]]
```

## Performance Considerations

- **Minimal Overhead**: Test flow capture adds <100ms overhead per step
- **Memory Management**: Automatic cleanup of old completed flows
- **Scalability**: Supports multiple concurrent test flows
- **Efficient Storage**: Optimized data structures for performance

## Error Handling

- **Graceful Degradation**: System continues working even if test flow features fail
- **Comprehensive Logging**: Detailed error tracking and debugging information
- **Recovery Mechanisms**: Automatic cleanup and state recovery
- **User Feedback**: Clear error messages and status updates

## Testing

### Running Tests

```bash
# Run the test suite
python test_test_flow.py

# Run the demonstration
python demo_test_flow.py
```

### Test Coverage

- Basic test flow functionality
- Lifecycle hooks system
- Error handling and edge cases
- Report generation in all formats
- Integration with existing systems

## Migration Guide

### Phase 1: Parallel Implementation
- New system runs alongside existing code
- No breaking changes to current functionality
- Gradual adoption of new features

### Phase 2: Feature Flag Implementation
- Control new vs. old behavior
- Easy rollback if issues arise
- A/B testing capabilities

### Phase 3: Gradual Replacement
- Replace complex logic with lifecycle hooks
- Update existing functions to use new system
- Maintain API contracts during transition

### Phase 4: Cleanup and Optimization
- Remove deprecated code
- Optimize based on real usage
- Finalize API and documentation

## Best Practices

1. **Always Use Context Managers**: `TestStepContext` ensures proper cleanup
2. **Set Meaningful Flow Names**: Use descriptive names for better organization
3. **Include User Context**: Store the original user request for traceability
4. **Handle Errors Gracefully**: Use try-catch blocks and record errors
5. **Clean Up Resources**: Complete test flows when done
6. **Monitor Performance**: Track overhead and optimize as needed

## Future Enhancements

- **Database Persistence**: Store test flows in database for long-term analysis
- **Advanced Analytics**: Trend analysis and performance regression detection
- **Integration Testing**: Support for CI/CD pipeline integration
- **Custom Metrics**: User-defined performance and quality metrics
- **Team Collaboration**: Share and compare test flows across team members

## Troubleshooting

### Common Issues

1. **Circular Import Errors**: Ensure lifecycle hooks are imported locally in agent functions
2. **Missing Dependencies**: Install required packages with `uv sync`
3. **Session ID Issues**: Verify session_id is set before using test flow features
4. **Performance Overhead**: Monitor step duration and optimize if needed

### Debug Mode

Enable detailed logging by setting log level to DEBUG:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Support

For issues or questions about the Test Flow Management System:

1. Check the logs for detailed error information
2. Verify all dependencies are installed correctly
3. Ensure proper session management
4. Review the test examples for usage patterns

## Conclusion

The Test Flow Management System provides a robust, scalable foundation for structured browser automation testing. It transforms random automation into predictable, measurable test flows while maintaining full backward compatibility with existing systems.

By following the patterns and best practices outlined in this documentation, developers can create comprehensive, reliable test automation that provides valuable insights into application performance and user experience.
