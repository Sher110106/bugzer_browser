from typing import Any
from anthropic import Client
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel
from .models import ModelConfig, ModelProvider
from typing import Sequence, Union, Dict, Type, Callable, Any
from langchain_core.tools import BaseTool
from langchain_anthropic.chat_models import convert_to_anthropic_tool
from functools import cached_property
import anthropic
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import SecretStr


class BetaChatAnthropic(ChatAnthropic):
    """ChatAnthropic that uses the beta.messages endpoint for computer-use."""

    @cached_property
    def _client(self) -> anthropic.Client:
        client = super()._client
        # Force use of beta client for all messages
        client.messages = client.beta.messages
        return client

    @cached_property
    def _async_client(self) -> anthropic.AsyncClient:
        client = super()._async_client
        # Force use of beta client for all messages
        client.messages = client.beta.messages
        return client

    def bind_tools(
        self,
        tools: Sequence[Union[Dict[str, Any], Type, Callable, BaseTool]],
        **kwargs: Any,
    ):
        """Override bind_tools to handle Anthropic-specific tool formats"""
        # Pass tools directly if they're in Anthropic format
        anthropic_tools = []
        for tool in tools:
            if isinstance(tool, dict) and "type" in tool:
                # Already in Anthropic format, pass through
                anthropic_tools.append(tool)
            else:
                # Use default conversion for standard tools
                anthropic_tools.append(convert_to_anthropic_tool(tool))

        return super().bind(tools=anthropic_tools, **kwargs)


def create_llm(config: ModelConfig) -> tuple[BaseChatModel | Client, bool]:
    """
    Returns a tuple containing:
    1. The appropriate LangChain LLM object based on the ModelConfig provider
    2. A boolean indicating whether vision should be used (False for DeepSeek, True for others)
    """
    if config.provider == ModelProvider.AZURE_OPENAI:
        return AzureChatOpenAI(
            azure_deployment=config.model_name or "gpt-4o-mini",
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            openai_api_key=(
                os.getenv("AZURE_OPENAI_API_KEY") if not config.api_key else config.api_key
            ),
            openai_api_version=os.getenv("OPENAI_API_VERSION", "2025-01-01-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            **config.extra_params,
        ), True
    elif config.provider == ModelProvider.OPENAI:
        return ChatOpenAI(
            model_name=config.model_name or "gpt-4o-mini",
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            api_key=(
                os.getenv("OPENAI_API_KEY") if not config.api_key else config.api_key
            ),
            **config.extra_params,
        ), True
    
    elif config.provider == ModelProvider.ANTHROPIC:
        return ChatAnthropic(
            model=config.model_name or "claude-3-7-sonnet-latest",
            max_tokens_to_sample=config.max_tokens,
            temperature=config.temperature,
            api_key=(
                os.getenv("ANTHROPIC_API_KEY") if not config.api_key else config.api_key
            ),
            **config.extra_params,
        ), True
    elif config.provider == ModelProvider.GEMINI:
        return ChatGoogleGenerativeAI(
            model=config.model_name or "gemini-2.0-flash",
            temperature=config.temperature,
            max_output_tokens=config.max_tokens,
            google_api_key=(
                os.getenv("GOOGLE_API_KEY") if not config.api_key else config.api_key
            ),
            **config.extra_params,
        ), True
    elif config.provider == ModelProvider.DEEPSEEK:
        api_key = config.api_key or os.getenv("DEEPSEEK_API_KEY", "")
        
        return ChatOpenAI(
            base_url="https://api.deepseek.com/v1",
            model_name=config.model_name or "deepseek-chat",
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            api_key=SecretStr(api_key),
            **config.extra_params,
        ), False
    else:
        raise ValueError(f"Unsupported provider: {config.provider}")
