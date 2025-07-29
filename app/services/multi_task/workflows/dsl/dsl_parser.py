"""
DSL Parser

Parser for the Domain Specific Language (DSL) used in multi-task workflows.
Supports conditional branching, parallel execution, and task sequencing.
"""

import json
import re
from typing import Dict, List, Any, Optional, Union
import logging

from ...core.models.workflow_models import DSLNodeType, DSLNode, DSLParseResult
from ...core.exceptions.execution_exceptions import ExecutionValidationError

logger = logging.getLogger(__name__)


class DSLParser:
    """
    Parser for the multi-task DSL.

    Supports the following DSL constructs:
    - Single tasks: {"task": "task_name", "tools": ["tool.operation"]}
    - Conditional branching: {"if": "condition", "then": [steps], "else": [steps]}
    - Parallel blocks: {"parallel": [task_definitions]}
    - Sequential blocks: {"sequence": [task_definitions]}
    - Loops: {"loop": {"condition": "expr", "body": [steps], "max_iterations": 10}}
    - Wait conditions: {"wait": {"condition": "expr", "timeout": 30}}
    """

    def __init__(self):
        """Initialize the DSL parser."""
        self.logger = logger
        self._node_counter = 0
        self._available_tasks = set()
        self._available_tools = set()

    def set_available_tasks(self, tasks: List[str]) -> None:
        """Set the list of available tasks for validation."""
        self._available_tasks = set(tasks)

    def set_available_tools(self, tools: List[str]) -> None:
        """Set the list of available tools for validation."""
        self._available_tools = set(tools)

    def parse(self, dsl_definition: Union[Dict, List]) -> DSLParseResult:
        """
        Parse a DSL definition into a node tree.

        Args:
            dsl_definition: DSL definition as dict or list

        Returns:
            DSLParseResult containing the parsed tree or errors
        """
        self._node_counter = 0
        errors = []
        warnings = []

        try:
            # Normalize input to list format
            if isinstance(dsl_definition, dict):
                dsl_definition = [dsl_definition]
            elif not isinstance(dsl_definition, list):
                errors.append("DSL definition must be a dict or list")
                return DSLParseResult(False, None, errors, warnings, {})

            # Parse the root sequence
            root_node = self._parse_sequence(dsl_definition, None)

            # Validate the parsed tree
            validation_errors = self._validate_tree(root_node)
            errors.extend(validation_errors)

            success = len(errors) == 0
            metadata = {
                'node_count': self._node_counter,
                'max_depth': self._calculate_max_depth(root_node),
                'parallel_blocks': self._count_parallel_blocks(root_node)
            }

            return DSLParseResult(success, root_node, errors, warnings, metadata)

        except Exception as e:
            self.logger.error(f"DSL parsing failed: {e}")
            errors.append(f"Parsing error: {str(e)}")
            return DSLParseResult(False, None, errors, warnings, {})

    def _parse_sequence(self, steps: List[Dict], parent: Optional[DSLNode]) -> DSLNode:
        """Parse a sequence of steps."""
        node_id = self._generate_node_id("seq")
        sequence_node = DSLNode(
            node_type=DSLNodeType.SEQUENCE,
            node_id=node_id,
            config={"steps": len(steps)},
            children=[],
            parent=parent
        )

        for step in steps:
            child_node = self._parse_step(step, sequence_node)
            if child_node:
                sequence_node.children.append(child_node)

        return sequence_node

    def _parse_step(self, step: Dict, parent: Optional[DSLNode]) -> Optional[DSLNode]:
        """Parse a single step in the DSL."""
        if not isinstance(step, dict):
            raise ExecutionValidationError(f"Step must be a dictionary, got {type(step)}")

        # Determine step type
        if "task" in step:
            return self._parse_task(step, parent)
        elif "if" in step:
            return self._parse_condition(step, parent)
        elif "parallel" in step:
            return self._parse_parallel(step, parent)
        elif "sequence" in step:
            return self._parse_sequence(step["sequence"], parent)
        elif "loop" in step:
            return self._parse_loop(step, parent)
        elif "wait" in step:
            return self._parse_wait(step, parent)
        else:
            raise ExecutionValidationError(f"Unknown step type in: {step}")

    def _parse_task(self, step: Dict, parent: Optional[DSLNode]) -> DSLNode:
        """Parse a task step."""
        task_name = step.get("task")
        if not task_name:
            raise ExecutionValidationError("Task step must have 'task' field")

        node_id = self._generate_node_id("task")
        config = {
            "task_name": task_name,
            "tools": step.get("tools", []),
            "parameters": step.get("parameters", {}),
            "timeout": step.get("timeout"),
            "retry_count": step.get("retry_count", 0),
            "conditions": step.get("conditions", [])
        }

        return DSLNode(
            node_type=DSLNodeType.TASK,
            node_id=node_id,
            config=config,
            children=[],
            parent=parent
        )

    def _parse_condition(self, step: Dict, parent: Optional[DSLNode]) -> DSLNode:
        """Parse a conditional step."""
        condition = step.get("if")
        if not condition:
            raise ExecutionValidationError("Conditional step must have 'if' field")

        node_id = self._generate_node_id("cond")
        config = {
            "condition": condition,
            "condition_type": self._determine_condition_type(condition)
        }

        condition_node = DSLNode(
            node_type=DSLNodeType.CONDITION,
            node_id=node_id,
            config=config,
            children=[],
            parent=parent
        )

        # Parse then branch
        then_steps = step.get("then", [])
        if then_steps:
            then_node = self._parse_sequence(then_steps, condition_node)
            then_node.metadata["branch"] = "then"
            condition_node.children.append(then_node)

        # Parse else branch
        else_steps = step.get("else", [])
        if else_steps:
            else_node = self._parse_sequence(else_steps, condition_node)
            else_node.metadata["branch"] = "else"
            condition_node.children.append(else_node)

        return condition_node

    def _parse_parallel(self, step: Dict, parent: Optional[DSLNode]) -> DSLNode:
        """Parse a parallel execution block."""
        parallel_tasks = step.get("parallel")
        if not parallel_tasks or not isinstance(parallel_tasks, list):
            raise ExecutionValidationError("Parallel step must have 'parallel' field with list of tasks")

        node_id = self._generate_node_id("par")
        config = {
            "max_concurrency": step.get("max_concurrency", len(parallel_tasks)),
            "wait_for_all": step.get("wait_for_all", True),
            "fail_fast": step.get("fail_fast", False)
        }

        parallel_node = DSLNode(
            node_type=DSLNodeType.PARALLEL,
            node_id=node_id,
            config=config,
            children=[],
            parent=parent
        )

        # Parse each parallel task
        for task_def in parallel_tasks:
            child_node = self._parse_step(task_def, parallel_node)
            if child_node:
                parallel_node.children.append(child_node)

        return parallel_node

    def _parse_loop(self, step: Dict, parent: Optional[DSLNode]) -> DSLNode:
        """Parse a loop construct."""
        loop_config = step.get("loop")
        if not loop_config or not isinstance(loop_config, dict):
            raise ExecutionValidationError("Loop step must have 'loop' field with configuration")

        condition = loop_config.get("condition")
        body = loop_config.get("body", [])

        if not condition:
            raise ExecutionValidationError("Loop must have a condition")

        node_id = self._generate_node_id("loop")
        config = {
            "condition": condition,
            "max_iterations": loop_config.get("max_iterations", 100),
            "break_on_error": loop_config.get("break_on_error", True)
        }

        loop_node = DSLNode(
            node_type=DSLNodeType.LOOP,
            node_id=node_id,
            config=config,
            children=[],
            parent=parent
        )

        # Parse loop body
        if body:
            body_node = self._parse_sequence(body, loop_node)
            body_node.metadata["loop_body"] = True
            loop_node.children.append(body_node)

        return loop_node

    def _parse_wait(self, step: Dict, parent: Optional[DSLNode]) -> DSLNode:
        """Parse a wait condition."""
        wait_config = step.get("wait")
        if not wait_config or not isinstance(wait_config, dict):
            raise ExecutionValidationError("Wait step must have 'wait' field with configuration")

        condition = wait_config.get("condition")
        if not condition:
            raise ExecutionValidationError("Wait must have a condition")

        node_id = self._generate_node_id("wait")
        config = {
            "condition": condition,
            "timeout": wait_config.get("timeout", 30),
            "poll_interval": wait_config.get("poll_interval", 1)
        }

        return DSLNode(
            node_type=DSLNodeType.WAIT,
            node_id=node_id,
            config=config,
            children=[],
            parent=parent
        )

    def _determine_condition_type(self, condition: str) -> str:
        """Determine the type of condition expression."""
        if "subtasks.includes" in condition:
            return "subtask_check"
        elif "result." in condition:
            return "result_check"
        elif "context." in condition:
            return "context_check"
        elif any(op in condition for op in ["==", "!=", ">", "<", ">=", "<="]):
            return "comparison"
        elif any(op in condition for op in ["and", "or", "not"]):
            return "logical"
        else:
            return "expression"

    def _validate_tree(self, root_node: DSLNode) -> List[str]:
        """Validate the parsed DSL tree."""
        errors = []

        def validate_node(node: DSLNode) -> None:
            # Validate task nodes
            if node.node_type == DSLNodeType.TASK:
                task_name = node.config.get("task_name")
                if self._available_tasks and task_name not in self._available_tasks:
                    errors.append(f"Unknown task: {task_name}")

                # Validate tools
                tools = node.config.get("tools", [])
                for tool in tools:
                    if self._available_tools and tool not in self._available_tools:
                        errors.append(f"Unknown tool: {tool}")

            # Validate condition nodes
            elif node.node_type == DSLNodeType.CONDITION:
                condition = node.config.get("condition")
                if not self._validate_condition_syntax(condition):
                    errors.append(f"Invalid condition syntax: {condition}")

            # Validate parallel nodes
            elif node.node_type == DSLNodeType.PARALLEL:
                if len(node.children) == 0:
                    errors.append(f"Parallel block {node.node_id} has no children")

            # Validate loop nodes
            elif node.node_type == DSLNodeType.LOOP:
                max_iterations = node.config.get("max_iterations", 100)
                if max_iterations <= 0:
                    errors.append(f"Loop {node.node_id} has invalid max_iterations: {max_iterations}")

            # Recursively validate children
            for child in node.children:
                validate_node(child)

        validate_node(root_node)
        return errors

    def _validate_condition_syntax(self, condition: str) -> bool:
        """Validate condition expression syntax."""
        if not condition or not isinstance(condition, str):
            return False

        # Basic syntax validation
        try:
            # Check for balanced parentheses
            if condition.count('(') != condition.count(')'):
                return False

            # Check for balanced quotes
            single_quotes = condition.count("'")
            double_quotes = condition.count('"')
            if single_quotes % 2 != 0 or double_quotes % 2 != 0:
                return False

            # Check for obvious syntax errors first
            if self._has_syntax_errors(condition):
                return False

            # Enhanced validation using a more structured approach
            return self._validate_expression_structure(condition)

        except Exception:
            return False

    def _has_syntax_errors(self, condition: str) -> bool:
        """Check for obvious syntax errors."""
        # Check for consecutive dots
        if '..' in condition:
            return True

        # Check for invalid operator sequences
        invalid_operators = ['=====', '====', '===', 'and and', 'or or', 'not not']
        for invalid_op in invalid_operators:
            if invalid_op in condition:
                return True

        # Check for identifiers starting with numbers
        if re.search(r'\b\d+[a-zA-Z_]', condition):
            return True

        # Check for invalid characters in identifiers (like hyphens)
        if re.search(r'[a-zA-Z_][a-zA-Z0-9_]*-[a-zA-Z0-9_]', condition):
            return True

        # Check for unclosed strings
        if re.search(r'["\'][^"\']*$', condition) or re.search(r'^[^"\']*["\']', condition):
            # More sophisticated string validation
            in_string = False
            quote_char = None
            i = 0
            while i < len(condition):
                char = condition[i]
                if char in ['"', "'"] and not in_string:
                    in_string = True
                    quote_char = char
                elif char == quote_char and in_string:
                    in_string = False
                    quote_char = None
                i += 1
            if in_string:
                return True

        return False

    def _validate_expression_structure(self, condition: str) -> bool:
        """Validate the overall structure of the expression."""
        # First check for malformed strings more carefully
        if not self._validate_string_literals(condition):
            return False

        # Tokenize the condition into meaningful parts
        tokens = self._tokenize_condition(condition)

        # Check if tokenization captured the entire condition
        reconstructed = ''.join(tokens)
        if reconstructed.replace(' ', '') != condition.replace(' ', ''):
            return False

        # Validate each token
        for token in tokens:
            if not self._is_valid_token(token):
                return False

        # Validate token combinations
        return self._validate_token_sequence(tokens)

    def _validate_string_literals(self, condition: str) -> bool:
        """Validate string literals more carefully."""
        # Check for malformed strings like unclosed'string' or 'unclosed string

        # Look for patterns where alphanumeric characters are directly adjacent to quotes
        # BUT exclude cases where the quote is part of a proper string literal

        # First, find all properly quoted strings
        proper_strings = []
        i = 0
        while i < len(condition):
            if condition[i] in ['"', "'"]:
                quote_char = condition[i]
                start = i
                i += 1
                # Find the closing quote
                while i < len(condition) and condition[i] != quote_char:
                    i += 1
                if i < len(condition):  # Found closing quote
                    proper_strings.append((start, i))
                    i += 1
                else:
                    # Unclosed string
                    return False
            else:
                i += 1

        # Now check for invalid patterns outside of proper strings
        for i in range(len(condition)):
            # Skip characters that are inside proper strings
            inside_string = any(start <= i <= end for start, end in proper_strings)
            if inside_string:
                continue

            char = condition[i]

            # Check for alphanumeric followed by quote (invalid pattern like word'string')
            if char.isalnum() and i + 1 < len(condition) and condition[i + 1] in ['"', "'"]:
                return False

            # Check for quote followed by alphanumeric (invalid pattern like 'string'word)
            if char in ['"', "'"] and i + 1 < len(condition) and condition[i + 1].isalnum():
                return False

        return True

    def _tokenize_condition(self, condition: str) -> List[str]:
        """Tokenize the condition into meaningful parts."""
        # Enhanced regex that better handles edge cases
        pattern = r'''
            (\s+)|                          # whitespace
            ("(?:[^"\\]|\\.)*")|           # double quoted strings with escape support
            ('(?:[^'\\]|\\.)*')|           # single quoted strings with escape support
            (=====|====|===|==|!=|<=|>=|<|>)|  # comparison operators (including invalid ones)
            (\band\s+and\b|\bor\s+or\b|\bnot\s+not\b)|  # invalid repeated operators
            (\band\b|\bor\b|\bnot\b)|      # logical operators
            (\btrue\b|\bfalse\b)|          # boolean literals
            ([()])|                        # parentheses
            (\d+(?:\.\d+)?)|              # numbers
            ([a-zA-Z_][a-zA-Z0-9_.]*)|    # identifiers and property access
            ([^\s]+)                       # any other non-whitespace (likely invalid)
        '''

        tokens = []
        for match in re.finditer(pattern, condition, re.VERBOSE):
            token = match.group(0)
            if token.strip():  # Skip pure whitespace
                tokens.append(token)

        return tokens

    def _validate_token_sequence(self, tokens: List[str]) -> bool:
        """Validate the sequence of tokens makes sense."""
        if not tokens:
            return False

        # Remove whitespace tokens for sequence validation
        non_ws_tokens = [t for t in tokens if t.strip()]

        # Check for invalid operator sequences
        for i in range(len(non_ws_tokens) - 1):
            current = non_ws_tokens[i]
            next_token = non_ws_tokens[i + 1]

            # Check for repeated logical operators
            if current in ['and', 'or'] and next_token in ['and', 'or']:
                return False

            # Check for invalid operator combinations
            if current in ['==', '!=', '<=', '>=', '<', '>'] and next_token in ['==', '!=', '<=', '>=', '<', '>']:
                return False

        return True

    def _is_valid_token(self, token: str) -> bool:
        """Check if a token is valid."""
        # Skip whitespace
        if not token.strip():
            return True

        # Valid comparison operators
        if token in ['==', '!=', '<=', '>=', '<', '>']:
            return True

        # Invalid comparison operators
        if token in ['=====', '====', '===']:
            return False

        # Logical operators
        if token in ['and', 'or', 'not']:
            return True

        # Invalid repeated operators
        if re.match(r'\b(and\s+and|or\s+or|not\s+not)\b', token):
            return False

        # Parentheses
        if token in ['(', ')']:
            return True

        # Boolean literals
        if token in ['true', 'false']:
            return True

        # Numbers
        if re.match(r'^\d+(?:\.\d+)?$', token):
            return True

        # String literals (properly quoted)
        if re.match(r'^["\'][^"\']*["\']$', token):
            return True

        # Property access patterns (no consecutive dots, valid identifiers)
        if re.match(r'^(result|context)\.[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*$', token):
            # Additional check for consecutive dots
            if '..' in token:
                return False
            return True

        # Simple identifiers
        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', token):
            return True

        # Function calls
        if re.match(r'^subtasks\.includes\(["\'][^"\']+["\']\)$', token):
            return True

        # If none of the above patterns match, it's invalid
        return False

        # Function calls
        if re.match(r'^subtasks\.includes\(["\'][^"\']+["\']\)$', token):
            return True

        # Simple identifiers
        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', token):
            return True

        # If none of the above patterns match, it's invalid
        return False

    def _generate_node_id(self, prefix: str) -> str:
        """Generate a unique node ID."""
        self._node_counter += 1
        return f"{prefix}_{self._node_counter}"

    def _calculate_max_depth(self, node: DSLNode) -> int:
        """Calculate the maximum depth of the DSL tree."""
        if not node.children:
            return 1
        return 1 + max(self._calculate_max_depth(child) for child in node.children)

    def _count_parallel_blocks(self, node: DSLNode) -> int:
        """Count the number of parallel blocks in the tree."""
        count = 1 if node.node_type == DSLNodeType.PARALLEL else 0
        for child in node.children:
            count += self._count_parallel_blocks(child)
        return count

    def serialize_tree(self, node: DSLNode) -> Dict[str, Any]:
        """Serialize a DSL tree to a dictionary."""
        return {
            "node_type": node.node_type.value,
            "node_id": node.node_id,
            "config": node.config,
            "metadata": node.metadata,
            "children": [self.serialize_tree(child) for child in node.children]
        }

    def deserialize_tree(self, data: Dict[str, Any], parent: Optional[DSLNode] = None) -> DSLNode:
        """Deserialize a dictionary to a DSL tree."""
        node = DSLNode(
            node_type=DSLNodeType(data["node_type"]),
            node_id=data["node_id"],
            config=data["config"],
            children=[],
            parent=parent,
            metadata=data.get("metadata", {})
        )

        for child_data in data.get("children", []):
            child = self.deserialize_tree(child_data, node)
            node.children.append(child)

        return node
