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
   :caption: User Guide

   installation
   quickstart
   configuration
   usage

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

   contributing
   changelog

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

