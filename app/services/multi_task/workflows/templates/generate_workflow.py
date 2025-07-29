"""
Generate Workflow Template

Workflow template for generate-type tasks that create new content, reports, or outputs.
Focuses on content generation, synthesis, formatting, and quality assurance.
"""

from typing import Dict, List, Any, Optional
from ..base_workflow import BaseWorkflow
from ..dsl import DSLNode, DSLNodeType
from ...core.models.execution_models import WorkflowExecution, ExecutionResult


class GenerateWorkflow(BaseWorkflow):
    """
    Workflow template for generate-type tasks.

    Typical flow:
    1. Understand generation requirements and output specifications
    2. Plan content structure and generation strategy
    3. Execute content generation with appropriate tools and methods
    4. Review and refine generated content
    5. Accept generation outcomes and validate quality
    """

    def __init__(self):
        """Initialize the generate workflow."""
        super().__init__()
        self.workflow_type = "generate"
        self.description = "Workflow for generating content, reports, and outputs"

    async def create_workflow_definition(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create workflow definition for generate tasks.

        Args:
            input_data: Input data containing generation requirements

        Returns:
            Workflow definition with DSL steps
        """
        generation_target = input_data.get("text", "")
        output_type = input_data.get("output_type", "report")
        content_source = input_data.get("content_source", "analyzed")
        quality_level = input_data.get("quality_level", "standard")
        format_requirements = input_data.get("format", "structured")

        # Determine generation strategy based on output type and quality level
        if output_type == "summary":
            workflow_steps = self._create_summary_generation_workflow(generation_target, content_source, quality_level, format_requirements)
        elif output_type == "report":
            workflow_steps = self._create_report_generation_workflow(generation_target, content_source, quality_level, format_requirements)
        elif output_type == "presentation":
            workflow_steps = self._create_presentation_generation_workflow(generation_target, content_source, quality_level, format_requirements)
        elif output_type == "document":
            workflow_steps = self._create_document_generation_workflow(generation_target, content_source, quality_level, format_requirements)
        else:
            workflow_steps = self._create_comprehensive_generation_workflow(generation_target, content_source, quality_level, format_requirements)

        return {
            "id": f"generate_workflow_{self._generate_workflow_id()}",
            "type": "generate",
            "description": f"Generate workflow for: {generation_target[:100]}...",
            "steps": workflow_steps,
            "metadata": {
                "output_type": output_type,
                "content_source": content_source,
                "quality_level": quality_level,
                "format_requirements": format_requirements,
                "estimated_duration": self._estimate_duration(workflow_steps)
            }
        }

    def _create_summary_generation_workflow(self, target: str, content_source: str, quality_level: str, format_req: str) -> List[Dict[str, Any]]:
        """Create workflow for summary generation tasks."""
        return [
            {
                "task": "generate_summary_requirements",
                "tools": ["analysis.text", "generator.planning"],
                "parameters": {
                    "target": target,
                    "content_source": content_source,
                    "summary_type": "comprehensive",
                    "length_target": "auto",
                    "quality_level": quality_level
                },
                "timeout": 30
            },
            {
                "task": "generate_extract_key_points",
                "tools": ["analysis.text", "extractor.key_points"],
                "parameters": {
                    "source_content": "${result.generate_summary_requirements.source_content}",
                    "extraction_strategy": "${result.generate_summary_requirements.extraction_strategy}",
                    "target": target
                },
                "timeout": 45
            },
            {
                "parallel": [
                    {
                        "task": "generate_structure_summary",
                        "tools": ["generator.structure"],
                        "parameters": {
                            "key_points": "${result.generate_extract_key_points.key_points}",
                            "structure_type": "hierarchical",
                            "format": format_req
                        }
                    },
                    {
                        "task": "generate_prioritize_content",
                        "tools": ["analysis.priority", "generator.ranking"],
                        "parameters": {
                            "key_points": "${result.generate_extract_key_points.key_points}",
                            "prioritization_criteria": "${result.generate_summary_requirements.priority_criteria}",
                            "target": target
                        }
                    }
                ],
                "wait_for_all": True
            },
            {
                "task": "generate_compose_summary",
                "tools": ["generator.text", "generator.summary"],
                "parameters": {
                    "structure": "${result.generate_structure_summary.structure}",
                    "prioritized_content": "${result.generate_prioritize_content.prioritized_content}",
                    "composition_style": "${result.generate_summary_requirements.style}",
                    "target": target,
                    "format": format_req
                },
                "timeout": 60
            },
            {
                "task": "generate_review_summary",
                "tools": ["reviewer.content", "analysis.text"],
                "parameters": {
                    "generated_summary": "${result.generate_compose_summary.summary}",
                    "review_criteria": ["accuracy", "completeness", "clarity", "conciseness"],
                    "target": target
                }
            },
            {
                "if": "result.generate_review_summary.review_score >= 0.8",
                "then": [
                    {
                        "task": "generate_accept_outcome",
                        "tools": ["analysis.text"],
                        "parameters": {
                            "generated_content": "${result.generate_compose_summary.summary}",
                            "review_results": "${result.generate_review_summary}",
                            "target": target,
                            "acceptance_criteria": "summary_quality"
                        }
                    }
                ],
                "else": [
                    {
                        "task": "generate_refine_summary",
                        "tools": ["generator.refine", "generator.text"],
                        "parameters": {
                            "summary": "${result.generate_compose_summary.summary}",
                            "review_feedback": "${result.generate_review_summary.feedback}",
                            "refinement_strategy": "targeted"
                        }
                    },
                    {
                        "task": "generate_accept_outcome",
                        "tools": ["analysis.text"],
                        "parameters": {
                            "generated_content": "${result.generate_refine_summary.refined_summary}",
                            "refinement_results": "${result.generate_refine_summary}",
                            "target": target,
                            "acceptance_criteria": "summary_quality"
                        }
                    }
                ]
            }
        ]

    def _create_report_generation_workflow(self, target: str, content_source: str, quality_level: str, format_req: str) -> List[Dict[str, Any]]:
        """Create workflow for report generation tasks."""
        return [
            {
                "task": "generate_report_planning",
                "tools": ["generator.planning", "analysis.requirements"],
                "parameters": {
                    "target": target,
                    "content_source": content_source,
                    "report_type": "analytical",
                    "quality_level": quality_level,
                    "format": format_req
                },
                "timeout": 45
            },
            {
                "sequence": [
                    {
                        "task": "generate_report_outline",
                        "tools": ["generator.structure", "generator.outline"],
                        "parameters": {
                            "planning_results": "${result.generate_report_planning}",
                            "outline_depth": "detailed",
                            "target": target
                        }
                    },
                    {
                        "parallel": [
                            {
                                "task": "generate_executive_summary",
                                "tools": ["generator.summary", "generator.text"],
                                "parameters": {
                                    "source_content": "${result.generate_report_planning.source_content}",
                                    "summary_type": "executive",
                                    "target": target
                                }
                            },
                            {
                                "task": "generate_main_content",
                                "tools": ["generator.content", "generator.text"],
                                "parameters": {
                                    "outline": "${result.generate_report_outline.outline}",
                                    "source_content": "${result.generate_report_planning.source_content}",
                                    "content_strategy": "comprehensive",
                                    "target": target
                                }
                            },
                            {
                                "task": "generate_visualizations",
                                "tools": ["generator.visualization", "analysis.data"],
                                "parameters": {
                                    "data_content": "${result.generate_report_planning.data_content}",
                                    "visualization_requirements": "${result.generate_report_planning.viz_requirements}",
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
                "task": "generate_assemble_report",
                "tools": ["generator.assembly", "formatter.document"],
                "parameters": {
                    "executive_summary": "${result.generate_executive_summary.summary}",
                    "main_content": "${result.generate_main_content.content}",
                    "visualizations": "${result.generate_visualizations.visualizations}",
                    "assembly_template": "${result.generate_report_planning.template}",
                    "format": format_req,
                    "target": target
                },
                "timeout": 75
            },
            {
                "parallel": [
                    {
                        "task": "generate_review_content",
                        "tools": ["reviewer.content", "analysis.text"],
                        "parameters": {
                            "assembled_report": "${result.generate_assemble_report.report}",
                            "review_aspects": ["accuracy", "completeness", "coherence", "clarity"],
                            "target": target
                        }
                    },
                    {
                        "task": "generate_review_format",
                        "tools": ["reviewer.format", "validator.format"],
                        "parameters": {
                            "assembled_report": "${result.generate_assemble_report.report}",
                            "format_requirements": format_req,
                            "quality_standards": quality_level
                        }
                    }
                ],
                "wait_for_all": True
            },
            {
                "if": "result.generate_review_content.content_score >= 0.8 and result.generate_review_format.format_score >= 0.8",
                "then": [
                    {
                        "task": "generate_accept_outcome",
                        "tools": ["analysis.text"],
                        "parameters": {
                            "generated_content": "${result.generate_assemble_report.report}",
                            "review_results": {
                                "content": "${result.generate_review_content}",
                                "format": "${result.generate_review_format}"
                            },
                            "target": target,
                            "acceptance_criteria": "report_excellence"
                        }
                    }
                ],
                "else": [
                    {
                        "task": "generate_identify_improvements",
                        "tools": ["analysis.improvement", "reviewer.feedback"],
                        "parameters": {
                            "content_review": "${result.generate_review_content}",
                            "format_review": "${result.generate_review_format}",
                            "report": "${result.generate_assemble_report.report}"
                        }
                    },
                    {
                        "task": "generate_apply_improvements",
                        "tools": ["generator.improve", "formatter.enhance"],
                        "parameters": {
                            "improvement_plan": "${result.generate_identify_improvements.improvements}",
                            "report": "${result.generate_assemble_report.report}",
                            "target": target
                        }
                    },
                    {
                        "task": "generate_accept_outcome",
                        "tools": ["analysis.text"],
                        "parameters": {
                            "generated_content": "${result.generate_apply_improvements.improved_report}",
                            "improvement_results": "${result.generate_apply_improvements}",
                            "target": target,
                            "acceptance_criteria": "report_excellence"
                        }
                    }
                ]
            }
        ]

    def _create_presentation_generation_workflow(self, target: str, content_source: str, quality_level: str, format_req: str) -> List[Dict[str, Any]]:
        """Create workflow for presentation generation tasks."""
        return [
            {
                "task": "generate_presentation_design",
                "tools": ["generator.presentation", "designer.layout"],
                "parameters": {
                    "target": target,
                    "content_source": content_source,
                    "presentation_type": "analytical",
                    "audience": "professional",
                    "duration": "auto_estimate",
                    "format": format_req
                },
                "timeout": 40
            },
            {
                "parallel": [
                    {
                        "task": "generate_slide_structure",
                        "tools": ["generator.structure", "designer.slides"],
                        "parameters": {
                            "design_specs": "${result.generate_presentation_design.design_specs}",
                            "content_outline": "${result.generate_presentation_design.content_outline}",
                            "slide_count": "auto_optimize"
                        }
                    },
                    {
                        "task": "generate_visual_elements",
                        "tools": ["generator.visualization", "designer.graphics"],
                        "parameters": {
                            "data_content": "${result.generate_presentation_design.data_content}",
                            "visual_strategy": "${result.generate_presentation_design.visual_strategy}",
                            "target": target
                        }
                    }
                ],
                "wait_for_all": True
            },
            {
                "task": "generate_slide_content",
                "tools": ["generator.slides", "generator.text"],
                "parameters": {
                    "slide_structure": "${result.generate_slide_structure.structure}",
                    "visual_elements": "${result.generate_visual_elements.elements}",
                    "content_source": "${result.generate_presentation_design.source_content}",
                    "presentation_style": "${result.generate_presentation_design.style}",
                    "target": target
                },
                "timeout": 90
            },
            {
                "task": "generate_speaker_notes",
                "tools": ["generator.notes", "generator.text"],
                "parameters": {
                    "slide_content": "${result.generate_slide_content.slides}",
                    "presentation_context": "${result.generate_presentation_design.context}",
                    "notes_detail_level": quality_level
                }
            },
            {
                "task": "generate_review_presentation",
                "tools": ["reviewer.presentation", "validator.slides"],
                "parameters": {
                    "presentation": "${result.generate_slide_content.slides}",
                    "speaker_notes": "${result.generate_speaker_notes.notes}",
                    "review_criteria": ["clarity", "flow", "visual_appeal", "content_accuracy"],
                    "target": target
                }
            },
            {
                "task": "generate_accept_outcome",
                "tools": ["analysis.text"],
                "parameters": {
                    "generated_content": {
                        "slides": "${result.generate_slide_content.slides}",
                        "speaker_notes": "${result.generate_speaker_notes.notes}"
                    },
                    "review_results": "${result.generate_review_presentation}",
                    "target": target,
                    "acceptance_criteria": "presentation_quality"
                }
            }
        ]

    def _create_document_generation_workflow(self, target: str, content_source: str, quality_level: str, format_req: str) -> List[Dict[str, Any]]:
        """Create workflow for document generation tasks."""
        return [
            {
                "task": "generate_document_specification",
                "tools": ["generator.planning", "analyzer.requirements"],
                "parameters": {
                    "target": target,
                    "content_source": content_source,
                    "document_type": "technical",
                    "quality_level": quality_level,
                    "format": format_req
                }
            },
            {
                "sequence": [
                    {
                        "task": "generate_document_structure",
                        "tools": ["generator.structure", "designer.document"],
                        "parameters": {
                            "specifications": "${result.generate_document_specification}",
                            "structure_complexity": "comprehensive",
                            "target": target
                        }
                    },
                    {
                        "parallel": [
                            {
                                "task": "generate_content_sections",
                                "tools": ["generator.content", "generator.text"],
                                "parameters": {
                                    "document_structure": "${result.generate_document_structure.structure}",
                                    "source_content": "${result.generate_document_specification.source_content}",
                                    "writing_style": "${result.generate_document_specification.style}",
                                    "target": target
                                }
                            },
                            {
                                "task": "generate_supporting_materials",
                                "tools": ["generator.appendix", "generator.references"],
                                "parameters": {
                                    "content_requirements": "${result.generate_document_specification.supporting_requirements}",
                                    "reference_style": "${result.generate_document_specification.reference_style}",
                                    "target": target
                                }
                            }
                        ],
                        "wait_for_all": True
                    }
                ]
            },
            {
                "task": "generate_format_document",
                "tools": ["formatter.document", "designer.layout"],
                "parameters": {
                    "content_sections": "${result.generate_content_sections.sections}",
                    "supporting_materials": "${result.generate_supporting_materials.materials}",
                    "format_specifications": "${result.generate_document_specification.format_specs}",
                    "format": format_req,
                    "target": target
                },
                "timeout": 60
            },
            {
                "task": "generate_quality_assurance",
                "tools": ["reviewer.document", "validator.quality"],
                "parameters": {
                    "formatted_document": "${result.generate_format_document.document}",
                    "quality_standards": quality_level,
                    "qa_checklist": "comprehensive",
                    "target": target
                }
            },
            {
                "task": "generate_accept_outcome",
                "tools": ["analysis.text"],
                "parameters": {
                    "generated_content": "${result.generate_format_document.document}",
                    "qa_results": "${result.generate_quality_assurance}",
                    "target": target,
                    "acceptance_criteria": "document_excellence"
                }
            }
        ]

    def _create_comprehensive_generation_workflow(self, target: str, content_source: str, quality_level: str, format_req: str) -> List[Dict[str, Any]]:
        """Create workflow for comprehensive generation tasks."""
        return [
            {
                "task": "generate_comprehensive_planning",
                "tools": ["generator.planning", "analyzer.comprehensive"],
                "parameters": {
                    "target": target,
                    "content_source": content_source,
                    "generation_scope": "multi_format",
                    "quality_level": quality_level,
                    "output_requirements": format_req
                },
                "timeout": 60
            },
            {
                "parallel": [
                    {
                        "task": "generate_primary_content",
                        "tools": ["generator.content", "generator.text"],
                        "parameters": {
                            "planning_results": "${result.generate_comprehensive_planning}",
                            "content_type": "primary",
                            "generation_strategy": "comprehensive",
                            "target": target
                        }
                    },
                    {
                        "task": "generate_supplementary_content",
                        "tools": ["generator.supplementary", "generator.support"],
                        "parameters": {
                            "planning_results": "${result.generate_comprehensive_planning}",
                            "content_type": "supplementary",
                            "target": target
                        }
                    },
                    {
                        "task": "generate_metadata_content",
                        "tools": ["generator.metadata", "analyzer.content"],
                        "parameters": {
                            "planning_results": "${result.generate_comprehensive_planning}",
                            "metadata_requirements": "comprehensive",
                            "target": target
                        }
                    }
                ],
                "max_concurrency": 3,
                "wait_for_all": True
            },
            {
                "task": "generate_integrate_content",
                "tools": ["generator.integration", "formatter.comprehensive"],
                "parameters": {
                    "primary_content": "${result.generate_primary_content.content}",
                    "supplementary_content": "${result.generate_supplementary_content.content}",
                    "metadata_content": "${result.generate_metadata_content.metadata}",
                    "integration_strategy": "${result.generate_comprehensive_planning.integration_strategy}",
                    "format": format_req,
                    "target": target
                },
                "timeout": 90
            },
            {
                "task": "generate_comprehensive_review",
                "tools": ["reviewer.comprehensive", "validator.multi_aspect"],
                "parameters": {
                    "integrated_content": "${result.generate_integrate_content.integrated_content}",
                    "review_dimensions": ["content_quality", "format_compliance", "completeness", "coherence"],
                    "quality_standards": quality_level,
                    "target": target
                },
                "timeout": 75
            },
            {
                "task": "generate_accept_outcome",
                "tools": ["analysis.text"],
                "parameters": {
                    "generated_content": "${result.generate_integrate_content.integrated_content}",
                    "review_results": "${result.generate_comprehensive_review}",
                    "target": target,
                    "acceptance_criteria": "comprehensive_excellence"
                }
            }
        ]

    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data for generate workflow.

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

        # Validate generation target
        target = input_data.get("text", "").strip()
        if not target:
            self.logger.error("Generation target is empty")
            return False

        # Validate output type
        output_type = input_data.get("output_type", "report")
        valid_types = ["summary", "report", "presentation", "document", "comprehensive"]
        if output_type not in valid_types:
            self.logger.warning(f"Unknown output type: {output_type}, using 'report'")
            input_data["output_type"] = "report"

        # Validate content source
        content_source = input_data.get("content_source", "analyzed")
        valid_sources = ["analyzed", "processed", "collected", "raw"]
        if content_source not in valid_sources:
            self.logger.warning(f"Unknown content source: {content_source}, using 'analyzed'")
            input_data["content_source"] = "analyzed"

        # Validate quality level
        quality_level = input_data.get("quality_level", "standard")
        valid_levels = ["basic", "standard", "high", "premium"]
        if quality_level not in valid_levels:
            self.logger.warning(f"Unknown quality level: {quality_level}, using 'standard'")
            input_data["quality_level"] = "standard"

        # Validate format requirements
        format_req = input_data.get("format", "structured")
        valid_formats = ["structured", "html", "pdf", "docx", "pptx", "markdown", "json"]
        if format_req not in valid_formats:
            self.logger.warning(f"Unknown format: {format_req}, using 'structured'")
            input_data["format"] = "structured"

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
            # Extract the generated content from the workflow results
            workflow_results = result.result

            # Find the acceptance outcome and generated content
            acceptance_result = None
            generated_content = None

            if isinstance(workflow_results, list):
                for step_result in reversed(workflow_results):
                    if isinstance(step_result, dict):
                        if "accept_outcome" in str(step_result):
                            acceptance_result = step_result
                        if "generated_content" in str(step_result) or "content" in str(step_result):
                            generated_content = step_result

            # Format the final result
            formatted_result = {
                "generated_content": generated_content.get("content") if generated_content else None,
                "acceptance_results": acceptance_result if acceptance_result else {},
                "quality_score": acceptance_result.get("quality_score", 0.0) if acceptance_result else 0.0,
                "accuracy_score": acceptance_result.get("accuracy", 0.0) if acceptance_result else 0.0,
                "meets_request": acceptance_result.get("meets_request", False) if acceptance_result else False,
                "no_synthetic_data": acceptance_result.get("no_synthetic_data", True) if acceptance_result else True,
                "generation_metadata": {
                    "output_type": input_data.get("output_type", "report"),
                    "content_source": input_data.get("content_source", "analyzed"),
                    "quality_level": input_data.get("quality_level", "standard"),
                    "format": input_data.get("format", "structured"),
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
        base_duration = 75.0  # Base duration for generation tasks

        # Count different types of operations
        generation_operations = 0
        review_operations = 0
        formatting_operations = 0
        design_operations = 0
        parallel_blocks = 0
        comprehensive_operations = 0

        def count_operations(steps):
            nonlocal generation_operations, review_operations, formatting_operations, design_operations, parallel_blocks, comprehensive_operations

            for step in steps:
                if isinstance(step, dict):
                    if "task" in step:
                        tools = step.get("tools", [])
                        if any("generator" in tool for tool in tools):
                            generation_operations += 1
                        if any("reviewer" in tool or "review" in tool for tool in tools):
                            review_operations += 1
                        if any("formatter" in tool or "format" in tool for tool in tools):
                            formatting_operations += 1
                        if any("designer" in tool or "design" in tool for tool in tools):
                            design_operations += 1
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
        estimated += generation_operations * 45  # 45 seconds per generation operation
        estimated += review_operations * 30  # 30 seconds per review
        estimated += formatting_operations * 25  # 25 seconds per formatting operation
        estimated += design_operations * 35  # 35 seconds per design operation
        estimated += comprehensive_operations * 90  # 90 seconds per comprehensive operation
        estimated += parallel_blocks * 30  # 30 seconds overhead per parallel block

        return estimated
