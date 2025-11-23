"""
LLM Output Structor - Readability and Tone Enhancer

This module transforms LLM outputs to be more readable and natural while preserving
the reasoning process and technical details. Instead of hiding the thinking process,
it makes it more accessible and easier to understand.

Key transformations:
1. Add friendly openings and closings
2. Transform technical jargon to more accessible language
3. Improve formatting and structure for better readability
4. Preserve reasoning but make it more conversational
5. Maintain transparency while improving user experience
"""

import re
import json
from typing import List, Dict, Any, Optional, Union


class LLMOutputTransformer:
    """
    Transformer that enhances readability while preserving LLM reasoning and analysis.
    """

    def __init__(self):
        # Word replacements for better readability
        self.technical_replacements = {
            # Technical terms to friendly alternatives
            "demand_state": "request status",
            "VAGUE_UNCLEAR": "needs clarification",
            "SMART_COMPLIANT": "well-defined",
            "SMART_LARGE_SCOPE": "comprehensive but needs focusing",
            "smart_analysis": "detailed analysis",
            "confidence": "certainty level",
            "intent_categories": "identified purposes",
            "complexity_assessment": "complexity evaluation",
            "execution_mode": "approach type",
            "agent_requirements": "required components",
            "meta_architect": "strategic planner",
            "intent_parser": "request analyzer",
            # Analysis terms
            "fails most SMART criteria": "lacks several key details",
            "SMART criteria": "clarity requirements",
            "not Specific": "not specific enough",
            "not Measurable": "missing measurable goals",
            "not Achievable": "unclear if achievable",
            "not Time-bound": "missing timeframe",
            "high-level goal": "general objective",
            "actionable task": "specific action item",
            # Common phrases
            "classic example": "typical case",
            "significant clarification": "more details",
            "multi-stage": "step-by-step",
            "architect_output": "strategic plan",
            "problem_analysis": "situation assessment",
            "intent parsing": "request understanding",
            "blueprint": "detailed plan",
            "roadmap": "action sequence",
        }

        # Friendly section headers
        self.section_headers = {
            "Reasoning:": "💭 My Analysis:",
            "Clarification needed": "📝 Questions to Help Me Understand Better",
            "clarification_needed:": "📝 Helpful Questions:",
            "Problem Analysis:": "🔍 Situation Overview:",
            "Solution Approach:": "💡 Recommended Approach:",
            "Key Components:": "🔧 Main Elements:",
            "Confidence:": "📊 Confidence Level:",
            "Intent Categories:": "🎯 Identified Goals:",
            "Complexity:": "📈 Complexity Level:",
        }

        # Opening greetings
        self.greetings = {
            "clarification": "Hello! Thank you for reaching out. Let me help you with your request.",
            "confirmation": "Great! I've carefully analyzed your requirements.",
            "completion": "Excellent! I've completed the analysis.",
            "general": "Thank you for your message.",
        }

        # Closing messages
        self.closings = {
            "clarification": "\n\n✨ These details will help me provide you with the most accurate and helpful solution!",
            "confirmation": "\n\n🤝 I'm ready to proceed whenever you are. Feel free to ask any questions or suggest modifications!",
            "completion": "\n\n✅ Everything is set up and ready. Let me know if you need any adjustments!",
            "general": "\n\n💬 Please let me know if you need any clarification!",
        }

    def transform_message(
        self,
        content: str,
        message_type: str = "general",
        preserve_structure: bool = True,
    ) -> str:
        """
        Transform LLM output to be more readable while preserving content.

        Args:
            content: Raw LLM output
            message_type: Type of message ('clarification', 'confirmation', 'completion', 'general')
            preserve_structure: Whether to preserve the original structure

        Returns:
            Enhanced, more readable message
        """
        # Add appropriate greeting
        result = self._add_greeting(message_type)

        # Transform the main content
        transformed_content = self._enhance_readability(content)

        # Special handling for different message types
        if message_type == "clarification":
            transformed_content = self._enhance_clarification(transformed_content)
        elif message_type == "confirmation":
            transformed_content = self._enhance_confirmation(transformed_content)

        result += "\n\n" + transformed_content

        # Add appropriate closing
        result += self._add_closing(message_type)

        return result

    def _add_greeting(self, message_type: str) -> str:
        """Add an appropriate greeting based on message type."""
        return self.greetings.get(message_type, self.greetings["general"])

    def _add_closing(self, message_type: str) -> str:
        """Add an appropriate closing based on message type."""
        return self.closings.get(message_type, self.closings["general"])

    def _enhance_readability(self, content: str) -> str:
        """Enhance readability by replacing technical terms and improving formatting."""
        result = content

        # Replace section headers with friendly versions
        for old_header, new_header in self.section_headers.items():
            result = result.replace(old_header, new_header)

        # Replace technical terms with friendly alternatives
        for technical, friendly in self.technical_replacements.items():
            # Case-insensitive replacement
            result = re.sub(
                rf"\b{re.escape(technical)}\b",
                friendly,
                result,
                flags=re.IGNORECASE,
            )

        # Improve JSON-like structures visibility
        result = self._format_json_structures(result)

        # Enhance bullet points
        result = self._enhance_bullet_points(result)

        # Add spacing for better readability
        result = self._improve_spacing(result)

        return result

    def _enhance_clarification(self, content: str) -> str:
        """Special enhancements for clarification messages."""
        # Transform reasoning section to be more conversational
        content = re.sub(
            r"(💭 My Analysis:)(.*?)(?=\n\n|$)",
            lambda m: f"{m.group(1)}\n{self._make_reasoning_conversational(m.group(2))}",
            content,
            flags=re.DOTALL,
        )

        # Format questions better
        content = self._format_clarification_questions(content)

        return content

    def _enhance_confirmation(self, content: str) -> str:
        """Special enhancements for confirmation messages."""
        # Make technical descriptions more accessible
        content = re.sub(
            r"I have generated a detailed (.*?):(.*?)(?=Do you|Would you|$)",
            r"I've prepared a comprehensive \1 for you:\n\n\2\n",
            content,
            flags=re.DOTALL,
        )

        # Format proposed plans better
        content = re.sub(
            r"Proposed plan:(.*?)(?=Do you|Would you|$)",
            r"📋 **Proposed Approach:**\n\1\n",
            content,
            flags=re.DOTALL,
        )

        return content

    def _make_reasoning_conversational(self, reasoning: str) -> str:
        """Make reasoning more conversational and easier to read."""
        # First, convert perspective from third-person to second-person
        reasoning = self._convert_perspective(reasoning)

        # Split into sentences for processing
        sentences = reasoning.strip().split(".")
        conversational_parts = []

        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue

            # Make the first sentence more natural
            if i == 0:
                # Remove phrases like "is a classic example of" to be more
                # direct
                sentence = re.sub(
                    r"is a (?:classic|typical|clear) example of",
                    "seems to be",
                    sentence,
                )
                sentence = "Looking at what you've shared, " + sentence.lower()
            # For sentences about what's missing
            elif any(word in sentence.lower() for word in ["lacks", "missing", "doesn't have", "without"]):
                if not sentence.lower().startswith(("i ", "it ", "this ")):
                    sentence = "I notice that it " + sentence.lower()
            # For sentences about what's not clear
            elif "not" in sentence.lower() and any(word in sentence.lower() for word in ["specific", "clear", "measurable"]):
                sentence = re.sub(
                    r"it is not",
                    "it isn't quite",
                    sentence,
                    flags=re.IGNORECASE,
                )
                if not sentence.lower().startswith(("i ", "this ")):
                    sentence = "I can see that " + sentence.lower()
            # For requirement sentences
            elif any(word in sentence.lower() for word in ["requires", "needs", "must"]):
                sentence = "To help you effectively, " + sentence.lower().replace("the request", "we'll")
            # Default: make it conversational
            else:
                if len(sentence) > 20 and not sentence.lower().startswith(("i ", "this ", "that ", "we ")):
                    sentence = "Additionally, " + sentence.lower()

            conversational_parts.append(sentence)

        result = ". ".join(conversational_parts)
        if result and not result.endswith("."):
            result += "."

        return result

    def _convert_perspective(self, text: str) -> str:
        """Convert text from third-person to second-person perspective."""
        # Replace "the user" references with "you"
        text = re.sub(r"the user'?s?\s+", "your ", text, flags=re.IGNORECASE)
        text = re.sub(r"user'?s?\s+", "your ", text, flags=re.IGNORECASE)

        # Replace "the request" with "your request" or "what you're asking"
        text = re.sub(r"the request", "your request", text, flags=re.IGNORECASE)

        # Replace "the business" with "your business"
        text = re.sub(r"the business", "your business", text, flags=re.IGNORECASE)

        # Replace impersonal constructions
        text = re.sub(r"it is (?:a|an)", "this is", text, flags=re.IGNORECASE)
        text = re.sub(
            r"this is (?:a|an) vague",
            "this seems vague",
            text,
            flags=re.IGNORECASE,
        )

        return text

    def _format_clarification_questions(self, content: str) -> str:
        """Format clarification questions for better readability."""
        # Find questions section
        questions_match = re.search(r"📝.*?:(.*?)(?=💭|✨|$)", content, re.DOTALL)
        if not questions_match:
            return content

        questions_text = questions_match.group(1)
        questions = self._extract_questions(questions_text)

        if questions:
            formatted = "📝 Questions to Help Me Understand Better:\n\n"
            for i, q in enumerate(questions, 1):
                # Clean up the question
                q = q.strip().strip("-*•")
                if not q.endswith("?"):
                    q += "?"
                formatted += f"**{i}.** {q}\n\n"

            # Replace the original questions section
            content = content.replace(questions_match.group(0), formatted)

        return content

    def _extract_questions(self, text: str) -> List[str]:
        """Extract individual questions from text."""
        # Split by semicolons or line breaks
        parts = re.split(r"[;\n]", text)
        questions = []

        for part in parts:
            part = part.strip()
            if part and not part.startswith("*Reason:"):
                questions.append(part)

        return questions

    def _format_json_structures(self, content: str) -> str:
        """Format JSON-like structures to be more readable."""

        # Find JSON-like structures
        def format_dict(match):
            try:
                # Extract the dictionary string
                dict_str = match.group(0)
                # Make it more readable
                formatted = dict_str.replace("'", "")
                formatted = formatted.replace("{", "{\n  ")
                formatted = formatted.replace(",", ",\n  ")
                formatted = formatted.replace("}", "\n}")
                return formatted
            except Exception:
                return match.group(0)

        # Apply to simple dictionaries
        content = re.sub(r"\{[^{}]+\}", format_dict, content)

        return content

    def _enhance_bullet_points(self, content: str) -> str:
        """Enhance bullet points for better visibility."""
        # Replace various bullet point styles with a consistent one
        content = re.sub(r"^[-*•]\s*", "• ", content, flags=re.MULTILINE)
        content = re.sub(
            r"^\d+\.\s*",
            lambda m: f"**{m.group(0)}**",
            content,
            flags=re.MULTILINE,
        )

        return content

    def _improve_spacing(self, content: str) -> str:
        """Improve spacing for better readability."""
        # Add space before emoji headers
        content = re.sub(r"(?<!\n)(💭|📝|🔍|💡|🔧|📊|🎯|📈)", r"\n\n\1", content)

        # Ensure proper spacing after headers
        content = re.sub(r"(💭|📝|🔍|💡|🔧|📊|🎯|📈)(.*?):", r"\1\2:\n", content)

        # Clean up excessive newlines
        content = re.sub(r"\n{3,}", "\n\n", content)

        return content.strip()


