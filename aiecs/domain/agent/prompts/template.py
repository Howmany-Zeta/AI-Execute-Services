"""
Prompt Templates

Native template system with variable substitution.
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass

from aiecs.llm import LLMMessage


class TemplateMissingVariableError(Exception):
    """Raised when required template variable is missing."""


class PromptTemplate:
    """
    String-based prompt template with {variable} substitution.

    Example:
        template = PromptTemplate(
            "Hello {name}, you are a {role}.",
            required_variables=["name", "role"]
        )
        result = template.format(name="Alice", role="developer")
    """

    def __init__(
        self,
        template: str,
        required_variables: Optional[List[str]] = None,
        defaults: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize prompt template.

        Args:
            template: Template string with {variable} placeholders
            required_variables: List of required variable names
            defaults: Default values for optional variables
        """
        self.template = template
        self.required_variables = required_variables or []
        self.defaults = defaults or {}

        # Extract all variables from template
        self._extract_variables()

    def _extract_variables(self) -> None:
        """Extract variable names from template."""
        # Find all {variable_name} patterns
        pattern = r"\{(\w+)\}"
        self.variables = set(re.findall(pattern, self.template))

    def format(self, **kwargs) -> str:
        """
        Format template with provided variables.

        Args:
            **kwargs: Variable values

        Returns:
            Formatted string

        Raises:
            TemplateMissingVariableError: If required variable missing
        """
        # Check required variables
        for var in self.required_variables:
            if var not in kwargs and var not in self.defaults:
                raise TemplateMissingVariableError(f"Required variable '{var}' not provided")

        # Merge with defaults
        values = {**self.defaults, **kwargs}

        # Format template
        try:
            return self.template.format(**values)
        except KeyError as e:
            raise TemplateMissingVariableError(f"Variable {e} not provided and has no default")

    def partial(self, **kwargs) -> "PromptTemplate":
        """
        Create a partial template with some variables pre-filled.

        Args:
            **kwargs: Variable values to pre-fill

        Returns:
            New PromptTemplate with updated defaults
        """
        new_defaults = {**self.defaults, **kwargs}
        return PromptTemplate(
            template=self.template,
            required_variables=self.required_variables,
            defaults=new_defaults,
        )

    def __repr__(self) -> str:
        return f"PromptTemplate(variables={self.variables})"


@dataclass
class MessageTemplate:
    """Template for a single message."""

    role: str
    content: str


class ChatPromptTemplate:
    """
    Multi-message chat template.

    Example:
        template = ChatPromptTemplate([
            MessageTemplate("system", "You are a {role}."),
            MessageTemplate("user", "{task}"),
        ])
        messages = template.format_messages(role="assistant", task="Help me")
    """

    def __init__(
        self,
        messages: List[MessageTemplate],
        required_variables: Optional[List[str]] = None,
        defaults: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize chat template.

        Args:
            messages: List of message templates
            required_variables: List of required variable names
            defaults: Default values for optional variables
        """
        self.messages = messages
        self.required_variables = required_variables or []
        self.defaults = defaults or {}

        # Extract all variables
        self._extract_variables()

    def _extract_variables(self) -> None:
        """Extract variables from all message templates."""
        self.variables = set()
        pattern = r"\{(\w+)\}"

        for msg in self.messages:
            vars_in_msg = set(re.findall(pattern, msg.content))
            self.variables.update(vars_in_msg)

    def format_messages(self, **kwargs) -> List[LLMMessage]:
        """
        Format all messages with provided variables.

        Args:
            **kwargs: Variable values

        Returns:
            List of LLMMessage instances

        Raises:
            TemplateMissingVariableError: If required variable missing
        """
        # Check required variables
        for var in self.required_variables:
            if var not in kwargs and var not in self.defaults:
                raise TemplateMissingVariableError(f"Required variable '{var}' not provided")

        # Merge with defaults
        values = {**self.defaults, **kwargs}

        # Format each message
        formatted_messages = []
        for msg_template in self.messages:
            try:
                content = msg_template.content.format(**values)
                formatted_messages.append(LLMMessage(role=msg_template.role, content=content))
            except KeyError as e:
                raise TemplateMissingVariableError(f"Variable {e} not provided and has no default")

        return formatted_messages

    def partial(self, **kwargs) -> "ChatPromptTemplate":
        """
        Create a partial template with some variables pre-filled.

        Args:
            **kwargs: Variable values to pre-fill

        Returns:
            New ChatPromptTemplate with updated defaults
        """
        new_defaults = {**self.defaults, **kwargs}
        return ChatPromptTemplate(
            messages=self.messages,
            required_variables=self.required_variables,
            defaults=new_defaults,
        )

    def add_message(self, role: str, content: str) -> "ChatPromptTemplate":
        """
        Add a message to the template.

        Args:
            role: Message role
            content: Message content template

        Returns:
            New ChatPromptTemplate with added message
        """
        new_messages = self.messages + [MessageTemplate(role, content)]
        return ChatPromptTemplate(
            messages=new_messages,
            required_variables=self.required_variables,
            defaults=self.defaults,
        )

    def __repr__(self) -> str:
        return f"ChatPromptTemplate(messages={len(self.messages)}, variables={self.variables})"


def create_system_prompt(content: str) -> ChatPromptTemplate:
    """
    Helper to create a chat template with system message.

    Args:
        content: System message content

    Returns:
        ChatPromptTemplate with system message
    """
    return ChatPromptTemplate([MessageTemplate("system", content)])


def create_basic_chat(system: str, user: str) -> ChatPromptTemplate:
    """
    Helper to create a basic system + user chat template.

    Args:
        system: System message content
        user: User message content

    Returns:
        ChatPromptTemplate with system and user messages
    """
    return ChatPromptTemplate(
        [
            MessageTemplate("system", system),
            MessageTemplate("user", user),
        ]
    )
