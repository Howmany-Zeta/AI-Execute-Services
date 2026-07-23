# Archived tests — AIECS 2.1.0 task_tools slim

Moved when built-in task tools were removed from core:

- `chart_tool`, `classfire_tool`, `office_tool`, `pandas_tool`, `report_tool`, `stats_tool`

Retained in `aiecs.tools.task_tools`: `image_tool`, `research_tool`.  
Web search remains at `aiecs.tools.search_tool`.

Archived:

- `unit/tools/test_{chart,classfire,office,pandas,report}_tool.py`
- `integration/agent/test_agent_performance_enhancements.py` (pandas/stats fixtures)
