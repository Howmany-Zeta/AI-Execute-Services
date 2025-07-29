"""
Researcher Agent

Specialized agent for research tasks and information gathering.
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
from ...tasks.task_factory import TaskFactory
from ...config.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class ResearcherAgent(BaseAgent):
    """
    Agent specialized in research and information gathering tasks.

    Its task definition is provided by TaskFactory, and its LLM is dynamically
    configured by LLMIntegrationManager through the LangChain adapter.
    """

    def __init__(self, config: AgentConfig, config_manager: ConfigManager, llm_manager: LLMIntegrationManager, tool_integration_manager=None):
        """
        Initialize the researcher agent.

        Args:
            config: Agent's basic configuration (such as agent_id, role)
            config_manager: Configuration manager for reading prompts.yaml and llm_bindings.yaml
            llm_manager: LLM integration manager for actual LLM calls
            tool_integration_manager: Optional tool integration manager for LangChain tools
        """
        # Call parent's initialization method, which handles role definition and LLM binding loading
        super().__init__(config, config_manager, llm_manager, tool_integration_manager)

        # Research specializations
        self.research_areas = [
            "academic_research",
            "market_research",
            "competitive_analysis",
            "trend_analysis",
            "fact_checking",
            "source_verification"
        ]

        # LangChain agent executor instance
        self._agent_executor: AgentExecutor = None

    async def initialize(self) -> None:
        """Initialize the researcher agent."""
        logger.info(f"Researcher agent initialized: {self.agent_id}")

    async def execute_task(self, task_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute research task using LangChain-based approach.
        """
        try:
            self.set_busy(context.get('task_id', 'unknown'))

            research_topic = task_data.get("parameters", {}).get("query", "")
            research_type = task_data.get("type", "general")
            depth_level = task_data.get("depth", "medium")
            sources_required = task_data.get("sources", 5)

            if not research_topic:
                raise ValueError("No research topic provided")

            # Create LangChain agent executor for this task
            agent_executor = await self.create_langchain_agent(context)

            # Prepare research input
            research_input = {
                "input": f"Conduct {research_type} research on: {research_topic}",
                "task_description": f"""
                Research Topic: {research_topic}
                Research Type: {research_type}
                Depth Level: {depth_level}
                Sources Required: {sources_required}
                Domain Specialization: {self.config.domain_specialization or 'General'}

                Please provide comprehensive research including:
                1. Executive summary
                2. Key findings (at least {sources_required} sources)
                3. Insights and analysis
                4. Recommendations
                5. Source citations
                """,
                "expected_output": "Comprehensive research report with structured findings, insights, and recommendations",
                "input_data": task_data
            }

            # Execute the research using LangChain agent
            result = await agent_executor.ainvoke(research_input)

            # Process and structure the result
            # Extract the actual output from LangChain result
            actual_output = result.get('output', str(result))
            structured_result = self._structure_research_result(actual_output, research_topic, research_type)

            # Store in memory for future reference
            self.add_memory('last_research', {
                'topic': research_topic,
                'type': research_type,
                'result': structured_result,
                'timestamp': context.get('timestamp')
            })

            self.set_available()

            return structured_result

        except Exception as e:
            self.set_available()
            logger.error(f"Research task failed: {e}")
            raise

    def get_capabilities(self) -> List[str]:
        """Get the capabilities of this agent."""
        return [
            "information_gathering",
            "source_verification",
            "fact_checking",
            "trend_analysis",
            "competitive_research",
            "academic_research",
            "market_research"
        ]

    def _structure_research_result(self, result: str, topic: str, research_type: str) -> Dict[str, Any]:
        """
        Structure the research result into a standardized format.

        Args:
            result: Raw research result
            topic: Research topic
            research_type: Type of research

        Returns:
            Structured research result
        """
        return {
            "topic": topic,
            "research_type": research_type,
            "summary": self._extract_summary(result),
            "key_findings": self._extract_key_findings(result),
            "sources": self._extract_sources(result),
            "insights": self._extract_insights(result),
            "recommendations": self._extract_recommendations(result),
            "full_report": result,
            "confidence_level": self._assess_confidence(result),
            "completeness_score": self._assess_completeness(result)
        }

    def _extract_summary(self, result: str) -> str:
        """Extract executive summary from research result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        # Simple extraction - could be enhanced with NLP
        lines = result.split('\n')
        summary_lines = []

        for line in lines[:10]:  # First 10 lines likely contain summary
            if line.strip() and not line.startswith('#'):
                summary_lines.append(line.strip())

        return ' '.join(summary_lines)[:500] + "..." if len(' '.join(summary_lines)) > 500 else ' '.join(summary_lines)

    def _extract_key_findings(self, result: str) -> List[str]:
        """Extract key findings from research result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        findings = []
        lines = result.split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith('- ') or line.startswith('• ') or line.startswith('* '):
                findings.append(line[2:])
            elif line.startswith(('Key finding:', 'Finding:', 'Important:')):
                findings.append(line)

        return findings[:10]  # Limit to top 10 findings

    def _extract_sources(self, result: str) -> List[Dict[str, Any]]:
        """Extract sources from research result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        sources = []
        lines = result.split('\n')

        for line in lines:
            line = line.strip()
            if 'http' in line or 'www.' in line:
                sources.append({
                    "url": line,
                    "credibility": "medium",  # Default credibility
                    "type": "web"
                })
            elif line.startswith(('Source:', 'Reference:', 'Citation:')):
                sources.append({
                    "citation": line,
                    "credibility": "medium",
                    "type": "citation"
                })

        return sources[:20]  # Limit to 20 sources

    def _extract_insights(self, result: str) -> List[str]:
        """Extract insights from research result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        insights = []
        lines = result.split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith(('Insight:', 'Analysis:', 'Observation:')):
                insights.append(line)
            elif 'trend' in line.lower() or 'pattern' in line.lower():
                insights.append(line)

        return insights[:5]  # Limit to top 5 insights

    def _extract_recommendations(self, result: str) -> List[str]:
        """Extract recommendations from research result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        recommendations = []
        lines = result.split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith(('Recommendation:', 'Suggest:', 'Advice:')):
                recommendations.append(line)
            elif 'should' in line.lower() or 'recommend' in line.lower():
                recommendations.append(line)

        return recommendations[:5]  # Limit to top 5 recommendations

    def _assess_confidence(self, result: str) -> float:
        """Assess confidence level of research result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        # Simple heuristic based on content indicators
        confidence_indicators = [
            'verified', 'confirmed', 'established', 'proven',
            'documented', 'official', 'peer-reviewed'
        ]

        uncertainty_indicators = [
            'unclear', 'uncertain', 'possibly', 'might',
            'could be', 'appears', 'seems'
        ]

        result_lower = result.lower()
        confidence_count = sum(1 for indicator in confidence_indicators if indicator in result_lower)
        uncertainty_count = sum(1 for indicator in uncertainty_indicators if indicator in result_lower)

        # Calculate confidence score
        base_confidence = 0.7
        confidence_boost = min(confidence_count * 0.05, 0.2)
        confidence_penalty = min(uncertainty_count * 0.03, 0.15)

        return max(0.1, min(1.0, base_confidence + confidence_boost - confidence_penalty))

    def _assess_completeness(self, result: str) -> float:
        """Assess completeness of research result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        # Simple heuristic based on content length and structure
        word_count = len(result.split())
        line_count = len(result.split('\n'))

        # Expected minimums for complete research
        min_words = 500
        min_lines = 20

        word_score = min(word_count / min_words, 1.0)
        structure_score = min(line_count / min_lines, 1.0)

        return (word_score + structure_score) / 2

    def get_research_history(self) -> List[Dict[str, Any]]:
        """
        Get history of research conducted.

        Returns:
            List of research history entries
        """
        history = []
        last_research = self.get_memory('last_research')
        if last_research:
            history.append(last_research)
        return history

    def analyze_research_quality(self, research_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the quality of research results.

        Args:
            research_result: Research result to analyze

        Returns:
            Dictionary containing quality analysis
        """
        confidence = research_result.get('confidence_level', 0.0)
        completeness = research_result.get('completeness_score', 0.0)
        source_count = len(research_result.get('sources', []))
        findings_count = len(research_result.get('key_findings', []))

        overall_quality = (confidence + completeness) / 2

        return {
            "overall_quality": overall_quality,
            "confidence_level": confidence,
            "completeness_score": completeness,
            "source_count": source_count,
            "findings_count": findings_count,
            "quality_level": "high" if overall_quality > 0.8 else "medium" if overall_quality > 0.6 else "low",
            "recommendations": self._get_quality_recommendations(overall_quality, source_count, findings_count)
        }

    def _get_quality_recommendations(self, quality: float, sources: int, findings: int) -> List[str]:
        """Get recommendations for improving research quality."""
        recommendations = []

        if quality < 0.7:
            recommendations.append("Consider additional research to improve overall quality")

        if sources < 3:
            recommendations.append("Gather more sources to strengthen research foundation")

        if findings < 5:
            recommendations.append("Identify more key findings to provide comprehensive insights")

        if quality > 0.8:
            recommendations.append("Excellent research quality - ready for analysis phase")

        return recommendations

    def suggest_research_improvements(self, topic: str, current_result: Dict[str, Any]) -> List[str]:
        """
        Suggest improvements for research.

        Args:
            topic: Research topic
            current_result: Current research result

        Returns:
            List of improvement suggestions
        """
        suggestions = []

        confidence = current_result.get('confidence_level', 0.0)
        if confidence < 0.7:
            suggestions.append("Seek more authoritative sources to increase confidence")

        completeness = current_result.get('completeness_score', 0.0)
        if completeness < 0.8:
            suggestions.append("Expand research scope to cover more aspects of the topic")

        sources = current_result.get('sources', [])
        if len(sources) < 5:
            suggestions.append("Include more diverse sources for comprehensive coverage")

        insights = current_result.get('insights', [])
        if len(insights) < 3:
            suggestions.append("Develop deeper analytical insights from the gathered data")

        return suggestions

    async def conduct_specialized_research(self, research_area: str, topic: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Conduct specialized research in a specific area.

        Args:
            research_area: Area of specialization
            topic: Research topic
            context: Execution context

        Returns:
            Specialized research result
        """
        if research_area not in self.research_areas:
            raise ValueError(f"Unsupported research area: {research_area}")

        # Create specialized task data
        specialized_task_data = {
            "parameters": {"query": topic},
            "type": research_area,
            "depth": "deep",
            "sources": 10,
            "specialization": research_area
        }

        return await self.execute_task(specialized_task_data, context)

    def get_research_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Get research templates for different types of research.

        Returns:
            Dictionary of research templates
        """
        return {
            "academic_research": {
                "description": "Comprehensive academic research with peer-reviewed sources",
                "required_sources": 10,
                "depth": "deep",
                "focus_areas": ["literature_review", "methodology", "findings", "conclusions"]
            },
            "market_research": {
                "description": "Market analysis and competitive intelligence",
                "required_sources": 8,
                "depth": "medium",
                "focus_areas": ["market_size", "competitors", "trends", "opportunities"]
            },
            "competitive_analysis": {
                "description": "Analysis of competitors and market positioning",
                "required_sources": 6,
                "depth": "medium",
                "focus_areas": ["competitor_profiles", "strengths_weaknesses", "market_share", "strategies"]
            },
            "trend_analysis": {
                "description": "Analysis of current and emerging trends",
                "required_sources": 5,
                "depth": "medium",
                "focus_areas": ["current_trends", "emerging_patterns", "future_predictions", "implications"]
            },
            "fact_checking": {
                "description": "Verification of facts and claims",
                "required_sources": 3,
                "depth": "focused",
                "focus_areas": ["source_verification", "cross_referencing", "credibility_assessment", "conclusion"]
            }
        }
