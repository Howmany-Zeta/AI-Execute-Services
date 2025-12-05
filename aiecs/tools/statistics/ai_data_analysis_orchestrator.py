"""
AI Data Analysis Orchestrator - AI-powered end-to-end data analysis workflow coordination

This orchestrator coordinates multiple foundation tools to provide:
- Natural language driven analysis
- Automated workflow orchestration
- Multi-tool coordination
- Comprehensive analysis execution
- Support for various analysis modes
"""

import logging
from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from aiecs.tools.base_tool import BaseTool
from aiecs.tools import register_tool


class AnalysisMode(str, Enum):
    """Analysis execution modes"""

    EXPLORATORY = "exploratory"
    DIAGNOSTIC = "diagnostic"
    PREDICTIVE = "predictive"
    PRESCRIPTIVE = "prescriptive"
    COMPARATIVE = "comparative"
    CAUSAL = "causal"


class AIProvider(str, Enum):
    """Supported AI providers for future integration"""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    LOCAL = "local"


class OrchestratorError(Exception):
    """Base exception for Orchestrator errors"""


class WorkflowError(OrchestratorError):
    """Raised when workflow execution fails"""


@register_tool("ai_data_analysis_orchestrator")
class AIDataAnalysisOrchestrator(BaseTool):
    """
    AI-powered data analysis orchestrator that can:
    1. Understand analysis requirements
    2. Automatically design analysis workflows
    3. Orchestrate multiple tools to complete analysis
    4. Generate comprehensive analysis reports

    Coordinates foundation tools: data_loader, data_profiler, data_transformer,
    data_visualizer, statistical_analyzer, model_trainer
    """

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the AI data analysis orchestrator tool
        
        Automatically reads from environment variables with AI_DATA_ORCHESTRATOR_ prefix.
        Example: AI_DATA_ORCHESTRATOR_DEFAULT_MODE -> default_mode
        """

        model_config = SettingsConfigDict(env_prefix="AI_DATA_ORCHESTRATOR_")

        default_mode: str = Field(default="exploratory", description="Default analysis mode to use")
        max_iterations: int = Field(default=10, description="Maximum number of analysis iterations")
        enable_auto_workflow: bool = Field(
            default=True,
            description="Whether to enable automatic workflow generation",
        )
        default_ai_provider: str = Field(default="openai", description="Default AI provider to use")
        enable_caching: bool = Field(default=True, description="Whether to enable result caching")

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """Initialize AI Data Analysis Orchestrator

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/ai_data_analysis_orchestrator.yaml)
        3. Environment variables (via dotenv from .env files)
        4. Tool defaults (lowest priority)

        Args:
            config: Optional configuration overrides
            **kwargs: Additional arguments passed to BaseTool (e.g., tool_name)
        """
        super().__init__(config, **kwargs)

        # Configuration is automatically loaded by BaseTool into self._config_obj
        # Access config via self._config_obj (BaseSettings instance)
        self.config = self._config_obj if self._config_obj else self.Config()

        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        # Initialize foundation tools
        self._init_foundation_tools()

        # Initialize AI providers (placeholder for future implementation)
        self._init_ai_providers()

        # Workflow cache
        self.workflow_cache: Dict[str, Any] = {}

    def _init_foundation_tools(self):
        """Initialize foundation data analysis tools"""
        self.foundation_tools = {}

        try:
            from aiecs.tools.statistics.data_loader_tool import DataLoaderTool

            self.foundation_tools["data_loader"] = DataLoaderTool()
            self.logger.info("DataLoaderTool initialized")
        except ImportError:
            self.logger.warning("DataLoaderTool not available")

        try:
            from aiecs.tools.statistics.data_profiler_tool import (
                DataProfilerTool,
            )

            self.foundation_tools["data_profiler"] = DataProfilerTool()
            self.logger.info("DataProfilerTool initialized")
        except ImportError:
            self.logger.warning("DataProfilerTool not available")

        try:
            from aiecs.tools.statistics.data_transformer_tool import (
                DataTransformerTool,
            )

            self.foundation_tools["data_transformer"] = DataTransformerTool()
            self.logger.info("DataTransformerTool initialized")
        except ImportError:
            self.logger.warning("DataTransformerTool not available")

        try:
            from aiecs.tools.statistics.data_visualizer_tool import (
                DataVisualizerTool,
            )

            self.foundation_tools["data_visualizer"] = DataVisualizerTool()
            self.logger.info("DataVisualizerTool initialized")
        except ImportError:
            self.logger.warning("DataVisualizerTool not available")

        try:
            from aiecs.tools.statistics.statistical_analyzer_tool import (
                StatisticalAnalyzerTool,
            )

            self.foundation_tools["statistical_analyzer"] = StatisticalAnalyzerTool()
            self.logger.info("StatisticalAnalyzerTool initialized")
        except ImportError:
            self.logger.warning("StatisticalAnalyzerTool not available")

        try:
            from aiecs.tools.statistics.model_trainer_tool import (
                ModelTrainerTool,
            )

            self.foundation_tools["model_trainer"] = ModelTrainerTool()
            self.logger.info("ModelTrainerTool initialized")
        except ImportError:
            self.logger.warning("ModelTrainerTool not available")

    def _init_ai_providers(self):
        """Initialize AI providers (placeholder for future implementation)"""
        self.ai_providers = {}
        # Future integration point for AIECS client
        # try:
        #     from aiecs import AIECS
        #     self.aiecs_client = AIECS()
        #     self.ai_providers['aiecs'] = self.aiecs_client
        # except ImportError:
        #     self.logger.warning("AIECS client not available")

    # Schema definitions
    class AnalyzeSchema(BaseModel):
        """Schema for analyze operation"""

        data_source: str = Field(description="Path to data source or data itself")
        question: str = Field(description="Analysis question in natural language")
        mode: AnalysisMode = Field(default=AnalysisMode.EXPLORATORY, description="Analysis mode")
        max_iterations: int = Field(default=10, description="Maximum workflow iterations")

    class AutoAnalyzeDatasetSchema(BaseModel):
        """Schema for auto_analyze_dataset operation"""

        data_source: str = Field(description="Path to data source")
        focus_areas: Optional[List[str]] = Field(default=None, description="Areas to focus on")
        generate_report: bool = Field(default=True, description="Generate analysis report")

    class OrchestrateWorkflowSchema(BaseModel):
        """Schema for orchestrate_workflow operation"""

        workflow_steps: List[Dict[str, Any]] = Field(description="Workflow steps to execute")
        data_source: str = Field(description="Data source")

    def analyze(
        self,
        data_source: str,
        question: str,
        mode: AnalysisMode = AnalysisMode.EXPLORATORY,
        max_iterations: int = 10,
    ) -> Dict[str, Any]:
        """
        Perform AI-driven data analysis based on natural language question.

        Args:
            data_source: Path to data source file
            question: Analysis question in natural language
            mode: Analysis mode to use
            max_iterations: Maximum workflow iterations

        Returns:
            Dict containing:
                - analysis_plan: Planned analysis steps
                - execution_log: Log of executed steps
                - findings: Analysis findings and insights
                - recommendations: Recommendations based on analysis
                - report: Analysis report
        """
        try:
            self.logger.info(f"Starting analysis: {question}")

            # Design analysis workflow based on question and mode
            workflow = self._design_workflow(question, mode, data_source)

            # Execute workflow
            execution_results = self._execute_workflow(workflow, data_source, max_iterations)

            # Generate findings from results
            findings = self._generate_findings(execution_results)

            # Generate recommendations
            recommendations = self._generate_recommendations(findings)

            # Generate report
            report = self._generate_analysis_report(
                question,
                workflow,
                execution_results,
                findings,
                recommendations,
            )

            return {
                "analysis_plan": workflow,
                "execution_log": execution_results.get("log", []),
                "findings": findings,
                "recommendations": recommendations,
                "report": report,
                "mode": mode.value,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error in analysis: {e}")
            raise WorkflowError(f"Analysis failed: {e}")

    def auto_analyze_dataset(
        self,
        data_source: str,
        focus_areas: Optional[List[str]] = None,
        generate_report: bool = True,
    ) -> Dict[str, Any]:
        """
        Automatically analyze dataset without specific question.

        Args:
            data_source: Path to data source
            focus_areas: Specific areas to focus on
            generate_report: Whether to generate comprehensive report

        Returns:
            Dict containing comprehensive analysis results
        """
        try:
            self.logger.info(f"Auto-analyzing dataset: {data_source}")

            # Load data
            load_result = self.foundation_tools["data_loader"].load_data(source=data_source)
            data = load_result["data"]

            # Profile data
            profile_result = self.foundation_tools["data_profiler"].profile_dataset(data=data, level="comprehensive")

            # Auto-transform if needed
            if profile_result.get("quality_issues"):
                transform_result = self.foundation_tools["data_transformer"].auto_transform(data=data)
                data = transform_result["transformed_data"]

            # Generate visualizations
            viz_result = self.foundation_tools["data_visualizer"].auto_visualize_dataset(
                data=data,
                focus_areas=focus_areas or ["distributions", "correlations"],
            )

            # Perform statistical analysis
            numeric_cols = data.select_dtypes(include=["number"]).columns.tolist()
            stats_result = {}
            if len(numeric_cols) >= 2:
                stats_result = self.foundation_tools["statistical_analyzer"].analyze_correlation(data=data, variables=numeric_cols)

            # Compile results
            results = {
                "data_profile": profile_result,
                "transformations_applied": (transform_result if "transform_result" in locals() else None),
                "visualizations": viz_result,
                "statistical_analysis": stats_result,
                "data_source": data_source,
                "timestamp": datetime.now().isoformat(),
            }

            if generate_report:
                results["report"] = self._generate_auto_analysis_report(results)

            return results

        except Exception as e:
            self.logger.error(f"Error in auto analysis: {e}")
            raise WorkflowError(f"Auto analysis failed: {e}")

    def orchestrate_workflow(self, workflow_steps: List[Dict[str, Any]], data_source: str) -> Dict[str, Any]:
        """
        Orchestrate a custom workflow with specified steps.

        Args:
            workflow_steps: List of workflow steps with tool and operation info
            data_source: Data source path

        Returns:
            Dict containing workflow execution results
        """
        try:
            results = self._execute_workflow(
                {"steps": workflow_steps},
                data_source,
                max_iterations=len(workflow_steps),
            )

            return {
                "workflow_results": results,
                "total_steps": len(workflow_steps),
                "status": "completed",
            }

        except Exception as e:
            self.logger.error(f"Error orchestrating workflow: {e}")
            raise WorkflowError(f"Workflow orchestration failed: {e}")

    # Internal workflow methods

    def _design_workflow(self, question: str, mode: AnalysisMode, data_source: str) -> Dict[str, Any]:
        """Design analysis workflow based on question and mode"""
        workflow: Dict[str, Any] = {"question": question, "mode": mode.value, "steps": []}

        # Standard workflow steps based on mode
        if mode == AnalysisMode.EXPLORATORY:
            workflow["steps"] = [
                {
                    "tool": "data_loader",
                    "operation": "load_data",
                    "params": {"source": data_source},
                },
                {
                    "tool": "data_profiler",
                    "operation": "profile_dataset",
                    "params": {"level": "comprehensive"},
                },
                {
                    "tool": "data_visualizer",
                    "operation": "auto_visualize_dataset",
                    "params": {"max_charts": 5},
                },
                {
                    "tool": "statistical_analyzer",
                    "operation": "analyze_correlation",
                    "params": {},
                },
            ]
        elif mode == AnalysisMode.PREDICTIVE:
            workflow["steps"] = [
                {
                    "tool": "data_loader",
                    "operation": "load_data",
                    "params": {"source": data_source},
                },
                {
                    "tool": "data_profiler",
                    "operation": "profile_dataset",
                    "params": {},
                },
                {
                    "tool": "data_transformer",
                    "operation": "auto_transform",
                    "params": {},
                },
                {
                    "tool": "model_trainer",
                    "operation": "auto_select_model",
                    "params": {},
                },
            ]
        elif mode == AnalysisMode.DIAGNOSTIC:
            workflow["steps"] = [
                {
                    "tool": "data_loader",
                    "operation": "load_data",
                    "params": {"source": data_source},
                },
                {
                    "tool": "data_profiler",
                    "operation": "detect_quality_issues",
                    "params": {},
                },
                {
                    "tool": "statistical_analyzer",
                    "operation": "test_hypothesis",
                    "params": {},
                },
            ]
        else:
            # Default exploratory workflow
            workflow["steps"] = [
                {
                    "tool": "data_loader",
                    "operation": "load_data",
                    "params": {"source": data_source},
                },
                {
                    "tool": "data_profiler",
                    "operation": "profile_dataset",
                    "params": {},
                },
            ]

        return workflow

    def _execute_workflow(self, workflow: Dict[str, Any], data_source: str, max_iterations: int) -> Dict[str, Any]:
        """Execute workflow steps"""
        results: Dict[str, Any] = {"log": [], "data": None, "outputs": {}}

        current_data = None

        for i, step in enumerate(workflow["steps"][:max_iterations]):
            try:
                tool_name = step["tool"]
                operation = step["operation"]
                params = step.get("params", {})

                self.logger.info(f"Executing step {i+1}: {tool_name}.{operation}")

                # Get tool
                tool = self.foundation_tools.get(tool_name)
                if not tool:
                    self.logger.warning(f"Tool {tool_name} not available, skipping")
                    continue

                # Prepare parameters
                if current_data is not None and "data" not in params:
                    params["data"] = current_data

                # Execute operation
                result = tool.run(operation, **params)

                # Update current data if result contains data
                if isinstance(result, dict) and "data" in result:
                    current_data = result["data"]
                elif isinstance(result, dict) and "transformed_data" in result:
                    current_data = result["transformed_data"]

                # Log execution
                results["log"].append(
                    {
                        "step": i + 1,
                        "tool": tool_name,
                        "operation": operation,
                        "status": "success",
                        "summary": self._summarize_result(result),
                    }
                )

                results["outputs"][f"{tool_name}_{operation}"] = result

            except Exception as e:
                self.logger.error(f"Error in step {i+1}: {e}")
                results["log"].append(
                    {
                        "step": i + 1,
                        "tool": step["tool"],
                        "operation": step["operation"],
                        "status": "failed",
                        "error": str(e),
                    }
                )

        results["data"] = current_data
        return results

    def _generate_findings(self, execution_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate findings from execution results"""
        findings = []

        outputs = execution_results.get("outputs", {})

        # Extract insights from profiling
        if "data_profiler_profile_dataset" in outputs:
            profile = outputs["data_profiler_profile_dataset"]
            summary = profile.get("summary", {})
            findings.append(
                {
                    "type": "data_profile",
                    "title": "Dataset Overview",
                    "description": f"Dataset contains {summary.get('rows', 0)} rows and {summary.get('columns', 0)} columns",
                    "confidence": "high",
                    "evidence": summary,
                }
            )

        # Extract insights from statistical analysis
        if "statistical_analyzer_analyze_correlation" in outputs:
            corr = outputs["statistical_analyzer_analyze_correlation"]
            high_corr = corr.get("high_correlations", [])
            if high_corr:
                findings.append(
                    {
                        "type": "correlation",
                        "title": "Significant Correlations Found",
                        "description": f"Found {len(high_corr)} significant correlations",
                        "confidence": "high",
                        "evidence": high_corr,
                    }
                )

        return findings

    def _generate_recommendations(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate recommendations based on findings"""
        recommendations = []

        for finding in findings:
            if finding["type"] == "data_profile":
                recommendations.append(
                    {
                        "action": "data_quality_check",
                        "reason": "Perform comprehensive data quality assessment",
                        "priority": "high",
                    }
                )
            elif finding["type"] == "correlation":
                recommendations.append(
                    {
                        "action": "investigate_relationships",
                        "reason": "Investigate significant correlations for potential insights",
                        "priority": "medium",
                    }
                )

        return recommendations

    def _generate_analysis_report(
        self,
        question: str,
        workflow: Dict[str, Any],
        execution_results: Dict[str, Any],
        findings: List[Dict[str, Any]],
        recommendations: List[Dict[str, Any]],
    ) -> str:
        """Generate comprehensive analysis report"""
        report_lines = [
            "# Data Analysis Report",
            "",
            f"**Question:** {question}",
            f"**Analysis Mode:** {workflow.get('mode', 'N/A')}",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Analysis Workflow",
            "",
        ]

        for i, step in enumerate(workflow.get("steps", []), 1):
            report_lines.append(f"{i}. {step['tool']}.{step['operation']}")

        report_lines.extend(["", "## Key Findings", ""])

        for i, finding in enumerate(findings, 1):
            report_lines.append(f"{i}. **{finding['title']}**: {finding['description']}")

        report_lines.extend(["", "## Recommendations", ""])

        for i, rec in enumerate(recommendations, 1):
            report_lines.append(f"{i}. {rec['action']}: {rec['reason']}")

        return "\n".join(report_lines)

    def _generate_auto_analysis_report(self, results: Dict[str, Any]) -> str:
        """Generate report for auto analysis"""
        profile = results.get("data_profile", {})
        summary = profile.get("summary", {})

        report_lines = [
            "# Automatic Data Analysis Report",
            "",
            f"**Data Source:** {results.get('data_source', 'N/A')}",
            f"**Generated:** {results.get('timestamp', 'N/A')}",
            "",
            "## Dataset Summary",
            "",
            f"- Rows: {summary.get('rows', 0)}",
            f"- Columns: {summary.get('columns', 0)}",
            f"- Missing Data: {summary.get('missing_percentage', 0):.2f}%",
            f"- Duplicate Rows: {summary.get('duplicate_rows', 0)}",
            "",
            "## Analysis Completed",
            "",
            "- Data profiling",
            "- Quality assessment",
            "- Statistical analysis",
            "- Visualization generation",
        ]

        return "\n".join(report_lines)

    def _summarize_result(self, result: Any) -> str:
        """Create summary of result"""
        if isinstance(result, dict):
            if "summary" in result:
                return f"Summary available with {len(result)} keys"
            return f"Result with {len(result)} keys"
        return "Result generated"
