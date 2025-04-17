from enum import Enum, auto
from typing import (
    Callable,
    List,
    Mapping,
    Any,
    AsyncIterator,
    TypedDict,
    Union,
    Optional,
)
from ..models import ModelConfig, ModelProvider
from .base import base_agent
from .browser_use import browser_use_agent
from ..utils.types import AgentSettings

# from .example_plugin import example_agent


class WebAgentType(Enum):
    BASE = "base"
    EXAMPLE = "example"
    BROWSER_USE = "browser_use_agent"
    BROWSER_USE_BATCH = "browser_use_batch"


class SettingType(Enum):
    INTEGER = "integer"
    FLOAT = "float"
    TEXT = "text"
    TEXTAREA = "textarea"


class SettingConfig(TypedDict):
    type: SettingType
    default: Union[int, float, str]
    min: Optional[Union[int, float]]
    max: Optional[Union[int, float]]
    step: Optional[Union[int, float]]
    maxLength: Optional[int]
    description: Optional[str]


# Agent configurations
AGENT_CONFIGS = {
    # WebAgentType.BASE.value: {
    #     "name": "Base Agent",
    #     "description": "A simple agent with basic functionality",
    #     "supported_models": [
    #         {
    #             "provider": ModelProvider.ANTHROPIC.value,
    #             "models": ["claude-3-opus-20240229", "claude-3-sonnet-20240229"],
    #         },
    #         {
    #             "provider": ModelProvider.OPENAI.value,
    #             "models": ["gpt-4-turbo-preview", "gpt-4", "gpt-3.5-turbo"],
    #         },
    #     ],
    #     "model_settings": {
    #         "max_tokens": {
    #             "type": SettingType.INTEGER.value,
    #             "default": 1000,
    #             "min": 1,
    #             "max": 4096,
    #             "description": "Maximum number of tokens to generate",
    #         },
    #         "temperature": {
    #             "type": SettingType.FLOAT.value,
    #             "default": 0.7,
    #             "min": 0,
    #             "max": 1,
    #             "step": 0.1,
    #             "description": "Controls randomness in the output",
    #         },
    #         "top_p": {
    #             "type": SettingType.FLOAT.value,
    #             "default": 0.9,
    #             "min": 0,
    #             "max": 1,
    #             "step": 0.1,
    #             "description": "Controls diversity via nucleus sampling",
    #         },
    #     },
    #     "agent_settings": {},
    # },
    WebAgentType.BROWSER_USE.value: {
        "name": "Browser Agent",
        "description": "Agent with web browsing capabilities",
        "supported_models": [
            {
                "provider": ModelProvider.AZURE_OPENAI.value,
                "models": ["gpt-4o", "gpt-4o-mini"],
            },
        ],
        "model_settings": {
            "max_tokens": {
                "type": SettingType.INTEGER.value,
                "default": 1000,
                "min": 1,
                "max": 4096,
                "description": "Maximum number of tokens to generate",
            },
            "temperature": {
                "type": SettingType.FLOAT.value,
                "default": 0.7,
                "min": 0,
                "max": 1,
                "step": 0.05,
                "description": "Controls randomness in the output",
            },
        },
        "agent_settings": {
            "steps": {
                "type": SettingType.INTEGER.value,
                "default": 100,
                "min": 10,
                "max": 125,
                "description": "Max number of steps to take",
            },
        },
    },
    WebAgentType.BROWSER_USE_BATCH.value: {
        "name": "Browser Agent (Batch)",
        "description": "Non-streaming browser agent that runs to completion",
        "supported_models": [
            {
                "provider": ModelProvider.AZURE_OPENAI.value,
                "models": ["gpt-4o", "gpt-4o-mini"],
            },
        ],
        "model_settings": {
            "max_tokens": {
                "type": SettingType.INTEGER.value,
                "default": 1000,
                "min": 1,
                "max": 4096,
                "description": "Maximum number of tokens to generate",
            },
            "temperature": {
                "type": SettingType.FLOAT.value,
                "default": 0.7,
                "min": 0,
                "max": 1,
                "step": 0.05,
                "description": "Controls randomness in the output",
            },
        },
        "agent_settings": {
            "steps": {
                "type": SettingType.INTEGER.value,
                "default": 125,  # More steps for batch mode since we don't need to wait for streaming
                "min": 10,
                "max": 150,
                "description": "Max number of steps to take",
            },
        },
    },
}


def get_web_agent(
    name: WebAgentType,
) -> Callable[
    [ModelConfig, AgentSettings, List[Mapping[str, Any]], str], Union[AsyncIterator[str], str]
]:
    if name == WebAgentType.BASE:
        return base_agent
    elif name == WebAgentType.BROWSER_USE:
        return browser_use_agent
    elif name == WebAgentType.BROWSER_USE_BATCH:
        return browser_use_agent_batch
    else:
        raise ValueError(f"Invalid agent type: {name}")


__all__ = ["WebAgentType", "get_web_agent", "AGENT_CONFIGS"]
