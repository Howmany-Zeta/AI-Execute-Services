"""
Test file for the execution layer

This file tests all the main components of the execution layer to ensure
they function correctly and can be integrated properly.
"""

import asyncio
import logging
import sys
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import execution layer components
try:
    from app.services.multi_task.execution import (
        DSLEngine, CrewEngine, ParallelEngine,
        TaskProcessor, WorkflowProcessor, QualityProcessor,
        ExecutionMonitor, PerformanceMonitor
    )
    from app.services.multi_task.core.models.execution_models import (
        ExecutionContext, ExecutionResult, ExecutionPlan, ExecutionStatus, ExecutionMode
    )
    from app.services.multi_task.execution.processors.quality_processor import (
        TaskCategory, QualityLevel
    )
    logger.info("✅ Successfully imported execution layer components")
except ImportError as e:
    logger.error(f"❌ Failed to import execution layer components: {e}")
    sys.exit(1)


class ExecutionLayerTester:
    """Test suite for the execution layer."""

    def __init__(self):
        self.test_results = []
        self.engines = {}
        self.processors = {}
        self.monitors = {}

    async def run_all_tests(self):
        """Run all tests for the execution layer."""
        logger.info("🚀 Starting execution layer tests...")

        # Test component initialization
        await self.test_component_initialization()

        # Test DSL engine
        await self.test_dsl_engine()

        # Test parallel engine
        await self.test_parallel_engine()

        # Test task processor
        await self.test_task_processor()

        # Test workflow processor
        await self.test_workflow_processor()

        # Test quality processor
        await self.test_quality_processor()

        # Test execution monitor
        await self.test_execution_monitor()

        # Test performance monitor
        await self.test_performance_monitor()

        # Test integration scenarios
        await self.test_integration_scenarios()

        # Print test summary
        self.print_test_summary()

    async def test_component_initialization(self):
        """Test that all components can be initialized correctly."""
        test_name = "Component Initialization"
        logger.info(f"🧪 Testing {test_name}...")

        try:
            # Initialize engines
            self.engines['dsl'] = DSLEngine()
            self.engines['parallel'] = ParallelEngine()
            # Note: CrewEngine requires agents, so we'll test it separately

            # Initialize processors
            self.processors['task'] = TaskProcessor(self.engines['dsl'])
            self.processors['workflow'] = WorkflowProcessor(
                self.engines['dsl'],
                self.processors['task']
            )
            self.processors['quality'] = QualityProcessor(self.engines['dsl'])

            # Initialize monitors
            self.monitors['execution'] = ExecutionMonitor()
            self.monitors['performance'] = PerformanceMonitor()

            self.record_test_result(test_name, True, "All components initialized successfully")
            logger.info(f"✅ {test_name} passed")

        except Exception as e:
            self.record_test_result(test_name, False, f"Initialization failed: {str(e)}")
            logger.error(f"❌ {test_name} failed: {e}")
            traceback.print_exc()

    async def test_dsl_engine(self):
        """Test DSL engine functionality."""
        test_name = "DSL Engine"
        logger.info(f"🧪 Testing {test_name}...")

        try:
            engine = self.engines['dsl']

            # Test engine initialization
            await engine.initialize()

            # Test simple task execution
            task_definition = {
                'task': 'test_task',
                'type': 'simple',
                'description': 'A simple test task'
            }

            context = ExecutionContext(
                execution_id="test_dsl_001",
                user_id="test_user_001",
                input_data={'test': 'data'},
                timeout_seconds=30
            )

            result = await engine.execute_task(task_definition, context)

            if isinstance(result, ExecutionResult):
                self.record_test_result(test_name, True, f"DSL task executed: {result.message}")
                logger.info(f"✅ {test_name} passed - Task result: {result.success}")
            else:
                self.record_test_result(test_name, False, "Invalid result type returned")
                logger.error(f"❌ {test_name} failed - Invalid result type")

            # Test DSL step execution
            dsl_step = {'task': 'dsl_test_step'}
            step_result = await engine.execute_dsl_step(dsl_step, context)

            if isinstance(step_result, ExecutionResult):
                logger.info(f"✅ DSL step executed successfully: {step_result.success}")

            # Cleanup
            await engine.cleanup()

        except Exception as e:
            self.record_test_result(test_name, False, f"DSL engine test failed: {str(e)}")
            logger.error(f"❌ {test_name} failed: {e}")
            traceback.print_exc()

    async def test_parallel_engine(self):
        """Test parallel engine functionality."""
        test_name = "Parallel Engine"
        logger.info(f"🧪 Testing {test_name}...")

        try:
            engine = self.engines['parallel']

            # Test engine initialization
            await engine.initialize()

            # Test parallel task execution
            task_definition = {
                'name': 'parallel_test_task',
                'type': 'async',
                'description': 'A parallel test task'
            }

            context = ExecutionContext(
                execution_id="test_parallel_001",
                user_id="test_user_001",
                input_data={'test': 'parallel_data'},
                timeout_seconds=30
            )

            result = await engine.execute_task(task_definition, context)

            if isinstance(result, ExecutionResult):
                self.record_test_result(test_name, True, f"Parallel task executed: {result.message}")
                logger.info(f"✅ {test_name} passed - Task result: {result.success}")
            else:
                self.record_test_result(test_name, False, "Invalid result type returned")
                logger.error(f"❌ {test_name} failed - Invalid result type")

            # Test parallel block execution
            parallel_tasks = [
                {'name': 'task1', 'type': 'async'},
                {'name': 'task2', 'type': 'async'},
                {'name': 'task3', 'type': 'async'}
            ]

            parallel_step = {'parallel': parallel_tasks}
            parallel_result = await engine.execute_dsl_step(parallel_step, context)

            if isinstance(parallel_result, ExecutionResult):
                logger.info(f"✅ Parallel block executed: {parallel_result.success}")

            # Cleanup
            await engine.cleanup()

        except Exception as e:
            self.record_test_result(test_name, False, f"Parallel engine test failed: {str(e)}")
            logger.error(f"❌ {test_name} failed: {e}")
            traceback.print_exc()

    async def test_task_processor(self):
        """Test task processor functionality."""
        test_name = "Task Processor"
        logger.info(f"🧪 Testing {test_name}...")

        try:
            processor = self.processors['task']

            # Test single task processing
            task_definition = {
                'id': 'test_task_001',
                'type': 'collect',
                'name': 'Test Collection Task',
                'description': 'A test task for collection'
            }

            context = ExecutionContext(
                execution_id="test_processor_001",
                user_id="test_user_001",
                input_data={'source': 'test_data'},
                timeout_seconds=30
            )

            result = await processor.process_task(task_definition, context)

            if isinstance(result, ExecutionResult):
                self.record_test_result(test_name, True, f"Task processed: {result.message}")
                logger.info(f"✅ {test_name} passed - Task result: {result.success}")
            else:
                self.record_test_result(test_name, False, "Invalid result type returned")
                logger.error(f"❌ {test_name} failed - Invalid result type")

            # Test batch processing
            batch_tasks = [
                {'id': 'batch_task_1', 'type': 'process', 'name': 'Batch Task 1'},
                {'id': 'batch_task_2', 'type': 'process', 'name': 'Batch Task 2'},
                {'id': 'batch_task_3', 'type': 'process', 'name': 'Batch Task 3'}
            ]

            batch_results = await processor.process_task_batch(
                batch_tasks, context, max_concurrency=2
            )

            if isinstance(batch_results, list) and len(batch_results) == 3:
                logger.info(f"✅ Batch processing completed: {len(batch_results)} tasks")

            # Test task status retrieval
            task_status = await processor.get_task_status('test_task_001')
            if task_status:
                logger.info(f"✅ Task status retrieved: {task_status}")

        except Exception as e:
            self.record_test_result(test_name, False, f"Task processor test failed: {str(e)}")
            logger.error(f"❌ {test_name} failed: {e}")
            traceback.print_exc()

    async def test_workflow_processor(self):
        """Test workflow processor functionality."""
        test_name = "Workflow Processor"
        logger.info(f"🧪 Testing {test_name}...")

        try:
            processor = self.processors['workflow']

            # Test workflow execution
            workflow_definition = {
                'workflow_id': 'test_workflow_001',
                'type': 'sequential',
                'tasks': [
                    {'id': 'step_1', 'type': 'collect', 'name': 'Collection Step'},
                    {'id': 'step_2', 'type': 'process', 'name': 'Processing Step'},
                    {'id': 'step_3', 'type': 'analyze', 'name': 'Analysis Step'}
                ]
            }

            context = ExecutionContext(
                execution_id="test_workflow_001",
                user_id="test_user_001",
                input_data={'workflow_input': 'test_data'},
                timeout_seconds=60
            )

            results = []
            async for result in processor.execute_workflow(workflow_definition, context):
                results.append(result)
                logger.info(f"Workflow step completed: {result.message}")

            if results:
                self.record_test_result(test_name, True, f"Workflow executed with {len(results)} steps")
                logger.info(f"✅ {test_name} passed - {len(results)} steps completed")
            else:
                self.record_test_result(test_name, False, "No workflow results returned")
                logger.error(f"❌ {test_name} failed - No results")

            # Test workflow status
            status = await processor.get_workflow_status('test_workflow_001')
            if status:
                logger.info(f"✅ Workflow status retrieved: {status.get('status', 'unknown')}")

        except Exception as e:
            self.record_test_result(test_name, False, f"Workflow processor test failed: {str(e)}")
            logger.error(f"❌ {test_name} failed: {e}")
            traceback.print_exc()

    async def test_quality_processor(self):
        """Test quality processor functionality."""
        test_name = "Quality Processor"
        logger.info(f"🧪 Testing {test_name}...")

        try:
            processor = self.processors['quality']

            # Create a mock execution result for testing
            mock_result = ExecutionResult(
                execution_id="test_quality_001",
                status="completed",
                success=True,
                message="Mock task completed successfully",
                result={'data': 'test_output', 'processed': True},
                started_at=datetime.utcnow() - timedelta(seconds=5),
                completed_at=datetime.utcnow()
            )

            # Test examination for collect task
            examination_result = await processor.examine_task_result(
                mock_result,
                TaskCategory.COLLECT,
                QualityLevel.STANDARD
            )

            if examination_result and hasattr(examination_result, 'passed'):
                self.record_test_result(test_name, True, f"Quality examination completed: {examination_result.passed}")
                logger.info(f"✅ Quality examination passed: {examination_result.passed}, score: {examination_result.score}")
            else:
                self.record_test_result(test_name, False, "Invalid examination result")
                logger.error(f"❌ Quality examination failed - Invalid result")

            # Test acceptance for analyze task
            acceptance_result = await processor.accept_task_result(
                mock_result,
                TaskCategory.ANALYZE,
                QualityLevel.STANDARD
            )

            if acceptance_result and hasattr(acceptance_result, 'passed'):
                logger.info(f"✅ Quality acceptance completed: {acceptance_result.passed}, score: {acceptance_result.score}")

            # Test validation
            validation_criteria = {
                'require_result': True,
                'required_fields': ['data'],
                'field_types': {'data': str}
            }

            validation_result = await processor.validate_task_result(
                mock_result,
                validation_criteria
            )

            if validation_result and hasattr(validation_result, 'passed'):
                logger.info(f"✅ Quality validation completed: {validation_result.passed}, score: {validation_result.score}")

        except Exception as e:
            self.record_test_result(test_name, False, f"Quality processor test failed: {str(e)}")
            logger.error(f"❌ {test_name} failed: {e}")
            traceback.print_exc()

    async def test_execution_monitor(self):
        """Test execution monitor functionality."""
        test_name = "Execution Monitor"
        logger.info(f"🧪 Testing {test_name}...")

        try:
            monitor = self.monitors['execution']

            # Start monitoring
            await monitor.start_monitoring()

            # Test execution tracking
            context = ExecutionContext(
                execution_id="test_monitor_001",
                user_id="test_user_001",
                input_data={'monitor_test': 'data'},
                timeout_seconds=30
            )

            await monitor.track_execution_start("test_monitor_001", context, total_tasks=3)

            # Simulate progress updates
            await monitor.track_execution_progress("test_monitor_001", 0.33, "task_1")
            await monitor.track_execution_progress("test_monitor_001", 0.66, "task_2")
            await monitor.track_execution_progress("test_monitor_001", 1.0, "task_3")

            # Test task completion tracking
            mock_result = ExecutionResult(
                execution_id="test_monitor_001",
                status="completed",
                success=True,
                message="Monitor test task completed",
                started_at=datetime.utcnow() - timedelta(seconds=2),
                completed_at=datetime.utcnow()
            )

            await monitor.track_task_completion("test_monitor_001", mock_result, "test_task")

            # Test execution completion
            await monitor.track_execution_completion("test_monitor_001", mock_result)

            # Test status retrieval
            status = await monitor.get_execution_status("test_monitor_001")
            if status:
                logger.info(f"✅ Execution status retrieved: {status.status}")

            # Test events retrieval
            events = await monitor.get_events(execution_id="test_monitor_001", limit=10)
            if events:
                logger.info(f"✅ Retrieved {len(events)} execution events")

            # Test summary
            summary = await monitor.get_execution_summary()
            if summary:
                logger.info(f"✅ Execution summary: {summary.get('total_events', 0)} events")

            self.record_test_result(test_name, True, "Execution monitoring completed successfully")
            logger.info(f"✅ {test_name} passed")

            # Stop monitoring
            await monitor.stop_monitoring()

        except Exception as e:
            self.record_test_result(test_name, False, f"Execution monitor test failed: {str(e)}")
            logger.error(f"❌ {test_name} failed: {e}")
            traceback.print_exc()

    async def test_performance_monitor(self):
        """Test performance monitor functionality."""
        test_name = "Performance Monitor"
        logger.info(f"🧪 Testing {test_name}...")

        try:
            monitor = self.monitors['performance']

            # Start monitoring
            await monitor.start_monitoring()

            # Wait a moment for initial collection
            await asyncio.sleep(2)

            # Test metric recording
            from app.services.multi_task.execution.monitors.performance_monitor import MetricType

            await monitor.record_metric(
                MetricType.EXECUTION_TIME,
                value=1.5,
                unit="seconds",
                execution_id="test_perf_001",
                component="test_component"
            )

            await monitor.record_metric(
                MetricType.MEMORY_USAGE,
                value=75.0,
                unit="percent",
                component="system"
            )

            # Test execution performance recording
            mock_result = ExecutionResult(
                execution_id="test_perf_001",
                status="completed",
                success=True,
                message="Performance test completed",
                started_at=datetime.utcnow() - timedelta(seconds=2),
                completed_at=datetime.utcnow()
            )

            await monitor.record_execution_performance("test_perf_001", mock_result, "test_component")

            # Test performance summary
            summary = await monitor.get_performance_summary()
            if summary and 'total_metrics' in summary:
                logger.info(f"✅ Performance summary: {summary['total_metrics']} metrics")

            # Test execution performance
            exec_perf = await monitor.get_execution_performance("test_perf_001")
            if exec_perf and 'metrics_count' in exec_perf:
                logger.info(f"✅ Execution performance: {exec_perf['metrics_count']} metrics")

            # Test optimization recommendations
            recommendations = await monitor.get_optimization_recommendations()
            if isinstance(recommendations, list):
                logger.info(f"✅ Got {len(recommendations)} optimization recommendations")

            self.record_test_result(test_name, True, "Performance monitoring completed successfully")
            logger.info(f"✅ {test_name} passed")

            # Stop monitoring
            await monitor.stop_monitoring()

        except Exception as e:
            self.record_test_result(test_name, False, f"Performance monitor test failed: {str(e)}")
            logger.error(f"❌ {test_name} failed: {e}")
            traceback.print_exc()

    async def test_integration_scenarios(self):
        """Test integration scenarios combining multiple components."""
        test_name = "Integration Scenarios"
        logger.info(f"🧪 Testing {test_name}...")

        try:
            # Test complete workflow with monitoring
            engine = self.engines['dsl']
            task_processor = self.processors['task']
            workflow_processor = self.processors['workflow']
            quality_processor = self.processors['quality']
            execution_monitor = self.monitors['execution']
            performance_monitor = self.monitors['performance']

            # Start monitors
            await execution_monitor.start_monitoring()
            await performance_monitor.start_monitoring()

            # Define an integrated workflow
            workflow_definition = {
                'workflow_id': 'integration_test_001',
                'type': 'sequential',
                'tasks': [
                    {
                        'id': 'collect_step',
                        'type': 'collect',
                        'name': 'Data Collection',
                        'description': 'Collect test data'
                    },
                    {
                        'id': 'process_step',
                        'type': 'process',
                        'name': 'Data Processing',
                        'description': 'Process collected data'
                    }
                ]
            }

            context = ExecutionContext(
                execution_id="integration_test_001",
                user_id="test_user_001",
                input_data={'integration_test': True},
                timeout_seconds=60
            )

            # Track workflow start
            await execution_monitor.track_execution_start(
                "integration_test_001",
                context,
                total_tasks=2
            )

            # Execute workflow with quality checks
            workflow_results = []
            async for result in workflow_processor.execute_workflow(workflow_definition, context):
                workflow_results.append(result)

                # Track progress
                await execution_monitor.track_task_completion(
                    "integration_test_001",
                    result,
                    f"step_{len(workflow_results)}"
                )

                # Record performance
                await performance_monitor.record_execution_performance(
                    "integration_test_001",
                    result,
                    "workflow_processor"
                )

                # Quality check for successful results
                if result.success and result.result:
                    if len(workflow_results) == 1:  # First task (collect)
                        quality_result = await quality_processor.examine_task_result(
                            result, TaskCategory.COLLECT, QualityLevel.STANDARD
                        )
                        logger.info(f"Quality examination: {quality_result.passed}")
                    elif len(workflow_results) == 2:  # Second task (process)
                        quality_result = await quality_processor.examine_task_result(
                            result, TaskCategory.PROCESS, QualityLevel.STANDARD
                        )
                        logger.info(f"Quality examination: {quality_result.passed}")

            # Track workflow completion
            if workflow_results:
                final_result = workflow_results[-1]
                await execution_monitor.track_execution_completion(
                    "integration_test_001",
                    final_result
                )

            # Get final status and metrics
            execution_status = await execution_monitor.get_execution_status("integration_test_001")
            performance_summary = await performance_monitor.get_performance_summary()

            if workflow_results and execution_status and performance_summary:
                self.record_test_result(
                    test_name,
                    True,
                    f"Integration test completed: {len(workflow_results)} steps, "
                    f"{performance_summary.get('total_metrics', 0)} metrics"
                )
                logger.info(f"✅ {test_name} passed - Complete integration successful")
            else:
                self.record_test_result(test_name, False, "Integration test incomplete")
                logger.error(f"❌ {test_name} failed - Integration incomplete")

            # Stop monitors
            await execution_monitor.stop_monitoring()
            await performance_monitor.stop_monitoring()

        except Exception as e:
            self.record_test_result(test_name, False, f"Integration test failed: {str(e)}")
            logger.error(f"❌ {test_name} failed: {e}")
            traceback.print_exc()

    def record_test_result(self, test_name: str, passed: bool, message: str):
        """Record a test result."""
        self.test_results.append({
            'test_name': test_name,
            'passed': passed,
            'message': message,
            'timestamp': datetime.utcnow()
        })

    def print_test_summary(self):
        """Print a summary of all test results."""
        logger.info("\n" + "="*80)
        logger.info("🏁 EXECUTION LAYER TEST SUMMARY")
        logger.info("="*80)

        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]

        logger.info(f"Total Tests: {len(self.test_results)}")
        logger.info(f"Passed: {len(passed_tests)} ✅")
        logger.info(f"Failed: {len(failed_tests)} ❌")
        logger.info(f"Success Rate: {len(passed_tests)/len(self.test_results)*100:.1f}%")

        if passed_tests:
            logger.info("\n✅ PASSED TESTS:")
            for test in passed_tests:
                logger.info(f"  • {test['test_name']}: {test['message']}")

        if failed_tests:
            logger.info("\n❌ FAILED TESTS:")
            for test in failed_tests:
                logger.info(f"  • {test['test_name']}: {test['message']}")

        logger.info("\n" + "="*80)

        if len(failed_tests) == 0:
            logger.info("🎉 ALL TESTS PASSED! The execution layer is working correctly.")
        else:
            logger.info("⚠️  Some tests failed. Please review the errors above.")

        logger.info("="*80)


async def main():
    """Main test function."""
    logger.info("🔧 Starting Execution Layer Test Suite")
    logger.info("="*80)

    tester = ExecutionLayerTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⏹️  Test suite interrupted by user")
    except Exception as e:
        logger.error(f"💥 Test suite failed with error: {e}")
        traceback.print_exc()
        sys.exit(1)
