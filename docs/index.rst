.. AIECS documentation master file

AIECS - AI Execute Services
============================

.. image:: https://img.shields.io/badge/python-3.10%2B-blue.svg
   :target: https://www.python.org/downloads/
   :alt: Python Version

.. image:: https://img.shields.io/badge/License-MIT-yellow.svg
   :target: https://opensource.org/licenses/MIT
   :alt: License: MIT

.. image:: https://badge.fury.io/py/aiecs.svg
   :target: https://badge.fury.io/py/aiecs
   :alt: PyPI version

Welcome to AIECS (AI Execute Services), a powerful Python middleware framework for building AI-powered applications with tool orchestration, task execution, and multi-provider LLM support.

Features
--------

* **Multi-Provider LLM Support**: Seamlessly integrate with OpenAI, Google Vertex AI, and xAI
* **Tool Orchestration**: Extensible tool system for various tasks (web scraping, data analysis, document processing, etc.)
* **Asynchronous Task Execution**: Built on Celery for scalable task processing
* **Real-time Communication**: WebSocket support for live updates and progress tracking
* **Enterprise-Ready**: Production-grade architecture with PostgreSQL, Redis, and Google Cloud Storage integration
* **Extensible Architecture**: Easy to add custom tools and AI providers

Quick Start
-----------

Installation
~~~~~~~~~~~~

Install AIECS from PyPI:

.. code-block:: bash

   pip install aiecs

Or install with documentation dependencies:

.. code-block:: bash

   pip install aiecs[docs]

Basic Usage
~~~~~~~~~~~

.. code-block:: python

   from aiecs import AIECSClient
   
   # Initialize the client
   client = AIECSClient()
   
   # Execute a task
   result = await client.execute_task(
       task_type="text_generation",
       parameters={"prompt": "Hello, world!"}
   )

Documentation Contents
----------------------

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   installation
   quickstart
   configuration
   usage
   user/USAGE_GUIDE
   user/PROJECT_SUMMARY

.. toctree::
   :maxdepth: 3
   :caption: Domain Agent

   user/DOMAIN_AGENT/README
   user/DOMAIN_AGENT/AGENT_INTEGRATION
   user/DOMAIN_AGENT/API_REFERENCE
   user/DOMAIN_AGENT/EXAMPLES
   user/DOMAIN_AGENT/FAQ
   user/DOMAIN_AGENT/COLLABORATION
   user/DOMAIN_AGENT/COMPRESSION_GUIDE
   user/DOMAIN_AGENT/CONTEXTENGINE_INTEGRATION
   user/DOMAIN_AGENT/ERROR_RECOVERY
   user/DOMAIN_AGENT/LEARNING
   user/DOMAIN_AGENT/OBSERVATION_REASONING
   user/DOMAIN_AGENT/PARALLEL_TOOL_EXECUTION
   user/DOMAIN_AGENT/PERFORMANCE_MONITORING
   user/DOMAIN_AGENT/PERFORMANCE_OPTIMIZATION
   user/DOMAIN_AGENT/RESOURCE_MANAGEMENT
   user/DOMAIN_AGENT/SERIALIZATION
   user/DOMAIN_AGENT/SESSION_MANAGEMENT
   user/DOMAIN_AGENT/STREAMING
   user/DOMAIN_AGENT/TOOL_CACHING
   user/DOMAIN_AGENT/TOOL_OBSERVATION

.. toctree::
   :maxdepth: 3
   :caption: Knowledge Graph

   user/knowledge_graph/README
   user/knowledge_graph/USER_GUIDE
   user/knowledge_graph/API_REFERENCE
   user/knowledge_graph/CONFIGURATION_GUIDE
   user/knowledge_graph/CONFIGURATION
   user/knowledge_graph/PERFORMANCE_GUIDE
   user/knowledge_graph/RUNNABLE_PATTERN
   user/knowledge_graph/SCHEMA_MAPPING_GUIDE
   user/knowledge_graph/STRUCTURED_DATA_PIPELINE
   user/knowledge_graph/TROUBLESHOOTING
   user/knowledge_graph/tutorials/END_TO_END_TUTORIAL
   user/knowledge_graph/tutorials/MULTI_HOP_REASONING_TUTORIAL
   user/knowledge_graph/tutorials/DOMAIN_SPECIFIC_TUTORIAL
   user/knowledge_graph/examples/visualization_examples
   user/knowledge_graph/examples/json_to_graph_tutorial
   user/knowledge_graph/examples/csv_to_graph_tutorial
   user/knowledge_graph/tools/GRAPH_BUILDER_TOOL
   user/knowledge_graph/tools/GRAPH_REASONING_TOOL
   user/knowledge_graph/tools/GRAPH_SEARCH_TOOL
   user/knowledge_graph/agent/AGENT_INTEGRATION
   user/knowledge_graph/agent/USAGE_EXAMPLES
   user/knowledge_graph/agent/KNOWLEDGE_RETRIEVAL_CONFIGURATION
   user/knowledge_graph/agent/METRICS_AND_MONITORING
   user/knowledge_graph/reasoning/REASONING_ENGINE
   user/knowledge_graph/reasoning/type-enum-usage-guide
   user/knowledge_graph/reasoning/query-optimization-guide
   user/knowledge_graph/reasoning/schema-caching-guide
   user/knowledge_graph/reasoning/reranking-strategies-guide
   user/knowledge_graph/reasoning/result-reranker-api
   user/knowledge_graph/reasoning/logic_query_parser
   user/knowledge_graph/reasoning/grammar-docs
   user/knowledge_graph/search/SEARCH_STRATEGIES
   user/knowledge_graph/deployment/PRODUCTION_DEPLOYMENT
   user/knowledge_graph/deployment/SECURITY
   user/knowledge_graph/deployment/BACKEND_CONFIGURATION
   user/knowledge_graph/performance/PERFORMANCE_GUIDE

