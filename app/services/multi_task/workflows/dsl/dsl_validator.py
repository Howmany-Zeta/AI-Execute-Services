"""
DSL Validator

Validates DSL definitions for semantic correctness, dependency resolution,
and execution feasibility.
"""

from typing import Dict, List, Set, Any, Optional, Tuple
import logging

from ...core.models.workflow_models import (
    DSLNode, DSLNodeType, ValidationSeverity, ValidationIssue, ValidationResult
)
from ...core.exceptions.execution_exceptions import ExecutionValidationError

logger = logging.getLogger(__name__)


class DSLValidator:
    """
    Validates DSL definitions for semantic correctness and execution feasibility.

    Performs the following validations:
    - Dependency resolution and cycle detection
    - Resource availability checks
    - Execution path analysis
    - Performance estimation
    - Security validation
    """

    def __init__(self):
        """Initialize the DSL validator."""
        self.logger = logger
        self._available_tasks = {}
        self._available_tools = {}
        self._resource_limits = {}

    def set_available_tasks(self, tasks: Dict[str, Dict[str, Any]]) -> None:
        """Set available tasks with their metadata."""
        self._available_tasks = tasks

    def set_available_tools(self, tools: Dict[str, Dict[str, Any]]) -> None:
        """Set available tools with their metadata."""
        self._available_tools = tools

    def set_resource_limits(self, limits: Dict[str, Any]) -> None:
        """Set resource limits for validation."""
        self._resource_limits = limits

    def validate(self, root_node: DSLNode) -> ValidationResult:
        """
        Validate a DSL tree comprehensively.

        Args:
            root_node: Root node of the DSL tree

        Returns:
            ValidationResult with validation status and issues
        """
        issues = []

        try:
            # Structural validation
            issues.extend(self._validate_structure(root_node))

            # Dependency validation
            dependency_graph = self._build_dependency_graph(root_node)
            issues.extend(self._validate_dependencies(dependency_graph))

            # Resource validation
            issues.extend(self._validate_resources(root_node))

            # Execution path validation
            execution_order = self._determine_execution_order(root_node, dependency_graph)
            issues.extend(self._validate_execution_paths(root_node, execution_order))

            # Performance validation
            estimated_duration = self._estimate_execution_duration(root_node)
            issues.extend(self._validate_performance(root_node, estimated_duration))

            # Security validation
            issues.extend(self._validate_security(root_node))

            # Determine overall validity
            has_errors = any(issue.severity == ValidationSeverity.ERROR for issue in issues)
            is_valid = not has_errors

            return ValidationResult(
                is_valid=is_valid,
                issues=issues,
                dependency_graph=dependency_graph,
                execution_order=execution_order,
                estimated_duration=estimated_duration
            )

        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Validation error: {str(e)}"
            ))
            return ValidationResult(
                is_valid=False,
                issues=issues,
                dependency_graph={},
                execution_order=[]
            )

    def _validate_structure(self, root_node: DSLNode) -> List[ValidationIssue]:
        """Validate the structural integrity of the DSL tree."""
        issues = []
        visited_ids = set()

        def validate_node(node: DSLNode, depth: int = 0) -> None:
            # Check for duplicate node IDs
            if node.node_id in visited_ids:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Duplicate node ID: {node.node_id}",
                    node_id=node.node_id
                ))
            visited_ids.add(node.node_id)

            # Check maximum depth
            if depth > 20:  # Configurable limit
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"Deep nesting detected at depth {depth}",
                    node_id=node.node_id,
                    suggestion="Consider flattening the workflow structure"
                ))

            # Validate node-specific structure
            if node.node_type == DSLNodeType.CONDITION:
                if len(node.children) == 0:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message="Condition node has no branches",
                        node_id=node.node_id
                    ))
                elif len(node.children) > 2:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message="Condition node has more than 2 branches",
                        node_id=node.node_id
                    ))

            elif node.node_type == DSLNodeType.PARALLEL:
                if len(node.children) < 2:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message="Parallel block with less than 2 children",
                        node_id=node.node_id,
                        suggestion="Consider using sequence instead"
                    ))

                max_concurrency = node.config.get("max_concurrency", len(node.children))
                if max_concurrency > len(node.children):
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message="max_concurrency exceeds number of parallel tasks",
                        node_id=node.node_id
                    ))

            elif node.node_type == DSLNodeType.LOOP:
                max_iterations = node.config.get("max_iterations", 100)
                if max_iterations > 1000:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message=f"High max_iterations: {max_iterations}",
                        node_id=node.node_id,
                        suggestion="Consider reducing max_iterations for better performance"
                    ))

                if len(node.children) == 0:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message="Loop node has no body",
                        node_id=node.node_id
                    ))

            # Recursively validate children
            for child in node.children:
                validate_node(child, depth + 1)

        validate_node(root_node)
        return issues

    def _build_dependency_graph(self, root_node: DSLNode) -> Dict[str, List[str]]:
        """Build a dependency graph from the DSL tree."""
        dependencies = {}

        def extract_dependencies(node: DSLNode) -> None:
            dependencies[node.node_id] = []

            # Extract dependencies from conditions
            if node.node_type == DSLNodeType.CONDITION:
                condition = node.config.get("condition", "")
                deps = self._extract_condition_dependencies(condition)
                dependencies[node.node_id].extend(deps)

            # Extract dependencies from task parameters
            elif node.node_type == DSLNodeType.TASK:
                parameters = node.config.get("parameters", {})
                deps = self._extract_parameter_dependencies(parameters)
                dependencies[node.node_id].extend(deps)

            # Process children
            for child in node.children:
                extract_dependencies(child)
                # Sequential dependencies
                if node.node_type == DSLNodeType.SEQUENCE:
                    if node.children.index(child) > 0:
                        prev_child = node.children[node.children.index(child) - 1]
                        dependencies[child.node_id].append(prev_child.node_id)

        extract_dependencies(root_node)
        return dependencies

    def _extract_condition_dependencies(self, condition: str) -> List[str]:
        """Extract dependencies from condition expressions."""
        dependencies = []

        # Look for result references: result.task_id.field
        import re
        result_pattern = r'result\.([a-zA-Z_][a-zA-Z0-9_]*)'
        matches = re.findall(result_pattern, condition)
        dependencies.extend(matches)

        return dependencies

    def _extract_parameter_dependencies(self, parameters: Dict[str, Any]) -> List[str]:
        """Extract dependencies from task parameters."""
        dependencies = []

        def extract_from_value(value: Any) -> None:
            if isinstance(value, str):
                # Look for ${result.task_id.field} patterns
                import re
                pattern = r'\$\{result\.([a-zA-Z_][a-zA-Z0-9_]*)'
                matches = re.findall(pattern, value)
                dependencies.extend(matches)
            elif isinstance(value, dict):
                for v in value.values():
                    extract_from_value(v)
            elif isinstance(value, list):
                for item in value:
                    extract_from_value(item)

        for value in parameters.values():
            extract_from_value(value)

        return dependencies

    def _validate_dependencies(self, dependency_graph: Dict[str, List[str]]) -> List[ValidationIssue]:
        """Validate dependencies and detect cycles."""
        issues = []

        # Check for cycles using DFS
        def has_cycle(node: str, visited: Set[str], rec_stack: Set[str]) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in dependency_graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        visited = set()
        for node in dependency_graph:
            if node not in visited:
                if has_cycle(node, visited, set()):
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Circular dependency detected involving node: {node}",
                        node_id=node
                    ))

        # Check for missing dependencies
        all_nodes = set(dependency_graph.keys())
        for node, deps in dependency_graph.items():
            for dep in deps:
                if dep not in all_nodes:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Missing dependency: {dep} required by {node}",
                        node_id=node
                    ))

        return issues

    def _validate_resources(self, root_node: DSLNode) -> List[ValidationIssue]:
        """Validate resource requirements and availability."""
        issues = []

        def validate_node_resources(node: DSLNode) -> None:
            if node.node_type == DSLNodeType.TASK:
                task_name = node.config.get("task_name")

                # Check task availability
                if task_name not in self._available_tasks:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Task not available: {task_name}",
                        node_id=node.node_id
                    ))
                else:
                    # Check task-specific requirements
                    task_info = self._available_tasks[task_name]
                    required_tools = task_info.get("required_tools", [])
                    provided_tools = node.config.get("tools", [])

                    for required_tool in required_tools:
                        if required_tool not in provided_tools:
                            issues.append(ValidationIssue(
                                severity=ValidationSeverity.WARNING,
                                message=f"Missing required tool: {required_tool} for task {task_name}",
                                node_id=node.node_id
                            ))

                # Check tool availability
                tools = node.config.get("tools", [])
                for tool in tools:
                    if tool not in self._available_tools:
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            message=f"Tool not available: {tool}",
                            node_id=node.node_id
                        ))

            # Recursively validate children
            for child in node.children:
                validate_node_resources(child)

        validate_node_resources(root_node)
        return issues

    def _determine_execution_order(self, root_node: DSLNode, dependency_graph: Dict[str, List[str]]) -> List[str]:
        """Determine the execution order using topological sort."""
        # Topological sort implementation
        in_degree = {node: 0 for node in dependency_graph}

        for node, deps in dependency_graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[node] += 1

        queue = [node for node, degree in in_degree.items() if degree == 0]
        execution_order = []

        while queue:
            current = queue.pop(0)
            execution_order.append(current)

            for node, deps in dependency_graph.items():
                if current in deps:
                    in_degree[node] -= 1
                    if in_degree[node] == 0:
                        queue.append(node)

        return execution_order

    def _validate_execution_paths(self, root_node: DSLNode, execution_order: List[str]) -> List[ValidationIssue]:
        """Validate execution paths and reachability."""
        issues = []

        # Check for unreachable nodes
        reachable_nodes = set()

        def mark_reachable(node: DSLNode) -> None:
            reachable_nodes.add(node.node_id)
            for child in node.children:
                mark_reachable(child)

        mark_reachable(root_node)

        all_nodes = set()
        def collect_all_nodes(node: DSLNode) -> None:
            all_nodes.add(node.node_id)
            for child in node.children:
                collect_all_nodes(child)

        collect_all_nodes(root_node)

        unreachable = all_nodes - reachable_nodes
        for node_id in unreachable:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message=f"Unreachable node: {node_id}",
                node_id=node_id
            ))

        return issues

    def _estimate_execution_duration(self, root_node: DSLNode) -> float:
        """Estimate the total execution duration."""
        def estimate_node_duration(node: DSLNode) -> float:
            if node.node_type == DSLNodeType.TASK:
                task_name = node.config.get("task_name")
                task_info = self._available_tasks.get(task_name, {})
                return task_info.get("estimated_duration", 30.0)  # Default 30 seconds

            elif node.node_type == DSLNodeType.SEQUENCE:
                return sum(estimate_node_duration(child) for child in node.children)

            elif node.node_type == DSLNodeType.PARALLEL:
                if not node.children:
                    return 0.0
                return max(estimate_node_duration(child) for child in node.children)

            elif node.node_type == DSLNodeType.CONDITION:
                # Estimate average of branches
                if not node.children:
                    return 0.0
                return sum(estimate_node_duration(child) for child in node.children) / len(node.children)

            elif node.node_type == DSLNodeType.LOOP:
                max_iterations = node.config.get("max_iterations", 10)
                body_duration = sum(estimate_node_duration(child) for child in node.children)
                return body_duration * min(max_iterations, 10)  # Cap estimation

            elif node.node_type == DSLNodeType.WAIT:
                return node.config.get("timeout", 30.0)

            return 0.0

        return estimate_node_duration(root_node)

    def _validate_performance(self, root_node: DSLNode, estimated_duration: float) -> List[ValidationIssue]:
        """Validate performance characteristics."""
        issues = []

        # Check for excessive duration
        max_duration = self._resource_limits.get("max_execution_duration", 3600)  # 1 hour default
        if estimated_duration > max_duration:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message=f"Estimated duration ({estimated_duration:.1f}s) exceeds limit ({max_duration}s)",
                suggestion="Consider optimizing the workflow or increasing limits"
            ))

        # Check for excessive parallel tasks
        def count_max_parallel(node: DSLNode) -> int:
            if node.node_type == DSLNodeType.PARALLEL:
                return len(node.children)
            return max((count_max_parallel(child) for child in node.children), default=0)

        max_parallel = count_max_parallel(root_node)
        parallel_limit = self._resource_limits.get("max_parallel_tasks", 10)
        if max_parallel > parallel_limit:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message=f"Maximum parallel tasks ({max_parallel}) exceeds limit ({parallel_limit})",
                suggestion="Consider reducing parallel task count or increasing limits"
            ))

        return issues

    def _validate_security(self, root_node: DSLNode) -> List[ValidationIssue]:
        """Validate security aspects of the workflow."""
        issues = []

        def validate_node_security(node: DSLNode) -> None:
            if node.node_type == DSLNodeType.TASK:
                # Check for potentially dangerous tools
                tools = node.config.get("tools", [])
                dangerous_tools = ["file.delete", "system.execute", "network.request"]

                for tool in tools:
                    if any(dangerous in tool for dangerous in dangerous_tools):
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            message=f"Potentially dangerous tool: {tool}",
                            node_id=node.node_id,
                            suggestion="Ensure proper security controls are in place"
                        ))

                # Check for parameter injection risks
                parameters = node.config.get("parameters", {})
                for key, value in parameters.items():
                    if isinstance(value, str) and "${" in value:
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.INFO,
                            message=f"Dynamic parameter detected: {key}",
                            node_id=node.node_id,
                            suggestion="Validate dynamic parameters for security"
                        ))

            # Recursively validate children
            for child in node.children:
                validate_node_security(child)

        validate_node_security(root_node)
        return issues
