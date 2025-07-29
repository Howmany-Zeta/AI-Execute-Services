"""
Analyst Agent

Specialized agent for data analysis and analytical tasks.
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


class AnalystAgent(BaseAgent):
    """
    Agent specialized in data analysis and analytical reasoning.

    Its task definition is provided by TaskFactory, and its LLM is dynamically
    configured by LLMIntegrationManager through the LangChain adapter.
    """

    def __init__(self, config: AgentConfig, config_manager: ConfigManager, llm_manager: LLMIntegrationManager, tool_integration_manager=None):
        """
        Initialize the analyst agent.

        Args:
            config: Agent's basic configuration (such as agent_id, role)
            config_manager: Configuration manager for reading prompts.yaml and llm_bindings.yaml
            llm_manager: LLM integration manager for actual LLM calls
            tool_integration_manager: Optional tool integration manager for LangChain tools
        """
        # Call parent's initialization method, which handles role definition and LLM binding loading
        super().__init__(config, config_manager, llm_manager, tool_integration_manager)

        # Analysis specializations
        self.analysis_types = [
            "statistical_analysis",
            "trend_analysis",
            "comparative_analysis",
            "pattern_recognition",
            "data_interpretation",
            "predictive_analysis",
            "root_cause_analysis"
        ]

        # LangChain agent executor instance
        self._agent_executor: AgentExecutor = None

    async def initialize(self) -> None:
        """Initialize the analyst agent."""
        logger.info(f"Analyst agent initialized: {self.agent_id}")

    async def execute_task(self, task_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute analysis task using LangChain-based approach.
        """
        try:
            self.set_busy(context.get('task_id', 'unknown'))

            data_to_analyze = task_data.get("data", {})
            analysis_type = task_data.get("analysis_type", "general")
            focus_areas = task_data.get("focus_areas", [])
            depth_level = task_data.get("depth", "medium")

            if not data_to_analyze:
                raise ValueError("No data provided for analysis")

            # Create LangChain agent executor for this task
            agent_executor = await self.create_langchain_agent(context)

            # Prepare analysis input
            analysis_input = {
                "input": f"Perform {analysis_type} analysis on the provided data",
                "task_description": f"""
                Data to Analyze: {self._format_data_for_analysis(data_to_analyze)}
                Analysis Type: {analysis_type}
                Focus Areas: {focus_areas}
                Depth Level: {depth_level}
                Domain Specialization: {self.config.domain_specialization or 'General'}

                Please provide comprehensive analysis including:
                1. Executive summary
                2. Key insights and findings
                3. Patterns and trends identified
                4. Data quality assessment
                5. Methodology used
                6. Recommendations and next steps
                7. Limitations and caveats
                """,
                "expected_output": "Comprehensive analytical report with structured findings, insights, and actionable recommendations",
                "input_data": task_data
            }

            # Execute the analysis using LangChain agent
            result = await agent_executor.ainvoke(analysis_input)

            # Process and structure the result
            # Extract the actual output from LangChain result
            actual_output = result.get('output', str(result))
            structured_result = self._structure_analysis_result(actual_output, analysis_type, data_to_analyze)

            # Store in memory for future reference
            self.add_memory('last_analysis', {
                'analysis_type': analysis_type,
                'data_summary': self._summarize_data(data_to_analyze),
                'result': structured_result,
                'timestamp': context.get('timestamp')
            })

            self.set_available()

            return structured_result

        except Exception as e:
            self.set_available()
            logger.error(f"Analysis task failed: {e}")
            raise

    def get_capabilities(self) -> List[str]:
        """Get the capabilities of this agent."""
        return [
            "data_analysis",
            "statistical_analysis",
            "pattern_recognition",
            "trend_analysis",
            "comparative_analysis",
            "predictive_modeling",
            "insight_generation",
            "data_interpretation"
        ]

    def _format_data_for_analysis(self, data: Dict[str, Any]) -> str:
        """
        Format data for analysis presentation.

        Args:
            data: Data to format

        Returns:
            Formatted data string
        """
        if isinstance(data, dict):
            formatted_lines = []
            for key, value in data.items():
                if isinstance(value, (list, dict)):
                    formatted_lines.append(f"{key}: {type(value).__name__} with {len(value)} items")
                else:
                    formatted_lines.append(f"{key}: {value}")
            return "\n".join(formatted_lines)
        else:
            return str(data)

    def _structure_analysis_result(self, result: str, analysis_type: str, original_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Structure the analysis result into a standardized format.

        Args:
            result: Raw analysis result
            analysis_type: Type of analysis performed
            original_data: Original data that was analyzed

        Returns:
            Structured analysis result
        """
        return {
            "analysis_type": analysis_type,
            "summary": self._extract_summary(result),
            "key_insights": self._extract_insights(result),
            "findings": self._extract_findings(result),
            "patterns": self._extract_patterns(result),
            "recommendations": self._extract_recommendations(result),
            "data_quality": self._assess_data_quality(original_data),
            "methodology": self._extract_methodology(result),
            "limitations": self._extract_limitations(result),
            "full_report": result,
            "confidence_score": self._calculate_confidence_score(result),
            "actionability_score": self._calculate_actionability_score(result)
        }

    def _extract_summary(self, result: str) -> str:
        """Extract executive summary from analysis result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        lines = result.split('\n')
        summary_lines = []

        for line in lines[:15]:  # First 15 lines likely contain summary
            if line.strip() and not line.startswith('#'):
                summary_lines.append(line.strip())

        return ' '.join(summary_lines)[:600] + "..." if len(' '.join(summary_lines)) > 600 else ' '.join(summary_lines)

    def _extract_insights(self, result: str) -> List[str]:
        """Extract key insights from analysis result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        insights = []
        lines = result.split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith(('Insight:', 'Key insight:', 'Analysis shows:', 'Data reveals:')):
                insights.append(line)
            elif any(keyword in line.lower() for keyword in ['correlation', 'trend', 'pattern', 'significant']):
                insights.append(line)

        return insights[:8]  # Limit to top 8 insights

    def _extract_findings(self, result: str) -> List[str]:
        """Extract findings from analysis result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        findings = []
        lines = result.split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith(('Finding:', 'Result:', 'Observation:', 'Discovery:')):
                findings.append(line)
            elif line.startswith('- ') and any(keyword in line.lower() for keyword in ['found', 'shows', 'indicates']):
                findings.append(line[2:])

        return findings[:10]  # Limit to top 10 findings

    def _extract_patterns(self, result: str) -> List[str]:
        """Extract patterns from analysis result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        patterns = []
        lines = result.split('\n')

        for line in lines:
            line = line.strip()
            if 'pattern' in line.lower() or 'trend' in line.lower():
                patterns.append(line)
            elif line.startswith(('Pattern:', 'Trend:', 'Cycle:')):
                patterns.append(line)

        return patterns[:5]  # Limit to top 5 patterns

    def _extract_recommendations(self, result: str) -> List[str]:
        """Extract recommendations from analysis result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        recommendations = []
        lines = result.split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith(('Recommendation:', 'Suggest:', 'Action:', 'Next step:')):
                recommendations.append(line)
            elif 'should' in line.lower() or 'recommend' in line.lower():
                recommendations.append(line)

        return recommendations[:6]  # Limit to top 6 recommendations

    def _extract_methodology(self, result: str) -> str:
        """Extract methodology from analysis result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        lines = result.split('\n')
        methodology_lines = []

        for line in lines:
            line = line.strip()
            if line.startswith(('Method:', 'Methodology:', 'Approach:', 'Analysis method:')):
                methodology_lines.append(line)
            elif 'method' in line.lower() or 'approach' in line.lower():
                methodology_lines.append(line)

        return ' '.join(methodology_lines) if methodology_lines else "Standard analytical methodology applied"

    def _extract_limitations(self, result: str) -> List[str]:
        """Extract limitations from analysis result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        limitations = []
        lines = result.split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith(('Limitation:', 'Constraint:', 'Note:', 'Caveat:')):
                limitations.append(line)
            elif 'limitation' in line.lower() or 'constraint' in line.lower():
                limitations.append(line)

        return limitations[:4]  # Limit to top 4 limitations

    def _assess_data_quality(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the quality of the input data."""
        if not isinstance(data, dict):
            return {"quality_score": 0.5, "issues": ["Data format not optimal for analysis"]}

        quality_score = 0.7  # Base score
        issues = []
        strengths = []

        # Check data completeness
        if len(data) < 3:
            quality_score -= 0.1
            issues.append("Limited data points available")
        else:
            strengths.append("Sufficient data points for analysis")

        # Check for missing values (simplified)
        missing_count = sum(1 for value in data.values() if value is None or value == "")
        if missing_count > 0:
            quality_score -= min(missing_count * 0.05, 0.2)
            issues.append(f"Missing values detected: {missing_count}")
        else:
            strengths.append("No missing values detected")

        return {
            "quality_score": max(0.1, min(1.0, quality_score)),
            "issues": issues,
            "strengths": strengths
        }

    def _calculate_confidence_score(self, result: str) -> float:
        """Calculate confidence score for the analysis."""
        confidence_indicators = [
            'statistically significant', 'strong correlation', 'clear pattern',
            'consistent', 'reliable', 'validated', 'confirmed'
        ]

        uncertainty_indicators = [
            'uncertain', 'unclear', 'possibly', 'might', 'could be',
            'appears', 'seems', 'limited data'
        ]

        result_lower = result.lower()
        confidence_count = sum(1 for indicator in confidence_indicators if indicator in result_lower)
        uncertainty_count = sum(1 for indicator in uncertainty_indicators if indicator in result_lower)

        base_confidence = 0.7
        confidence_boost = min(confidence_count * 0.06, 0.25)
        confidence_penalty = min(uncertainty_count * 0.04, 0.2)

        return max(0.1, min(1.0, base_confidence + confidence_boost - confidence_penalty))

    def _calculate_actionability_score(self, result: str) -> float:
        """Calculate how actionable the analysis results are."""
        actionable_indicators = [
            'recommend', 'should', 'action', 'implement', 'strategy',
            'next step', 'priority', 'focus on'
        ]

        result_lower = result.lower()
        actionable_count = sum(1 for indicator in actionable_indicators if indicator in result_lower)

        # Base score plus boost for actionable content
        base_score = 0.6
        actionability_boost = min(actionable_count * 0.08, 0.3)

        return max(0.1, min(1.0, base_score + actionability_boost))

    def _summarize_data(self, data: Dict[str, Any]) -> str:
        """Create a summary of the analyzed data."""
        if isinstance(data, dict):
            return f"Dictionary with {len(data)} keys: {list(data.keys())[:5]}"
        else:
            return f"{type(data).__name__} data structure"

    def get_analysis_history(self) -> List[Dict[str, Any]]:
        """
        Get history of analyses performed.

        Returns:
            List of analysis history entries
        """
        history = []
        last_analysis = self.get_memory('last_analysis')
        if last_analysis:
            history.append(last_analysis)
        return history

    def evaluate_analysis_quality(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate the quality of analysis results.

        Args:
            analysis_result: Analysis result to evaluate

        Returns:
            Dictionary containing quality evaluation
        """
        confidence = analysis_result.get('confidence_score', 0.0)
        actionability = analysis_result.get('actionability_score', 0.0)
        data_quality = analysis_result.get('data_quality', {}).get('quality_score', 0.0)

        insights_count = len(analysis_result.get('key_insights', []))
        recommendations_count = len(analysis_result.get('recommendations', []))

        # Calculate overall quality
        overall_quality = (confidence + actionability + data_quality) / 3

        return {
            "overall_quality": overall_quality,
            "confidence_score": confidence,
            "actionability_score": actionability,
            "data_quality_score": data_quality,
            "insights_count": insights_count,
            "recommendations_count": recommendations_count,
            "quality_level": "high" if overall_quality > 0.8 else "medium" if overall_quality > 0.6 else "low",
            "improvement_areas": self._identify_improvement_areas(analysis_result)
        }

    def _identify_improvement_areas(self, analysis_result: Dict[str, Any]) -> List[str]:
        """Identify areas for improvement in analysis."""
        improvements = []

        confidence = analysis_result.get('confidence_score', 0.0)
        if confidence < 0.7:
            improvements.append("Increase analysis confidence with more robust methodology")

        actionability = analysis_result.get('actionability_score', 0.0)
        if actionability < 0.7:
            improvements.append("Provide more actionable recommendations")

        insights_count = len(analysis_result.get('key_insights', []))
        if insights_count < 3:
            improvements.append("Generate more analytical insights")

        recommendations_count = len(analysis_result.get('recommendations', []))
        if recommendations_count < 2:
            improvements.append("Develop more specific recommendations")

        return improvements

    def suggest_follow_up_analysis(self, current_analysis: Dict[str, Any]) -> List[str]:
        """
        Suggest follow-up analysis based on current results.

        Args:
            current_analysis: Current analysis result

        Returns:
            List of follow-up analysis suggestions
        """
        suggestions = []

        analysis_type = current_analysis.get('analysis_type', '')
        patterns = current_analysis.get('patterns', [])

        if analysis_type == 'descriptive':
            suggestions.append("Conduct diagnostic analysis to understand root causes")

        if analysis_type in ['descriptive', 'diagnostic']:
            suggestions.append("Perform predictive analysis to forecast future trends")

        if len(patterns) > 0:
            suggestions.append("Deep dive analysis on identified patterns")

        confidence = current_analysis.get('confidence_score', 0.0)
        if confidence < 0.8:
            suggestions.append("Gather additional data to improve analysis confidence")

        return suggestions

    async def conduct_specialized_analysis(self, analysis_type: str, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Conduct specialized analysis in a specific area.

        Args:
            analysis_type: Type of specialized analysis
            data: Data to analyze
            context: Execution context

        Returns:
            Specialized analysis result
        """
        if analysis_type not in self.analysis_types:
            raise ValueError(f"Unsupported analysis type: {analysis_type}")

        # Create specialized task data
        specialized_task_data = {
            "data": data,
            "analysis_type": analysis_type,
            "depth": "deep",
            "focus_areas": self._get_focus_areas_for_analysis_type(analysis_type)
        }

        return await self.execute_task(specialized_task_data, context)

    def _get_focus_areas_for_analysis_type(self, analysis_type: str) -> List[str]:
        """Get focus areas for specific analysis types."""
        focus_areas_map = {
            "statistical_analysis": ["descriptive_stats", "inferential_stats", "hypothesis_testing"],
            "trend_analysis": ["temporal_patterns", "seasonality", "growth_rates"],
            "comparative_analysis": ["benchmarking", "variance_analysis", "performance_gaps"],
            "pattern_recognition": ["clustering", "anomaly_detection", "correlation_analysis"],
            "data_interpretation": ["business_insights", "actionable_findings", "implications"],
            "predictive_analysis": ["forecasting", "modeling", "scenario_analysis"],
            "root_cause_analysis": ["causal_factors", "contributing_elements", "systemic_issues"]
        }
        return focus_areas_map.get(analysis_type, ["general_analysis"])

    def get_analysis_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Get analysis templates for different types of analysis.

        Returns:
            Dictionary of analysis templates
        """
        return {
            "statistical_analysis": {
                "description": "Comprehensive statistical analysis with hypothesis testing",
                "required_data_points": 30,
                "depth": "deep",
                "focus_areas": ["descriptive_stats", "inferential_stats", "significance_testing"]
            },
            "trend_analysis": {
                "description": "Analysis of trends and patterns over time",
                "required_data_points": 20,
                "depth": "medium",
                "focus_areas": ["temporal_patterns", "seasonality", "trend_direction"]
            },
            "comparative_analysis": {
                "description": "Comparison between different groups or time periods",
                "required_data_points": 15,
                "depth": "medium",
                "focus_areas": ["group_differences", "performance_gaps", "benchmarking"]
            },
            "pattern_recognition": {
                "description": "Identification of patterns and anomalies in data",
                "required_data_points": 25,
                "depth": "deep",
                "focus_areas": ["clustering", "anomaly_detection", "correlation_patterns"]
            },
            "predictive_analysis": {
                "description": "Forecasting and predictive modeling",
                "required_data_points": 50,
                "depth": "deep",
                "focus_areas": ["forecasting", "model_validation", "scenario_analysis"]
            }
        }
