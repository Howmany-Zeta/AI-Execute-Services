Installation
============

Requirements
------------

* Python 3.10 or higher
* pip (Python package installer)

Basic Installation
------------------

From PyPI (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~

The easiest way to install AIECS is from PyPI:

.. code-block:: bash

   pip install aiecs

From Source
~~~~~~~~~~~

To install from source:

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/aiecs-team/aiecs.git
   cd aiecs

   # Install in development mode
   pip install -e .

   # Or install with development dependencies
   pip install -e ".[dev]"

Optional Dependencies
---------------------

Documentation
~~~~~~~~~~~~~

To build the documentation locally:

.. code-block:: bash

   pip install aiecs[docs]

Development
~~~~~~~~~~~

For development work:

.. code-block:: bash

   pip install aiecs[dev]

Post-Installation Setup
-----------------------

After installation, you can use the built-in tools to set up dependencies and verify your installation:

Check Dependencies
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Check all dependencies
   aiecs-check-deps

   # Quick dependency check
   aiecs-quick-check

   # Fix missing dependencies
   aiecs-fix-deps

Download NLP Data
~~~~~~~~~~~~~~~~~

If you plan to use NLP features:

.. code-block:: bash

   # Download required NLP data packages
   aiecs-download-nlp-data

Apply Patches
~~~~~~~~~~~~~

Some dependencies may require patches:

.. code-block:: bash

   # Apply weasel validator patch
   aiecs-patch-weasel

Configuration
-------------

Create a ``.env`` file in your project root with the required configuration:

.. code-block:: bash

   # LLM Provider Configuration
   OPENAI_API_KEY=your_openai_api_key
   VERTEX_PROJECT_ID=your_gcp_project_id
   
   # Database Configuration
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=aiecs
   POSTGRES_USER=aiecs_user
   POSTGRES_PASSWORD=your_password
   
   # Redis Configuration
   REDIS_HOST=localhost
   REDIS_PORT=6379
   
   # Google Cloud Storage (Optional)
   GCS_BUCKET_NAME=your_bucket_name

See the :doc:`configuration` page for detailed configuration options.

Verification
------------

Verify your installation by running:

.. code-block:: python

   import aiecs
   print(aiecs.__version__)

Or check the version from the command line:

.. code-block:: bash

   aiecs-version

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Import Errors**

If you encounter import errors, ensure all dependencies are installed:

.. code-block:: bash

   aiecs-check-deps

**Database Connection Issues**

Verify your PostgreSQL configuration in the ``.env`` file and ensure the database server is running.

**Redis Connection Issues**

Ensure Redis is running and accessible at the configured host and port.

For more help, visit our `GitHub Issues <https://github.com/aiecs-team/aiecs/issues>`_ page.

