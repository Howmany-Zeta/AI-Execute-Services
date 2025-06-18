import pytest
import asyncio
import json
import sys
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any

# Mock heavy dependencies before importing
sys.modules['websockets'] = MagicMock()
sys.modules['websockets.server'] = MagicMock()
sys.modules['prometheus_client'] = MagicMock()

# Import the refactored summarizer
from app.services.multi_task.services.summarizer import (
    MultiTaskSummarizerRefactored,
    TaskCategory,
    TaskStepResult,
    TaskStatus,
    ErrorCode
)
from app.services.multi_task.tools import MultiTaskTools


class TestMultiTaskSummarizerRefactored:
    """测试重构后的多任务汇总器"""

    @pytest.fixture
    def mock_executor(self):
        """模拟执行器"""
        executor = Mock()
        executor.config = Mock()
        executor.config.call_timeout_seconds = 600
        executor.initialize = AsyncMock()
        executor.execute_with_timeout = AsyncMock()
        executor.execute_dsl_step = AsyncMock()
        executor.execute_operations_sequence = AsyncMock()
        executor.execute_parallel_operations = AsyncMock()
        executor.evaluate_condition = Mock(return_value=True)
        executor.save_task_history = AsyncMock()
        executor.load_task_history = AsyncMock(return_value=[])
        executor.check_task_status = AsyncMock(return_value=TaskStatus.PENDING)
        executor.notify_user = AsyncMock()
        return executor

    @pytest.fixture
    def mock_tools_manager(self):
        """模拟工具管理器"""
        tools_manager = Mock(spec=MultiTaskTools)
        tools_manager.get_available_tools.return_value = ['scraper', 'pandas', 'stats', 'classifier']
        tools_manager.execute_tool = AsyncMock()
        return tools_manager

    @pytest.fixture
    def sample_input_data(self):
        """示例输入数据"""
        return {
            "user_id": "test_user_123",
            "task_id": "test_task_456",
            "text": "Analyze sales data from the last quarter and generate a report"
        }

    @pytest.fixture
    def sample_context(self):
        """示例上下文"""
        return {
            "domain": "business",
            "format": "pdf",
            "urgency": "high"
        }

    @pytest.fixture
    async def summarizer(self, mock_executor, mock_tools_manager):
        """创建重构后的汇总器实例"""
        with patch('app.services.multi_task.services.summarizer.get_executor', return_value=mock_executor):
            with patch('app.services.multi_task.services.summarizer.MultiTaskTools', return_value=mock_tools_manager):
                with patch('app.services.multi_task.services.summarizer.load_yaml_config') as mock_load_yaml:
                    # 模拟 YAML 配置
                    mock_load_yaml.side_effect = [
                        {  # prompts.yaml
                            "system_prompt": "Test system prompt",
                            "roles": {
                                "intent_parser": {
                                    "goal": "Parse user intent",
                                    "backstory": "Expert in NLP",
                                    "tools_instruction": "Use NLP tools"
                                },
                                "task_decomposer": {
                                    "goal": "Break down tasks",
                                    "backstory": "Task decomposition expert"
                                },
                                "supervisor": {
                                    "goal": "Quality control",
                                    "backstory": "Quality supervisor"
                                },
                                "planner": {
                                    "goal": "Plan sequences",
                                    "backstory": "Strategic planner"
                                },
                                "director": {
                                    "goal": "Accept outcomes",
                                    "backstory": "Quality director"
                                }
                            }
                        },
                        {  # tasks.yaml
                            "system_tasks": {
                                "parse_intent": {
                                    "description": "Parse user intent",
                                    "agent": "intent_parser",
                                    "expected_output": "List of categories",
                                    "task_type": "fast"
                                }
                            },
                            "sub_tasks": {
                                "collect_scrape": {
                                    "description": "Scrape data",
                                    "agent": "fieldwork_webscraper",
                                    "expected_output": "Scraped data",
                                    "task_type": "fast",
                                    "tools": {
                                        "scraper": {
                                            "operations": {
                                                "get_aiohttp": {
                                                    "conditions": [{"if": "domain == 'web'", "then": "execute"}]
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    ]

                    with patch('app.services.multi_task.services.summarizer.Agent'):
                        with patch('app.services.multi_task.services.summarizer.Task'):
                            summarizer = MultiTaskSummarizerRefactored()
                            await summarizer.initialize()
                            return summarizer

    @pytest.mark.asyncio
    async def test_initialization(self, summarizer):
        """测试初始化"""
        assert summarizer is not None
        assert hasattr(summarizer, '_executor')
        assert hasattr(summarizer, 'tools_manager')
        assert hasattr(summarizer, 'agents')
        assert hasattr(summarizer, 'system_tasks')
        assert hasattr(summarizer, 'sub_tasks')

    @pytest.mark.asyncio
    async def test_parse_intent(self, summarizer, sample_input_data, mock_executor):
        """测试意图解析"""
        # 模拟 CrewAI 返回结果
        mock_executor.execute_with_timeout.return_value = '["collect", "analyze", "generate"]'

        result = await summarizer._parse_intent(sample_input_data)

        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(cat, TaskCategory) for cat in result)
        assert TaskCategory.COLLECT in result
        assert TaskCategory.ANALYZE in result
        assert TaskCategory.GENERATE in result

    @pytest.mark.asyncio
    async def test_breakdown_subtasks(self, summarizer, mock_executor):
        """测试子任务分解"""
        categories = [TaskCategory.COLLECT, TaskCategory.ANALYZE]
        expected_breakdown = {
            "collect": ["collect_scrape", "collect_search"],
            "analyze": ["analyze_dataoutcome"]
        }

        mock_executor.execute_with_timeout.return_value = json.dumps(expected_breakdown)

        result = await summarizer._breakdown_subtasks(categories)

        assert result == expected_breakdown
        mock_executor.execute_with_timeout.assert_called_once()

    @pytest.mark.asyncio
    async def test_examine_outcome(self, summarizer, mock_executor):
        """测试结果检查"""
        task_result = {"data": "test_data", "quality": "high"}
        expected_examination = {
            "task": "collect_scrape",
            "credibility": 0.9,
            "confidence": 0.85,
            "passed": True
        }

        mock_executor.execute_with_timeout.return_value = json.dumps(expected_examination)

        result = await summarizer._examine_outcome("collect_scrape", "collect", task_result)

        assert result == expected_examination
        assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_accept_outcome(self, summarizer, mock_executor):
        """测试结果接受"""
        task_result = {"analysis": "comprehensive", "accuracy": "high"}
        expected_acceptance = {
            "task": "analyze_dataoutcome",
            "passed": True,
            "criteria": {
                "meets_request": True,
                "accurate": True,
                "no_synthetic_data": True
            }
        }

        mock_executor.execute_with_timeout.return_value = json.dumps(expected_acceptance)

        result = await summarizer._accept_outcome("analyze_dataoutcome", "analyze", task_result)

        assert result == expected_acceptance
        assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_plan_task_sequence(self, summarizer, mock_executor):
        """测试任务序列规划"""
        subtask_breakdown = {
            "collect": ["collect_scrape"],
            "analyze": ["analyze_dataoutcome"]
        }
        expected_sequence = [
            {
                "if": "intent.includes('collect')",
                "then": [{"task": "collect_scrape", "tools": ["scraper.get_aiohttp"]}]
            },
            {"task": "analyze_dataoutcome", "tools": ["stats.correlation"]}
        ]

        mock_executor.execute_with_timeout.return_value = json.dumps(expected_sequence)

        result = await summarizer._plan_task_sequence(subtask_breakdown)

        assert result == expected_sequence
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_execute_dsl_step(self, summarizer, sample_input_data, sample_context, mock_executor):
        """测试 DSL 步骤执行"""
        step = {"task": "collect_scrape", "tools": ["scraper.get_aiohttp"]}
        intent_categories = ["collect"]

        expected_result = TaskStepResult(
            step="collect/collect_scrape",
            result={"data": "scraped_data"},
            completed=True,
            message="Task completed",
            status=TaskStatus.COMPLETED
        )

        mock_executor.execute_dsl_step.return_value = expected_result

        result = await summarizer._execute_dsl_step(step, intent_categories, sample_input_data, sample_context)

        assert isinstance(result, TaskStepResult)
        assert result.completed is True
        mock_executor.execute_dsl_step.assert_called_once_with(
            step, intent_categories, sample_input_data, sample_context,
            summarizer._execute_single_task, summarizer._execute_batch_task
        )

    @pytest.mark.asyncio
    async def test_execute_single_task(self, summarizer, sample_input_data, sample_context, mock_executor):
        """测试单个任务执行"""
        task_name = "collect_scrape"

        # 模拟操作执行结果
        mock_operation_results = [
            TaskStepResult(
                step="scraper.get_aiohttp",
                result={"scraped_data": "test_data"},
                completed=True,
                message="Scraping completed",
                status=TaskStatus.COMPLETED
            )
        ]
        mock_executor.execute_operations_sequence.return_value = mock_operation_results

        result = await summarizer._execute_single_task(task_name, sample_input_data, sample_context)

        assert isinstance(result, dict)
        assert result["completed"] is True
        assert "collect" in result["step"]

    @pytest.mark.asyncio
    async def test_execute_batch_task(self, summarizer, sample_input_data, sample_context, mock_executor):
        """测试批量任务执行"""
        batch_tasks = [
            {"task": "collect_scrape", "category": "collect"},
            {"task": "collect_search", "category": "collect"}
        ]

        # 模拟并行执行结果
        mock_parallel_results = [
            TaskStepResult(
                step="parallel_0_task.collect_scrape",
                result={"data": "scraped"},
                completed=True,
                message="Scraping completed",
                status=TaskStatus.COMPLETED
            ),
            TaskStepResult(
                step="parallel_1_task.collect_search",
                result={"data": "searched"},
                completed=True,
                message="Search completed",
                status=TaskStatus.COMPLETED
            )
        ]
        mock_executor.execute_parallel_operations.return_value = mock_parallel_results

        results = await summarizer._execute_batch_task(batch_tasks, sample_input_data, sample_context)

        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(r, TaskStepResult) for r in results)

    @pytest.mark.asyncio
    async def test_category_enum_conversion(self, summarizer):
        """测试类别枚举转换"""
        assert summarizer._category_enum("collect") == TaskCategory.COLLECT
        assert summarizer._category_enum("analyze") == TaskCategory.ANALYZE

        with pytest.raises(ValueError):
            summarizer._category_enum("invalid_category")

    @pytest.mark.asyncio
    async def test_determine_task_category(self, summarizer):
        """测试任务类别确定"""
        assert summarizer._determine_task_category("collect_scrape") == "collect"
        assert summarizer._determine_task_category("analyze_dataoutcome") == "analyze"
        assert summarizer._determine_task_category("generate_report") == "generate"
        assert summarizer._determine_task_category("process_data") == "process"
        assert summarizer._determine_task_category("answer_question") == "answer"
        assert summarizer._determine_task_category("unknown_task") == "system"

    @pytest.mark.asyncio
    async def test_convert_tools_to_operations(self, summarizer, sample_input_data, sample_context):
        """测试工具到操作的转换"""
        task_tools = {
            "scraper": {
                "operations": {
                    "get_aiohttp": {
                        "conditions": [{"if": "domain == 'web'", "then": "execute"}],
                        "params": {"url": "test_url"}
                    }
                }
            }
        }

        # 模拟条件检查通过
        with patch.object(summarizer, '_check_operation_conditions', return_value=True):
            operations = summarizer._convert_tools_to_operations(task_tools, sample_input_data, sample_context)

        assert len(operations) == 1
        assert operations[0]["operation"] == "scraper.get_aiohttp"
        assert "params" in operations[0]

    @pytest.mark.asyncio
    async def test_check_operation_conditions(self, summarizer, sample_input_data, sample_context, mock_executor):
        """测试操作条件检查"""
        # 无条件的操作
        operation_config = {"params": {"test": "value"}}
        assert summarizer._check_operation_conditions(operation_config, sample_input_data, sample_context) is True

        # 有条件的操作
        operation_config_with_conditions = {
            "conditions": [{"if": "domain == 'business'", "then": "execute"}],
            "params": {"test": "value"}
        }

        # 模拟条件评估
        mock_executor.evaluate_condition.return_value = True
        assert summarizer._check_operation_conditions(operation_config_with_conditions, sample_input_data, sample_context) is True

        mock_executor.evaluate_condition.return_value = False
        assert summarizer._check_operation_conditions(operation_config_with_conditions, sample_input_data, sample_context) is False

    @pytest.mark.asyncio
    async def test_combine_operation_results(self, summarizer):
        """测试操作结果合并"""
        # 空结果
        assert summarizer._combine_operation_results([]) is None

        # 单个结果
        single_result = [TaskStepResult(
            step="test",
            result={"data": "test"},
            completed=True,
            message="Test",
            status=TaskStatus.COMPLETED
        )]
        assert summarizer._combine_operation_results(single_result) == {"data": "test"}

        # 多个结果
        multiple_results = [
            TaskStepResult(
                step="test1",
                result={"data": "test1"},
                completed=True,
                message="Test1",
                status=TaskStatus.COMPLETED
            ),
            TaskStepResult(
                step="test2",
                result={"data": "test2"},
                completed=True,
                message="Test2",
                status=TaskStatus.COMPLETED
            )
        ]
        combined = summarizer._combine_operation_results(multiple_results)
        assert isinstance(combined, dict)
        assert combined["success_count"] == 2
        assert combined["total_count"] == 2
        assert len(combined["combined_result"]) == 2

    @pytest.mark.asyncio
    async def test_error_handling(self, summarizer, sample_input_data, sample_context, mock_executor):
        """测试错误处理"""
        # 模拟执行超时
        mock_executor.execute_with_timeout.return_value = {
            "status": TaskStatus.TIMED_OUT.value,
            "error_message": "Operation timed out"
        }

        with pytest.raises(asyncio.TimeoutError):
            await summarizer._parse_intent(sample_input_data)

        # 模拟执行异常
        mock_executor.execute_with_timeout.side_effect = Exception("Test exception")

        with pytest.raises(Exception):
            await summarizer._parse_intent(sample_input_data)

    def test_yaml_config_validation(self):
        """测试 YAML 配置验证"""
        # 这个测试需要实际的 YAML 文件，或者模拟文件系统
        # 在实际环境中，可以测试配置文件的加载和验证
        pass

    @pytest.mark.asyncio
    async def test_stream_method(self, summarizer, sample_input_data, sample_context):
        """测试流式执行方法"""
        # 模拟 execute_workflow 方法
        async def mock_execute_workflow(input_data, context):
            yield {"status": "info", "message": "Starting workflow"}
            yield {"status": "completed", "message": "Workflow completed"}

        with patch.object(summarizer, 'execute_workflow', side_effect=mock_execute_workflow):
            results = []
            async for result in summarizer.stream(sample_input_data, sample_context):
                results.append(result)

            assert len(results) == 2
            assert results[0]["status"] == "info"
            assert results[1]["status"] == "completed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
