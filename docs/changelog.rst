Changelog
=========

All notable changes to AIECS will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

[Unreleased]
------------

Changed
~~~~~~~

* **BREAKING**: HybridAgent no longer supports ReAct text format (TOOL:/OPERATION:/PARAMETERS:, FINAL RESPONSE: finish). Use OpenAI-compatible Function Calling only. See docs/developer/DOMAIN_AGENT/REACT_TO_FUNCTION_CALLING_MIGRATION.md.
* **BREAKING**: Removed `react_format_enabled` from AgentConfiguration.
* HybridAgent tool loop aligned with Claude BetaToolRunner: append-only messages, no iteration labels, first user message = raw task only.
* Callers (e.g., MasterController) MUST NOT append initial_act_prompt or Step 1/2 to task; move to system prompt if needed.

Planned (v3)
~~~~~~~~~~~~

* **BREAKING (v3, E-11)**: Remove public ``SkillCapableMixin`` API (``attach_skills``, ``get_skill_context``, ``detach_all_skills``). Skill attach, context injection, and detach will be **SkillPlugin only**. See ``docs/developer/DOMAIN_AGENT/PLUGIN_SYSTEM.md`` §SkillCapableMixin removal plan for caller inventory and migration checklist. Mixin deletion is a **separate breaking PR** after grep confirms no new direct callers.

Added (Phase 3+ extensions)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

* ``KnowledgePlugin`` (``knowledge@builtin``): PRE_TASK augment, PRE_MAIN_LOOP graph short-circuit, ON_ITERATION_START retrieval; ``KnowledgeAwareAgent`` delegates to plugin kernel (E-01–E-07).
* ``CollaborationPlugin`` (``collaboration@builtin``): AGENT_INIT peer registry in ``plugin_state["collaboration.peers"]``; optional BUILD_MESSAGES hint; no cross-agent orchestration (E-08).
* Knowledge parity golden fixtures: ``knowledge_augment.yaml``, ``knowledge_short_circuit.yaml``.

[1.5.3] - 2024-01-XX
--------------------

Added
~~~~~

* Comprehensive Sphinx documentation
* Read the Docs integration
* API reference documentation
* User guides and tutorials

Changed
~~~~~~~

* Improved configuration management
* Enhanced error handling
* Updated dependencies

Fixed
~~~~~

* Various bug fixes and improvements

[1.5.2] - 2024-01-XX
--------------------

Added
~~~~~

* New tool validation scripts
* Enhanced type checking
* Improved dependency management

Changed
~~~~~~~

* Updated LLM provider integrations
* Improved performance

[1.5.1] - 2024-01-XX
--------------------

Added
~~~~~

* Document processing tools
* Web scraping capabilities
* Data analysis tools

Changed
~~~~~~~

* Refactored core architecture
* Improved async support

Fixed
~~~~~

* Database connection issues
* Cache invalidation bugs

[1.5.0] - 2024-01-XX
--------------------

Added
~~~~~

* Multi-provider LLM support
* Agent system
* Context management
* Task orchestration
* WebSocket support

Changed
~~~~~~~

* Major architecture refactoring
* Renamed from "app" to "aiecs"
* Updated project structure

[1.0.0] - 2023-XX-XX
--------------------

Added
~~~~~

* Initial release
* Basic FastAPI server
* Celery task queue
* PostgreSQL integration
* Redis caching
* Basic tool system

.. note::
   For a complete list of changes, see the `GitHub releases page <https://github.com/aiecs-team/aiecs/releases>`_.

