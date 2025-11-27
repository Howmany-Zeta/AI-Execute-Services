Quick Start Guide
=================

This guide will help you get started with AIECS quickly.

Prerequisites
-------------

Before you begin, ensure you have:

* Python 3.10 or higher installed
* AIECS installed (see :doc:`installation`)
* Required environment variables configured

Basic Usage
-----------

Starting the Server
~~~~~~~~~~~~~~~~~~~

Start the AIECS FastAPI server:

.. code-block:: bash

   # Using the CLI
   aiecs

   # Or using Python module
   python -m aiecs

The server will start on ``http://localhost:8000`` by default.

Using the Client
~~~~~~~~~~~~~~~~

Here's a simple example of using the AIECS client:

.. code-block:: python

   from aiecs.aiecs_client import AIECSClient
   import asyncio

   async def main():
       # Initialize the client
       client = AIECSClient(base_url="http://localhost:8000")
       
       # Execute a simple task
       result = await client.execute_task(
           task_type="text_generation",
           parameters={
               "prompt": "Explain what AIECS is in one sentence.",
               "max_tokens": 100
           }
       )
       
       print(result)

   if __name__ == "__main__":
       asyncio.run(main())

Working with Tools
------------------

AIECS provides a rich set of tools for various tasks.

Document Processing
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from aiecs.tools.docs.document_parser_tool import DocumentParserTool

   # Initialize the tool
   parser = DocumentParserTool()
   
   # Parse a document
   result = await parser.execute({
       "operation": "parse_document",
       "document_path": "/path/to/document.pdf"
   })
   
   print(result["content"])

Web Scraping
~~~~~~~~~~~~

.. code-block:: python

   from aiecs.tools.web.web_scraper_tool import WebScraperTool

   # Initialize the tool
   scraper = WebScraperTool()
   
   # Scrape a webpage
   result = await scraper.execute({
       "operation": "scrape_url",
       "url": "https://example.com"
   })
   
   print(result["content"])

Data Analysis
~~~~~~~~~~~~~

.. code-block:: python

   from aiecs.tools.data.pandas_tool import PandasTool

   # Initialize the tool
   pandas_tool = PandasTool()
   
   # Analyze data
   result = await pandas_tool.execute({
       "operation": "read_csv",
       "file_path": "/path/to/data.csv"
   })
   
   print(result["dataframe_info"])

Using LLM Providers
-------------------

OpenAI
~~~~~~

.. code-block:: python

   from aiecs.llm.llm_integration import LLMIntegration

   # Initialize with OpenAI
   llm = LLMIntegration(provider="openai")
   
   # Generate text
   response = await llm.generate(
       prompt="What is artificial intelligence?",
       max_tokens=150
   )
   
   print(response)

Google Vertex AI
~~~~~~~~~~~~~~~~

.. code-block:: python

   from aiecs.llm.llm_integration import LLMIntegration

   # Initialize with Vertex AI
   llm = LLMIntegration(provider="vertex")
   
   # Generate text
   response = await llm.generate(
       prompt="Explain machine learning.",
       max_tokens=150
   )
   
   print(response)

Task Execution with Celery
---------------------------

AIECS uses Celery for asynchronous task execution.

Starting Workers
~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Start a Celery worker
   celery -A aiecs.tasks.worker worker --loglevel=info

Submitting Tasks
~~~~~~~~~~~~~~~~

.. code-block:: python

   from aiecs.tasks.worker import execute_task

   # Submit a task
   task = execute_task.delay(
       task_type="data_processing",
       parameters={"input": "data"}
   )
   
   # Get task result
   result = task.get(timeout=30)
   print(result)

WebSocket Communication
-----------------------

AIECS supports real-time communication via WebSockets.

.. code-block:: python

   import socketio

   # Create a Socket.IO client
   sio = socketio.AsyncClient()

   @sio.on('task_update')
   async def on_task_update(data):
       print(f"Task update: {data}")

   async def main():
       await sio.connect('http://localhost:8000')
       await sio.wait()

   if __name__ == '__main__':
       asyncio.run(main())

Next Steps
----------

* Read the :doc:`configuration` guide for detailed configuration options
* Explore the :doc:`api/tools` reference for available tools
* Check out the :doc:`usage` guide for advanced usage patterns

