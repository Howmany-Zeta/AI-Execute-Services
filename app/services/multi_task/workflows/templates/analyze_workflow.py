"""
Analyze Workflow Template

Workflow template for analyze-type tasks that perform deep analysis and insights generation.
Focuses on data analysis, pattern recognition, statistical analysis, and insight extraction.
"""

from typing import Dict, List, Any, Optional
from ..base_workflow import BaseWorkflow
from ..dsl import DSLNode, DSLNodeType
from ...core.models.execution_models import WorkflowExecution, ExecutionResult


class AnalyzeWorkflow(BaseWorkflow):
    """
    Workflow template for analyze-type tasks.

    Typical flow:
    1. Understand analysis requirements and data characteristics
    2. Plan analysis methodology and approach
    3. Execute analytical operations (statistical, pattern, trend analysis)
    4. Generate insights and findings
    5. Accept analysis outcomes and validate results
    """

    def __init__(self):
        """Initialize the analyze workflow."""
        super().__init__()
        self.workflow_type = "analyze"
        self.description = "Workflow for analyzing data and generating insights"

    async def create_workflow_definition(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create workflow definition for analyze tasks.

        Args:
            input_data: Input data containing analysis requirements

        Returns:
            Workflow definition with DSL steps
        """
        analysis_target = input_data.get("text", "")
        analysis_type = input_data.get("analysis_type", "comprehensive")
        data_source = input_data.get("data_source", "processed")
        depth = input_data.get("depth", "standard")

        # Determine analysis strategy based on type and depth
        if analysis_type == "statistical":
            workflow_steps = self._create_statistical_analysis_workflow(analysis_target, data_source, depth)
        elif analysis_type == "pattern":
            workflow_steps = self._create_pattern_analysis_workflow(analysis_target, data_source, depth)
        elif analysis_type == "trend":
            workflow_steps = self._create_trend_analysis_workflow(analysis_target, data_source, depth)
        elif analysis_type == "comparative":
            workflow_steps = self._create_comparative_analysis_workflow(analysis_target, data_source, depth)
        else:
            workflow_steps = self._create_comprehensive_analysis_workflow(analysis_target, data_source, depth)

        return {
            "id": f"analyze_workflow_{self._generate_workflow_id()}",
            "type": "analyze",
            "description": f"Analyze workflow for: {analysis_target[:100]}...",
            "steps": workflow_steps,
            "metadata": {
                "analysis_type": analysis_type,
                "data_source": data_source,
                "depth": depth,
                "estimated_duration": self._estimate_duration(workflow_steps)
            }
        }

    def _create_statistical_analysis_workflow(self, target: str, data_source: str, depth: str) -> List[Dict[str, Any]]:
        """Create workflow for statistical analysis tasks."""
        return [
            {
                "task": "analyze_statistical_requirements",
                "tools": ["analysis.statistical", "analysis.data"],
                "parameters": {
                    "target": target,
                    "data_source": data_source,
                    "depth": depth,
                    "statistical_focus": True
                },
                "timeout": 45
            },
            {
                "parallel": [
                    {
                        "task": "analyze_descriptive_stats",
                        "tools": ["analysis.statistical"],
                        "parameters": {
                            "data": "${result.analyze_statistical_requirements.data}",
                            "statistics": ["mean", "median", "mode", "std", "variance", "quartiles"],
                            "target": target
                        }
                    },
                    {
                        "task": "analyze_distribution",
                        "tools": ["analysis.statistical", "visualization.stats"],
                        "parameters": {
                            "data": "${result.analyze_statistical_requirements.data}",
                            "distribution_tests": ["normality", "skewness", "kurtosis"],
                            "target": target
                        }
                    },
                    {
                        "task": "analyze_correlations",
                        "tools": ["analysis.statistical"],
                        "parameters": {
                            "data": "${result.analyze_statistical_requirements.data}",
                            "correlation_methods": ["pearson", "spearman", "kendall"],
                            "target": target
                        }
                    }
                ],
                "max_concurrency": 3,
                "wait_for_all": True
            },
            {
                "if": "result.analyze_statistical_requirements.depth == 'deep'",
                "then": [
                    {
                        "parallel": [
                            {
                                "task": "analyze_hypothesis_testing",
                                "tools": ["analysis.statistical"],
                                "parameters": {
                                    "data": "${result.analyze_statistical_requirements.data}",
                                    "hypotheses": "${result.analyze_statistical_requirements.hypotheses}",
                                    "significance_level": 0.05
                                }
                            },
                            {
                                "task": "analyze_regression",
                                "tools": ["analysis.statistical", "analysis.ml"],
                                "parameters": {
                                    "data": "${result.analyze_statistical_requirements.data}",
                                    "regression_types": ["linear", "polynomial", "logistic"],
                                    "target": target
                                }
                            }
                        ],
                        "wait_for_all": True
                    }
                ]
            },
            {
                "task": "analyze_statistical_insights",
                "tools": ["analysis.statistical", "analysis.text"],
                "parameters": {
                    "descriptive_results": "${result.analyze_descriptive_stats}",
                    "distribution_results": "${result.analyze_distribution}",
                    "correlation_results": "${result.analyze_correlations}",
                    "hypothesis_results": "${result.analyze_hypothesis_testing}",
                    "regression_results": "${result.analyze_regression}",
                    "target": target
                },
                "timeout": 60
            },
            {
                "task": "analyze_accept_outcome",
                "tools": ["analysis.text"],
                "parameters": {
                    "statistical_insights": "${result.analyze_statistical_insights.insights}",
                    "analysis_results": "${result.analyze_statistical_insights}",
                    "target": target,
                    "acceptance_criteria": "statistical_validity"
                }
            }
        ]

    def _create_pattern_analysis_workflow(self, target: str, data_source: str, depth: str) -> List[Dict[str, Any]]:
        """Create workflow for pattern analysis tasks."""
        return [
            {
                "task": "analyze_pattern_requirements",
                "tools": ["analysis.pattern", "analysis.data"],
                "parameters": {
                    "target": target,
                    "data_source": data_source,
                    "pattern_types": ["temporal", "spatial", "behavioral", "structural"],
                    "depth": depth
                },
                "timeout": 40
            },
            {
                "sequence": [
                    {
                        "task": "analyze_data_preprocessing",
                        "tools": ["processor.pattern", "analysis.data"],
                        "parameters": {
                            "data": "${result.analyze_pattern_requirements.data}",
                            "preprocessing_plan": "${result.analyze_pattern_requirements.preprocessing_plan}",
                            "target": target
                        }
                    },
                    {
                        "parallel": [
                            {
                                "task": "analyze_temporal_patterns",
                                "tools": ["analysis.temporal", "analysis.pattern"],
                                "parameters": {
                                    "preprocessed_data": "${result.analyze_data_preprocessing.preprocessed_data}",
                                    "temporal_methods": ["seasonality", "trends", "cycles", "anomalies"],
                                    "target": target
                                }
                            },
                            {
                                "task": "analyze_frequency_patterns",
                                "tools": ["analysis.frequency", "analysis.pattern"],
                                "parameters": {
                                    "preprocessed_data": "${result.analyze_data_preprocessing.preprocessed_data}",
                                    "frequency_methods": ["fft", "wavelet", "spectral"],
                                    "target": target
                                }
                            },
                            {
                                "task": "analyze_clustering_patterns",
                                "tools": ["analysis.clustering", "analysis.ml"],
                                "parameters": {
                                    "preprocessed_data": "${result.analyze_data_preprocessing.preprocessed_data}",
                                    "clustering_methods": ["kmeans", "hierarchical", "dbscan"],
                                    "target": target
                                }
                            }
                        ],
                        "max_concurrency": 3,
                        "wait_for_all": True
                    }
                ]
            },
            {
                "task": "analyze_pattern_synthesis",
                "tools": ["analysis.pattern", "analysis.text"],
                "parameters": {
                    "temporal_patterns": "${result.analyze_temporal_patterns}",
                    "frequency_patterns": "${result.analyze_frequency_patterns}",
                    "clustering_patterns": "${result.analyze_clustering_patterns}",
                    "synthesis_strategy": "comprehensive",
                    "target": target
                },
                "timeout": 75
            },
            {
                "task": "analyze_pattern_validation",
                "tools": ["validator.pattern", "analysis.statistical"],
                "parameters": {
                    "synthesized_patterns": "${result.analyze_pattern_synthesis.patterns}",
                    "validation_methods": ["cross_validation", "bootstrap", "significance_testing"],
                    "target": target
                }
            },
            {
                "task": "analyze_accept_outcome",
                "tools": ["analysis.text"],
                "parameters": {
                    "pattern_results": "${result.analyze_pattern_synthesis}",
                    "validation_results": "${result.analyze_pattern_validation}",
                    "target": target,
                    "acceptance_criteria": "pattern_significance"
                }
            }
        ]

    def _create_trend_analysis_workflow(self, target: str, data_source: str, depth: str) -> List[Dict[str, Any]]:
        """Create workflow for trend analysis tasks."""
        return [
            {
                "task": "analyze_trend_requirements",
                "tools": ["analysis.trend", "analysis.data"],
                "parameters": {
                    "target": target,
                    "data_source": data_source,
                    "trend_types": ["linear", "exponential", "seasonal", "cyclical"],
                    "time_horizon": "auto_detect",
                    "depth": depth
                },
                "timeout": 35
            },
            {
                "parallel": [
                    {
                        "task": "analyze_trend_decomposition",
                        "tools": ["analysis.trend", "analysis.time_series"],
                        "parameters": {
                            "data": "${result.analyze_trend_requirements.data}",
                            "decomposition_methods": ["additive", "multiplicative", "stl"],
                            "target": target
                        }
                    },
                    {
                        "task": "analyze_trend_detection",
                        "tools": ["analysis.trend", "analysis.statistical"],
                        "parameters": {
                            "data": "${result.analyze_trend_requirements.data}",
                            "detection_methods": ["mann_kendall", "linear_regression", "change_point"],
                            "target": target
                        }
                    }
                ],
                "wait_for_all": True
            },
            {
                "task": "analyze_trend_forecasting",
                "tools": ["analysis.forecasting", "analysis.ml"],
                "parameters": {
                    "decomposition_results": "${result.analyze_trend_decomposition}",
                    "detection_results": "${result.analyze_trend_detection}",
                    "forecasting_methods": ["arima", "exponential_smoothing", "prophet"],
                    "forecast_horizon": "${result.analyze_trend_requirements.forecast_horizon}",
                    "target": target
                },
                "timeout": 90
            },
            {
                "task": "analyze_trend_confidence",
                "tools": ["analysis.statistical", "validator.trend"],
                "parameters": {
                    "forecasting_results": "${result.analyze_trend_forecasting}",
                    "confidence_methods": ["prediction_intervals", "cross_validation", "residual_analysis"],
                    "target": target
                }
            },
            {
                "task": "analyze_accept_outcome",
                "tools": ["analysis.text"],
                "parameters": {
                    "trend_results": "${result.analyze_trend_forecasting}",
                    "confidence_results": "${result.analyze_trend_confidence}",
                    "target": target,
                    "acceptance_criteria": "trend_reliability"
                }
            }
        ]

    def _create_comparative_analysis_workflow(self, target: str, data_source: str, depth: str) -> List[Dict[str, Any]]:
        """Create workflow for comparative analysis tasks."""
        return [
            {
                "task": "analyze_comparative_setup",
                "tools": ["analysis.comparative", "analysis.data"],
                "parameters": {
                    "target": target,
                    "data_source": data_source,
                    "comparison_dimensions": "auto_detect",
                    "depth": depth
                },
                "timeout": 40
            },
            {
                "parallel": [
                    {
                        "task": "analyze_group_comparison",
                        "tools": ["analysis.statistical", "analysis.comparative"],
                        "parameters": {
                            "data": "${result.analyze_comparative_setup.data}",
                            "groups": "${result.analyze_comparative_setup.groups}",
                            "comparison_tests": ["t_test", "anova", "chi_square", "mann_whitney"],
                            "target": target
                        }
                    },
                    {
                        "task": "analyze_performance_comparison",
                        "tools": ["analysis.performance", "analysis.comparative"],
                        "parameters": {
                            "data": "${result.analyze_comparative_setup.data}",
                            "performance_metrics": "${result.analyze_comparative_setup.performance_metrics}",
                            "benchmarking_methods": ["relative", "absolute", "normalized"],
                            "target": target
                        }
                    }
                ],
                "wait_for_all": True
            },
            {
                "task": "analyze_comparative_insights",
                "tools": ["analysis.comparative", "analysis.text"],
                "parameters": {
                    "group_results": "${result.analyze_group_comparison}",
                    "performance_results": "${result.analyze_performance_comparison}",
                    "insight_generation": "comprehensive",
                    "target": target
                },
                "timeout": 60
            },
            {
                "task": "analyze_accept_outcome",
                "tools": ["analysis.text"],
                "parameters": {
                    "comparative_insights": "${result.analyze_comparative_insights.insights}",
                    "analysis_results": "${result.analyze_comparative_insights}",
                    "target": target,
                    "acceptance_criteria": "comparative_validity"
                }
            }
        ]

    def _create_comprehensive_analysis_workflow(self, target: str, data_source: str, depth: str) -> List[Dict[str, Any]]:
        """Create workflow for comprehensive analysis tasks."""
        return [
            {
                "task": "analyze_comprehensive_planning",
                "tools": ["analysis.comprehensive", "analysis.data"],
                "parameters": {
                    "target": target,
                    "data_source": data_source,
                    "analysis_scope": "full_spectrum",
                    "depth": depth
                },
                "timeout": 60
            },
            {
                "sequence": [
                    {
                        "parallel": [
                            {
                                "task": "analyze_exploratory_analysis",
                                "tools": ["analysis.exploratory", "visualization.data"],
                                "parameters": {
                                    "data": "${result.analyze_comprehensive_planning.data}",
                                    "exploration_methods": ["summary_stats", "distributions", "correlations", "outliers"],
                                    "target": target
                                }
                            },
                            {
                                "task": "analyze_data_quality",
                                "tools": ["analysis.quality", "validator.data"],
                                "parameters": {
                                    "data": "${result.analyze_comprehensive_planning.data}",
                                    "quality_dimensions": ["completeness", "accuracy", "consistency", "timeliness"],
                                    "target": target
                                }
                            }
                        ],
                        "wait_for_all": True
                    },
                    {
                        "parallel": [
                            {
                                "task": "analyze_statistical_comprehensive",
                                "tools": ["analysis.statistical", "analysis.advanced"],
                                "parameters": {
                                    "data": "${result.analyze_comprehensive_planning.data}",
                                    "statistical_suite": "comprehensive",
                                    "quality_context": "${result.analyze_data_quality}",
                                    "target": target
                                }
                            },
                            {
                                "task": "analyze_pattern_comprehensive",
                                "tools": ["analysis.pattern", "analysis.ml"],
                                "parameters": {
                                    "data": "${result.analyze_comprehensive_planning.data}",
                                    "pattern_suite": "comprehensive",
                                    "exploratory_context": "${result.analyze_exploratory_analysis}",
                                    "target": target
                                }
                            },
                            {
                                "task": "analyze_predictive_modeling",
                                "tools": ["analysis.ml", "analysis.predictive"],
                                "parameters": {
                                    "data": "${result.analyze_comprehensive_planning.data}",
                                    "modeling_approaches": ["supervised", "unsupervised", "ensemble"],
                                    "target": target
                                }
                            }
                        ],
                        "max_concurrency": 3,
                        "wait_for_all": True
                    }
                ]
            },
            {
                "task": "analyze_synthesis_comprehensive",
                "tools": ["analysis.synthesis", "analysis.text"],
                "parameters": {
                    "exploratory_results": "${result.analyze_exploratory_analysis}",
                    "quality_results": "${result.analyze_data_quality}",
                    "statistical_results": "${result.analyze_statistical_comprehensive}",
                    "pattern_results": "${result.analyze_pattern_comprehensive}",
                    "predictive_results": "${result.analyze_predictive_modeling}",
                    "synthesis_strategy": "holistic",
                    "target": target
                },
                "timeout": 90
            },
            {
                "parallel": [
                    {
                        "task": "analyze_insight_generation",
                        "tools": ["analysis.insight", "analysis.text"],
                        "parameters": {
                            "synthesized_results": "${result.analyze_synthesis_comprehensive.synthesis}",
                            "insight_types": ["descriptive", "diagnostic", "predictive", "prescriptive"],
                            "target": target
                        }
                    },
                    {
                        "task": "analyze_recommendation_generation",
                        "tools": ["analysis.recommendation", "analysis.text"],
                        "parameters": {
                            "synthesized_results": "${result.analyze_synthesis_comprehensive.synthesis}",
                            "recommendation_types": ["actionable", "strategic", "tactical"],
                            "target": target
                        }
                    }
                ],
                "wait_for_all": True
            },
            {
                "task": "analyze_comprehensive_validation",
                "tools": ["validator.comprehensive", "analysis.validation"],
                "parameters": {
                    "insights": "${result.analyze_insight_generation.insights}",
                    "recommendations": "${result.analyze_recommendation_generation.recommendations}",
                    "synthesis": "${result.analyze_synthesis_comprehensive.synthesis}",
                    "validation_criteria": "comprehensive",
                    "target": target
                },
                "timeout": 75
            },
            {
                "task": "analyze_accept_outcome",
                "tools": ["analysis.text"],
                "parameters": {
                    "comprehensive_results": {
                        "insights": "${result.analyze_insight_generation.insights}",
                        "recommendations": "${result.analyze_recommendation_generation.recommendations}",
                        "synthesis": "${result.analyze_synthesis_comprehensive.synthesis}"
                    },
                    "validation_results": "${result.analyze_comprehensive_validation}",
                    "target": target,
                    "acceptance_criteria": "comprehensive_excellence"
                }
            }
        ]

    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data for analyze workflow.

        Args:
            input_data: Input data to validate

        Returns:
            True if input is valid, False otherwise
        """
        required_fields = ["text"]

        # Check required fields
        for field in required_fields:
            if field not in input_data:
                self.logger.error(f"Missing required field: {field}")
                return False

        # Validate analysis target
        target = input_data.get("text", "").strip()
        if not target:
            self.logger.error("Analysis target is empty")
            return False

        # Validate analysis type
        analysis_type = input_data.get("analysis_type", "comprehensive")
        valid_types = ["statistical", "pattern", "trend", "comparative", "comprehensive"]
        if analysis_type not in valid_types:
            self.logger.warning(f"Unknown analysis type: {analysis_type}, using 'comprehensive'")
            input_data["analysis_type"] = "comprehensive"

        # Validate data source
        data_source = input_data.get("data_source", "processed")
        valid_sources = ["processed", "collected", "raw", "external"]
        if data_source not in valid_sources:
            self.logger.warning(f"Unknown data source: {data_source}, using 'processed'")
            input_data["data_source"] = "processed"

        # Validate depth
        depth = input_data.get("depth", "standard")
        valid_depths = ["shallow", "standard", "deep"]
        if depth not in valid_depths:
            self.logger.warning(f"Unknown depth: {depth}, using 'standard'")
            input_data["depth"] = "standard"

        return True

    async def post_process_result(self, result: ExecutionResult, input_data: Dict[str, Any]) -> ExecutionResult:
        """
        Post-process the workflow execution result.

        Args:
            result: Execution result to process
            input_data: Original input data

        Returns:
            Processed execution result
        """
        if result.status.value == "completed" and result.result:
            # Extract the analysis results from the workflow results
            workflow_results = result.result

            # Find the acceptance outcome and analysis results
            acceptance_result = None
            analysis_results = None

            if isinstance(workflow_results, list):
                for step_result in reversed(workflow_results):
                    if isinstance(step_result, dict):
                        if "accept_outcome" in str(step_result):
                            acceptance_result = step_result
                        if "insights" in str(step_result) or "analysis_results" in str(step_result):
                            analysis_results = step_result

            # Format the final result
            formatted_result = {
                "analysis_results": analysis_results.get("results") if analysis_results else {},
                "insights": analysis_results.get("insights", []) if analysis_results else [],
                "recommendations": analysis_results.get("recommendations", []) if analysis_results else [],
                "acceptance_results": acceptance_result if acceptance_result else {},
                "accuracy_score": acceptance_result.get("accuracy", 0.0) if acceptance_result else 0.0,
                "confidence_score": acceptance_result.get("confidence", 0.0) if acceptance_result else 0.0,
                "analysis_metadata": {
                    "analysis_type": input_data.get("analysis_type", "comprehensive"),
                    "data_source": input_data.get("data_source", "processed"),
                    "depth": input_data.get("depth", "standard"),
                    "target": input_data.get("text", "")
                },
                "workflow_metadata": {
                    "execution_time": result.metadata.get("total_duration"),
                    "steps_completed": result.metadata.get("completed_nodes", 0),
                    "acceptance_passed": acceptance_result.get("passed", False) if acceptance_result else False,
                    "criteria_met": acceptance_result.get("criteria", {}) if acceptance_result else {}
                }
            }

            result.result = formatted_result

        return result

    def _estimate_duration(self, workflow_steps: List[Dict[str, Any]]) -> float:
        """Estimate workflow execution duration in seconds."""
        base_duration = 60.0  # Base duration for analysis tasks

        # Count different types of operations
        statistical_operations = 0
        ml_operations = 0
        pattern_operations = 0
        validation_operations = 0
        parallel_blocks = 0
        comprehensive_operations = 0

        def count_operations(steps):
            nonlocal statistical_operations, ml_operations, pattern_operations, validation_operations, parallel_blocks, comprehensive_operations

            for step in steps:
                if isinstance(step, dict):
                    if "task" in step:
                        tools = step.get("tools", [])
                        if any("statistical" in tool for tool in tools):
                            statistical_operations += 1
                        if any("ml" in tool or "predictive" in tool for tool in tools):
                            ml_operations += 1
                        if any("pattern" in tool for tool in tools):
                            pattern_operations += 1
                        if any("validator" in tool or "validation" in tool for tool in tools):
                            validation_operations += 1
                        if any("comprehensive" in tool for tool in tools):
                            comprehensive_operations += 1
                    elif "parallel" in step:
                        parallel_blocks += 1
                        count_operations(step["parallel"])
                    elif "sequence" in step:
                        count_operations(step["sequence"])
                    elif "if" in step:
                        count_operations(step.get("then", []))
                        count_operations(step.get("else", []))

        count_operations(workflow_steps)

        # Calculate estimated duration
        estimated = base_duration
        estimated += statistical_operations * 30  # 30 seconds per statistical operation
        estimated += ml_operations * 60  # 60 seconds per ML operation
        estimated += pattern_operations * 45  # 45 seconds per pattern operation
        estimated += validation_operations * 25  # 25 seconds per validation
        estimated += comprehensive_operations * 90  # 90 seconds per comprehensive operation
        estimated += parallel_blocks * 25  # 25 seconds overhead per parallel block

        return estimated
