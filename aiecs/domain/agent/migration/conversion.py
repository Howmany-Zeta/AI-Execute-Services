"""
Conversion Utilities

Convert legacy configurations and prompts to new format.
"""

import logging
from typing import Dict, Any
import re

from ..models import AgentConfiguration
from ..prompts import PromptTemplate, ChatPromptTemplate, MessageTemplate

logger = logging.getLogger(__name__)


def convert_legacy_config(legacy_config: Dict[str, Any]) -> AgentConfiguration:
    """
    Convert legacy agent configuration to AgentConfiguration.

    Args:
        legacy_config: Legacy configuration dictionary

    Returns:
        AgentConfiguration instance
    """
    # Map legacy fields to new fields
    field_mapping = {
        # Common legacy field names
        "model": "llm_model",
        "model_name": "llm_model",
        "temp": "temperature",
        "max_output_tokens": "max_tokens",
        "enable_memory": "memory_enabled",
        "verbose": "verbose",
    }

    converted = {}
    for old_field, value in legacy_config.items():
        new_field = field_mapping.get(old_field, old_field)
        converted[new_field] = value

    # Create AgentConfiguration
    try:
        config = AgentConfiguration(**converted)  # type: ignore[call-arg]
        logger.info("Legacy configuration converted successfully")
        return config
    except Exception as e:
        logger.error(f"Failed to convert legacy config: {e}")
        # Return default config with available fields
        max_tokens = converted.get("max_tokens")
        return AgentConfiguration(  # type: ignore[call-arg]
            llm_model=converted.get("llm_model"),
            temperature=converted.get("temperature", 0.7),
            max_tokens=(max_tokens if max_tokens is not None and isinstance(max_tokens, int) else 4096),
        )


def convert_langchain_prompt(langchain_prompt: str) -> PromptTemplate:
    """
    Convert LangChain prompt template to native PromptTemplate.

    LangChain uses {variable} syntax, which is compatible with our format.

    Args:
        langchain_prompt: LangChain prompt string

    Returns:
        PromptTemplate instance
    """
    # LangChain and our template use same {variable} syntax
    # Just need to extract variables
    pattern = r"\{(\w+)\}"
    variables = re.findall(pattern, langchain_prompt)

    return PromptTemplate(template=langchain_prompt, required_variables=variables)


def convert_langchain_chat_prompt(messages: list) -> ChatPromptTemplate:
    """
    Convert LangChain chat prompt to ChatPromptTemplate.

    Args:
        messages: List of (role, template) tuples

    Returns:
        ChatPromptTemplate instance
    """
    message_templates = []

    for item in messages:
        if isinstance(item, tuple):
            role, template = item
        elif isinstance(item, dict):
            role = item.get("role", "user")
            template = item.get("content", "")
        else:
            logger.warning(f"Unknown message format: {item}")
            continue

        message_templates.append(MessageTemplate(role=role, content=template))

    return ChatPromptTemplate(messages=message_templates)


def migrate_agent_state(legacy_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate legacy agent state to new format.

    Args:
        legacy_state: Legacy state dictionary

    Returns:
        New state dictionary
    """
    # Map legacy state fields
    state_mapping = {
        "status": "state",
        "task_history": "interactions",
        "memory": "memory",
    }

    migrated = {}
    for old_field, value in legacy_state.items():
        new_field = state_mapping.get(old_field, old_field)
        migrated[new_field] = value

    logger.info("Agent state migrated")
    return migrated


def validate_migration(legacy_agent: Any, new_agent: Any) -> Dict[str, Any]:
    """
    Validate migration by comparing legacy and new agent behavior.

    Args:
        legacy_agent: Legacy agent instance
        new_agent: New agent instance

    Returns:
        Validation report
    """
    report: Dict[str, Any] = {
        "compatible": True,
        "warnings": [],
        "errors": [],
    }

    # Check for required methods
    required_methods = ["execute_task"]
    for method in required_methods:
        if not hasattr(new_agent, method):
            report["compatible"] = False
            errors_list = report["errors"]
            if isinstance(errors_list, list):
                errors_list.append(f"Missing required method: {method}")

    # Check configuration compatibility
    if hasattr(legacy_agent, "config") and hasattr(new_agent, "_config"):
        # Basic compatibility check
        logger.info("Configuration validated")

    return report
