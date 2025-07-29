"""
Writer Agent

Specialized agent for content generation and writing tasks.
Refactored to use LangChain framework and TaskFactory for complete configuration-driven behavior.
"""

import logging
from typing import Dict, List, Any

# LangChain dependencies
from langchain.agents import AgentExecutor
from langchain.tools import BaseTool
from langchain.schema import AgentAction, AgentFinish

# Import our system's core components
from ..base_agent import BaseAgent
from ...core.models.agent_models import AgentConfig
from app.services.llm_integration import LLMIntegrationManager
from ...config.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class WriterAgent(BaseAgent):
    """
    Agent specialized in content generation and writing tasks.

    Refactored to use LangChain framework and TaskFactory for complete configuration-driven behavior.
    Its task definition is provided by TaskFactory, and its LLM is dynamically
    configured by LLMIntegrationManager through the LangChain adapter.
    """

    def __init__(self, config: AgentConfig, config_manager: ConfigManager, llm_manager: LLMIntegrationManager, tool_integration_manager=None):
        """
        Initialize the writer agent.

        Args:
            config: Agent's basic configuration (such as agent_id, role)
            config_manager: Configuration manager for reading prompts.yaml and llm_bindings.yaml
            llm_manager: LLM integration manager for actual LLM calls
            tool_integration_manager: Optional tool integration manager for LangChain tools
        """
        # Call parent's initialization method, which handles role definition and LLM binding loading
        super().__init__(config, config_manager, llm_manager, tool_integration_manager)

        # Writing specializations
        self.writing_types = [
            "report_writing",
            "content_creation",
            "documentation",
            "summary_writing",
            "technical_writing",
            "creative_writing",
            "structured_output"
        ]

        # LangChain agent executor instance
        self._agent_executor: AgentExecutor = None

    async def initialize(self) -> None:
        """Initialize the writer agent."""
        logger.info(f"Writer agent initialized: {self.agent_id}")

    async def execute_task(self, task_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute writing task using LangChain-based approach.
        """
        try:
            self.set_busy(context.get('task_id', 'unknown'))

            content_type = task_data.get("content_type", "report")
            source_data = task_data.get("source_data", {})
            format_requirements = task_data.get("format", "standard")
            target_audience = task_data.get("audience", "general")
            length_requirement = task_data.get("length", "medium")
            style_guide = task_data.get("style", "professional")

            if not source_data:
                raise ValueError("No source data provided for content generation")

            # Create LangChain agent executor for this task
            agent_executor = await self.create_langchain_agent(context)

            # Prepare writing input
            writing_input = {
                "input": f"Generate {content_type} content based on provided source data",
                "task_description": f"""
                Content Type: {content_type}
                Source Data: {self._format_source_data(source_data)}
                Format Requirements: {format_requirements}
                Target Audience: {target_audience}
                Length Requirement: {length_requirement}
                Style Guide: {style_guide}
                Domain Specialization: {self.config.domain_specialization or 'General'}

                Please generate comprehensive content including:
                1. Compelling title and executive summary
                2. Well-structured main content with clear sections
                3. Key points and highlights
                4. Conclusions and insights
                5. Actionable recommendations
                6. Proper formatting and readability
                7. References and citations where applicable
                """,
                "expected_output": f"High-quality {content_type} content formatted according to {format_requirements} requirements for {target_audience} audience",
                "input_data": task_data
            }

            # Execute the writing task using LangChain agent
            result = await agent_executor.ainvoke(writing_input)

            # Process and structure the result
            # Extract the actual output from LangChain result
            actual_output = result.get('output', str(result))
            structured_result = self._structure_writing_result(actual_output, content_type, format_requirements)

            # Store in memory for future reference
            self.add_memory('last_writing', {
                'content_type': content_type,
                'format': format_requirements,
                'result': structured_result,
                'timestamp': context.get('timestamp')
            })

            self.set_available()

            return structured_result

        except Exception as e:
            self.set_available()
            logger.error(f"Writing task failed: {e}")
            raise

    def get_capabilities(self) -> List[str]:
        """Get the capabilities of this agent."""
        return [
            "content_generation",
            "report_writing",
            "documentation",
            "summary_creation",
            "technical_writing",
            "structured_formatting",
            "audience_adaptation",
            "style_customization"
        ]

    def _format_source_data(self, source_data: Dict[str, Any]) -> str:
        """
        Format source data for writing presentation.

        Args:
            source_data: Source data to format

        Returns:
            Formatted source data string
        """
        if isinstance(source_data, dict):
            formatted_lines = []
            for key, value in source_data.items():
                if isinstance(value, (list, dict)):
                    formatted_lines.append(f"{key.title()}: {self._summarize_complex_data(value)}")
                else:
                    formatted_lines.append(f"{key.title()}: {value}")
            return "\n".join(formatted_lines)
        else:
            return str(source_data)

    def _summarize_complex_data(self, data: Any) -> str:
        """Summarize complex data structures."""
        if isinstance(data, list):
            return f"List with {len(data)} items: {data[:3]}..." if len(data) > 3 else str(data)
        elif isinstance(data, dict):
            return f"Dictionary with {len(data)} keys: {list(data.keys())[:3]}..." if len(data) > 3 else str(data)
        else:
            return str(data)

    def _structure_writing_result(self, result: str, content_type: str, format_requirements: str) -> Dict[str, Any]:
        """
        Structure the writing result into a standardized format.

        Args:
            result: Raw writing result
            content_type: Type of content generated
            format_requirements: Format requirements

        Returns:
            Structured writing result
        """
        return {
            "content_type": content_type,
            "format": format_requirements,
            "title": self._extract_title(result),
            "executive_summary": self._extract_executive_summary(result),
            "main_content": self._extract_main_content(result),
            "key_points": self._extract_key_points(result),
            "conclusions": self._extract_conclusions(result),
            "recommendations": self._extract_recommendations(result),
            "references": self._extract_references(result),
            "full_content": result,
            "word_count": len(result.split()),
            "readability_score": self._calculate_readability_score(result),
            "quality_metrics": self._assess_content_quality(result)
        }

    def _extract_title(self, result: str) -> str:
        """Extract title from writing result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        lines = result.split('\n')
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if line and not line.startswith('#') and len(line) < 100:
                return line
        return "Generated Content"

    def _extract_executive_summary(self, result: str) -> str:
        """Extract executive summary from writing result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        lines = result.split('\n')
        summary_lines = []
        in_summary = False

        for line in lines:
            line = line.strip()
            if 'executive summary' in line.lower() or 'summary' in line.lower():
                in_summary = True
                continue
            elif in_summary and line.startswith('#'):
                break
            elif in_summary and line:
                summary_lines.append(line)

        if summary_lines:
            return ' '.join(summary_lines)[:500] + "..." if len(' '.join(summary_lines)) > 500 else ' '.join(summary_lines)
        else:
            # Fallback: use first paragraph
            return self._extract_first_paragraph(result)

    def _extract_first_paragraph(self, result: str) -> str:
        """Extract first substantial paragraph."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        lines = result.split('\n')
        paragraph_lines = []

        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                paragraph_lines.append(line)
                if len(' '.join(paragraph_lines)) > 200:
                    break

        return ' '.join(paragraph_lines)[:300] + "..." if len(' '.join(paragraph_lines)) > 300 else ' '.join(paragraph_lines)

    def _extract_main_content(self, result: str) -> str:
        """Extract main content sections."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        # Remove title and summary, return the rest
        lines = result.split('\n')
        content_lines = []
        skip_lines = 0

        for i, line in enumerate(lines):
            if i < skip_lines:
                continue
            if 'executive summary' in line.lower():
                # Skip summary section
                skip_lines = i + 10
                continue
            content_lines.append(line)

        return '\n'.join(content_lines)

    def _extract_key_points(self, result: str) -> List[str]:
        """Extract key points from writing result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        key_points = []
        lines = result.split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith(('- ', '• ', '* ', '1. ', '2. ', '3.')):
                key_points.append(line)
            elif line.startswith(('Key point:', 'Important:', 'Note:')):
                key_points.append(line)

        return key_points[:10]  # Limit to top 10 key points

    def _extract_conclusions(self, result: str) -> List[str]:
        """Extract conclusions from writing result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        conclusions = []
        lines = result.split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith(('Conclusion:', 'In conclusion:', 'Therefore:')):
                conclusions.append(line)
            elif 'conclusion' in line.lower() and len(line) > 20:
                conclusions.append(line)

        return conclusions[:5]  # Limit to top 5 conclusions

    def _extract_recommendations(self, result: str) -> List[str]:
        """Extract recommendations from writing result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        recommendations = []
        lines = result.split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith(('Recommendation:', 'Recommend:', 'Suggest:')):
                recommendations.append(line)
            elif 'recommend' in line.lower() or 'should' in line.lower():
                recommendations.append(line)

        return recommendations[:6]  # Limit to top 6 recommendations

    def _extract_references(self, result: str) -> List[str]:
        """Extract references from writing result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        references = []
        lines = result.split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith(('Reference:', 'Source:', 'Citation:')):
                references.append(line)
            elif 'http' in line or 'www.' in line:
                references.append(line)

        return references[:10]  # Limit to 10 references

    def _calculate_readability_score(self, result: str) -> float:
        """Calculate readability score for the content."""
        # Simple readability heuristic
        sentences = result.count('.') + result.count('!') + result.count('?')
        words = len(result.split())

        if sentences == 0:
            return 0.5

        avg_sentence_length = words / sentences

        # Ideal sentence length is around 15-20 words
        if 15 <= avg_sentence_length <= 20:
            readability = 0.9
        elif 10 <= avg_sentence_length <= 25:
            readability = 0.8
        elif 8 <= avg_sentence_length <= 30:
            readability = 0.7
        else:
            readability = 0.6

        # Adjust for complexity indicators
        complex_words = sum(1 for word in result.split() if len(word) > 8)
        complexity_ratio = complex_words / words if words > 0 else 0

        if complexity_ratio > 0.3:
            readability -= 0.1
        elif complexity_ratio < 0.1:
            readability += 0.1

        return max(0.1, min(1.0, readability))

    def _assess_content_quality(self, result: str) -> Dict[str, Any]:
        """Assess the quality of generated content."""
        word_count = len(result.split())
        sentence_count = result.count('.') + result.count('!') + result.count('?')
        paragraph_count = len([p for p in result.split('\n\n') if p.strip()])

        # Quality indicators
        structure_score = min(paragraph_count / 5, 1.0)  # Normalize to 5 paragraphs
        length_score = min(word_count / 500, 1.0)  # Normalize to 500 words
        readability = self._calculate_readability_score(result)

        overall_quality = (structure_score + length_score + readability) / 3

        return {
            "overall_quality": overall_quality,
            "structure_score": structure_score,
            "length_score": length_score,
            "readability_score": readability,
            "word_count": word_count,
            "sentence_count": sentence_count,
            "paragraph_count": paragraph_count,
            "quality_level": "high" if overall_quality > 0.8 else "medium" if overall_quality > 0.6 else "low"
        }

    def get_writing_history(self) -> List[Dict[str, Any]]:
        """
        Get history of writing tasks completed.

        Returns:
            List of writing history entries
        """
        history = []
        last_writing = self.get_memory('last_writing')
        if last_writing:
            history.append(last_writing)
        return history

    def analyze_content_effectiveness(self, writing_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the effectiveness of generated content.

        Args:
            writing_result: Writing result to analyze

        Returns:
            Dictionary containing effectiveness analysis
        """
        quality_metrics = writing_result.get('quality_metrics', {})
        overall_quality = quality_metrics.get('overall_quality', 0.0)
        readability = quality_metrics.get('readability_score', 0.0)
        word_count = quality_metrics.get('word_count', 0)

        key_points_count = len(writing_result.get('key_points', []))
        conclusions_count = len(writing_result.get('conclusions', []))
        recommendations_count = len(writing_result.get('recommendations', []))

        # Calculate effectiveness
        content_completeness = min((key_points_count + conclusions_count + recommendations_count) / 10, 1.0)
        effectiveness = (overall_quality + readability + content_completeness) / 3

        return {
            "effectiveness_score": effectiveness,
            "content_quality": overall_quality,
            "readability": readability,
            "content_completeness": content_completeness,
            "word_count": word_count,
            "key_points": key_points_count,
            "conclusions": conclusions_count,
            "recommendations": recommendations_count,
            "effectiveness_level": "high" if effectiveness > 0.8 else "medium" if effectiveness > 0.6 else "low",
            "improvement_areas": self._identify_improvement_areas(writing_result)
        }

    def _identify_improvement_areas(self, writing_result: Dict[str, Any]) -> List[str]:
        """Identify areas for content improvement."""
        improvements = []

        quality_metrics = writing_result.get('quality_metrics', {})
        overall_quality = quality_metrics.get('overall_quality', 0.0)

        if overall_quality < 0.7:
            improvements.append("Improve overall content quality and structure")

        readability = quality_metrics.get('readability_score', 0.0)
        if readability < 0.7:
            improvements.append("Enhance readability with clearer language and sentence structure")

        word_count = quality_metrics.get('word_count', 0)
        if word_count < 300:
            improvements.append("Expand content to provide more comprehensive coverage")

        key_points_count = len(writing_result.get('key_points', []))
        if key_points_count < 3:
            improvements.append("Include more key points and highlights")

        conclusions_count = len(writing_result.get('conclusions', []))
        if conclusions_count < 1:
            improvements.append("Add clear conclusions and summary statements")

        return improvements

    def suggest_content_enhancements(self, writing_result: Dict[str, Any]) -> List[str]:
        """
        Suggest enhancements for generated content.

        Args:
            writing_result: Writing result to enhance

        Returns:
            List of enhancement suggestions
        """
        suggestions = []

        content_type = writing_result.get('content_type', '')

        if content_type == 'report':
            suggestions.append("Add visual elements like charts or graphs if applicable")
            suggestions.append("Include an appendix with supporting data")

        elif content_type == 'summary':
            suggestions.append("Ensure all key points from source material are covered")
            suggestions.append("Add action items or next steps")

        quality_metrics = writing_result.get('quality_metrics', {})
        if quality_metrics.get('paragraph_count', 0) < 3:
            suggestions.append("Break content into more digestible paragraphs")

        references = writing_result.get('references', [])
        if len(references) < 2:
            suggestions.append("Add more supporting references and citations")

        recommendations = writing_result.get('recommendations', [])
        if len(recommendations) < 2:
            suggestions.append("Provide more actionable recommendations")

        return suggestions

    def format_content_for_output(self, writing_result: Dict[str, Any], output_format: str = "markdown") -> str:
        """
        Format content for specific output requirements.

        Args:
            writing_result: Writing result to format
            output_format: Desired output format

        Returns:
            Formatted content string
        """
        title = writing_result.get('title', 'Generated Content')
        executive_summary = writing_result.get('executive_summary', '')
        main_content = writing_result.get('main_content', '')
        key_points = writing_result.get('key_points', [])
        conclusions = writing_result.get('conclusions', [])
        recommendations = writing_result.get('recommendations', [])

        if output_format.lower() == "markdown":
            formatted_content = [
                f"# {title}",
                "",
                "## Executive Summary",
                executive_summary,
                "",
                "## Main Content",
                main_content,
                ""
            ]

            if key_points:
                formatted_content.extend([
                    "## Key Points",
                    ""
                ])
                for point in key_points:
                    formatted_content.append(f"- {point}")
                formatted_content.append("")

            if conclusions:
                formatted_content.extend([
                    "## Conclusions",
                    ""
                ])
                for conclusion in conclusions:
                    formatted_content.append(f"- {conclusion}")
                formatted_content.append("")

            if recommendations:
                formatted_content.extend([
                    "## Recommendations",
                    ""
                ])
                for rec in recommendations:
                    formatted_content.append(f"- {rec}")

            return "\n".join(formatted_content)

        else:
            # Plain text format
            return writing_result.get('full_content', '')

    async def generate_specialized_content(self, writing_type: str, source_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate specialized content in a specific writing type.

        Args:
            writing_type: Type of specialized writing
            source_data: Source data for content generation
            context: Execution context

        Returns:
            Specialized writing result
        """
        if writing_type not in self.writing_types:
            raise ValueError(f"Unsupported writing type: {writing_type}")

        # Create specialized task data
        specialized_task_data = {
            "content_type": writing_type,
            "source_data": source_data,
            "format": self._get_format_for_writing_type(writing_type),
            "style": self._get_style_for_writing_type(writing_type),
            "audience": self._get_audience_for_writing_type(writing_type)
        }

        return await self.execute_task(specialized_task_data, context)

    def _get_format_for_writing_type(self, writing_type: str) -> str:
        """Get format requirements for specific writing types."""
        format_map = {
            "report_writing": "structured_report",
            "content_creation": "engaging_content",
            "documentation": "technical_documentation",
            "summary_writing": "executive_summary",
            "technical_writing": "technical_specification",
            "creative_writing": "narrative_format",
            "structured_output": "structured_data"
        }
        return format_map.get(writing_type, "standard")

    def _get_style_for_writing_type(self, writing_type: str) -> str:
        """Get style guide for specific writing types."""
        style_map = {
            "report_writing": "professional",
            "content_creation": "engaging",
            "documentation": "technical",
            "summary_writing": "concise",
            "technical_writing": "precise",
            "creative_writing": "creative",
            "structured_output": "formal"
        }
        return style_map.get(writing_type, "professional")

    def _get_audience_for_writing_type(self, writing_type: str) -> str:
        """Get target audience for specific writing types."""
        audience_map = {
            "report_writing": "business_stakeholders",
            "content_creation": "general_audience",
            "documentation": "technical_users",
            "summary_writing": "executives",
            "technical_writing": "technical_professionals",
            "creative_writing": "readers",
            "structured_output": "data_consumers"
        }
        return audience_map.get(writing_type, "general")

    def get_writing_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Get writing templates for different types of content.

        Returns:
            Dictionary of writing templates
        """
        return {
            "report_writing": {
                "description": "Comprehensive business or technical reports",
                "structure": ["executive_summary", "introduction", "methodology", "findings", "conclusions", "recommendations"],
                "style": "professional",
                "length": "long"
            },
            "content_creation": {
                "description": "Engaging content for various platforms",
                "structure": ["hook", "main_content", "call_to_action"],
                "style": "engaging",
                "length": "medium"
            },
            "documentation": {
                "description": "Technical documentation and user guides",
                "structure": ["overview", "requirements", "procedures", "examples", "troubleshooting"],
                "style": "technical",
                "length": "comprehensive"
            },
            "summary_writing": {
                "description": "Executive summaries and brief overviews",
                "structure": ["key_points", "main_findings", "recommendations"],
                "style": "concise",
                "length": "short"
            },
            "technical_writing": {
                "description": "Technical specifications and procedures",
                "structure": ["specifications", "implementation", "validation", "maintenance"],
                "style": "precise",
                "length": "detailed"
            },
            "creative_writing": {
                "description": "Creative and narrative content",
                "structure": ["introduction", "development", "climax", "resolution"],
                "style": "creative",
                "length": "variable"
            },
            "structured_output": {
                "description": "Structured data and formatted outputs",
                "structure": ["headers", "data_sections", "metadata", "references"],
                "style": "formal",
                "length": "structured"
            }
        }
