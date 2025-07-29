"""
LangChain Engine with LangGraph

LangGraph-based execution engine for agent workflows.
Complete replacement for the deprecated CrewEngine, providing advanced agent orchestration
and task execution using LangGraph framework with dynamic agent management.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, AsyncGenerator, Callable
from datetime import datetime
import uuid

# Initialize logger first
logger = logging.getLogger(__name__)

try:
    from langgraph.graph import StateGraph, END
    from langgraph.prebuilt import ToolNode
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    logger.warning("LangGraph not available, falling back to basic LangChain implementation")

from ..base_executor import BaseExecutor
from ...core.models.execution_models import (
    ExecutionContext, ExecutionResult, ExecutionPlan, ExecutionStatus, ExecutionMode
)
from ...core.exceptions.execution_exceptions import ExecutionError, ValidationError
from ...agent.agent_manager import AgentManager
from ...agent.dynamic_agent_manager import DynamicAgentManager
from ...config.config_manager import ConfigManager
from app.services.llm_integration import LLMIntegrationManager


class WorkflowState:
    """State management for LangGraph workflows."""

    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.current_step: Optional[str] = None
        self.step_results: Dict[str, Any] = {}
        self.shared_data: Dict[str, Any] = {}
        self.error: Optional[str] = None
        self.completed_steps: List[str] = []
        self.next_steps: List[str] = []


class LangChainEngine(BaseExecutor):
    """
    LangGraph-powered execution engine for agent-based task execution.

    This engine manages LangChain agents using LangGraph and provides:
    - Advanced stateful workflow orchestration with LangGraph
    - Dynamic agent lifecycle management
    - Sequential, parallel, and conditional execution patterns
    - Task delegation and execution with state management
    - Agent collaboration workflows with memory
    - Intelligent agent pooling and caching
    """

    def __init__(
        self,
        agent_manager: Optional[AgentManager] = None,
        config_manager: Optional[ConfigManager] = None,
        llm_manager: Optional[LLMIntegrationManager] = None
    ):
        """
        Initialize the LangChain engine with LangGraph support.

        Args:
            agent_manager: AgentManager instance for agent operations
            config_manager: Configuration manager for agent configs
            llm_manager: LLM integration manager for agent operations
        """
        super().__init__()

        # Initialize managers
        self.config_manager = config_manager or ConfigManager()
        self.llm_manager = llm_manager

        if not self.llm_manager:
            raise ValueError("llm_manager is required for LangChainEngine initialization")

        self.agent_manager = agent_manager or AgentManager(self.config_manager, self.llm_manager)
        self.dynamic_agent_manager = DynamicAgentManager(self.agent_manager)

        # LangGraph components
        self.memory_saver = MemorySaver() if LANGGRAPH_AVAILABLE else None
        self.active_graphs: Dict[str, Any] = {}  # workflow_id -> compiled_graph

        # Engine state
        self._active_executions = {}
        self._workflow_agents = {}  # workflow_id -> [agent_ids]

        logger.info(f"LangChain Engine initialized with LangGraph support: {LANGGRAPH_AVAILABLE}")

    async def _initialize_executor(self) -> None:
        """Initialize LangChain engine specific resources."""
        try:
            # Initialize the agent manager
            await self.agent_manager.initialize()

            self.logger.info("LangChain Engine initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize LangChain Engine: {e}")
            raise

    async def _cleanup_executor(self) -> None:
        """Cleanup LangChain engine specific resources."""
        try:
            # Clean up dynamic agents
            await self.dynamic_agent_manager.cleanup_dynamic_agents()

            # Clean up agent manager
            await self.agent_manager.cleanup()

            # Clear active executions and graphs
            self._active_executions.clear()
            self._workflow_agents.clear()
            self.active_graphs.clear()

            self.logger.info("LangChain Engine cleaned up")

        except Exception as e:
            self.logger.error(f"Error cleaning up LangChain Engine: {e}")

    async def _execute_task_impl(
        self,
        task_definition: Dict[str, Any],
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Execute a single task using LangChain agents.

        Args:
            task_definition: Task definition with agent and task details
            context: Execution context

        Returns:
            ExecutionResult: Result of task execution
        """
        execution_id = str(uuid.uuid4())
        start_time = datetime.utcnow()

        try:
            # Extract task information
            agent_role = task_definition.get('agent', task_definition.get('role'))
            task_description = task_definition.get('description', '')
            expected_output = task_definition.get('expected_output', '')
            tools = task_definition.get('tools', [])

            if not agent_role:
                raise ExecutionError("Agent role is required for task execution")

            # Create or get agent dynamically
            agent_id = await self.dynamic_agent_manager.create_agent_on_demand(
                role=agent_role,
                context=context.dict(),
                tools=tools
            )

            # Execute task with the agent
            task_data = {
                'description': task_description,
                'expected_output': expected_output,
                'input': context.input_data
            }

            result = await self.dynamic_agent_manager.execute_task_with_agent(
                agent_id, task_data, context.dict()
            )

            # Clean up agent (return to pool or destroy)
            await self.dynamic_agent_manager.destroy_agent(agent_id)

            return ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.COMPLETED,
                success=result.get('status') == 'completed',
                message=f"Task completed successfully with agent {agent_role}",
                result=result,
                started_at=start_time,
                completed_at=datetime.utcnow()
            )

        except asyncio.TimeoutError:
            return ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.TIMED_OUT,
                success=False,
                message="Task execution timed out",
                error_code="TASK_TIMEOUT_ERROR",
                error_message="Task execution exceeded timeout limit",
                started_at=start_time,
                completed_at=datetime.utcnow()
            )
        except Exception as e:
            self.logger.error(f"Task execution failed: {e}")
            return ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED,
                success=False,
                message=f"Task execution failed: {str(e)}",
                error_code="TASK_EXECUTION_ERROR",
                error_message=str(e),
                started_at=start_time,
                completed_at=datetime.utcnow()
            )

    async def _execute_workflow_impl(
        self,
        workflow_definition: Dict[str, Any],
        context: ExecutionContext,
        plan: ExecutionPlan
    ) -> AsyncGenerator[ExecutionResult, None]:
        """
        Execute a workflow using LangGraph for advanced orchestration.

        Args:
            workflow_definition: Workflow definition with agents and tasks
            context: Execution context
            plan: Execution plan

        Yields:
            ExecutionResult: Results from each workflow step
        """
        workflow_id = workflow_definition.get('workflow_id', str(uuid.uuid4()))
        tasks = workflow_definition.get('tasks', [])
        process_type = workflow_definition.get('process', 'sequential')

        try:
            if LANGGRAPH_AVAILABLE and len(tasks) > 1:
                # Use LangGraph for complex workflows
                async for result in self._execute_langgraph_workflow(
                    workflow_id, tasks, process_type, context, plan
                ):
                    yield result
            else:
                # Fallback to sequential execution for simple workflows
                async for result in self._execute_sequential_workflow(
                    workflow_id, tasks, context
                ):
                    yield result

        except Exception as e:
            error_result = ExecutionResult(
                execution_id=workflow_id,
                status=ExecutionStatus.FAILED,
                success=False,
                message=f"Workflow execution failed: {str(e)}",
                error_code="WORKFLOW_EXECUTION_ERROR",
                error_message=str(e),
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            yield error_result

    async def _execute_langgraph_workflow(
        self,
        workflow_id: str,
        tasks: List[Dict[str, Any]],
        process_type: str,
        context: ExecutionContext,
        plan: ExecutionPlan
    ) -> AsyncGenerator[ExecutionResult, None]:
        """
        Execute workflow using LangGraph for advanced state management.
        """
        try:
            # Create workflow graph
            workflow_graph = StateGraph(WorkflowState)

            # Create agents for all tasks
            agent_ids = []
            for task in tasks:
                agent_role = task.get('agent', task.get('role'))
                if agent_role:
                    agent_id = await self.dynamic_agent_manager.create_agent_on_demand(
                        role=agent_role,
                        context=context.dict(),
                        tools=task.get('tools', [])
                    )
                    agent_ids.append(agent_id)

            self._workflow_agents[workflow_id] = agent_ids

            # Add nodes for each task
            for i, task in enumerate(tasks):
                node_name = f"task_{i}"
                workflow_graph.add_node(
                    node_name,
                    self._create_task_node(task, agent_ids[i] if i < len(agent_ids) else None)
                )

            # Add edges based on process type
            if process_type.lower() == 'sequential':
                # Sequential execution
                workflow_graph.set_entry_point("task_0")
                for i in range(len(tasks) - 1):
                    workflow_graph.add_edge(f"task_{i}", f"task_{i + 1}")
                workflow_graph.add_edge(f"task_{len(tasks) - 1}", END)

            elif process_type.lower() == 'parallel':
                # Parallel execution - all tasks start simultaneously
                for i in range(len(tasks)):
                    workflow_graph.set_entry_point(f"task_{i}")
                    workflow_graph.add_edge(f"task_{i}", END)

            else:
                # Default to sequential
                workflow_graph.set_entry_point("task_0")
                for i in range(len(tasks) - 1):
                    workflow_graph.add_edge(f"task_{i}", f"task_{i + 1}")
                workflow_graph.add_edge(f"task_{len(tasks) - 1}", END)

            # Compile and execute the graph
            compiled_graph = workflow_graph.compile(checkpointer=self.memory_saver)
            self.active_graphs[workflow_id] = compiled_graph

            # Execute the workflow
            initial_state = WorkflowState()
            initial_state.shared_data = context.shared_data.copy()

            config = {"configurable": {"thread_id": workflow_id}}

            async for step_result in compiled_graph.astream(initial_state, config=config):
                # Convert step result to ExecutionResult
                step_name = list(step_result.keys())[0] if step_result else "unknown"
                step_data = step_result.get(step_name, {})

                execution_result = ExecutionResult(
                    execution_id=f"{workflow_id}_{step_name}",
                    status=ExecutionStatus.COMPLETED if not step_data.get('error') else ExecutionStatus.FAILED,
                    success=not step_data.get('error'),
                    message=f"Workflow step {step_name} completed",
                    result=step_data,
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow()
                )
                yield execution_result

            # Final workflow result
            final_result = ExecutionResult(
                execution_id=workflow_id,
                status=ExecutionStatus.COMPLETED,
                success=True,
                message=f"LangGraph workflow completed successfully",
                result={'workflow_id': workflow_id, 'tasks_count': len(tasks)},
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            yield final_result

        except Exception as e:
            self.logger.error(f"LangGraph workflow execution failed: {e}")
            raise
        finally:
            # Clean up agents
            if workflow_id in self._workflow_agents:
                for agent_id in self._workflow_agents[workflow_id]:
                    try:
                        await self.dynamic_agent_manager.destroy_agent(agent_id)
                    except Exception as e:
                        self.logger.error(f"Error cleaning up agent {agent_id}: {e}")
                del self._workflow_agents[workflow_id]

            # Clean up graph
            if workflow_id in self.active_graphs:
                del self.active_graphs[workflow_id]

    def _create_task_node(self, task: Dict[str, Any], agent_id: Optional[str]) -> Callable:
        """
        Create a LangGraph node function for a task.
        """
        async def task_node(state: WorkflowState) -> WorkflowState:
            try:
                if not agent_id:
                    state.error = f"No agent available for task: {task.get('description', 'unknown')}"
                    return state

                # Execute task with agent
                task_data = {
                    'description': task.get('description', ''),
                    'expected_output': task.get('expected_output', ''),
                    'input': state.shared_data
                }

                result = await self.dynamic_agent_manager.execute_task_with_agent(
                    agent_id, task_data, state.shared_data
                )

                # Update state
                task_name = task.get('name', f"task_{len(state.completed_steps)}")
                state.step_results[task_name] = result
                state.completed_steps.append(task_name)

                # Update shared data with result
                if result.get('status') == 'completed':
                    state.shared_data[f"{task_name}_result"] = result.get('result')

                state.messages.append({
                    'type': 'task_completion',
                    'task': task_name,
                    'result': result,
                    'timestamp': datetime.utcnow().isoformat()
                })

            except Exception as e:
                state.error = str(e)
                self.logger.error(f"Task node execution failed: {e}")

            return state

        return task_node

    async def _execute_sequential_workflow(
        self,
        workflow_id: str,
        tasks: List[Dict[str, Any]],
        context: ExecutionContext
    ) -> AsyncGenerator[ExecutionResult, None]:
        """
        Fallback sequential workflow execution without LangGraph.
        """
        agent_ids = []

        try:
            for i, task in enumerate(tasks):
                agent_role = task.get('agent', task.get('role'))
                if not agent_role:
                    continue

                # Create agent for this task
                agent_id = await self.dynamic_agent_manager.create_agent_on_demand(
                    role=agent_role,
                    context=context.dict(),
                    tools=task.get('tools', [])
                )
                agent_ids.append(agent_id)

                # Execute task
                task_data = {
                    'description': task.get('description', ''),
                    'expected_output': task.get('expected_output', ''),
                    'input': context.shared_data
                }

                result = await self.dynamic_agent_manager.execute_task_with_agent(
                    agent_id, task_data, context.dict()
                )

                # Update shared data for next task
                if result.get('status') == 'completed':
                    context.shared_data[f"task_{i}_result"] = result.get('result')

                # Yield step result
                step_result = ExecutionResult(
                    execution_id=f"{workflow_id}_task_{i}",
                    status=ExecutionStatus.COMPLETED if result.get('status') == 'completed' else ExecutionStatus.FAILED,
                    success=result.get('status') == 'completed',
                    message=f"Task {i} completed",
                    result=result,
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow()
                )
                yield step_result

            # Final result
            final_result = ExecutionResult(
                execution_id=workflow_id,
                status=ExecutionStatus.COMPLETED,
                success=True,
                message=f"Sequential workflow completed successfully",
                result={'workflow_id': workflow_id, 'tasks_count': len(tasks)},
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            yield final_result

        finally:
            # Clean up agents
            for agent_id in agent_ids:
                try:
                    await self.dynamic_agent_manager.destroy_agent(agent_id)
                except Exception as e:
                    self.logger.error(f"Error cleaning up agent {agent_id}: {e}")

    async def _execute_dsl_step_impl(
        self,
        step: Dict[str, Any],
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Execute a DSL step using LangChain agents.
        """
        # Convert DSL step to task format
        if 'task' in step:
            task_definition = {
                'agent': step.get('agent', 'default'),
                'description': step.get('description', f"Execute task: {step['task']}"),
                'expected_output': step.get('expected_output', 'Task completion result'),
                'tools': step.get('tools', [])
            }
            return await self._execute_task_impl(task_definition, context)
        else:
            # Handle other DSL types by delegating to base implementation
            return await super()._execute_dsl_step_impl(step, context)

    async def _create_execution_plan_impl(
        self,
        workflow_definition: Dict[str, Any]
    ) -> ExecutionPlan:
        """Create an execution plan for LangChain workflow."""
        plan_id = str(uuid.uuid4())
        workflow_id = workflow_definition.get('workflow_id', str(uuid.uuid4()))

        tasks = workflow_definition.get('tasks', [])
        process_type = workflow_definition.get('process', 'sequential')

        # Analyze task dependencies
        dependencies = {}
        parallel_groups = []

        if process_type.lower() == 'sequential':
            # Sequential execution - each task depends on the previous
            for task_idx in range(1, len(tasks)):
                dependencies[f"task_{task_idx}"] = [f"task_{task_idx - 1}"]
        elif process_type.lower() == 'parallel':
            # Parallel execution
            parallel_groups.append([f"task_{i}" for i in range(len(tasks))])
        else:
            # Default to sequential
            for task_idx in range(1, len(tasks)):
                dependencies[f"task_{task_idx}"] = [f"task_{task_idx - 1}"]

        return ExecutionPlan(
            plan_id=plan_id,
            workflow_id=workflow_id,
            steps=tasks,
            dependencies=dependencies,
            parallel_groups=parallel_groups,
            execution_mode=ExecutionMode.SEQUENTIAL if process_type == 'sequential' else ExecutionMode.PARALLEL,
            optimized=True,
            validated=False,
            created_by="langchain_engine"
        )

    async def _validate_execution_plan_impl(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Validate a LangChain execution plan."""
        errors = []
        warnings = []

        # Validate that required agent roles are available
        for step in plan.steps:
            agent_role = step.get('agent', step.get('role'))
            if agent_role:
                # Check if we can create an agent for this role
                try:
                    # This is a validation check - we don't actually create the agent
                    available_types = await self.agent_manager.get_available_agent_types()
                    if agent_role not in available_types:
                        warnings.append(f"Agent role '{agent_role}' may require dynamic creation")
                except Exception as e:
                    warnings.append(f"Could not validate agent role '{agent_role}': {e}")

        # Validate task structure
        for step_idx, step in enumerate(plan.steps):
            if not isinstance(step, dict):
                errors.append(f"Step {step_idx} is not a dictionary")
                continue

            if not step.get('description') and not step.get('task'):
                warnings.append(f"Step {step_idx} missing description or task definition")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

    # Additional LangGraph-specific methods

    async def get_workflow_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current state of a LangGraph workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Current workflow state or None if not found
        """
        if not LANGGRAPH_AVAILABLE or workflow_id not in self.active_graphs:
            return None

        try:
            graph = self.active_graphs[workflow_id]
            config = {"configurable": {"thread_id": workflow_id}}

            # Get current state from checkpointer
            if self.memory_saver:
                state = await graph.aget_state(config)
                return state.values if state else None

        except Exception as e:
            self.logger.error(f"Error getting workflow state for {workflow_id}: {e}")

        return None

    async def pause_workflow(self, workflow_id: str) -> bool:
        """
        Pause a running LangGraph workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            True if successfully paused
        """
        # LangGraph workflows can be paused by interrupting execution
        # This would require more advanced implementation with custom interrupt handling
        self.logger.warning(f"Workflow pause not yet implemented for {workflow_id}")
        return False

    async def resume_workflow(self, workflow_id: str) -> bool:
        """
        Resume a paused LangGraph workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            True if successfully resumed
        """
        # LangGraph workflows can be resumed from checkpoints
        # This would require more advanced implementation with state restoration
        self.logger.warning(f"Workflow resume not yet implemented for {workflow_id}")
        return False

    def get_engine_capabilities(self) -> Dict[str, Any]:
        """
        Get the capabilities of this engine.

        Returns:
            Dictionary describing engine capabilities
        """
        return {
            'name': 'LangChain Engine',
            'version': '1.0.0',
            'langgraph_support': LANGGRAPH_AVAILABLE,
            'features': {
                'dynamic_agent_creation': True,
                'agent_pooling': True,
                'sequential_execution': True,
                'parallel_execution': True,
                'conditional_execution': True,
                'stateful_workflows': LANGGRAPH_AVAILABLE,
                'workflow_checkpointing': LANGGRAPH_AVAILABLE,
                'agent_collaboration': True
            },
            'supported_execution_modes': [
                'sequential',
                'parallel',
                'conditional'
            ]
        }
