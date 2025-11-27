Advanced Usage
==============

This guide covers advanced usage patterns and best practices for AIECS.

Agent System
------------

AIECS provides a powerful agent system for building autonomous AI agents.

Creating Custom Agents
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from aiecs.domain.agent.base_agent import BaseAgent
   from aiecs.domain.agent.agent_config import AgentConfig

   class MyCustomAgent(BaseAgent):
       def __init__(self, config: AgentConfig):
           super().__init__(config)
       
       async def process_task(self, task):
           # Custom task processing logic
           result = await self.execute_with_tools(task)
           return result

   # Create and use the agent
   config = AgentConfig(
       name="MyAgent",
       description="A custom agent",
       tools=["web_scraper", "document_parser"]
   )
   
   agent = MyCustomAgent(config)
   result = await agent.process_task({"query": "Search for information"})

Tool Integration
----------------

Creating Custom Tools
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from aiecs.tools.base_tool import BaseTool
   from pydantic import BaseModel, Field

   class MyToolConfig(BaseModel):
       api_key: str = Field(description="API key for the service")

   class MyCustomTool(BaseTool):
       name = "my_custom_tool"
       description = "A custom tool for specific tasks"
       
       def __init__(self, config: MyToolConfig):
           super().__init__()
           self.config = config
       
       async def execute(self, parameters: dict):
           # Tool execution logic
           result = await self._process(parameters)
           return result
       
       async def _process(self, parameters: dict):
           # Implementation details
           return {"status": "success", "data": parameters}

   # Register and use the tool
   tool = MyCustomTool(config=MyToolConfig(api_key="your_key"))
   result = await tool.execute({"input": "data"})

Context Management
------------------

AIECS provides sophisticated context management for maintaining conversation state.

Using Context Engine
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from aiecs.domain.context.context_engine import ContextEngine
   from aiecs.domain.context.context_config import ContextConfig

   # Initialize context engine
   config = ContextConfig(
       max_history_length=100,
       compression_enabled=True
   )
   
   context_engine = ContextEngine(config)
   
   # Add messages to context
   await context_engine.add_message({
       "role": "user",
       "content": "Hello, how are you?"
   })
   
   await context_engine.add_message({
       "role": "assistant",
       "content": "I'm doing well, thank you!"
   })
   
   # Retrieve context
   context = await context_engine.get_context()
   print(context)

Task Orchestration
------------------

Complex Task Workflows
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from aiecs.application.orchestrator import TaskOrchestrator
   from aiecs.domain.task.task_definition import TaskDefinition

   # Define a complex workflow
   orchestrator = TaskOrchestrator()
   
   # Create task definitions
   task1 = TaskDefinition(
       name="fetch_data",
       tool="web_scraper",
       parameters={"url": "https://example.com"}
   )
   
   task2 = TaskDefinition(
       name="process_data",
       tool="pandas_tool",
       parameters={"operation": "analyze"},
       depends_on=["fetch_data"]
   )
   
   task3 = TaskDefinition(
       name="generate_report",
       tool="document_creator",
       parameters={"template": "report"},
       depends_on=["process_data"]
   )
   
   # Execute workflow
   results = await orchestrator.execute_workflow([task1, task2, task3])

Error Handling
--------------

Robust Error Handling
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from aiecs.common.exceptions import AIECSException
   from tenacity import retry, stop_after_attempt, wait_exponential

   @retry(
       stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=4, max=10)
   )
   async def execute_with_retry(tool, parameters):
       try:
           result = await tool.execute(parameters)
           return result
       except AIECSException as e:
           print(f"Error: {e}")
           raise

Monitoring and Observability
-----------------------------

Metrics Collection
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from aiecs.infrastructure.monitoring.metrics_collector import MetricsCollector

   # Initialize metrics collector
   metrics = MetricsCollector()
   
   # Record metrics
   metrics.record_task_execution(
       task_id="task_123",
       duration=1.5,
       status="success"
   )
   
   # Get metrics
   stats = metrics.get_statistics()
   print(stats)

Distributed Tracing
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from aiecs.infrastructure.monitoring.tracer import Tracer

   # Initialize tracer
   tracer = Tracer(service_name="aiecs")
   
   # Create spans
   with tracer.start_span("task_execution") as span:
       span.set_tag("task_id", "task_123")
       result = await execute_task()
       span.set_tag("status", "success")

Performance Optimization
------------------------

Caching Strategies
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from aiecs.infrastructure.cache.cache_manager import CacheManager

   # Initialize cache
   cache = CacheManager()
   
   # Cache results
   await cache.set("key", "value", ttl=3600)
   
   # Retrieve cached data
   value = await cache.get("key")

Connection Pooling
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from aiecs.infrastructure.persistence.database import DatabaseManager

   # Configure connection pool
   db = DatabaseManager(
       pool_size=20,
       max_overflow=10,
       pool_timeout=30
   )

Best Practices
--------------

1. **Use async/await**: Leverage asynchronous programming for better performance
2. **Implement retries**: Use retry mechanisms for transient failures
3. **Monitor resources**: Track memory and CPU usage
4. **Log appropriately**: Use structured logging for better debugging
5. **Test thoroughly**: Write comprehensive tests for custom components

See Also
--------

* :doc:`api/core` - Core API reference
* :doc:`api/tools` - Tools API reference
* :doc:`configuration` - Configuration guide