# Convenience functions
def format_clarification_message(
    questions: List[str],
    round_number: int = 1,
    reasoning: Optional[str] = None,
) -> str:
    """
    Format clarification messages with preserved reasoning.

    Args:
        questions: List of clarification questions
        round_number: Current round number
        reasoning: Optional reasoning to include

    Returns:
        Formatted message with enhanced readability
    """
    transformer = LLMOutputTransformer()

    # Build content
    content = f"Clarification needed (Round {round_number}): "
    content += "; ".join(questions)

    if reasoning:
        content += f"\n\nReasoning: {reasoning}"

    return transformer.transform_message(content, "clarification")


def format_confirmation_message(content: Union[str, Dict[str, Any]], confirmation_type: str = "strategy") -> str:
    """
    Format confirmation messages with preserved technical details.

    Args:
        content: Confirmation content
        confirmation_type: Type of confirmation

    Returns:
        Enhanced confirmation message
    """
    transformer = LLMOutputTransformer()

    if isinstance(content, dict):
        content = json.dumps(content, indent=2)

    return transformer.transform_message(content, "confirmation")


def enhance_reasoning(reasoning: str) -> str:
    """
    Enhance reasoning text to be more readable.

    Args:
        reasoning: Raw reasoning text

    Returns:
        Enhanced reasoning text
    """
    transformer = LLMOutputTransformer()
    return transformer._make_reasoning_conversational(reasoning)


def clean_technical_terms(content: str) -> str:
    """
    Replace technical terms with user-friendly alternatives.

    Args:
        content: Content with technical terms

    Returns:
        Content with friendly terms
    """
    transformer = LLMOutputTransformer()
    return transformer._enhance_readability(content)
