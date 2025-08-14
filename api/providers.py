from typing import Any
from anthropic import Client
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

# Browser-use LLM imports
from browser_use.llm import ChatOpenAI as BrowserUseOpenAI
from browser_use.llm import ChatAnthropic as BrowserUseAnthropic
from browser_use.llm import ChatGoogle as BrowserUseGoogle
from browser_use.llm import ChatAzureOpenAI as BrowserUseAzureOpenAI

# Pydantic model issue resolved with langchain-openai 0.3.29+ and langchain-core 0.3.74+
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


def create_llm(config: ModelConfig) -> tuple[Any, bool]:
    """
    Returns a tuple containing:
    1. The appropriate browser_use LLM object based on the ModelConfig provider
    2. A boolean indicating whether vision should be used (False for DeepSeek, True for others)
    """
    if config.provider == ModelProvider.AZURE_OPENAI:
        return BrowserUseAzureOpenAI(
            model=config.model_name or "gpt-4o-mini",
            temperature=config.temperature,
            **config.extra_params,
        ), True
    elif config.provider == ModelProvider.OPENAI:
        return BrowserUseOpenAI(
            model=config.model_name or "gpt-4o-mini",
            temperature=config.temperature,
            **config.extra_params,
        ), True
    
    elif config.provider == ModelProvider.ANTHROPIC:
        return BrowserUseAnthropic(
            model=config.model_name or "claude-3-5-sonnet-20241022",
            temperature=config.temperature,
            **config.extra_params,
        ), True
    elif config.provider == ModelProvider.GEMINI:
        return BrowserUseGoogle(
            model=config.model_name or "gemini-2.0-flash-exp",
            temperature=config.temperature,
            **config.extra_params,
        ), True
    elif config.provider == ModelProvider.DEEPSEEK:
        # For DeepSeek, use OpenAI-compatible endpoint with browser_use
        return BrowserUseOpenAI(
            model=config.model_name or "deepseek-chat",
            temperature=config.temperature,
            base_url="https://api.deepseek.com/v1",
            **config.extra_params,
        ), False
    else:
        raise ValueError(f"Unsupported provider: {config.provider}")
