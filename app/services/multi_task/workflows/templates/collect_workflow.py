"""
Collect Workflow Template

Workflow template for collect-type tasks that gather information from various sources.
Focuses on data collection, scraping, and information aggregation with quality validation.
"""

from typing import Dict, List, Any, Optional
from ..base_workflow import BaseWorkflow
from ..dsl import DSLNode, DSLNodeType
from ...core.models.execution_models import WorkflowExecution, ExecutionResult


class CollectWorkflow(BaseWorkflow):
    """
    Workflow template for collect-type tasks.

    Typical flow:
    1. Identify data sources and collection requirements
    2. Execute parallel data collection from multiple sources
    3. Validate and filter collected data
    4. Examine data quality and credibility
    5. Aggregate and structure collected information
    """

    def __init__(self):
        """Initialize the collect workflow."""
        super().__init__()
        self.workflow_type = "collect"
        self.description = "Workflow for collecting and aggregating information from multiple sources"

    async def create_workflow_definition(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create workflow definition for collect tasks.

        Args:
            input_data: Input data containing collection requirements

        Returns:
            Workflow definition with DSL steps
        """
        collection_target = input_data.get("text", "")
        sources = input_data.get("sources", ["web", "academic"])
        scope = input_data.get("scope", "comprehensive")
        quality_threshold = input_data.get("quality_threshold", 0.7)

        # Determine collection strategy based on scope
        if scope == "quick":
            workflow_steps = self._create_quick_collect_workflow(collection_target, sources, quality_threshold)
        elif scope == "comprehensive":
            workflow_steps = self._create_comprehensive_collect_workflow(collection_target, sources, quality_threshold)
        else:
            workflow_steps = self._create_standard_collect_workflow(collection_target, sources, quality_threshold)

        return {
            "id": f"collect_workflow_{self._generate_workflow_id()}",
            "type": "collect",
            "description": f"Collect workflow for: {collection_target[:100]}...",
            "steps": workflow_steps,
            "metadata": {
                "sources": sources,
                "scope": scope,
                "quality_threshold": quality_threshold,
                "estimated_duration": self._estimate_duration(workflow_steps)
            }
        }

    def _create_quick_collect_workflow(self, target: str, sources: List[str], quality_threshold: float) -> List[Dict[str, Any]]:
        """Create workflow for quick collection tasks."""
        return [
            {
                "task": "collect_identify_sources",
                "tools": ["analysis.text"],
                "parameters": {
                    "target": target,
                    "preferred_sources": sources,
                    "scope": "quick",
                    "max_sources": 3
                },
                "timeout": 20
            },
            {
                "parallel": [
                    {
                        "task": "collect_scrape",
                        "tools": ["search.web", "scraper.web"],
                        "parameters": {
                            "target": target,
                            "sources": "${result.collect_identify_sources.web_sources}",
                            "max_pages": 5
                        }
                    },
                    {
                        "task": "collect_search",
                        "tools": ["search.web"],
                        "parameters": {
                            "query": target,
                            "max_results": 10,
                            "filter_quality": True
                        }
                    }
                ],
                "max_concurrency": 2,
                "wait_for_all": True
            },
            {
                "task": "collect_filter_quality",
                "tools": ["analysis.text", "analysis.data"],
                "parameters": {
                    "scraped_data": "${result.collect_scrape.data}",
                    "search_results": "${result.collect_search.results}",
                    "quality_threshold": quality_threshold,
                    "target": target
                },
                "timeout": 30
            },
            {
                "task": "collect_examine_outcome",
                "tools": ["analysis.text"],
                "parameters": {
                    "collected_data": "${result.collect_filter_quality.filtered_data}",
                    "target": target,
                    "quality_metrics": "${result.collect_filter_quality.quality_metrics}"
                },
                "conditions": [
                    "result.collect_filter_quality.completed == true"
                ]
            }
        ]

    def _create_standard_collect_workflow(self, target: str, sources: List[str], quality_threshold: float) -> List[Dict[str, Any]]:
        """Create workflow for standard collection tasks."""
        return [
            {
                "task": "collect_plan_strategy",
                "tools": ["analysis.text"],
                "parameters": {
                    "target": target,
                    "available_sources": sources,
                    "scope": "standard",
                    "quality_requirements": quality_threshold
                },
                "timeout": 30
            },
            {
                "parallel": [
                    {
                        "if": "subtasks.includes('web')",
                        "then": [
                            {
                                "task": "collect_web_search",
                                "tools": ["search.web"],
                                "parameters": {
                                    "query": target,
                                    "search_strategy": "${result.collect_plan_strategy.web_strategy}",
                                    "max_results": 20
                                }
                            }
                        ]
                    },
                    {
                        "if": "subtasks.includes('academic')",
                        "then": [
                            {
                                "task": "collect_academic_search",
                                "tools": ["search.academic"],
                                "parameters": {
                                    "query": target,
                                    "search_strategy": "${result.collect_plan_strategy.academic_strategy}",
                                    "max_results": 15
                                }
                            }
                        ]
                    },
                    {
                        "if": "subtasks.includes('scrape')",
                        "then": [
                            {
                                "task": "collect_scrape_sources",
                                "tools": ["scraper.web", "scraper.api"],
                                "parameters": {
                                    "target": target,
                                    "sources": "${result.collect_plan_strategy.scrape_sources}",
                                    "max_pages": 10
                                }
                            }
                        ]
                    }
                ],
                "max_concurrency": 3,
                "wait_for_all": False
            },
            {
                "task": "collect_aggregate_results",
                "tools": ["analysis.data"],
                "parameters": {
                    "web_results": "${result.collect_web_search.results}",
                    "academic_results": "${result.collect_academic_search.results}",
                    "scraped_data": "${result.collect_scrape_sources.data}",
                    "target": target
                },
                "timeout": 45
            },
            {
                "task": "collect_validate_data",
                "tools": ["analysis.text", "analysis.data"],
                "parameters": {
                    "aggregated_data": "${result.collect_aggregate_results.data}",
                    "validation_criteria": {
                        "relevance": 0.8,
                        "credibility": quality_threshold,
                        "completeness": 0.7
                    },
                    "target": target
                },
                "timeout": 60
            },
            {
                "if": "result.collect_validate_data.validation_score >= 0.7",
                "then": [
                    {
                        "task": "collect_examine_outcome",
                        "tools": ["analysis.text"],
                        "parameters": {
                            "validated_data": "${result.collect_validate_data.validated_data}",
                            "validation_results": "${result.collect_validate_data.validation_results}",
                            "target": target,
                            "examination_type": "standard"
                        }
                    }
                ],
                "else": [
                    {
                        "task": "collect_enhance_data",
                        "tools": ["search.specialized", "analysis.text"],
                        "parameters": {
                            "current_data": "${result.collect_validate_data.validated_data}",
                            "validation_issues": "${result.collect_validate_data.issues}",
                            "target": target
                        }
                    },
                    {
                        "task": "collect_examine_outcome",
                        "tools": ["analysis.text"],
                        "parameters": {
                            "enhanced_data": "${result.collect_enhance_data.enhanced_data}",
                            "target": target,
                            "examination_type": "enhanced"
                        }
                    }
                ]
            }
        ]

    def _create_comprehensive_collect_workflow(self, target: str, sources: List[str], quality_threshold: float) -> List[Dict[str, Any]]:
        """Create workflow for comprehensive collection tasks."""
        return [
            {
                "task": "collect_analyze_requirements",
                "tools": ["analysis.text"],
                "parameters": {
                    "target": target,
                    "scope": "comprehensive",
                    "available_sources": sources,
                    "quality_requirements": quality_threshold
                },
                "timeout": 45
            },
            {
                "task": "collect_create_collection_plan",
                "tools": ["analysis.text"],
                "parameters": {
                    "requirements": "${result.collect_analyze_requirements.requirements}",
                    "target": target,
                    "collection_phases": 3
                }
            },
            {
                "sequence": [
                    {
                        "task": "collect_phase_1_broad",
                        "tools": ["search.web", "search.academic"],
                        "parameters": {
                            "target": target,
                            "phase": "broad_collection",
                            "search_terms": "${result.collect_create_collection_plan.phase_1_terms}",
                            "max_results": 50
                        },
                        "timeout": 120
                    },
                    {
                        "task": "collect_analyze_phase_1",
                        "tools": ["analysis.text", "analysis.data"],
                        "parameters": {
                            "phase_1_data": "${result.collect_phase_1_broad.results}",
                            "target": target,
                            "analysis_type": "gap_identification"
                        }
                    },
                    {
                        "parallel": [
                            {
                                "task": "collect_phase_2_targeted",
                                "tools": ["search.specialized", "scraper.api"],
                                "parameters": {
                                    "target": target,
                                    "gaps": "${result.collect_analyze_phase_1.identified_gaps}",
                                    "specialized_sources": "${result.collect_analyze_phase_1.recommended_sources}"
                                }
                            },
                            {
                                "task": "collect_phase_2_deep_scrape",
                                "tools": ["scraper.web", "scraper.social"],
                                "parameters": {
                                    "target": target,
                                    "deep_sources": "${result.collect_analyze_phase_1.deep_sources}",
                                    "scrape_depth": "comprehensive"
                                }
                            }
                        ],
                        "max_concurrency": 2,
                        "wait_for_all": True
                    },
                    {
                        "task": "collect_phase_3_validation",
                        "tools": ["analysis.text", "analysis.data", "validator.credibility"],
                        "parameters": {
                            "all_collected_data": {
                                "phase_1": "${result.collect_phase_1_broad.results}",
                                "phase_2_targeted": "${result.collect_phase_2_targeted.results}",
                                "phase_2_scraped": "${result.collect_phase_2_deep_scrape.data}"
                            },
                            "target": target,
                            "validation_level": "comprehensive"
                        },
                        "timeout": 90
                    }
                ]
            },
            {
                "task": "collect_synthesize_comprehensive",
                "tools": ["analysis.text", "analysis.data"],
                "parameters": {
                    "validated_data": "${result.collect_phase_3_validation.validated_data}",
                    "target": target,
                    "synthesis_strategy": "comprehensive",
                    "include_metadata": True
                },
                "timeout": 60
            },
            {
                "parallel": [
                    {
                        "task": "collect_quality_assessment",
                        "tools": ["analysis.text", "validator.credibility"],
                        "parameters": {
                            "synthesized_data": "${result.collect_synthesize_comprehensive.synthesis}",
                            "quality_criteria": {
                                "credibility": quality_threshold,
                                "completeness": 0.9,
                                "relevance": 0.85,
                                "currency": 0.8
                            }
                        }
                    },
                    {
                        "task": "collect_coverage_analysis",
                        "tools": ["analysis.data"],
                        "parameters": {
                            "synthesized_data": "${result.collect_synthesize_comprehensive.synthesis}",
                            "target": target,
                            "coverage_requirements": "${result.collect_analyze_requirements.coverage_requirements}"
                        }
                    }
                ],
                "wait_for_all": True
            },
            {
                "if": "result.collect_quality_assessment.overall_score >= 0.8 and result.collect_coverage_analysis.coverage_score >= 0.85",
                "then": [
                    {
                        "task": "collect_examine_outcome",
                        "tools": ["analysis.text"],
                        "parameters": {
                            "comprehensive_data": "${result.collect_synthesize_comprehensive.synthesis}",
                            "quality_assessment": "${result.collect_quality_assessment}",
                            "coverage_analysis": "${result.collect_coverage_analysis}",
                            "target": target,
                            "examination_type": "comprehensive_success"
                        }
                    }
                ],
                "else": [
                    {
                        "task": "collect_identify_deficiencies",
                        "tools": ["analysis.text"],
                        "parameters": {
                            "quality_results": "${result.collect_quality_assessment}",
                            "coverage_results": "${result.collect_coverage_analysis}",
                            "target": target
                        }
                    },
                    {
                        "task": "collect_remedial_collection",
                        "tools": ["search.expert", "scraper.specialized"],
                        "parameters": {
                            "deficiencies": "${result.collect_identify_deficiencies.deficiencies}",
                            "target": target,
                            "remedial_strategy": "targeted"
                        }
                    },
                    {
                        "task": "collect_examine_outcome",
                        "tools": ["analysis.text"],
                        "parameters": {
                            "final_data": "${result.collect_remedial_collection.enhanced_data}",
                            "remedial_results": "${result.collect_remedial_collection}",
                            "target": target,
                            "examination_type": "comprehensive_remediated"
                        }
                    }
                ]
            }
        ]

    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data for collect workflow.

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

        # Validate collection target
        target = input_data.get("text", "").strip()
        if not target:
            self.logger.error("Collection target is empty")
            return False

        if len(target) < 2:
            self.logger.error("Collection target is too short")
            return False

        # Validate sources if provided
        sources = input_data.get("sources", ["web", "academic"])
        valid_sources = ["web", "academic", "scrape", "social", "specialized", "expert"]

        for source in sources:
            if source not in valid_sources:
                self.logger.warning(f"Unknown source: {source}, removing from list")
                sources.remove(source)

        if not sources:
            self.logger.warning("No valid sources specified, using default: ['web', 'academic']")
            input_data["sources"] = ["web", "academic"]

        # Validate quality threshold
        quality_threshold = input_data.get("quality_threshold", 0.7)
        if not isinstance(quality_threshold, (int, float)) or quality_threshold < 0 or quality_threshold > 1:
            self.logger.warning(f"Invalid quality threshold: {quality_threshold}, using default: 0.7")
            input_data["quality_threshold"] = 0.7

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
            # Extract the collected data from the workflow results
            workflow_results = result.result

            # Find the examination outcome
            examination_result = None
            collected_data = None

            if isinstance(workflow_results, list):
                for step_result in reversed(workflow_results):
                    if isinstance(step_result, dict):
                        if "examine_outcome" in str(step_result):
                            examination_result = step_result
                        if "collected_data" in str(step_result) or "synthesized_data" in str(step_result):
                            collected_data = step_result

            # Format the final result
            formatted_result = {
                "collected_data": collected_data.get("data") if collected_data else [],
                "examination_results": examination_result if examination_result else {},
                "credibility_score": examination_result.get("credibility", 0.0) if examination_result else 0.0,
                "confidence_score": examination_result.get("confidence", 0.0) if examination_result else 0.0,
                "data_quality": examination_result.get("quality_metrics", {}) if examination_result else {},
                "sources_used": input_data.get("sources", []),
                "collection_target": input_data.get("text", ""),
                "workflow_metadata": {
                    "execution_time": result.metadata.get("total_duration"),
                    "steps_completed": result.metadata.get("completed_nodes", 0),
                    "examination_passed": examination_result.get("passed", False) if examination_result else False,
                    "scope": input_data.get("scope", "standard")
                }
            }

            result.result = formatted_result

        return result

    def _estimate_duration(self, workflow_steps: List[Dict[str, Any]]) -> float:
        """Estimate workflow execution duration in seconds."""
        base_duration = 60.0  # Base duration for collection tasks

        # Count different types of operations
        search_operations = 0
        scrape_operations = 0
        analysis_operations = 0
        parallel_blocks = 0
        validation_operations = 0

        def count_operations(steps):
            nonlocal search_operations, scrape_operations, analysis_operations, parallel_blocks, validation_operations

            for step in steps:
                if isinstance(step, dict):
                    if "task" in step:
                        tools = step.get("tools", [])
                        if any("search" in tool for tool in tools):
                            search_operations += 1
                        if any("scraper" in tool or "scrape" in tool for tool in tools):
                            scrape_operations += 1
                        if any("analysis" in tool for tool in tools):
                            analysis_operations += 1
                        if any("validator" in tool or "validate" in tool for tool in tools):
                            validation_operations += 1
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
        estimated += search_operations * 20  # 20 seconds per search
        estimated += scrape_operations * 45  # 45 seconds per scrape operation
        estimated += analysis_operations * 30  # 30 seconds per analysis
        estimated += validation_operations * 25  # 25 seconds per validation
        estimated += parallel_blocks * 15  # 15 seconds overhead per parallel block

        return estimated
