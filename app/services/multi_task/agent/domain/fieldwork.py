"""
Fieldwork Agent

Specialized agent for fieldwork and hands-on data collection tasks.
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


class FieldworkAgent(BaseAgent):
    """
    Agent specialized in fieldwork and practical data collection.

    Its task definition is provided by TaskFactory, and its LLM is dynamically
    configured by LLMIntegrationManager through the LangChain adapter.
    """

    def __init__(self, config: AgentConfig, config_manager: ConfigManager, llm_manager: LLMIntegrationManager, tool_integration_manager=None):
        """
        Initialize the fieldwork agent.

        Args:
            config: Agent's basic configuration (such as agent_id, role)
            config_manager: Configuration manager for reading prompts.yaml and llm_bindings.yaml
            llm_manager: LLM integration manager for actual LLM calls
            tool_integration_manager: Optional tool integration manager for LangChain tools
        """
        # Call parent's initialization method, which handles role definition and LLM binding loading
        super().__init__(config, config_manager, llm_manager, tool_integration_manager)

        # Fieldwork specializations
        self.fieldwork_types = [
            "data_collection",
            "verification_tasks",
            "testing_procedures",
            "validation_activities",
            "monitoring_tasks",
            "inspection_work",
            "survey_execution"
        ]

        # LangChain agent executor instance
        self._agent_executor: AgentExecutor = None

    async def initialize(self) -> None:
        """Initialize the fieldwork agent."""
        logger.info(f"Fieldwork agent initialized: {self.agent_id}")

    async def execute_task(self, task_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute fieldwork task using LangChain-based approach.
        """
        try:
            self.set_busy(context.get('task_id', 'unknown'))

            task_type = task_data.get("task_type", "data_collection")
            target_scope = task_data.get("scope", "general")
            methodology = task_data.get("methodology", "standard")
            quality_requirements = task_data.get("quality_requirements", {})

            if not task_type:
                raise ValueError("No fieldwork task type provided")

            # Create LangChain agent executor for this task
            agent_executor = await self.create_langchain_agent(context)

            # Prepare fieldwork input
            fieldwork_input = {
                "input": f"Execute {task_type} fieldwork task with {methodology} methodology",
                "task_description": f"""
                Task Type: {task_type}
                Target Scope: {target_scope}
                Methodology: {methodology}
                Quality Requirements: {quality_requirements}
                Domain Specialization: {self.config.domain_specialization or 'General'}

                Please execute comprehensive fieldwork including:
                1. Data collection according to specified methodology
                2. Quality validation and verification procedures
                3. Documentation of findings and observations
                4. Assessment of data quality and completeness
                5. Identification of issues and challenges
                6. Recommendations for follow-up actions
                7. Validation results and compliance checks
                """,
                "expected_output": "Comprehensive fieldwork report with collected data, quality metrics, findings, and validation results",
                "input_data": task_data
            }

            # Execute the fieldwork using LangChain agent
            result = await agent_executor.ainvoke(fieldwork_input)

            # Process and structure the result
            # Extract the actual output from LangChain result
            actual_output = result.get('output', str(result))
            structured_result = self._structure_analysis_result(actual_output, analysis_type, data_to_analyze)

            # Store in memory for future reference
            self.add_memory('last_fieldwork', {
                'task_type': task_type,
                'scope': target_scope,
                'result': structured_result,
                'timestamp': context.get('timestamp')
            })

            self.set_available()

            return structured_result

        except Exception as e:
            self.set_available()
            logger.error(f"Fieldwork task failed: {e}")
            raise

    def get_capabilities(self) -> List[str]:
        """Get the capabilities of this agent."""
        return [
            "data_collection",
            "field_verification",
            "quality_testing",
            "validation_procedures",
            "monitoring_activities",
            "inspection_tasks",
            "survey_execution",
            "hands_on_validation"
        ]

    def _structure_fieldwork_result(self, result: str, task_type: str, scope: str) -> Dict[str, Any]:
        """
        Structure the fieldwork result into a standardized format.

        Args:
            result: Raw fieldwork result
            task_type: Type of fieldwork performed
            scope: Scope of the fieldwork

        Returns:
            Structured fieldwork result
        """
        return {
            "task_type": task_type,
            "scope": scope,
            "summary": self._extract_summary(result),
            "collected_data": self._extract_collected_data(result),
            "methodology": self._extract_methodology(result),
            "quality_metrics": self._extract_quality_metrics(result),
            "findings": self._extract_findings(result),
            "issues_encountered": self._extract_issues(result),
            "recommendations": self._extract_recommendations(result),
            "validation_results": self._extract_validation_results(result),
            "full_report": result,
            "completion_status": self._assess_completion_status(result),
            "quality_score": self._calculate_quality_score(result)
        }

    def _extract_summary(self, result: str) -> str:
        """Extract executive summary from fieldwork result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        lines = result.split('\n')
        summary_lines = []

        for line in lines[:12]:  # First 12 lines likely contain summary
            if line.strip() and not line.startswith('#'):
                summary_lines.append(line.strip())

        return ' '.join(summary_lines)[:500] + "..." if len(' '.join(summary_lines)) > 500 else ' '.join(summary_lines)

    def _extract_collected_data(self, result: str) -> List[Dict[str, Any]]:
        """Extract collected data from fieldwork result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        data_items = []
        lines = result.split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith(('Data:', 'Collected:', 'Found:', 'Measured:')):
                data_items.append({
                    "type": "measurement",
                    "value": line,
                    "source": "fieldwork"
                })
            elif line.startswith('- ') and any(keyword in line.lower() for keyword in ['data', 'value', 'result']):
                data_items.append({
                    "type": "observation",
                    "value": line[2:],
                    "source": "fieldwork"
                })

        return data_items[:15]  # Limit to 15 data items

    def _extract_methodology(self, result: str) -> Dict[str, Any]:
        """Extract methodology from fieldwork result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        lines = result.split('\n')
        methodology_info = {
            "approach": "Standard fieldwork methodology",
            "tools_used": [],
            "procedures": [],
            "duration": "Not specified"
        }

        for line in lines:
            line = line.strip()
            if line.startswith(('Method:', 'Methodology:', 'Approach:', 'Procedure:')):
                methodology_info["approach"] = line
            elif 'tool' in line.lower() or 'instrument' in line.lower():
                methodology_info["tools_used"].append(line)
            elif 'step' in line.lower() or 'procedure' in line.lower():
                methodology_info["procedures"].append(line)
            elif 'duration' in line.lower() or 'time' in line.lower():
                methodology_info["duration"] = line

        return methodology_info

    def _extract_quality_metrics(self, result: str) -> Dict[str, Any]:
        """Extract quality metrics from fieldwork result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        lines = result.split('\n')
        quality_metrics = {
            "accuracy": "Not assessed",
            "completeness": "Not assessed",
            "reliability": "Not assessed",
            "timeliness": "Not assessed"
        }

        for line in lines:
            line = line.strip().lower()
            if 'accuracy' in line:
                quality_metrics["accuracy"] = line
            elif 'completeness' in line or 'complete' in line:
                quality_metrics["completeness"] = line
            elif 'reliability' in line or 'reliable' in line:
                quality_metrics["reliability"] = line
            elif 'timeliness' in line or 'timely' in line:
                quality_metrics["timeliness"] = line

        return quality_metrics

    def _extract_findings(self, result: str) -> List[str]:
        """Extract findings from fieldwork result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        findings = []
        lines = result.split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith(('Finding:', 'Result:', 'Observation:', 'Discovery:')):
                findings.append(line)
            elif line.startswith('- ') and any(keyword in line.lower() for keyword in ['found', 'observed', 'noted']):
                findings.append(line[2:])

        return findings[:10]  # Limit to top 10 findings

    def _extract_issues(self, result: str) -> List[str]:
        """Extract issues encountered from fieldwork result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        issues = []
        lines = result.split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith(('Issue:', 'Problem:', 'Challenge:', 'Limitation:')):
                issues.append(line)
            elif any(keyword in line.lower() for keyword in ['issue', 'problem', 'challenge', 'difficulty']):
                issues.append(line)

        return issues[:8]  # Limit to top 8 issues

    def _extract_recommendations(self, result: str) -> List[str]:
        """Extract recommendations from fieldwork result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        recommendations = []
        lines = result.split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith(('Recommendation:', 'Suggest:', 'Advice:', 'Next step:')):
                recommendations.append(line)
            elif 'recommend' in line.lower() or 'should' in line.lower():
                recommendations.append(line)

        return recommendations[:6]  # Limit to top 6 recommendations

    def _extract_validation_results(self, result: str) -> Dict[str, Any]:
        """Extract validation results from fieldwork result."""
        # Ensure result is a string
        if not isinstance(result, str):
            result = str(result)

        lines = result.split('\n')
        validation = {
            "status": "Not validated",
            "criteria_met": [],
            "criteria_failed": [],
            "overall_validity": "Unknown"
        }

        for line in lines:
            line = line.strip()
            if 'validation' in line.lower() or 'validated' in line.lower():
                validation["status"] = line
            elif 'criteria met' in line.lower() or 'passed' in line.lower():
                validation["criteria_met"].append(line)
            elif 'criteria failed' in line.lower() or 'failed' in line.lower():
                validation["criteria_failed"].append(line)
            elif 'valid' in line.lower():
                validation["overall_validity"] = line

        return validation

    def _assess_completion_status(self, result: str) -> str:
        """Assess the completion status of fieldwork."""
        result_lower = result.lower()

        completion_indicators = ['completed', 'finished', 'done', 'accomplished']
        partial_indicators = ['partial', 'incomplete', 'ongoing', 'in progress']

        if any(indicator in result_lower for indicator in completion_indicators):
            return "completed"
        elif any(indicator in result_lower for indicator in partial_indicators):
            return "partial"
        else:
            return "unknown"

    def _calculate_quality_score(self, result: str) -> float:
        """Calculate quality score for the fieldwork."""
        quality_indicators = [
            'accurate', 'precise', 'thorough', 'complete',
            'reliable', 'validated', 'verified'
        ]

        quality_issues = [
            'inaccurate', 'incomplete', 'unreliable', 'failed',
            'error', 'issue', 'problem'
        ]

        result_lower = result.lower()
        quality_count = sum(1 for indicator in quality_indicators if indicator in result_lower)
        issue_count = sum(1 for issue in quality_issues if issue in result_lower)

        # Calculate quality score
        base_quality = 0.7
        quality_boost = min(quality_count * 0.05, 0.25)
        quality_penalty = min(issue_count * 0.04, 0.2)

        return max(0.1, min(1.0, base_quality + quality_boost - quality_penalty))

    def get_fieldwork_history(self) -> List[Dict[str, Any]]:
        """
        Get history of fieldwork conducted.

        Returns:
            List of fieldwork history entries
        """
        history = []
        last_fieldwork = self.get_memory('last_fieldwork')
        if last_fieldwork:
            history.append(last_fieldwork)
        return history

    def assess_fieldwork_effectiveness(self, fieldwork_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess the effectiveness of fieldwork results.

        Args:
            fieldwork_result: Fieldwork result to assess

        Returns:
            Dictionary containing effectiveness assessment
        """
        quality_score = fieldwork_result.get('quality_score', 0.0)
        completion_status = fieldwork_result.get('completion_status', 'unknown')
        data_count = len(fieldwork_result.get('collected_data', []))
        findings_count = len(fieldwork_result.get('findings', []))
        issues_count = len(fieldwork_result.get('issues_encountered', []))

        # Calculate effectiveness score
        completion_score = 1.0 if completion_status == 'completed' else 0.5 if completion_status == 'partial' else 0.2
        data_score = min(data_count / 10, 1.0)  # Normalize to 10 data points
        findings_score = min(findings_count / 5, 1.0)  # Normalize to 5 findings
        issues_penalty = min(issues_count * 0.1, 0.3)  # Penalty for issues

        effectiveness = (quality_score + completion_score + data_score + findings_score) / 4 - issues_penalty
        effectiveness = max(0.0, min(1.0, effectiveness))

        return {
            "effectiveness_score": effectiveness,
            "quality_score": quality_score,
            "completion_status": completion_status,
            "data_collected": data_count,
            "findings_generated": findings_count,
            "issues_encountered": issues_count,
            "effectiveness_level": "high" if effectiveness > 0.8 else "medium" if effectiveness > 0.6 else "low",
            "improvement_suggestions": self._generate_improvement_suggestions(fieldwork_result)
        }

    def _generate_improvement_suggestions(self, fieldwork_result: Dict[str, Any]) -> List[str]:
        """Generate improvement suggestions for fieldwork."""
        suggestions = []

        quality_score = fieldwork_result.get('quality_score', 0.0)
        if quality_score < 0.7:
            suggestions.append("Improve quality control procedures")

        completion_status = fieldwork_result.get('completion_status', 'unknown')
        if completion_status != 'completed':
            suggestions.append("Ensure complete execution of all fieldwork activities")

        data_count = len(fieldwork_result.get('collected_data', []))
        if data_count < 5:
            suggestions.append("Collect more comprehensive data points")

        issues_count = len(fieldwork_result.get('issues_encountered', []))
        if issues_count > 3:
            suggestions.append("Address recurring issues in methodology")

        validation = fieldwork_result.get('validation_results', {})
        if validation.get('status') == 'Not validated':
            suggestions.append("Implement validation procedures for quality assurance")

        return suggestions

    def plan_follow_up_fieldwork(self, current_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Plan follow-up fieldwork based on current results.

        Args:
            current_result: Current fieldwork result

        Returns:
            Dictionary containing follow-up plan
        """
        follow_up_plan = {
            "recommended": False,
            "priority": "low",
            "focus_areas": [],
            "methodology_adjustments": [],
            "timeline": "Not specified"
        }

        completion_status = current_result.get('completion_status', 'unknown')
        if completion_status == 'partial':
            follow_up_plan["recommended"] = True
            follow_up_plan["priority"] = "high"
            follow_up_plan["focus_areas"].append("Complete remaining fieldwork activities")

        quality_score = current_result.get('quality_score', 0.0)
        if quality_score < 0.6:
            follow_up_plan["recommended"] = True
            follow_up_plan["priority"] = "medium"
            follow_up_plan["focus_areas"].append("Improve data quality and accuracy")

        issues = current_result.get('issues_encountered', [])
        if len(issues) > 2:
            follow_up_plan["recommended"] = True
            follow_up_plan["methodology_adjustments"].append("Address identified issues in methodology")

        findings_count = len(current_result.get('findings', []))
        if findings_count < 3:
            follow_up_plan["focus_areas"].append("Generate more comprehensive findings")

        return follow_up_plan

    async def conduct_specialized_fieldwork(self, fieldwork_type: str, scope: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Conduct specialized fieldwork in a specific area.

        Args:
            fieldwork_type: Type of specialized fieldwork
            scope: Scope of the fieldwork
            context: Execution context

        Returns:
            Specialized fieldwork result
        """
        if fieldwork_type not in self.fieldwork_types:
            raise ValueError(f"Unsupported fieldwork type: {fieldwork_type}")

        # Create specialized task data
        specialized_task_data = {
            "task_type": fieldwork_type,
            "scope": scope,
            "methodology": "specialized",
            "quality_requirements": self._get_quality_requirements_for_type(fieldwork_type)
        }

        return await self.execute_task(specialized_task_data, context)

    def _get_quality_requirements_for_type(self, fieldwork_type: str) -> Dict[str, Any]:
        """Get quality requirements for specific fieldwork types."""
        requirements_map = {
            "data_collection": {"accuracy": "high", "completeness": "required", "timeliness": "critical"},
            "verification_tasks": {"accuracy": "critical", "reliability": "high", "documentation": "required"},
            "testing_procedures": {"precision": "high", "repeatability": "required", "validation": "critical"},
            "validation_activities": {"thoroughness": "critical", "compliance": "required", "documentation": "detailed"},
            "monitoring_tasks": {"consistency": "high", "timeliness": "critical", "coverage": "comprehensive"},
            "inspection_work": {"detail": "high", "accuracy": "critical", "documentation": "complete"},
            "survey_execution": {"coverage": "comprehensive", "response_rate": "high", "quality": "consistent"}
        }
        return requirements_map.get(fieldwork_type, {"quality": "standard"})

    def get_fieldwork_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Get fieldwork templates for different types of fieldwork.

        Returns:
            Dictionary of fieldwork templates
        """
        return {
            "data_collection": {
                "description": "Systematic collection of data from field sources",
                "required_tools": ["measurement_instruments", "data_recording_tools"],
                "methodology": "structured",
                "quality_focus": ["accuracy", "completeness", "timeliness"]
            },
            "verification_tasks": {
                "description": "Verification and validation of existing data or processes",
                "required_tools": ["verification_checklists", "validation_tools"],
                "methodology": "systematic_verification",
                "quality_focus": ["accuracy", "reliability", "compliance"]
            },
            "testing_procedures": {
                "description": "Execution of testing protocols and procedures",
                "required_tools": ["testing_equipment", "measurement_tools"],
                "methodology": "controlled_testing",
                "quality_focus": ["precision", "repeatability", "validity"]
            },
            "validation_activities": {
                "description": "Comprehensive validation of systems or processes",
                "required_tools": ["validation_frameworks", "compliance_checklists"],
                "methodology": "systematic_validation",
                "quality_focus": ["thoroughness", "compliance", "documentation"]
            },
            "monitoring_tasks": {
                "description": "Continuous monitoring and observation activities",
                "required_tools": ["monitoring_systems", "observation_tools"],
                "methodology": "continuous_monitoring",
                "quality_focus": ["consistency", "coverage", "timeliness"]
            },
            "inspection_work": {
                "description": "Detailed inspection and assessment activities",
                "required_tools": ["inspection_checklists", "assessment_tools"],
                "methodology": "systematic_inspection",
                "quality_focus": ["detail", "accuracy", "completeness"]
            },
            "survey_execution": {
                "description": "Execution of surveys and data collection campaigns",
                "required_tools": ["survey_instruments", "data_collection_tools"],
                "methodology": "structured_survey",
                "quality_focus": ["coverage", "response_quality", "representativeness"]
            }
        }
