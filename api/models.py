from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ModelProvider(str, Enum):
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"
    # OPENROUTER = "openrouter"
    # GOOGLE = "google"


class ModelConfig(BaseModel):
    """
    A Pydantic model representing configuration details for different LLM providers.
    Extend this to add more providers or model versions in the future.
    """
    
    provider: ModelProvider
    model_name: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1024
    top_k: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    api_key: Optional[str] = None
    extra_params: dict = Field(default_factory=dict)

    def model_post_init(self, __context):
        """Set default model name if not provided"""
        if not self.model_name:
            self.model_name = self.default_model(self.provider)

    @staticmethod
    def default_model(provider: ModelProvider) -> str:
        """
        Returns a default model for each provider.
        """
        default_models = {
            ModelProvider.OPENAI: "gpt-4o-mini",
            ModelProvider.AZURE_OPENAI: "gpt-4o-mini",
            ModelProvider.ANTHROPIC: "claude-3-7-sonnet-latest",
            ModelProvider.GEMINI: "gemini-2.0-flash",
            ModelProvider.DEEPSEEK: "deepseek-chat",
        }
        return default_models.get(provider, "gpt-4o-mini")