.. toctree::
   :maxdepth: 3
   :caption: Tools and Configuration

   user/TOOLS_USED_INSTRUCTION/DOCUMENT_PARSER_TOOL_CONFIGURATION
   user/TOOLS_USED_INSTRUCTION/DOCUMENT_WRITER_TOOL_CONFIGURATION
   user/TOOLS_USED_INSTRUCTION/CONFIGURATION_BEST_PRACTICES
   user/TOOLS_USED_INSTRUCTION/AI_DOCUMENT_WRITER_ORCHESTRATOR_CONFIGURATION
   user/TOOLS_USED_INSTRUCTION/AI_DOCUMENT_ORCHESTRATOR_CONFIGURATION
   user/TOOLS_USED_INSTRUCTION/AI_DATA_ANALYSIS_ORCHESTRATOR_CONFIGURATION
   user/TOOLS_USED_INSTRUCTION/APISOURCE_TOOL_CONFIGURATION_REFERENCE
   user/TOOLS_USED_INSTRUCTION/APISOURCE_TOOL_DEVELOPER_GUIDE
   user/TOOLS_USED_INSTRUCTION/APISOURCE_TOOL_TECHNICAL_DOCUMENTATION
   user/TOOLS_USED_INSTRUCTION/SEARCH_TOOL_CONFIGURATION_REFERENCE
   user/TOOLS_USED_INSTRUCTION/SEARCH_TOOL_DEVELOPER_GUIDE
   user/TOOLS_USED_INSTRUCTION/SEARCH_TOOL_TECHNICAL_DOCUMENTATION
   user/TOOLS_USED_INSTRUCTION/STATISTICAL_ANALYZER_TOOL_CONFIGURATION
   user/TOOLS_USED_INSTRUCTION/MODEL_TRAINER_TOOL_CONFIGURATION
   user/TOOLS_USED_INSTRUCTION/DATA_VISUALIZER_TOOL_CONFIGURATION
   user/TOOLS_USED_INSTRUCTION/DATA_TRANSFORMER_TOOL_CONFIGURATION
   user/TOOLS_USED_INSTRUCTION/DATA_PROFILER_TOOL_CONFIGURATION
   user/TOOLS_USED_INSTRUCTION/DATA_LOADER_TOOL_CONFIGURATION
   user/TOOLS_USED_INSTRUCTION/AI_REPORT_ORCHESTRATOR_TOOL_CONFIGURATION
   user/TOOLS_USED_INSTRUCTION/AI_INSIGHT_GENERATOR_TOOL_CONFIGURATION
   user/TOOLS_USED_INSTRUCTION/DOCUMENT_CREATOR_TOOL_CONFIGURATION
   user/TOOLS_USED_INSTRUCTION/REPORT_TOOL_CONFIGURATION
   user/TOOLS_USED_INSTRUCTION/CHART_TOOL_CONFIGURATION
   user/TOOLS_USED_INSTRUCTION/CHART_TOOL_LANGCHAIN_GUIDE
   user/TOOLS_USED_INSTRUCTION/CLASSIFIER_TOOL_CONFIGURATION
   user/TOOLS_USED_INSTRUCTION/CONTENT_INSERTION_TOOL_CONFIGURATION
   user/TOOLS_USED_INSTRUCTION/DOCUMENT_LAYOUT_TOOL_CONFIGURATION
   user/TOOLS_USED_INSTRUCTION/IMAGE_TOOL_CONFIGURATION
   user/TOOLS_USED_INSTRUCTION/OFFICE_TOOL_CONFIGURATION
   user/TOOLS_USED_INSTRUCTION/PANDAS_TOOL_CONFIGURATION
   user/TOOLS_USED_INSTRUCTION/RESEARCH_TOOL_CONFIGURATION
   user/TOOLS_USED_INSTRUCTION/SCRAPER_TOOL_CONFIGURATION
   user/TOOLS_USED_INSTRUCTION/STATS_TOOL_CONFIGURATION
   user/TOOLS_USED_INSTRUCTION/STATISTICS_LAYER
   user/TOOLS_USED_INSTRUCTION/DOCUMENT_CREATION_ARCHITECTURE
   user/TOOLS_USED_INSTRUCTION/DOCUMENT_CREATION_QUICK_REFERENCE
   user/TOOLS_USED_INSTRUCTION/DOCUMENT_WRITER_TOOL
   user/TOOLS_USED_INSTRUCTION/DOCUMENT_PARSER_TOOL
   user/TOOLS_USED_INSTRUCTION/DOCUMENT_PARSER_QUICK_START
   user/TOOLS_USED_INSTRUCTION/TOOL_SPECIAL_SPECIAL_INSTRUCTIONS
   user/TOOLS/TOOL_EXECUTOR_TTL_STRATEGIES
   user/TOOLS/TOOL_NAMING_CONVENTION
   user/TOOLS/TOOLS_TOOL_EXECUTOR
   user/TOOLS/TOOLS_TEMP_FILE_MANAGER
   user/TOOLS/TOOLS_LANGCHAIN_ADAPTER
   user/TOOLS/TOOLS_BASE_TOOL
   user/TOOLS/TOOLS_SCHEMA_GENERATOR

