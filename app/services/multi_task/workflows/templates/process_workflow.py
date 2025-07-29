"""
Process Workflow Template

Workflow template for process-type tasks that transform and manipulate data.
Focuses on data processing, transformation, filtering, and structuring operations.
"""

from typing import Dict, List, Any, Optional
from ..base_workflow import BaseWorkflow
from ..dsl import DSLNode, DSLNodeType
from ...core.models.execution_models import WorkflowExecution, ExecutionResult


class ProcessWorkflow(BaseWorkflow):
    """
    Workflow template for process-type tasks.

    Typical flow:
    1. Analyze input data structure and processing requirements
    2. Plan processing pipeline with appropriate transformations
    3. Execute data processing operations (filtering, transformation, aggregation)
    4. Validate processed data quality and integrity
    5. Examine processing outcomes and results
    """

    def __init__(self):
        """Initialize the process workflow."""
        super().__init__()
        self.workflow_type = "process"
        self.description = "Workflow for processing and transforming data"

    async def create_workflow_definition(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create workflow definition for process tasks.

        Args:
            input_data: Input data containing processing requirements

        Returns:
            Workflow definition with DSL steps
        """
        processing_target = input_data.get("text", "")
        data_source = input_data.get("data_source", "collected")
        processing_type = input_data.get("processing_type", "standard")
        output_format = input_data.get("output_format", "structured")

        # Determine processing strategy based on type
        if processing_type == "simple":
            workflow_steps = self._create_simple_process_workflow(processing_target, data_source, output_format)
        elif processing_type == "complex":
            workflow_steps = self._create_complex_process_workflow(processing_target, data_source, output_format)
        else:
            workflow_steps = self._create_standard_process_workflow(processing_target, data_source, output_format)

        return {
            "id": f"process_workflow_{self._generate_workflow_id()}",
            "type": "process",
            "description": f"Process workflow for: {processing_target[:100]}...",
            "steps": workflow_steps,
            "metadata": {
                "data_source": data_source,
                "processing_type": processing_type,
                "output_format": output_format,
                "estimated_duration": self._estimate_duration(workflow_steps)
            }
        }

    def _create_simple_process_workflow(self, target: str, data_source: str, output_format: str) -> List[Dict[str, Any]]:
        """Create workflow for simple processing tasks."""
        return [
            {
                "task": "process_analyze_input",
                "tools": ["analysis.data"],
                "parameters": {
                    "target": target,
                    "data_source": data_source,
                    "analysis_type": "simple"
                },
                "timeout": 30
            },
            {
                "task": "process_clean_data",
                "tools": ["processor.clean", "analysis.data"],
                "parameters": {
                    "input_data": "${result.process_analyze_input.data}",
                    "cleaning_rules": "${result.process_analyze_input.cleaning_requirements}",
                    "target": target
                },
                "timeout": 45
            },
            {
                "task": "process_transform_basic",
                "tools": ["processor.transform"],
                "parameters": {
                    "cleaned_data": "${result.process_clean_data.cleaned_data}",
                    "output_format": output_format,
                    "transformation_type": "basic"
                },
                "timeout": 30
            },
            {
                "task": "process_examine_outcome",
                "tools": ["analysis.data"],
                "parameters": {
                    "processed_data": "${result.process_transform_basic.transformed_data}",
                    "target": target,
                    "quality_check": "basic"
                },
                "conditions": [
                    "result.process_transform_basic.completed == true"
                ]
            }
        ]

    def _create_standard_process_workflow(self, target: str, data_source: str, output_format: str) -> List[Dict[str, Any]]:
        """Create workflow for standard processing tasks."""
        return [
            {
                "task": "process_analyze_requirements",
                "tools": ["analysis.data", "analysis.text"],
                "parameters": {
                    "target": target,
                    "data_source": data_source,
                    "output_format": output_format,
                    "analysis_depth": "standard"
                },
                "timeout": 45
            },
            {
                "task": "process_plan_pipeline",
                "tools": ["analysis.data"],
                "parameters": {
                    "requirements": "${result.process_analyze_requirements.requirements}",
                    "data_characteristics": "${result.process_analyze_requirements.data_characteristics}",
                    "target": target
                }
            },
            {
                "sequence": [
                    {
                        "task": "process_validate_input",
                        "tools": ["validator.data"],
                        "parameters": {
                            "input_data": "${result.process_analyze_requirements.data}",
                            "validation_rules": "${result.process_plan_pipeline.validation_rules}",
                            "target": target
                        }
                    },
                    {
                        "parallel": [
                            {
                                "task": "process_clean_normalize",
                                "tools": ["processor.clean", "processor.normalize"],
                                "parameters": {
                                    "validated_data": "${result.process_validate_input.validated_data}",
                                    "normalization_rules": "${result.process_plan_pipeline.normalization_rules}"
                                }
                            },
                            {
                                "task": "process_extract_features",
                                "tools": ["processor.extract", "analysis.data"],
                                "parameters": {
                                    "validated_data": "${result.process_validate_input.validated_data}",
                                    "feature_requirements": "${result.process_plan_pipeline.feature_requirements}"
                                }
                            }
                        ],
                        "max_concurrency": 2,
                        "wait_for_all": True
                    },
                    {
                        "task": "process_merge_features",
                        "tools": ["processor.merge"],
                        "parameters": {
                            "cleaned_data": "${result.process_clean_normalize.cleaned_data}",
                            "extracted_features": "${result.process_extract_features.features}",
                            "merge_strategy": "${result.process_plan_pipeline.merge_strategy}"
                        }
                    }
                ]
            },
            {
                "task": "process_apply_transformations",
                "tools": ["processor.transform", "analysis.data"],
                "parameters": {
                    "merged_data": "${result.process_merge_features.merged_data}",
                    "transformations": "${result.process_plan_pipeline.transformations}",
                    "output_format": output_format,
                    "target": target
                },
                "timeout": 60
            },
            {
                "task": "process_quality_check",
                "tools": ["validator.data", "analysis.data"],
                "parameters": {
                    "transformed_data": "${result.process_apply_transformations.transformed_data}",
                    "quality_criteria": {
                        "completeness": 0.9,
                        "consistency": 0.85,
                        "accuracy": 0.8
                    },
                    "target": target
                },
                "timeout": 45
            },
            {
                "if": "result.process_quality_check.quality_score >= 0.8",
                "then": [
                    {
                        "task": "process_examine_outcome",
                        "tools": ["analysis.data"],
                        "parameters": {
                            "processed_data": "${result.process_apply_transformations.transformed_data}",
                            "quality_results": "${result.process_quality_check}",
                            "target": target,
                            "examination_type": "standard_success"
                        }
                    }
                ],
                "else": [
                    {
                        "task": "process_identify_issues",
                        "tools": ["analysis.data"],
                        "parameters": {
                            "quality_results": "${result.process_quality_check}",
                            "transformed_data": "${result.process_apply_transformations.transformed_data}",
                            "target": target
                        }
                    },
                    {
                        "task": "process_remediate_issues",
                        "tools": ["processor.repair", "processor.enhance"],
                        "parameters": {
                            "issues": "${result.process_identify_issues.identified_issues}",
                            "data": "${result.process_apply_transformations.transformed_data}",
                            "remediation_strategy": "targeted"
                        }
                    },
                    {
                        "task": "process_examine_outcome",
                        "tools": ["analysis.data"],
                        "parameters": {
                            "processed_data": "${result.process_remediate_issues.remediated_data}",
                            "remediation_results": "${result.process_remediate_issues}",
                            "target": target,
                            "examination_type": "standard_remediated"
                        }
                    }
                ]
            }
        ]

    def _create_complex_process_workflow(self, target: str, data_source: str, output_format: str) -> List[Dict[str, Any]]:
        """Create workflow for complex processing tasks."""
        return [
            {
                "task": "process_comprehensive_analysis",
                "tools": ["analysis.data", "analysis.text", "analysis.statistical"],
                "parameters": {
                    "target": target,
                    "data_source": data_source,
                    "output_format": output_format,
                    "analysis_depth": "comprehensive"
                },
                "timeout": 90
            },
            {
                "task": "process_design_pipeline",
                "tools": ["analysis.data", "processor.design"],
                "parameters": {
                    "comprehensive_analysis": "${result.process_comprehensive_analysis}",
                    "target": target,
                    "pipeline_complexity": "high"
                }
            },
            {
                "sequence": [
                    {
                        "task": "process_stage_1_preparation",
                        "tools": ["validator.data", "processor.prepare"],
                        "parameters": {
                            "input_data": "${result.process_comprehensive_analysis.data}",
                            "preparation_plan": "${result.process_design_pipeline.stage_1_plan}",
                            "target": target
                        },
                        "timeout": 60
                    },
                    {
                        "parallel": [
                            {
                                "task": "process_stage_2a_structural",
                                "tools": ["processor.structural", "analysis.data"],
                                "parameters": {
                                    "prepared_data": "${result.process_stage_1_preparation.prepared_data}",
                                    "structural_operations": "${result.process_design_pipeline.structural_operations}"
                                }
                            },
                            {
                                "task": "process_stage_2b_semantic",
                                "tools": ["processor.semantic", "analysis.text"],
                                "parameters": {
                                    "prepared_data": "${result.process_stage_1_preparation.prepared_data}",
                                    "semantic_operations": "${result.process_design_pipeline.semantic_operations}"
                                }
                            },
                            {
                                "task": "process_stage_2c_statistical",
                                "tools": ["processor.statistical", "analysis.statistical"],
                                "parameters": {
                                    "prepared_data": "${result.process_stage_1_preparation.prepared_data}",
                                    "statistical_operations": "${result.process_design_pipeline.statistical_operations}"
                                }
                            }
                        ],
                        "max_concurrency": 3,
                        "wait_for_all": True
                    },
                    {
                        "task": "process_stage_3_integration",
                        "tools": ["processor.integrate", "analysis.data"],
                        "parameters": {
                            "structural_results": "${result.process_stage_2a_structural.results}",
                            "semantic_results": "${result.process_stage_2b_semantic.results}",
                            "statistical_results": "${result.process_stage_2c_statistical.results}",
                            "integration_strategy": "${result.process_design_pipeline.integration_strategy}"
                        },
                        "timeout": 75
                    }
                ]
            },
            {
                "task": "process_advanced_transformations",
                "tools": ["processor.advanced", "processor.ml", "analysis.data"],
                "parameters": {
                    "integrated_data": "${result.process_stage_3_integration.integrated_data}",
                    "advanced_operations": "${result.process_design_pipeline.advanced_operations}",
                    "output_format": output_format,
                    "target": target
                },
                "timeout": 120
            },
            {
                "parallel": [
                    {
                        "task": "process_comprehensive_validation",
                        "tools": ["validator.comprehensive", "analysis.data"],
                        "parameters": {
                            "processed_data": "${result.process_advanced_transformations.transformed_data}",
                            "validation_suite": "comprehensive",
                            "target": target
                        }
                    },
                    {
                        "task": "process_performance_analysis",
                        "tools": ["analysis.performance", "analysis.statistical"],
                        "parameters": {
                            "processed_data": "${result.process_advanced_transformations.transformed_data}",
                            "performance_metrics": "${result.process_design_pipeline.performance_requirements}"
                        }
                    },
                    {
                        "task": "process_quality_assessment",
                        "tools": ["analysis.quality", "validator.data"],
                        "parameters": {
                            "processed_data": "${result.process_advanced_transformations.transformed_data}",
                            "quality_standards": "enterprise",
                            "target": target
                        }
                    }
                ],
                "wait_for_all": True
            },
            {
                "task": "process_evaluate_results",
                "tools": ["analysis.comprehensive"],
                "parameters": {
                    "validation_results": "${result.process_comprehensive_validation}",
                    "performance_results": "${result.process_performance_analysis}",
                    "quality_results": "${result.process_quality_assessment}",
                    "success_criteria": {
                        "validation_score": 0.9,
                        "performance_score": 0.85,
                        "quality_score": 0.9
                    }
                }
            },
            {
                "if": "result.process_evaluate_results.overall_score >= 0.85",
                "then": [
                    {
                        "task": "process_examine_outcome",
                        "tools": ["analysis.data"],
                        "parameters": {
                            "processed_data": "${result.process_advanced_transformations.transformed_data}",
                            "evaluation_results": "${result.process_evaluate_results}",
                            "target": target,
                            "examination_type": "complex_success"
                        }
                    }
                ],
                "else": [
                    {
                        "task": "process_optimization_analysis",
                        "tools": ["analysis.optimization", "processor.optimize"],
                        "parameters": {
                            "evaluation_results": "${result.process_evaluate_results}",
                            "processed_data": "${result.process_advanced_transformations.transformed_data}",
                            "target": target
                        }
                    },
                    {
                        "task": "process_apply_optimizations",
                        "tools": ["processor.optimize", "processor.enhance"],
                        "parameters": {
                            "optimization_plan": "${result.process_optimization_analysis.optimization_plan}",
                            "data": "${result.process_advanced_transformations.transformed_data}",
                            "target": target
                        }
                    },
                    {
                        "task": "process_examine_outcome",
                        "tools": ["analysis.data"],
                        "parameters": {
                            "processed_data": "${result.process_apply_optimizations.optimized_data}",
                            "optimization_results": "${result.process_apply_optimizations}",
                            "target": target,
                            "examination_type": "complex_optimized"
                        }
                    }
                ]
            }
        ]

    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data for process workflow.

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

        # Validate processing target
        target = input_data.get("text", "").strip()
        if not target:
            self.logger.error("Processing target is empty")
            return False

        # Validate data source
        data_source = input_data.get("data_source", "collected")
        valid_sources = ["collected", "uploaded", "streamed", "database", "api"]
        if data_source not in valid_sources:
            self.logger.warning(f"Unknown data source: {data_source}, using 'collected'")
            input_data["data_source"] = "collected"

        # Validate processing type
        processing_type = input_data.get("processing_type", "standard")
        valid_types = ["simple", "standard", "complex"]
        if processing_type not in valid_types:
            self.logger.warning(f"Unknown processing type: {processing_type}, using 'standard'")
            input_data["processing_type"] = "standard"

        # Validate output format
        output_format = input_data.get("output_format", "structured")
        valid_formats = ["structured", "json", "csv", "xml", "text", "binary"]
        if output_format not in valid_formats:
            self.logger.warning(f"Unknown output format: {output_format}, using 'structured'")
            input_data["output_format"] = "structured"

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
            # Extract the processed data from the workflow results
            workflow_results = result.result

            # Find the examination outcome and processed data
            examination_result = None
            processed_data = None

            if isinstance(workflow_results, list):
                for step_result in reversed(workflow_results):
                    if isinstance(step_result, dict):
                        if "examine_outcome" in str(step_result):
                            examination_result = step_result
                        if "processed_data" in str(step_result) or "transformed_data" in str(step_result):
                            processed_data = step_result

            # Format the final result
            formatted_result = {
                "processed_data": processed_data.get("data") if processed_data else None,
                "examination_results": examination_result if examination_result else {},
                "processing_quality": examination_result.get("quality_score", 0.0) if examination_result else 0.0,
                "credibility_score": examination_result.get("credibility", 0.0) if examination_result else 0.0,
                "confidence_score": examination_result.get("confidence", 0.0) if examination_result else 0.0,
                "data_characteristics": processed_data.get("characteristics", {}) if processed_data else {},
                "processing_metadata": {
                    "data_source": input_data.get("data_source", "collected"),
                    "processing_type": input_data.get("processing_type", "standard"),
                    "output_format": input_data.get("output_format", "structured"),
                    "target": input_data.get("text", "")
                },
                "workflow_metadata": {
                    "execution_time": result.metadata.get("total_duration"),
                    "steps_completed": result.metadata.get("completed_nodes", 0),
                    "examination_passed": examination_result.get("passed", False) if examination_result else False
                }
            }

            result.result = formatted_result

        return result

    def _estimate_duration(self, workflow_steps: List[Dict[str, Any]]) -> float:
        """Estimate workflow execution duration in seconds."""
        base_duration = 45.0  # Base duration for processing tasks

        # Count different types of operations
        analysis_operations = 0
        processing_operations = 0
        validation_operations = 0
        parallel_blocks = 0
        complex_operations = 0

        def count_operations(steps):
            nonlocal analysis_operations, processing_operations, validation_operations, parallel_blocks, complex_operations

            for step in steps:
                if isinstance(step, dict):
                    if "task" in step:
                        tools = step.get("tools", [])
                        if any("analysis" in tool for tool in tools):
                            analysis_operations += 1
                        if any("processor" in tool for tool in tools):
                            processing_operations += 1
                        if any("validator" in tool for tool in tools):
                            validation_operations += 1
                        if any("ml" in tool or "advanced" in tool or "comprehensive" in tool for tool in tools):
                            complex_operations += 1
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
        estimated += analysis_operations * 25  # 25 seconds per analysis
        estimated += processing_operations * 35  # 35 seconds per processing operation
        estimated += validation_operations * 20  # 20 seconds per validation
        estimated += complex_operations * 60  # 60 seconds per complex operation
        estimated += parallel_blocks * 20  # 20 seconds overhead per parallel block

        return estimated
