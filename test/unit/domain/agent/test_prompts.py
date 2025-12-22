"""
Unit tests for prompt templates.
"""

import pytest
from aiecs.domain.agent.prompts import (
    PromptTemplate,
    ChatPromptTemplate,
    MessageTemplate,
    MessageBuilder,
    TemplateMissingVariableError,
)
from aiecs.llm import LLMMessage


@pytest.mark.unit
class TestPromptTemplate:
    """Test PromptTemplate."""

    def test_basic_template(self):
        """Test basic template formatting."""
        template = PromptTemplate("Hello {name}!")
        result = template.format(name="Alice")
        assert result == "Hello Alice!"

    def test_template_with_multiple_variables(self):
        """Test template with multiple variables."""
        template = PromptTemplate("Hello {name}, you are a {role}.")
        result = template.format(name="Alice", role="developer")
        assert result == "Hello Alice, you are a developer."

    def test_template_with_defaults(self):
        """Test template with default values."""
        template = PromptTemplate(
            "Hello {name}!",
            defaults={"name": "User"}
        )
        result = template.format()
        assert result == "Hello User!"

    def test_template_missing_required_variable(self):
        """Test template with missing required variable."""
        template = PromptTemplate(
            "Hello {name}!",
            required_variables=["name"]
        )
        with pytest.raises(TemplateMissingVariableError):
            template.format()

    def test_template_partial(self):
        """Test creating partial template."""
        template = PromptTemplate("Hello {name}, you are a {role}.")
        partial = template.partial(name="Alice")
        result = partial.format(role="developer")
        assert result == "Hello Alice, you are a developer."

    def test_template_variable_extraction(self):
        """Test extracting variables from template."""
        template = PromptTemplate("Hello {name}, age {age}!")
        assert "name" in template.variables
        assert "age" in template.variables


@pytest.mark.unit
class TestChatPromptTemplate:
    """Test ChatPromptTemplate."""

    def test_chat_template_creation(self):
        """Test creating chat template."""
        messages = [
            MessageTemplate("system", "You are a {role}."),
            MessageTemplate("user", "{question}")
        ]
        template = ChatPromptTemplate(messages)
        assert len(template.messages) == 2

    def test_chat_template_format_messages(self):
        """Test formatting chat messages."""
        messages = [
            MessageTemplate("system", "You are a {role}."),
            MessageTemplate("user", "{question}")
        ]
        template = ChatPromptTemplate(messages)
        
        formatted = template.format_messages(role="assistant", question="Hello?")
        assert len(formatted) == 2
        assert formatted[0].role == "system"
        assert formatted[0].content == "You are a assistant."
        assert formatted[1].role == "user"
        assert formatted[1].content == "Hello?"

    def test_chat_template_add_message(self):
        """Test adding message to template."""
        messages = [MessageTemplate("system", "System message")]
        template = ChatPromptTemplate(messages)
        new_template = template.add_message("user", "User message")
        assert len(new_template.messages) == 2


@pytest.mark.unit
class TestMessageBuilder:
    """Test MessageBuilder."""

    def test_message_builder_add_system(self):
        """Test adding system message."""
        builder = MessageBuilder()
        builder.add_system("You are a helpful assistant")
        messages = builder.build()
        assert len(messages) == 1
        assert messages[0].role == "system"

    def test_message_builder_add_user(self):
        """Test adding user message."""
        builder = MessageBuilder()
        builder.add_user("Hello")
        messages = builder.build()
        assert len(messages) == 1
        assert messages[0].role == "user"

    def test_message_builder_add_assistant(self):
        """Test adding assistant message."""
        builder = MessageBuilder()
        builder.add_assistant("Hi there!")
        messages = builder.build()
        assert len(messages) == 1
        assert messages[0].role == "assistant"

    def test_message_builder_add_context(self):
        """Test adding context."""
        builder = MessageBuilder()
        builder.add_context({"key": "value"})
        messages = builder.build()
        assert len(messages) == 1
        assert "key: value" in messages[0].content

    def test_message_builder_add_conversation_history(self):
        """Test adding conversation history."""
        builder = MessageBuilder()
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"}
        ]
        builder.add_conversation_history(history)
        messages = builder.build()
        assert len(messages) == 2

    def test_message_builder_clear(self):
        """Test clearing messages."""
        builder = MessageBuilder()
        builder.add_user("Hello")
        builder.clear()
        assert len(builder.build()) == 0

