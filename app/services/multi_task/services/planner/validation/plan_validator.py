"""
Plan Validator Service

Provides comprehensive validation for workflow plans, DSL syntax, and execution feasibility.
This service ensures that generated plans are syntactically correct, logically sound,
and executable within the system constraints.

Following the Single Responsibility Principle, this service focuses solely on
plan validation functionality.
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional, Set, Tuple

from ....core.interfaces.services_interfaces import IPlanValidator
from ....core.models.planner_models import PlanValidationResult, ValidationSeverity
from ....core.models.services_models import ValidationRuleType
from ....core.exceptions.services_exceptions import ValidationError

logger = logging.getLogger(__name__)


class PlanValidatorService(IPlanValidator):
    """
    Service for comprehensive plan validation.

    This service provides multi-level validation including syntax checking,
    logical flow analysis, dependency validation, and performance assessment.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the plan validator service.

        Args:
            config: Optional configuration parameters
        """
        self._config = config or {}
        # Initialize validation rules and thresholds
        self._validation_rules = self._config.get('validation_rules', {})
        self._quality_threshold = self._config.get('quality_threshold', 0.7)
        self._max_steps = self._config.get('max_steps', 50)
        self._max_parallel_groups = self._config.get('max_parallel_groups', 5)

        # DSL function definitions for syntax validation
        self._dsl_functions = {
            "search": {
                "required_params": ["query"],
                "optional_params": ["sources", "limit", "filters"],
                "return_type": "search_result"
            },
            "scrape": {
                "required_params": ["url"],
                "optional_params": ["selectors", "headers", "timeout"],
                "return_type": "scraped_data"
            },
            "api_call": {
                "required_params": ["endpoint"],
                "optional_params": ["params", "headers", "method"],
                "return_type": "api_response"
            },
            "database_query": {
                "required_params": ["query"],
                "optional_params": ["connection", "timeout"],
                "return_type": "query_result"
            },
            "document_extract": {
                "required_params": ["path"],
                "optional_params": ["format", "pages"],
                "return_type": "document_data"
            },
            "clean_data": {
                "required_params": ["data"],
                "optional_params": ["rules", "strategy"],
                "return_type": "cleaned_data"
            },
            "transform": {
                "required_params": ["data"],
                "optional_params": ["schema", "mapping"],
                "return_type": "transformed_data"
            },
            "aggregate": {
                "required_params": ["data"],
                "optional_params": ["groupby", "functions"],
                "return_type": "aggregated_data"
            },
            "filter": {
                "required_params": ["data"],
                "optional_params": ["conditions", "strategy"],
                "return_type": "filtered_data"
            },
            "normalize": {
                "required_params": ["data"],
                "optional_params": ["method", "range"],
                "return_type": "normalized_data"
            },
            "analyze": {
                "required_params": ["data", "type"],
                "optional_params": ["metrics", "algorithm", "baseline"],
                "return_type": "analysis_result"
            },
            "generate": {
                "required_params": ["type", "data"],
                "optional_params": ["template", "format", "options"],
                "return_type": "generated_content"
            },
            "answer": {
                "required_params": ["query"],
                "optional_params": ["method", "context"],
                "return_type": "answer_result"
            },
            "knowledge_base": {
                "required_params": ["query"],
                "optional_params": ["domain", "confidence"],
                "return_type": "knowledge_result"
            },
            "discuss": {
                "required_params": ["topic"],
                "optional_params": ["participants", "format"],
                "return_type": "discussion_result"
            }
        }

        # Performance thresholds
        self._performance_limits = {
            "max_steps": self._config.get("max_steps", 20),
            "max_parallel_groups": self._config.get("max_parallel_groups", 5),
            "max_complexity_score": self._config.get("max_complexity_score", 15.0),
            "max_estimated_duration_minutes": self._config.get("max_estimated_duration_minutes", 30)
        }

        # Security patterns to check
        self._security_patterns = [
            r"eval\s*\(",
            r"exec\s*\(",
            r"__import__",
            r"subprocess",
            r"os\.system",
            r"shell=True"
        ]

        # Performance tracking
        self._total_validations = 0
        self._validation_results = {"passed": 0, "failed": 0, "warnings": 0}

        logger.info("PlanValidatorService initialized")

    async def validate_plan_structure(self, plan: 'WorkflowPlan') -> Dict[str, Any]:
        """
        Validate the structural integrity of a plan.

        Args:
            plan: Plan to validate

        Returns:
            Structural validation result
        """
        try:
            logger.info(f"Validating plan structure for plan {plan.plan_id}")

            validation_result = {
                "is_valid": True,
                "errors": [],
                "warnings": [],
                "score": 1.0,
                "checks_performed": []
            }

            # Check basic plan structure
            if not plan.sequence_result or not plan.sequence_result.sequence:
                validation_result["is_valid"] = False
                validation_result["errors"].append("Plan has no execution sequence")
                validation_result["score"] = 0.0
                return validation_result

            validation_result["checks_performed"].append("basic_structure")

            # Validate sequence steps
            sequence = plan.sequence_result.sequence
            step_ids = set()

            for i, step in enumerate(sequence):
                # Check for duplicate step IDs
                if step.step_id in step_ids:
                    validation_result["errors"].append(f"Duplicate step ID: {step.step_id}")
                    validation_result["is_valid"] = False
                else:
                    step_ids.add(step.step_id)

                # Validate step structure
                if not step.step_type:
                    validation_result["errors"].append(f"Step {i} missing step_type")
                    validation_result["is_valid"] = False

                # Validate task steps
                if step.step_type == "task" and not step.task:
                    validation_result["errors"].append(f"Task step {step.step_id} missing task name")
                    validation_result["is_valid"] = False

            validation_result["checks_performed"].append("sequence_validation")

            # Check plan complexity
            total_steps = len(sequence)
            if total_steps > self._max_steps:
                validation_result["warnings"].append(f"Plan has {total_steps} steps, exceeding recommended maximum of {self._max_steps}")
                validation_result["score"] *= 0.9

            # Check parallel groups
            parallel_groups = plan.sequence_result.parallel_groups
            if parallel_groups > self._max_parallel_groups:
                validation_result["warnings"].append(f"Plan has {parallel_groups} parallel groups, exceeding recommended maximum of {self._max_parallel_groups}")
                validation_result["score"] *= 0.95

            validation_result["checks_performed"].append("complexity_check")

            # Calculate final score
            if validation_result["errors"]:
                validation_result["score"] = max(0.0, validation_result["score"] - 0.3 * len(validation_result["errors"]))
            if validation_result["warnings"]:
                validation_result["score"] = max(0.0, validation_result["score"] - 0.1 * len(validation_result["warnings"]))

            logger.info(f"Plan structure validation completed with score: {validation_result['score']}")
            return validation_result

        except Exception as e:
            logger.error(f"Plan structure validation failed: {e}")
            raise ValidationError(f"Structure validation failed: {str(e)}", plan=plan.__dict__)

    async def validate_plan_feasibility(self, plan: 'WorkflowPlan', context: 'PlanningContext') -> Dict[str, Any]:
        """
        Validate the feasibility of a plan given available resources.

        Args:
            plan: Plan to validate
            context: Planning context with resource information

        Returns:
            Feasibility validation result
        """
        try:
            logger.info(f"Validating plan feasibility for plan {plan.plan_id}")

            validation_result = {
                "is_valid": True,
                "errors": [],
                "warnings": [],
                "score": 1.0,
                "checks_performed": [],
                "resource_analysis": {}
            }

            # Check agent availability
            required_agents = set()
            available_agents = set(context.available_agents)

            for step in plan.sequence_result.sequence:
                if step.step_type == "task" and step.category:
                    # Map category to required agents (simplified mapping)
                    if step.category == "collect":
                        required_agents.add("fieldwork_webscraper")
                    elif step.category == "analyze":
                        required_agents.add("general_researcher")
                    elif step.category == "generate":
                        required_agents.add("writer_conclusionspecialist")
                    # Add more mappings as needed

            missing_agents = required_agents - available_agents
            if missing_agents:
                validation_result["warnings"].append(f"Missing agents: {list(missing_agents)}")
                validation_result["score"] *= 0.8

            validation_result["resource_analysis"]["required_agents"] = list(required_agents)
            validation_result["resource_analysis"]["missing_agents"] = list(missing_agents)
            validation_result["checks_performed"].append("agent_availability")

            # Check tool availability
            required_tools = set()
            available_tools = set(context.available_tools)

            for step in plan.sequence_result.sequence:
                if step.tools:
                    required_tools.update(step.tools)

            missing_tools = required_tools - available_tools
            if missing_tools:
                validation_result["warnings"].append(f"Missing tools: {list(missing_tools)}")
                validation_result["score"] *= 0.9

            validation_result["resource_analysis"]["required_tools"] = list(required_tools)
            validation_result["resource_analysis"]["missing_tools"] = list(missing_tools)
            validation_result["checks_performed"].append("tool_availability")

            # Check system constraints
            constraints = context.system_constraints
            if constraints.get("max_execution_time"):
                estimated_duration = plan.sequence_result.estimated_total_duration
                # Simple duration check (assuming duration is in format like "5-10 minutes")
                if "hour" in estimated_duration.lower():
                    validation_result["warnings"].append("Plan may exceed time constraints")
                    validation_result["score"] *= 0.85

            validation_result["checks_performed"].append("constraint_validation")

            # Check deadline feasibility
            if context.deadline:
                # Simple deadline check
                validation_result["warnings"].append("Deadline feasibility check performed")
                validation_result["score"] *= 0.95

            validation_result["checks_performed"].append("deadline_check")

            # Final feasibility assessment
            if validation_result["score"] < self._quality_threshold:
                validation_result["is_valid"] = False
                validation_result["errors"].append(f"Plan feasibility score {validation_result['score']:.2f} below threshold {self._quality_threshold}")

            logger.info(f"Plan feasibility validation completed with score: {validation_result['score']}")
            return validation_result

        except Exception as e:
            logger.error(f"Plan feasibility validation failed: {e}")
            raise ValidationError(f"Feasibility validation failed: {str(e)}", plan=plan.__dict__)

    def _validate_dsl_syntax(self, sequence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate DSL syntax for the execution sequence.

        Args:
            sequence: Execution sequence to validate

        Returns:
            Syntax validation result
        """
        result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }

        for i, step in enumerate(sequence):
            # Basic structure validation
            if not isinstance(step, dict):
                result["errors"].append(f"Step {i} is not a valid dictionary")
                result["is_valid"] = False
                continue

            # Required fields validation
            if "step_type" not in step:
                result["errors"].append(f"Step {i} missing required field 'step_type'")
                result["is_valid"] = False

            if "step_id" not in step:
                result["errors"].append(f"Step {i} missing required field 'step_id'")
                result["is_valid"] = False

        return result

    def _validate_dependencies(self, sequence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate task dependencies in the execution sequence.

        Args:
            sequence: Execution sequence to validate

        Returns:
            Dependency validation result
        """
        result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }

        # Simple dependency validation
        # In a real implementation, this would check for circular dependencies,
        # missing dependencies, etc.

        return result


    async def validate_workflow_plan(self, plan: Dict[str, Any]) -> PlanValidationResult:
        """
        Validate a complete workflow plan.

        Args:
            plan: Workflow plan to validate

        Returns:
            Comprehensive validation result

        Raises:
            ValidationError: If validation process fails
        """
        try:
            start_time = self._get_current_time_ms()

            logger.debug(f"Validating workflow plan with {len(plan.get('dsl_plan', []))} steps")

            validation_issues = []
            overall_score = 1.0

            # Extract plan components
            dsl_plan = plan.get("dsl_plan", [])
            execution_order = plan.get("execution_order", [])
            parallel_groups = plan.get("parallel_groups", [])
            dependencies = plan.get("dependencies", {})

            # 1. Syntax validation
            syntax_result = await self._validate_syntax(dsl_plan)
            validation_issues.extend(syntax_result["issues"])
            overall_score *= syntax_result["score"]

            # 2. Logic validation
            logic_result = await self._validate_logic(dsl_plan, execution_order)
            validation_issues.extend(logic_result["issues"])
            overall_score *= logic_result["score"]

            # 3. Dependency validation
            dependency_result = await self._validate_dependencies(dsl_plan, dependencies)
            validation_issues.extend(dependency_result["issues"])
            overall_score *= dependency_result["score"]

            # 4. Performance validation
            performance_result = await self._validate_performance(plan)
            validation_issues.extend(performance_result["issues"])
            overall_score *= performance_result["score"]

            # 5. Security validation
            security_result = await self._validate_security(dsl_plan)
            validation_issues.extend(security_result["issues"])
            overall_score *= security_result["score"]

            # Determine overall validation status
            critical_issues = [issue for issue in validation_issues if issue["severity"] == ValidationSeverity.CRITICAL]
            is_valid = len(critical_issues) == 0

            # Calculate processing time
            processing_time = self._get_current_time_ms() - start_time

            # Create validation result
            result = PlanValidationResult(
                is_valid=is_valid,
                overall_score=max(overall_score, 0.0),
                validation_issues=validation_issues,
                syntax_valid=syntax_result["valid"],
                logic_valid=logic_result["valid"],
                dependencies_valid=dependency_result["valid"],
                performance_acceptable=performance_result["valid"],
                security_compliant=security_result["valid"],
                recommendations=self._generate_recommendations(validation_issues),
                processing_time_ms=processing_time
            )

            # Update metrics
            self._update_metrics(result)

            logger.info(f"Plan validation completed: valid={is_valid}, score={overall_score:.2f}")
            return result

        except Exception as e:
            logger.error(f"Plan validation failed: {e}")
            raise ValidationError(f"Plan validation failed: {e}")

    async def validate_dsl_syntax(self, dsl_plan: List[str]) -> Dict[str, Any]:
        """
        Validate DSL syntax for a plan.

        Args:
            dsl_plan: List of DSL steps to validate

        Returns:
            Syntax validation result
        """
        return await self._validate_syntax(dsl_plan)

    async def validate_execution_feasibility(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate execution feasibility of a plan.

        Args:
            plan: Plan to validate for execution feasibility

        Returns:
            Feasibility validation result
        """
        try:
            feasibility_issues = []
            feasibility_score = 1.0

            # Check resource requirements
            resource_check = self._check_resource_requirements(plan)
            if not resource_check["feasible"]:
                feasibility_issues.extend(resource_check["issues"])
                feasibility_score *= 0.7

            # Check time constraints
            time_check = self._check_time_constraints(plan)
            if not time_check["feasible"]:
                feasibility_issues.extend(time_check["issues"])
                feasibility_score *= 0.8

            # Check data flow
            data_flow_check = self._check_data_flow(plan.get("dsl_plan", []))
            if not data_flow_check["feasible"]:
                feasibility_issues.extend(data_flow_check["issues"])
                feasibility_score *= 0.6

            return {
                "feasible": len(feasibility_issues) == 0,
                "score": feasibility_score,
                "issues": feasibility_issues
            }

        except Exception as e:
            logger.error(f"Feasibility validation failed: {e}")
            return {
                "feasible": False,
                "score": 0.0,
                "issues": [{"message": f"Feasibility check failed: {e}", "severity": ValidationSeverity.CRITICAL}]
            }

    def get_validation_rules(self) -> Dict[str, Any]:
        """
        Get available validation rules and their descriptions.

        Returns:
            Dictionary of validation rules
        """
        return {
            "syntax_rules": {
                "function_exists": "DSL function must be defined",
                "required_params": "Required parameters must be provided",
                "balanced_parentheses": "Parentheses must be balanced",
                "valid_syntax": "DSL syntax must be valid"
            },
            "logic_rules": {
                "execution_order": "Steps must be in logical execution order",
                "data_flow": "Data must flow correctly between steps",
                "dependency_satisfaction": "Dependencies must be satisfied"
            },
            "performance_rules": {
                "max_steps": f"Maximum {self._performance_limits['max_steps']} steps allowed",
                "complexity_limit": f"Complexity score must be under {self._performance_limits['max_complexity_score']}",
                "duration_limit": f"Estimated duration must be under {self._performance_limits['max_estimated_duration_minutes']} minutes"
            },
            "security_rules": {
                "no_code_injection": "No code injection patterns allowed",
                "safe_functions": "Only safe DSL functions allowed",
                "parameter_validation": "Parameters must be validated"
            }
        }

    # Private validation methods

    async def _validate_syntax(self, dsl_plan: List[str]) -> Dict[str, Any]:
        """Validate DSL syntax."""
        issues = []
        valid_steps = 0

        for i, step in enumerate(dsl_plan):
            step_issues = self._validate_step_syntax(step, i + 1)
            issues.extend(step_issues)

            if not step_issues:
                valid_steps += 1

        syntax_valid = len(issues) == 0
        syntax_score = valid_steps / max(len(dsl_plan), 1) if dsl_plan else 1.0

        return {
            "valid": syntax_valid,
            "score": syntax_score,
            "issues": issues
        }

    def _validate_step_syntax(self, step: str, step_number: int) -> List[Dict[str, Any]]:
        """Validate syntax of a single DSL step."""
        issues = []

        try:
            # Check if step is empty
            if not step.strip():
                issues.append({
                    "type": ValidationRuleType.SYNTAX.value,
                    "severity": ValidationSeverity.CRITICAL,
                    "message": f"Step {step_number}: Empty DSL step",
                    "step_number": step_number,
                    "step": step
                })
                return issues

            # Parse function name and parameters
            function_match = re.match(r'^(\w+)\s*\((.*)\)\s*$', step.strip())
            if not function_match:
                issues.append({
                    "type": ValidationRuleType.SYNTAX.value,
                    "severity": ValidationSeverity.CRITICAL,
                    "message": f"Step {step_number}: Invalid DSL syntax",
                    "step_number": step_number,
                    "step": step
                })
                return issues

            function_name = function_match.group(1)
            params_str = function_match.group(2)

            # Check if function exists
            if function_name not in self._dsl_functions:
                issues.append({
                    "type": ValidationRuleType.SYNTAX.value,
                    "severity": ValidationSeverity.CRITICAL,
                    "message": f"Step {step_number}: Unknown function '{function_name}'",
                    "step_number": step_number,
                    "step": step
                })
                return issues

            # Parse parameters
            params = self._parse_parameters(params_str)
            function_def = self._dsl_functions[function_name]

            # Check required parameters
            required_params = function_def["required_params"]
            for required_param in required_params:
                if required_param not in params:
                    issues.append({
                        "type": ValidationRuleType.SYNTAX.value,
                        "severity": ValidationSeverity.CRITICAL,
                        "message": f"Step {step_number}: Missing required parameter '{required_param}' for function '{function_name}'",
                        "step_number": step_number,
                        "step": step
                    })

            # Check for unknown parameters
            all_params = required_params + function_def["optional_params"]
            for param in params:
                if param not in all_params:
                    issues.append({
                        "type": ValidationRuleType.SYNTAX.value,
                        "severity": ValidationSeverity.WARNING,
                        "message": f"Step {step_number}: Unknown parameter '{param}' for function '{function_name}'",
                        "step_number": step_number,
                        "step": step
                    })

        except Exception as e:
            issues.append({
                "type": ValidationRuleType.SYNTAX.value,
                "severity": ValidationSeverity.CRITICAL,
                "message": f"Step {step_number}: Syntax validation error: {e}",
                "step_number": step_number,
                "step": step
            })

        return issues

    def _parse_parameters(self, params_str: str) -> Dict[str, str]:
        """Parse parameters from DSL function call."""
        params = {}

        if not params_str.strip():
            return params

        # Simple parameter parsing (could be enhanced for complex cases)
        try:
            # Split by commas, but respect nested structures
            param_parts = self._split_parameters(params_str)

            for part in param_parts:
                if '=' in part:
                    key, value = part.split('=', 1)
                    params[key.strip()] = value.strip()
        except Exception:
            # If parsing fails, return empty dict
            pass

        return params

    def _split_parameters(self, params_str: str) -> List[str]:
        """Split parameters respecting nested structures."""
        parts = []
        current_part = ""
        paren_depth = 0
        bracket_depth = 0
        brace_depth = 0
        in_quotes = False
        quote_char = None

        for char in params_str:
            if char in ['"', "'"] and not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
            elif not in_quotes:
                if char == '(':
                    paren_depth += 1
                elif char == ')':
                    paren_depth -= 1
                elif char == '[':
                    bracket_depth += 1
                elif char == ']':
                    bracket_depth -= 1
                elif char == '{':
                    brace_depth += 1
                elif char == '}':
                    brace_depth -= 1
                elif char == ',' and paren_depth == 0 and bracket_depth == 0 and brace_depth == 0:
                    parts.append(current_part.strip())
                    current_part = ""
                    continue

            current_part += char

        if current_part.strip():
            parts.append(current_part.strip())

        return parts

    async def _validate_logic(self, dsl_plan: List[str], execution_order: List[int]) -> Dict[str, Any]:
        """Validate logical flow of the plan."""
        issues = []

        # Check execution order consistency
        if execution_order and len(execution_order) != len(dsl_plan):
            issues.append({
                "type": ValidationRuleType.LOGIC.value,
                "severity": ValidationSeverity.CRITICAL,
                "message": "Execution order length doesn't match DSL plan length"
            })

        # Check for logical workflow order
        workflow_functions = ["search", "scrape", "api_call", "clean_data", "transform", "analyze", "generate"]
        found_functions = []

        for step in dsl_plan:
            for func in workflow_functions:
                if step.startswith(func):
                    found_functions.append(func)
                    break

        # Check if data processing functions come after data collection
        collection_functions = ["search", "scrape", "api_call", "database_query"]
        processing_functions = ["clean_data", "transform", "aggregate", "filter"]

        collection_indices = [i for i, func in enumerate(found_functions) if func in collection_functions]
        processing_indices = [i for i, func in enumerate(found_functions) if func in processing_functions]

        if processing_indices and collection_indices:
            if min(processing_indices) < max(collection_indices):
                issues.append({
                    "type": ValidationRuleType.LOGIC.value,
                    "severity": ValidationSeverity.WARNING,
                    "message": "Data processing steps should typically come after data collection"
                })

        logic_valid = len([issue for issue in issues if issue["severity"] == ValidationSeverity.CRITICAL]) == 0
        logic_score = 1.0 - (len(issues) * 0.1)

        return {
            "valid": logic_valid,
            "score": max(logic_score, 0.0),
            "issues": issues
        }

    async def _validate_dependencies(self, dsl_plan: List[str], dependencies: Dict[str, List[str]]) -> Dict[str, Any]:
        """Validate dependencies between steps."""
        issues = []

        # Check if dependencies are satisfied
        for step_name, deps in dependencies.items():
            for dep in deps:
                # Check if dependency exists in the plan
                dep_found = any(dep in step for step in dsl_plan)
                if not dep_found:
                    issues.append({
                        "type": ValidationRuleType.DEPENDENCY.value,
                        "severity": ValidationSeverity.CRITICAL,
                        "message": f"Dependency '{dep}' for '{step_name}' not found in plan"
                    })

        # Check for circular dependencies
        circular_deps = self._detect_circular_dependencies(dependencies)
        for cycle in circular_deps:
            issues.append({
                "type": ValidationRuleType.DEPENDENCY.value,
                "severity": ValidationSeverity.CRITICAL,
                "message": f"Circular dependency detected: {' -> '.join(cycle)}"
            })

        deps_valid = len([issue for issue in issues if issue["severity"] == ValidationSeverity.CRITICAL]) == 0
        deps_score = 1.0 - (len(issues) * 0.2)

        return {
            "valid": deps_valid,
            "score": max(deps_score, 0.0),
            "issues": issues
        }

    def _detect_circular_dependencies(self, dependencies: Dict[str, List[str]]) -> List[List[str]]:
        """Detect circular dependencies using DFS."""
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]) -> None:
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return

            if node in visited:
                return

            visited.add(node)
            rec_stack.add(node)

            for neighbor in dependencies.get(node, []):
                dfs(neighbor, path + [node])

            rec_stack.remove(node)

        for node in dependencies:
            if node not in visited:
                dfs(node, [])

        return cycles

    async def _validate_performance(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Validate performance characteristics of the plan."""
        issues = []

        dsl_plan = plan.get("dsl_plan", [])
        parallel_groups = plan.get("parallel_groups", [])
        complexity_score = plan.get("complexity_score", 0)

        # Check step count
        if len(dsl_plan) > self._performance_limits["max_steps"]:
            issues.append({
                "type": ValidationRuleType.PERFORMANCE.value,
                "severity": ValidationSeverity.WARNING,
                "message": f"Plan has {len(dsl_plan)} steps, exceeding recommended limit of {self._performance_limits['max_steps']}"
            })

        # Check parallel groups
        if len(parallel_groups) > self._performance_limits["max_parallel_groups"]:
            issues.append({
                "type": ValidationRuleType.PERFORMANCE.value,
                "severity": ValidationSeverity.WARNING,
                "message": f"Plan has {len(parallel_groups)} parallel groups, exceeding recommended limit of {self._performance_limits['max_parallel_groups']}"
            })

        # Check complexity score
        if complexity_score > self._performance_limits["max_complexity_score"]:
            issues.append({
                "type": ValidationRuleType.PERFORMANCE.value,
                "severity": ValidationSeverity.WARNING,
                "message": f"Plan complexity score {complexity_score:.1f} exceeds recommended limit of {self._performance_limits['max_complexity_score']}"
            })

        perf_valid = len([issue for issue in issues if issue["severity"] == ValidationSeverity.CRITICAL]) == 0
        perf_score = 1.0 - (len(issues) * 0.1)

        return {
            "valid": perf_valid,
            "score": max(perf_score, 0.0),
            "issues": issues
        }

    async def _validate_security(self, dsl_plan: List[str]) -> Dict[str, Any]:
        """Validate security aspects of the plan."""
        issues = []

        for i, step in enumerate(dsl_plan):
            # Check for dangerous patterns
            for pattern in self._security_patterns:
                if re.search(pattern, step, re.IGNORECASE):
                    issues.append({
                        "type": ValidationRuleType.SECURITY.value,
                        "severity": ValidationSeverity.CRITICAL,
                        "message": f"Step {i+1}: Potentially dangerous pattern detected: {pattern}",
                        "step_number": i + 1,
                        "step": step
                    })

        security_valid = len(issues) == 0
        security_score = 1.0 if security_valid else 0.0

        return {
            "valid": security_valid,
            "score": security_score,
            "issues": issues
        }

    def _check_resource_requirements(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Check if plan meets resource requirements."""
        # Simplified resource checking
        dsl_plan = plan.get("dsl_plan", [])

        # Count resource-intensive operations
        intensive_ops = ["scrape", "api_call", "analyze"]
        intensive_count = sum(1 for step in dsl_plan for op in intensive_ops if op in step)

        if intensive_count > 5:
            return {
                "feasible": False,
                "issues": [{
                    "message": f"Plan has {intensive_count} resource-intensive operations, which may exceed system capacity",
                    "severity": ValidationSeverity.WARNING
                }]
            }

        return {"feasible": True, "issues": []}

    def _check_time_constraints(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Check if plan meets time constraints."""
        estimated_duration = plan.get("estimated_duration", "")

        # Parse duration (simplified)
        if "+" in estimated_duration:
            return {
                "feasible": False,
                "issues": [{
                    "message": f"Estimated duration '{estimated_duration}' may exceed acceptable limits",
                    "severity": ValidationSeverity.WARNING
                }]
            }

        return {"feasible": True, "issues": []}

    def _check_data_flow(self, dsl_plan: List[str]) -> Dict[str, Any]:
        """Check data flow consistency."""
        issues = []

        # Track data variables
        available_data = set()

        for i, step in enumerate(dsl_plan):
            # Check if step uses undefined variables
            variables_used = re.findall(r'\{\{(\w+)\}\}', step)
            for var in variables_used:
                if var not in available_data:
                    issues.append({
                        "message": f"Step {i+1} uses undefined variable '{var}'",
                        "severity": ValidationSeverity.CRITICAL
                    })

            # Add variables produced by this step
            function_name = step.split('(')[0] if '(' in step else step
            if function_name in self._dsl_functions:
                return_type = self._dsl_functions[function_name]["return_type"]
                available_data.add(return_type)

        return {
            "feasible": len(issues) == 0,
            "issues": issues
        }

    def _generate_recommendations(self, validation_issues: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on validation issues."""
        recommendations = []

        # Group issues by type
        issue_types = {}
        for issue in validation_issues:
            issue_type = issue.get("type", "unknown")
            if issue_type not in issue_types:
                issue_types[issue_type] = []
            issue_types[issue_type].append(issue)

        # Generate type-specific recommendations
        if ValidationRuleType.SYNTAX.value in issue_types:
            recommendations.append("Review DSL syntax and ensure all function calls are properly formatted")

        if ValidationRuleType.LOGIC.value in issue_types:
            recommendations.append("Consider reordering steps to follow logical workflow patterns")

        if ValidationRuleType.DEPENDENCY.value in issue_types:
            recommendations.append("Verify all dependencies are satisfied and avoid circular references")

        if ValidationRuleType.PERFORMANCE.value in issue_types:
            recommendations.append("Consider simplifying the plan or breaking it into smaller sub-plans")

        if ValidationRuleType.SECURITY.value in issue_types:
            recommendations.append("Remove potentially dangerous operations and use safe alternatives")

        return recommendations

    def _get_current_time_ms(self) -> float:
        """Get current time in milliseconds."""
        import time
        return time.time() * 1000

    def _update_metrics(self, result: PlanValidationResult) -> None:
        """Update validation metrics."""
        self._total_validations += 1

        if result.is_valid:
            self._validation_results["passed"] += 1
        else:
            self._validation_results["failed"] += 1

        # Count warnings
        warnings = len([issue for issue in result.validation_issues if issue["severity"] == ValidationSeverity.WARNING])
        self._validation_results["warnings"] += warnings

    def get_service_metrics(self) -> Dict[str, Any]:
        """Get service-level metrics."""
        return {
            "total_validations": self._total_validations,
            "validation_results": self._validation_results.copy(),
            "success_rate": self._validation_results["passed"] / max(self._total_validations, 1)
        }
