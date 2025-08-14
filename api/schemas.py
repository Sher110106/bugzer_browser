
from api.plugins import WebAgentType
from .utils.prompt import ClientMessage
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from .models import ModelProvider
from .utils.types import AgentSettings, ModelSettings
from datetime import datetime
from enum import Enum


class SessionRequest(BaseModel):
    agent_type: WebAgentType
    api_key: Optional[str] = None
    timeout: Optional[int] = 90000


class ChatRequest(BaseModel):
    session_id: str
    agent_type: WebAgentType
    provider: ModelProvider = ModelProvider.ANTHROPIC
    messages: List[ClientMessage]
    api_key: str = ""
    agent_settings: AgentSettings
    model_settings: ModelSettings


# Test Flow Management Schemas
class TestFlowStatus(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class TestStepData(BaseModel):
    """Data captured for each test step"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    url: str
    title: Optional[str] = None
    action: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    screenshot: Optional[str] = None  # base64 encoded
    network_data: Optional[Dict[str, Any]] = None
    console_logs: Optional[List[str]] = None
    errors: Optional[List[str]] = None
    duration_ms: Optional[float] = None


class TestFlowMetadata(BaseModel):
    """Metadata for a test flow"""
    name: str
    user_request: str
    test_id: Optional[str] = None
    user_id: Optional[str] = None
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    status: TestFlowStatus = TestFlowStatus.RUNNING
    total_steps: int = 0
    successful_steps: int = 0
    failed_steps: int = 0
    summary: Optional[str] = None
    tags: Optional[List[str]] = None


class TestFlow(BaseModel):
    """Complete test flow data structure"""
    session_id: str
    metadata: TestFlowMetadata
    steps: List[TestStepData] = Field(default_factory=list)
    performance_summary: Optional[Dict[str, Any]] = None
    error_summary: Optional[Dict[str, Any]] = None


class TestFlowRequest(BaseModel):
    """Request to start a new test flow"""
    session_id: str
    flow_name: str
    user_request: str
    test_id: Optional[str] = None
    user_id: Optional[str] = None
    tags: Optional[List[str]] = None


class TestFlowResponse(BaseModel):
    """Response from test flow operations"""
    status: str
    message: str
    flow_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None