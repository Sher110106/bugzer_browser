from api.plugins import WebAgentType
from .utils.prompt import ClientMessage
from pydantic import BaseModel
from typing import List, Optional
from .models import ModelProvider
from .utils.types import AgentSettings, ModelSettings


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


class TestCreate(BaseModel):
    """Model for creating a new test"""
    url: str
    description: Optional[str] = None
    status: str = "pending"  # pending, running, completed, failed


class TestResponse(BaseModel):
    """Response model for a test"""
    id: str
    url: str
    description: Optional[str] = None
    status: str
    user_id: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    error: Optional[str] = None


class ReportCreate(BaseModel):
    """Model for creating a new report"""
    test_id: str
    content: str
    status: str = "completed"  # completed, failed


class ReportResponse(BaseModel):
    """Response model for a report"""
    id: str
    test_id: str
    content: str
    status: str
    user_id: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class BatchAgentRequest(BaseModel):
    """Request model for the batch browser agent"""
    url: str
    description: Optional[str] = None
    provider: ModelProvider = ModelProvider.AZURE_OPENAI
    model_settings: ModelSettings
    agent_settings: Optional[AgentSettings] = None
    timeout: Optional[int] = 300