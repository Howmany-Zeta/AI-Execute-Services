"""
Answer Workflow Template

Workflow template for answer-type tasks that provide direct responses to user queries.
Focuses on information retrieval, analysis, and response generation.
"""

from typing import Dict, List, Any, Optional
from ..base_workflow import BaseWorkflow
from ..dsl import DSLNode, DSLNodeType
from ...core.models.execution_models import WorkflowExecution, ExecutionResult


class AnswerWorkflow(BaseWorkflow):
    """
    Workflow template for answer-type tasks.

    Typical flow:
    1. Parse user query and identify information needs
    2. Search for relevant information (parallel searches if needed)
    3. Analyze and synthesize information
    4. Generate comprehensive answer
    5. Validate answer quality and completeness
    """

    def __init__(self):
        """Initialize the answer workflow."""
        super().__init__()
        self.workflow_type = "answer"
        self.description = "Workflow for providing direct answers to user queries"

    async def create_workflow_definition(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create workflow definition for answer tasks.

        Args:
            input_data: Input data containing user query and context

        Returns:
            Workflow definition with DSL steps
        """
        user_query = input_data.get("text", "")
        domain = input_data.get("domain", "general")
        complexity = input_data.get("complexity", "medium")

        # Determine search strategy based on query complexity
        if complexity == "simple":
            workflow_steps = self._create_simple_answer_workflow(user_query, domain)
        elif complexity == "complex":
            workflow_steps = self._create_complex_answer_workflow(user_query, domain)
        else:
            workflow_steps = self._create_standard_answer_workflow(user_query, domain)

        return {
            "id": f"answer_workflow_{self._generate_workflow_id()}",
            "type": "answer",
            "description": f"Answer workflow for: {user_query[:100]}...",
            "steps": workflow_steps,
            "metadata": {
                "domain": domain,
                "complexity": complexity,
                "estimated_duration": self._estimate_duration(workflow_steps)
            }
        }

    def _create_simple_answer_workflow(self, query: str, domain: str) -> List[Dict[str, Any]]:
        """Create workflow for simple answer tasks."""
        return [
            {
                "task": "answer_direct",
                "tools": ["search.web"],
                "parameters": {
                    "query": query,
                    "domain": domain,
                    "max_results": 5
                },
                "timeout": 30
            },
            {
                "if": "result.answer_direct.confidence < 0.8",
                "then": [
                    {
                        "task": "answer_enhance",
                        "tools": ["search.academic", "analysis.text"],
                        "parameters": {
                            "original_query": query,
                            "initial_result": "${result.answer_direct.result}",
                            "domain": domain
                        }
                    }
                ],
                "else": [
                    {
                        "task": "answer_validate",
                        "tools": ["analysis.text"],
                        "parameters": {
                            "answer": "${result.answer_direct.result}",
                            "query": query
                        }
                    }
                ]
            }
        ]

    def _create_standard_answer_workflow(self, query: str, domain: str) -> List[Dict[str, Any]]:
        """Create workflow for standard answer tasks."""
        return [
            {
                "task": "answer_parse_query",
                "tools": ["analysis.text"],
                "parameters": {
                    "query": query,
                    "domain": domain
                },
                "timeout": 15
            },
            {
                "parallel": [
                    {
                        "task": "answer_search_web",
                        "tools": ["search.web"],
                        "parameters": {
                            "query": "${result.answer_parse_query.search_terms}",
                            "domain": domain,
                            "max_results": 10
                        }
                    },
                    {
                        "task": "answer_search_academic",
                        "tools": ["search.academic"],
                        "parameters": {
                            "query": "${result.answer_parse_query.academic_terms}",
                            "domain": domain,
                            "max_results": 5
                        }
                    }
                ],
                "max_concurrency": 2,
                "wait_for_all": True
            },
            {
                "task": "answer_synthesize",
                "tools": ["analysis.text", "analysis.data"],
                "parameters": {
                    "web_results": "${result.answer_search_web.results}",
                    "academic_results": "${result.answer_search_academic.results}",
                    "original_query": query,
                    "domain": domain
                },
                "timeout": 60
            },
            {
                "task": "answer_generate",
                "tools": ["analysis.text"],
                "parameters": {
                    "synthesized_info": "${result.answer_synthesize.synthesis}",
                    "query": query,
                    "domain": domain,
                    "format": "comprehensive"
                },
                "timeout": 45
            },
            {
                "task": "answer_validate",
                "tools": ["analysis.text"],
                "parameters": {
                    "answer": "${result.answer_generate.answer}",
                    "query": query,
                    "sources": "${result.answer_synthesize.sources}"
                },
                "conditions": [
                    "result.answer_generate.completed == true"
                ]
            }
        ]

    def _create_complex_answer_workflow(self, query: str, domain: str) -> List[Dict[str, Any]]:
        """Create workflow for complex answer tasks."""
        return [
            {
                "task": "answer_decompose_query",
                "tools": ["analysis.text"],
                "parameters": {
                    "query": query,
                    "domain": domain,
                    "complexity": "high"
                },
                "timeout": 30
            },
            {
                "task": "answer_plan_research",
                "tools": ["analysis.text"],
                "parameters": {
                    "sub_queries": "${result.answer_decompose_query.sub_queries}",
                    "domain": domain,
                    "research_depth": "deep"
                }
            },
            {
                "loop": {
                    "condition": "context.current_sub_query_index < result.answer_plan_research.sub_query_count",
                    "max_iterations": 5,
                    "body": [
                        {
                            "parallel": [
                                {
                                    "task": "answer_research_web",
                                    "tools": ["search.web"],
                                    "parameters": {
                                        "query": "${result.answer_plan_research.sub_queries[context.current_sub_query_index]}",
                                        "domain": domain,
                                        "depth": "deep"
                                    }
                                },
                                {
                                    "task": "answer_research_academic",
                                    "tools": ["search.academic"],
                                    "parameters": {
                                        "query": "${result.answer_plan_research.sub_queries[context.current_sub_query_index]}",
                                        "domain": domain,
                                        "depth": "deep"
                                    }
                                },
                                {
                                    "task": "answer_research_specialized",
                                    "tools": ["search.specialized"],
                                    "parameters": {
                                        "query": "${result.answer_plan_research.sub_queries[context.current_sub_query_index]}",
                                        "domain": domain,
                                        "sources": "expert"
                                    }
                                }
                            ],
                            "max_concurrency": 3
                        },
                        {
                            "task": "answer_analyze_sub_results",
                            "tools": ["analysis.text", "analysis.data"],
                            "parameters": {
                                "web_results": "${result.answer_research_web.results}",
                                "academic_results": "${result.answer_research_academic.results}",
                                "specialized_results": "${result.answer_research_specialized.results}",
                                "sub_query": "${result.answer_plan_research.sub_queries[context.current_sub_query_index]}"
                            }
                        }
                    ]
                }
            },
            {
                "task": "answer_integrate_findings",
                "tools": ["analysis.text", "analysis.data"],
                "parameters": {
                    "all_sub_results": "${result.answer_analyze_sub_results}",
                    "original_query": query,
                    "domain": domain,
                    "integration_strategy": "comprehensive"
                },
                "timeout": 90
            },
            {
                "task": "answer_generate_comprehensive",
                "tools": ["analysis.text"],
                "parameters": {
                    "integrated_findings": "${result.answer_integrate_findings.integration}",
                    "query": query,
                    "domain": domain,
                    "format": "detailed",
                    "include_sources": True
                },
                "timeout": 60
            },
            {
                "parallel": [
                    {
                        "task": "answer_validate_accuracy",
                        "tools": ["analysis.text"],
                        "parameters": {
                            "answer": "${result.answer_generate_comprehensive.answer}",
                            "sources": "${result.answer_integrate_findings.sources}",
                            "validation_type": "accuracy"
                        }
                    },
                    {
                        "task": "answer_validate_completeness",
                        "tools": ["analysis.text"],
                        "parameters": {
                            "answer": "${result.answer_generate_comprehensive.answer}",
                            "original_query": query,
                            "validation_type": "completeness"
                        }
                    }
                ],
                "wait_for_all": True
            },
            {
                "if": "result.answer_validate_accuracy.passed == true and result.answer_validate_completeness.passed == true",
                "then": [
                    {
                        "task": "answer_finalize",
                        "tools": ["analysis.text"],
                        "parameters": {
                            "answer": "${result.answer_generate_comprehensive.answer}",
                            "validation_results": {
                                "accuracy": "${result.answer_validate_accuracy}",
                                "completeness": "${result.answer_validate_completeness}"
                            }
                        }
                    }
                ],
                "else": [
                    {
                        "task": "answer_refine",
                        "tools": ["analysis.text"],
                        "parameters": {
                            "answer": "${result.answer_generate_comprehensive.answer}",
                            "validation_issues": {
                                "accuracy": "${result.answer_validate_accuracy}",
                                "completeness": "${result.answer_validate_completeness}"
                            },
                            "original_query": query
                        }
                    }
                ]
            }
        ]

    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data for answer workflow.

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

        # Validate query content
        query = input_data.get("text", "").strip()
        if not query:
            self.logger.error("Query text is empty")
            return False

        if len(query) < 3:
            self.logger.error("Query text is too short")
            return False

        # Validate domain if provided
        domain = input_data.get("domain")
        if domain and domain not in ["general", "science", "technology", "business", "health", "education"]:
            self.logger.warning(f"Unknown domain: {domain}, using 'general'")
            input_data["domain"] = "general"

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
            # Extract the final answer from the workflow results
            workflow_results = result.result

            # Find the final answer task result
            final_answer = None
            if isinstance(workflow_results, list):
                for step_result in reversed(workflow_results):
                    if isinstance(step_result, dict) and "answer" in str(step_result):
                        final_answer = step_result
                        break

            # Format the final result
            formatted_result = {
                "answer": final_answer.get("answer") if final_answer else "No answer generated",
                "confidence": final_answer.get("confidence", 0.0) if final_answer else 0.0,
                "sources": final_answer.get("sources", []) if final_answer else [],
                "domain": input_data.get("domain", "general"),
                "query": input_data.get("text", ""),
                "workflow_metadata": {
                    "execution_time": result.metadata.get("total_duration"),
                    "steps_completed": result.metadata.get("completed_nodes", 0),
                    "validation_passed": final_answer.get("validation_passed", False) if final_answer else False
                }
            }

            result.result = formatted_result

        return result

    def _estimate_duration(self, workflow_steps: List[Dict[str, Any]]) -> float:
        """Estimate workflow execution duration in seconds."""
        base_duration = 30.0  # Base duration for simple tasks

        # Count different types of operations
        search_operations = 0
        analysis_operations = 0
        parallel_blocks = 0
        loops = 0

        def count_operations(steps):
            nonlocal search_operations, analysis_operations, parallel_blocks, loops

            for step in steps:
                if isinstance(step, dict):
                    if "task" in step:
                        tools = step.get("tools", [])
                        if any("search" in tool for tool in tools):
                            search_operations += 1
                        if any("analysis" in tool for tool in tools):
                            analysis_operations += 1
                    elif "parallel" in step:
                        parallel_blocks += 1
                        count_operations(step["parallel"])
                    elif "loop" in step:
                        loops += 1
                        count_operations(step["loop"].get("body", []))
                    elif "if" in step:
                        count_operations(step.get("then", []))
                        count_operations(step.get("else", []))

        count_operations(workflow_steps)

        # Calculate estimated duration
        estimated = base_duration
        estimated += search_operations * 15  # 15 seconds per search
        estimated += analysis_operations * 20  # 20 seconds per analysis
        estimated += parallel_blocks * 10  # 10 seconds overhead per parallel block
        estimated += loops * 30  # 30 seconds per loop iteration (average)

        return estimated
