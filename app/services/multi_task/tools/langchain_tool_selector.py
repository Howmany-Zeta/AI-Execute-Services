"""
LangChain Tool Selector

This module provides intelligent tool selection and execution logic for LangChain agents.
It implements dynamic tool selection based on task context, agent capabilities, and
runtime conditions with comprehensive error handling and fallback mechanisms.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass
from enum import Enum

from .langchain_adapter_tools import LangChainToolAdapter, LangChainToolRegistry, LangChainToolInjector
from .tool_manager import ToolManager
from ..core.exceptions.task_exceptions import TaskValidationError, TaskExecutionError

logger = logging.getLogger(__name__)


class ToolSelectionStrategy(Enum):
    """Tool selection strategies."""
    AUTOMATIC = "automatic"  # Automatic selection based on context
    EXPLICIT = "explicit"    # Explicit tool specification
    FALLBACK = "fallback"    # Fallback to safe tools
    ADAPTIVE = "adaptive"    # Adaptive selection based on success rate


@dataclass
class ToolExecutionContext:
    """Context for tool execution."""
    task_id: str
    agent_id: str
    task_category: str
    user_input: str
    domain: Optional[str] = None
    priority: str = "normal"
    timeout: int = 300
    retry_count: int = 3
    fallback_enabled: bool = True
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ToolExecutionResult:
    """Result of tool execution."""
    success: bool
    result: Any
    tool_name: str
    operation_name: str
    execution_time: float
    error_message: Optional[str] = None
    fallback_used: bool = False
    retry_count: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class LangChainToolSelector:
    """
    Intelligent tool selector for LangChain agents.

    This class implements dynamic tool selection logic that can:
    - Select appropriate tools based on task context
    - Handle tool execution with retries and fallbacks
    - Prevent system crashes through comprehensive error handling
    - Adapt tool selection based on success patterns
    """

    def __init__(
        self,
        tool_registry: LangChainToolRegistry,
        tool_injector: LangChainToolInjector,
        tool_manager: ToolManager
    ):
        """
        Initialize the tool selector.

        Args:
            tool_registry: Tool registry for discovering tools
            tool_injector: Tool injector for agent-specific tools
            tool_manager: Underlying tool manager
        """
        self.tool_registry = tool_registry
        self.tool_injector = tool_injector
        self.tool_manager = tool_manager

        # Tool selection state
        self._tool_success_rates: Dict[str, float] = {}
        self._tool_execution_counts: Dict[str, int] = {}
        self._blacklisted_tools: set = set()
        self._fallback_tools: List[str] = []

        # Configuration
        self.min_success_rate = 0.7
        self.max_retry_attempts = 3
        self.default_timeout = 300

        logger.info("LangChain tool selector initialized")

    async def select_and_execute_tools(
        self,
        context: ToolExecutionContext,
        available_tools: List[LangChainToolAdapter],
        tool_requirements: Optional[Dict[str, Any]] = None
    ) -> List[ToolExecutionResult]:
        """
        Select and execute appropriate tools based on context.

        Args:
            context: Execution context
            available_tools: List of available tools
            tool_requirements: Optional tool requirements/constraints

        Returns:
            List of tool execution results
        """
        try:
            logger.info(f"Starting tool selection and execution for task {context.task_id}")

            # Select tools based on strategy
            selected_tools = await self._select_tools(
                context, available_tools, tool_requirements
            )

            if not selected_tools:
                logger.warning(f"No tools selected for task {context.task_id}")
                return []

            # Execute selected tools
            results = await self._execute_tools(context, selected_tools)

            # Update tool performance metrics
            self._update_tool_metrics(results)

            logger.info(f"Completed tool execution for task {context.task_id}: {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Tool selection and execution failed: {e}")
            return [self._create_error_result(str(e), context)]

    async def _select_tools(
        self,
        context: ToolExecutionContext,
        available_tools: List[LangChainToolAdapter],
        tool_requirements: Optional[Dict[str, Any]] = None
    ) -> List[LangChainToolAdapter]:
        """
        Select tools based on context and requirements.

        Args:
            context: Execution context
            available_tools: Available tools to choose from
            tool_requirements: Tool requirements/constraints

        Returns:
            List of selected tools
        """
        try:
            strategy = self._determine_selection_strategy(context, tool_requirements)

            if strategy == ToolSelectionStrategy.EXPLICIT:
                return self._select_explicit_tools(available_tools, tool_requirements)
            elif strategy == ToolSelectionStrategy.AUTOMATIC:
                return await self._select_automatic_tools(context, available_tools)
            elif strategy == ToolSelectionStrategy.ADAPTIVE:
                return self._select_adaptive_tools(context, available_tools)
            elif strategy == ToolSelectionStrategy.FALLBACK:
                return self._select_fallback_tools(available_tools)
            else:
                return await self._select_automatic_tools(context, available_tools)

        except Exception as e:
            logger.error(f"Tool selection failed: {e}")
            return self._select_fallback_tools(available_tools)

    def _determine_selection_strategy(
        self,
        context: ToolExecutionContext,
        tool_requirements: Optional[Dict[str, Any]] = None
    ) -> ToolSelectionStrategy:
        """
        Determine the appropriate tool selection strategy.

        Args:
            context: Execution context
            tool_requirements: Tool requirements

        Returns:
            Selected strategy
        """
        try:
            # Check for explicit tool requirements
            if tool_requirements and tool_requirements.get('explicit_tools'):
                return ToolSelectionStrategy.EXPLICIT

            # Check if we should use adaptive selection
            if len(self._tool_success_rates) > 5:  # Have enough data
                return ToolSelectionStrategy.ADAPTIVE

            # Check if fallback is needed
            if context.priority == "safe" or not context.fallback_enabled:
                return ToolSelectionStrategy.FALLBACK

            # Default to automatic
            return ToolSelectionStrategy.AUTOMATIC

        except Exception as e:
            logger.error(f"Strategy determination failed: {e}")
            return ToolSelectionStrategy.FALLBACK

    def _select_explicit_tools(
        self,
        available_tools: List[LangChainToolAdapter],
        tool_requirements: Dict[str, Any]
    ) -> List[LangChainToolAdapter]:
        """
        Select explicitly specified tools.

        Args:
            available_tools: Available tools
            tool_requirements: Tool requirements with explicit tools

        Returns:
            List of selected tools
        """
        try:
            explicit_tools = tool_requirements.get('explicit_tools', [])
            selected = []

            for tool_spec in explicit_tools:
                if isinstance(tool_spec, str):
                    # Find tool by name
                    for tool in available_tools:
                        if tool.name == tool_spec:
                            selected.append(tool)
                            break
                elif isinstance(tool_spec, dict):
                    # Find tool by name and operation
                    tool_name = tool_spec.get('tool')
                    operation = tool_spec.get('operation')

                    for tool in available_tools:
                        if (tool.tool_name == tool_name and
                            tool.operation_name == operation):
                            selected.append(tool)
                            break

            logger.debug(f"Selected {len(selected)} explicit tools")
            return selected

        except Exception as e:
            logger.error(f"Explicit tool selection failed: {e}")
            return []

    async def _select_automatic_tools(
        self,
        context: ToolExecutionContext,
        available_tools: List[LangChainToolAdapter]
    ) -> List[LangChainToolAdapter]:
        """
        Automatically select tools based on context.

        Args:
            context: Execution context
            available_tools: Available tools

        Returns:
            List of selected tools
        """
        try:
            selected = []

            # Filter tools based on task category
            category_tools = self._filter_tools_by_category(
                available_tools, context.task_category
            )

            # Filter out blacklisted tools
            safe_tools = [
                tool for tool in category_tools
                if f"{tool.tool_name}.{tool.operation_name}" not in self._blacklisted_tools
            ]

            # Select based on domain if specified
            if context.domain:
                domain_tools = self._filter_tools_by_domain(safe_tools, context.domain)
                if domain_tools:
                    safe_tools = domain_tools

            # Limit selection to avoid overwhelming the agent
            max_tools = 5  # Configurable limit
            selected = safe_tools[:max_tools]

            logger.debug(f"Automatically selected {len(selected)} tools")
            return selected

        except Exception as e:
            logger.error(f"Automatic tool selection failed: {e}")
            return []

    def _select_adaptive_tools(
        self,
        context: ToolExecutionContext,
        available_tools: List[LangChainToolAdapter]
    ) -> List[LangChainToolAdapter]:
        """
        Select tools adaptively based on success rates.

        Args:
            context: Execution context
            available_tools: Available tools

        Returns:
            List of selected tools
        """
        try:
            # Score tools based on success rate and relevance
            scored_tools = []

            for tool in available_tools:
                tool_key = f"{tool.tool_name}.{tool.operation_name}"

                # Skip blacklisted tools
                if tool_key in self._blacklisted_tools:
                    continue

                # Calculate score
                success_rate = self._tool_success_rates.get(tool_key, 0.5)  # Default neutral
                execution_count = self._tool_execution_counts.get(tool_key, 0)

                # Boost score for tools with more executions (experience)
                experience_boost = min(execution_count / 10.0, 0.2)

                # Category relevance boost
                category_boost = 0.1 if self._is_tool_relevant_to_category(
                    tool, context.task_category
                ) else 0

                total_score = success_rate + experience_boost + category_boost
                scored_tools.append((tool, total_score))

            # Sort by score and select top tools
            scored_tools.sort(key=lambda x: x[1], reverse=True)
            selected = [tool for tool, score in scored_tools[:5] if score >= self.min_success_rate]

            logger.debug(f"Adaptively selected {len(selected)} tools")
            return selected

        except Exception as e:
            logger.error(f"Adaptive tool selection failed: {e}")
            return []

    def _select_fallback_tools(
        self,
        available_tools: List[LangChainToolAdapter]
    ) -> List[LangChainToolAdapter]:
        """
        Select safe fallback tools.

        Args:
            available_tools: Available tools

        Returns:
            List of safe fallback tools
        """
        try:
            # Define safe tool patterns
            safe_patterns = [
                'classifier.summarize',
                'research.summarize',
                'classifier.keyword_extract'
            ]

            fallback_tools = []

            for tool in available_tools:
                tool_key = f"{tool.tool_name}.{tool.operation_name}"

                # Check if tool matches safe patterns
                if any(pattern in tool_key for pattern in safe_patterns):
                    fallback_tools.append(tool)

                # Also include tools with high success rates
                success_rate = self._tool_success_rates.get(tool_key, 0)
                if success_rate >= 0.9:
                    fallback_tools.append(tool)

            # Remove duplicates
            fallback_tools = list(set(fallback_tools))

            logger.debug(f"Selected {len(fallback_tools)} fallback tools")
            return fallback_tools[:3]  # Limit to 3 safe tools

        except Exception as e:
            logger.error(f"Fallback tool selection failed: {e}")
            return []

    async def _execute_tools(
        self,
        context: ToolExecutionContext,
        tools: List[LangChainToolAdapter]
    ) -> List[ToolExecutionResult]:
        """
        Execute selected tools with error handling and retries.

        Args:
            context: Execution context
            tools: Tools to execute

        Returns:
            List of execution results
        """
        results = []

        for tool in tools:
            try:
                result = await self._execute_single_tool(context, tool)
                results.append(result)

                # If execution failed and fallback is enabled, try fallback
                if not result.success and context.fallback_enabled:
                    fallback_result = await self._try_fallback_execution(context, tool)
                    if fallback_result and fallback_result.success:
                        fallback_result.fallback_used = True
                        results.append(fallback_result)

            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                error_result = self._create_error_result(str(e), context, tool)
                results.append(error_result)

        return results

    async def _execute_single_tool(
        self,
        context: ToolExecutionContext,
        tool: LangChainToolAdapter
    ) -> ToolExecutionResult:
        """
        Execute a single tool with retries and timeout.

        Args:
            context: Execution context
            tool: Tool to execute

        Returns:
            Execution result
        """
        import time

        start_time = time.time()
        last_error = None

        for attempt in range(context.retry_count + 1):
            try:
                # Prepare tool parameters from context
                tool_params = self._prepare_tool_parameters(context, tool)

                # Execute with timeout
                result = await asyncio.wait_for(
                    tool._arun(**tool_params),
                    timeout=context.timeout
                )

                execution_time = time.time() - start_time

                return ToolExecutionResult(
                    success=True,
                    result=result,
                    tool_name=tool.tool_name,
                    operation_name=tool.operation_name,
                    execution_time=execution_time,
                    retry_count=attempt
                )

            except asyncio.TimeoutError:
                last_error = f"Tool execution timed out after {context.timeout}s"
                logger.warning(f"Tool {tool.name} timed out on attempt {attempt + 1}")

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Tool {tool.name} failed on attempt {attempt + 1}: {e}")

                # Wait before retry (exponential backoff)
                if attempt < context.retry_count:
                    await asyncio.sleep(2 ** attempt)

        # All attempts failed
        execution_time = time.time() - start_time

        return ToolExecutionResult(
            success=False,
            result=None,
            tool_name=tool.tool_name,
            operation_name=tool.operation_name,
            execution_time=execution_time,
            error_message=last_error,
            retry_count=context.retry_count
        )

    async def _try_fallback_execution(
        self,
        context: ToolExecutionContext,
        failed_tool: LangChainToolAdapter
    ) -> Optional[ToolExecutionResult]:
        """
        Try fallback execution for a failed tool.

        Args:
            context: Execution context
            failed_tool: Tool that failed

        Returns:
            Fallback execution result or None
        """
        try:
            # Find a suitable fallback tool
            fallback_tool = self._find_fallback_tool(failed_tool)

            if fallback_tool:
                logger.info(f"Trying fallback tool for {failed_tool.name}")
                return await self._execute_single_tool(context, fallback_tool)

            return None

        except Exception as e:
            logger.error(f"Fallback execution failed: {e}")
            return None

    def _find_fallback_tool(self, failed_tool: LangChainToolAdapter) -> Optional[LangChainToolAdapter]:
        """
        Find a suitable fallback tool for a failed tool.

        Args:
            failed_tool: Tool that failed

        Returns:
            Fallback tool or None
        """
        try:
            # Simple fallback logic - could be enhanced
            fallback_mapping = {
                'scraper': 'classifier.summarize',
                'search_api': 'research.summarize',
                'pandas': 'stats.describe'
            }

            fallback_spec = fallback_mapping.get(failed_tool.tool_name)
            if fallback_spec:
                # This would need to be implemented to find the actual tool
                # For now, return None
                pass

            return None

        except Exception as e:
            logger.error(f"Fallback tool search failed: {e}")
            return None

    def _prepare_tool_parameters(
        self,
        context: ToolExecutionContext,
        tool: LangChainToolAdapter
    ) -> Dict[str, Any]:
        """
        Prepare parameters for tool execution based on context.

        Args:
            context: Execution context
            tool: Tool to prepare parameters for

        Returns:
            Dictionary of tool parameters
        """
        try:
            # Basic parameter preparation
            params = {
                'input': context.user_input,
                'task_id': context.task_id
            }

            # Add tool-specific parameters based on operation
            if tool.operation_name == 'summarize':
                params['text'] = context.user_input
            elif tool.operation_name == 'keyword_extract':
                params['text'] = context.user_input
            elif tool.operation_name in ['get_requests', 'get_aiohttp']:
                # For scraper tools, we might need URL
                params['url'] = context.metadata.get('url', '')

            return params

        except Exception as e:
            logger.error(f"Parameter preparation failed: {e}")
            return {'input': context.user_input}

    def _filter_tools_by_category(
        self,
        tools: List[LangChainToolAdapter],
        category: str
    ) -> List[LangChainToolAdapter]:
        """
        Filter tools by task category.

        Args:
            tools: Tools to filter
            category: Task category

        Returns:
            Filtered tools
        """
        try:
            # Define category mappings
            category_mappings = {
                'collect': ['scraper', 'search_api', 'office'],
                'process': ['pandas', 'stats'],
                'analyze': ['stats', 'research'],
                'generate': ['report', 'chart', 'office'],
                'answer': ['research', 'classifier']
            }

            relevant_tool_names = category_mappings.get(category, [])

            if not relevant_tool_names:
                return tools  # Return all if no mapping

            filtered = [
                tool for tool in tools
                if tool.tool_name in relevant_tool_names
            ]

            return filtered

        except Exception as e:
            logger.error(f"Category filtering failed: {e}")
            return tools

    def _filter_tools_by_domain(
        self,
        tools: List[LangChainToolAdapter],
        domain: str
    ) -> List[LangChainToolAdapter]:
        """
        Filter tools by domain specialization.

        Args:
            tools: Tools to filter
            domain: Domain name

        Returns:
            Domain-relevant tools
        """
        try:
            # For now, return all tools
            # This could be enhanced with domain-specific tool mappings
            return tools

        except Exception as e:
            logger.error(f"Domain filtering failed: {e}")
            return tools

    def _is_tool_relevant_to_category(
        self,
        tool: LangChainToolAdapter,
        category: str
    ) -> bool:
        """
        Check if a tool is relevant to a task category.

        Args:
            tool: Tool to check
            category: Task category

        Returns:
            True if relevant, False otherwise
        """
        try:
            relevant_tools = self._filter_tools_by_category([tool], category)
            return len(relevant_tools) > 0

        except Exception as e:
            logger.error(f"Relevance check failed: {e}")
            return False

    def _update_tool_metrics(self, results: List[ToolExecutionResult]) -> None:
        """
        Update tool performance metrics based on execution results.

        Args:
            results: List of execution results
        """
        try:
            for result in results:
                tool_key = f"{result.tool_name}.{result.operation_name}"

                # Update execution count
                self._tool_execution_counts[tool_key] = (
                    self._tool_execution_counts.get(tool_key, 0) + 1
                )

                # Update success rate
                current_rate = self._tool_success_rates.get(tool_key, 0.5)
                execution_count = self._tool_execution_counts[tool_key]

                # Weighted average with new result
                new_rate = (
                    (current_rate * (execution_count - 1) + (1.0 if result.success else 0.0))
                    / execution_count
                )

                self._tool_success_rates[tool_key] = new_rate

                # Blacklist tools with consistently poor performance
                if execution_count >= 5 and new_rate < 0.3:
                    self._blacklisted_tools.add(tool_key)
                    logger.warning(f"Blacklisted tool {tool_key} due to poor performance")

        except Exception as e:
            logger.error(f"Metrics update failed: {e}")

    def _create_error_result(
        self,
        error_message: str,
        context: ToolExecutionContext,
        tool: Optional[LangChainToolAdapter] = None
    ) -> ToolExecutionResult:
        """
        Create an error result.

        Args:
            error_message: Error message
            context: Execution context
            tool: Optional tool that failed

        Returns:
            Error result
        """
        return ToolExecutionResult(
            success=False,
            result=None,
            tool_name=tool.tool_name if tool else "unknown",
            operation_name=tool.operation_name if tool else "unknown",
            execution_time=0.0,
            error_message=error_message
        )

    def get_tool_metrics(self) -> Dict[str, Any]:
        """
        Get tool performance metrics.

        Returns:
            Dictionary containing tool metrics
        """
        return {
            "success_rates": self._tool_success_rates.copy(),
            "execution_counts": self._tool_execution_counts.copy(),
            "blacklisted_tools": list(self._blacklisted_tools),
            "total_tools_tracked": len(self._tool_success_rates)
        }

    def reset_metrics(self) -> None:
        """Reset all tool metrics."""
        self._tool_success_rates.clear()
        self._tool_execution_counts.clear()
        self._blacklisted_tools.clear()
        logger.info("Tool metrics reset")