.. toctree::
   :maxdepth: 3
   :caption: LLM Integration

   user/LLM/LLM_CONFIGURATION
   user/LLM/CUSTOM_LLM_CLIENTS
   user/LLM/BASE_LLM_CLIENT
   user/LLM/LLM_AI_CLIENTS
   user/LLM/LLM_CUSTOM_CALLBACKS

.. toctree::
   :maxdepth: 3
   :caption: Domain Modules

   user/DOMAIN_COMMUNITY/README
   user/DOMAIN_COMMUNITY/INDEX
   user/DOMAIN_COMMUNITY/USAGE_GUIDE
   user/DOMAIN_COMMUNITY/API_REFERENCE
   user/DOMAIN_COMMUNITY/EXAMPLES
   user/DOMAIN_COMMUNITY/ARCHITECTURE
   user/DOMAIN_COMMUNITY/ADDENDUM
   user/DOMAIN_COMMUNITY/ANALYTICS
   user/DOMAIN_CONTEXT/CONVERSATION_MODELS
   user/DOMAIN_CONTEXT/CONTENT_ENGINE
   user/DOMAIN_EXECUTION/EXECUTION_MODELS
   user/DOMAIN_TASK/TASK_MODELS
   user/DOMAIN_TASK/TASK_CONTEXT
   user/DOMAIN_TASK/DSL_PROCESSOR
   user/TASKS/TASKS_WORKER

.. toctree::
   :maxdepth: 3
   :caption: Infrastructure

   user/INFRASTRUCTURE_MESSAGEING/WEBSOCKET_MANAGER
   user/INFRASTRUCTURE_MESSAGEING/CELERY_TASK_MANAGER
   user/INFRASTRUCTURE_MONITORING/TRACING_MANAGER
   user/INFRASTRUCTURE_MONITORING/EXECUTOR_METRICS
   user/INFRASTRUCTURE_MONITORING/GLOBAL_METRICS_MANAGER
   user/INFRASTRUCTURE_PERSISTENCE/DATABASE_MANAGER
   user/INFRASTRUCTURE_PERSISTENCE/FILE_STORAGE
   user/INFRASTRUCTURE_PERSISTENCE/REDIS_CLIENT

.. toctree::
   :maxdepth: 3
   :caption: Core and Application

   user/CORE/STORAGE_INTERFACES
   user/CORE/EXECUTION_INTERFACES
   user/CONFIG/SERVICE_REGISTRY
   user/CONFIG/CONFIG_MANAGEMENT
   user/APPLICATION/OPERATION_EXECUTOR
   user/UTILS/LLM_OUTPUT_STRUCTOR
   user/UTILS/PROMPT_LOADER
   user/UTILS/TOKEN_USAGE_REPOSITORY
   user/UTILS/EXECUTION_UTILS
   user/UTILS/BASE_CALLBACK

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/core
   api/domain
   api/application
   api/infrastructure
   api/tools
   api/llm

.. toctree::
   :maxdepth: 1
   :caption: Development

   developer/contributing
   changelog

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

