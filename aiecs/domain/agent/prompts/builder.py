"""
Message Builder

Helper for constructing LLMMessage lists.
"""

from typing import List, Dict, Any, Optional
from aiecs.llm import LLMMessage


class MessageBuilder:
    """
    Builder for constructing LLM message sequences.

    Example:
        builder = MessageBuilder()
        builder.add_system("You are a helpful assistant")
        builder.add_user("What is AI?")
        messages = builder.build()
    """

    def __init__(self) -> None:
        """Initialize message builder."""
        self.messages: List[LLMMessage] = []

    def add_system(self, content: str) -> "MessageBuilder":
        """
        Add system message.

        Args:
            content: Message content

        Returns:
            Self for chaining
        """
        self.messages.append(LLMMessage(role="system", content=content))
        return self

    def add_user(self, content: str) -> "MessageBuilder":
        """
        Add user message.

        Args:
            content: Message content

        Returns:
            Self for chaining
        """
        self.messages.append(LLMMessage(role="user", content=content))
        return self

    def add_assistant(self, content: str) -> "MessageBuilder":
        """
        Add assistant message.

        Args:
            content: Message content

        Returns:
            Self for chaining
        """
        self.messages.append(LLMMessage(role="assistant", content=content))
        return self

    def add_message(self, role: str, content: str) -> "MessageBuilder":
        """
        Add message with custom role.

        Args:
            role: Message role
            content: Message content

        Returns:
            Self for chaining
        """
        self.messages.append(LLMMessage(role=role, content=content))
        return self

    def add_messages(self, messages: List[LLMMessage]) -> "MessageBuilder":
        """
        Add multiple messages.

        Args:
            messages: List of messages to add

        Returns:
            Self for chaining
        """
        self.messages.extend(messages)
        return self

    def add_context(self, context: Dict[str, Any], prefix: str = "Context:") -> "MessageBuilder":
        """
        Add context as a system message.

        Args:
            context: Context dictionary
            prefix: Prefix for context message

        Returns:
            Self for chaining
        """
        context_str = self._format_context(context)
        if context_str:
            self.add_system(f"{prefix}\n{context_str}")
        return self

    def add_conversation_history(self, history: List[Dict[str, str]], max_messages: Optional[int] = None) -> "MessageBuilder":
        """
        Add conversation history.

        Args:
            history: List of {role, content} dicts
            max_messages: Optional limit on number of messages

        Returns:
            Self for chaining
        """
        if max_messages:
            history = history[-max_messages:]

        for msg in history:
            self.add_message(msg.get("role", "user"), msg.get("content", ""))

        return self

    def clear(self) -> "MessageBuilder":
        """
        Clear all messages.

        Returns:
            Self for chaining
        """
        self.messages.clear()
        return self

    def build(self) -> List[LLMMessage]:
        """
        Build and return message list.

        Returns:
            List of LLMMessage instances
        """
        return self.messages.copy()

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dictionary as string."""
        lines = []
        for key, value in context.items():
            if not key.startswith("_") and value is not None:
                lines.append(f"{key}: {value}")
        return "\n".join(lines) if lines else ""

    def __len__(self) -> int:
        """Get number of messages."""
        return len(self.messages)

    def __repr__(self) -> str:
        return f"MessageBuilder(messages={len(self.messages)})"
