Configuration
=============

AIECS uses environment variables for configuration. You can set these in a ``.env`` file or as system environment variables.

Environment Variables
---------------------

LLM Provider Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~

OpenAI
^^^^^^

.. code-block:: bash

   OPENAI_API_KEY=your_openai_api_key
   OPENAI_API_BASE=https://api.openai.com/v1  # Optional
   OPENAI_MODEL=gpt-4  # Default model

Google Vertex AI
^^^^^^^^^^^^^^^^

.. code-block:: bash

   VERTEX_PROJECT_ID=your_gcp_project_id
   VERTEX_LOCATION=us-central1  # Default location
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

xAI
^^^

.. code-block:: bash

   XAI_API_KEY=your_xai_api_key
   XAI_API_BASE=https://api.x.ai/v1

Database Configuration
~~~~~~~~~~~~~~~~~~~~~~

PostgreSQL
^^^^^^^^^^

.. code-block:: bash

   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=aiecs
   POSTGRES_USER=aiecs_user
   POSTGRES_PASSWORD=your_password
   POSTGRES_POOL_SIZE=10  # Connection pool size
   POSTGRES_MAX_OVERFLOW=20  # Max overflow connections

Redis Configuration
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   REDIS_HOST=localhost
   REDIS_PORT=6379
   REDIS_DB=0
   REDIS_PASSWORD=  # Optional
   REDIS_MAX_CONNECTIONS=50

Celery Configuration
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   CELERY_BROKER_URL=redis://localhost:6379/0
   CELERY_RESULT_BACKEND=redis://localhost:6379/0
   CELERY_TASK_SERIALIZER=json
   CELERY_RESULT_SERIALIZER=json
   CELERY_ACCEPT_CONTENT=["json"]
   CELERY_TIMEZONE=UTC
   CELERY_ENABLE_UTC=true

Google Cloud Storage
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   GCS_BUCKET_NAME=your_bucket_name
   GCS_PROJECT_ID=your_gcp_project_id
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

Server Configuration
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   HOST=0.0.0.0
   PORT=8000
   DEBUG=false
   LOG_LEVEL=INFO
   WORKERS=4  # Number of worker processes

Tool Configuration
------------------

Document Parser Tool
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   DOC_PARSER_GCS_PROJECT_ID=your_project_id
   DOC_PARSER_GCS_BUCKET_NAME=your_bucket_name
   DOC_PARSER_TEMP_DIR=/tmp/doc_parser
   DOC_PARSER_MAX_FILE_SIZE=104857600  # 100MB in bytes

Document Creator Tool
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   DOC_CREATOR_TEMPLATES_DIR=/path/to/templates
   DOC_CREATOR_OUTPUT_DIR=/path/to/output
   DOC_CREATOR_DEFAULT_FORMAT=markdown
   DOC_CREATOR_DEFAULT_STYLE=default
   DOC_CREATOR_AUTO_BACKUP=true

Web Scraper Tool
~~~~~~~~~~~~~~~~

.. code-block:: bash

   WEB_SCRAPER_USER_AGENT=AIECS/1.5.3
   WEB_SCRAPER_TIMEOUT=30
   WEB_SCRAPER_MAX_RETRIES=3
   WEB_SCRAPER_ENABLE_JAVASCRIPT=false

Configuration File
------------------

You can also use a configuration file for more complex setups.

Example ``.env`` File
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # LLM Providers
   OPENAI_API_KEY=sk-...
   VERTEX_PROJECT_ID=my-project-123
   
   # Database
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=aiecs
   POSTGRES_USER=aiecs_user
   POSTGRES_PASSWORD=secure_password
   
   # Redis
   REDIS_HOST=localhost
   REDIS_PORT=6379
   
   # Celery
   CELERY_BROKER_URL=redis://localhost:6379/0
   CELERY_RESULT_BACKEND=redis://localhost:6379/0
   
   # Google Cloud
   GCS_BUCKET_NAME=my-aiecs-bucket
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
   
   # Server
   HOST=0.0.0.0
   PORT=8000
   DEBUG=false
   LOG_LEVEL=INFO

Programmatic Configuration
--------------------------

You can also configure AIECS programmatically:

.. code-block:: python

   from aiecs.config.config import Settings

   # Create custom settings
   settings = Settings(
       openai_api_key="your_key",
       postgres_host="localhost",
       postgres_port=5432,
       redis_host="localhost"
   )

   # Use settings in your application
   from aiecs.llm.llm_integration import LLMIntegration
   
   llm = LLMIntegration(
       provider="openai",
       api_key=settings.openai_api_key
   )

Best Practices
--------------

1. **Never commit secrets**: Keep your ``.env`` file out of version control
2. **Use environment-specific configs**: Maintain separate configs for dev, staging, and production
3. **Validate configuration**: Use the built-in validation tools to check your configuration
4. **Secure credentials**: Use secret management services in production
5. **Monitor resources**: Configure appropriate pool sizes and timeouts based on your workload

See Also
--------

* :doc:`installation` - Installation guide
* :doc:`quickstart` - Quick start guide
* :doc:`usage` - Advanced usage patterns

