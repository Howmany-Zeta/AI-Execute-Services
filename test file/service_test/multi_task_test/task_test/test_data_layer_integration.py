"""
Data Layer Integration Test

Tests the complete data layer integration with existing infrastructure.
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any
import uuid

from ..core.models.execution_models import ExecutionModel, ExecutionResult, ExecutionContext, ExecutionStatus, ExecutionMode
from ..core.models.data_models import StorageMetadata, DataFormat, CompressionType
from .data_layer_service import create_data_layer_service
from app.infrastructure.persistence.database_manager import DatabaseManager
from app.infrastructure.persistence.redis_client import RedisClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataLayerIntegrationTest:
    """
    Integration test for the data layer service.
    Tests compatibility with existing summarizer patterns and infrastructure.
    """

    def __init__(self):
        self.db_manager = None
        self.redis_client = None
        self.data_service = None
        self.test_results = {}

        # Track created test data for cleanup
        self.created_storage_keys = []
        self.created_execution_ids = []
        self.created_result_ids = []

    async def setup(self):
        """Setup test environment."""
        try:
            # Initialize database manager with test configuration
            db_config = {
                "user": "test_user",
                "password": "abc123456789.",
                "database": "test_database",
                "host": "localhost",
                "port": 5432
            }
            self.db_manager = DatabaseManager(db_config)
            await self.db_manager.init_connection_pool()
            await self.db_manager.init_database_schema()

            # Initialize Redis client (optional)
            try:
                self.redis_client = RedisClient()
                await self.redis_client.initialize()
                await self.redis_client.ping()
                logger.info("Redis client initialized successfully")
            except Exception as e:
                logger.warning(f"Redis not available: {e}")
                self.redis_client = None

            # Initialize data layer service
            storage_config = {
                'storage_type': 'cloud_storage',
                'bucket_name': 'test-multi-task-storage',
                'gcs_project_id': 'ca-biz-kjmsdw-y59m',
                'google_application_credentials': '/opt/gloud/ca-biz-kjmsdw-y59m-18f53a65e004.json',
                'enable_cache': True,
                'default_compression': 'gzip',
                'default_encryption': 'none'
            }

            self.data_service = create_data_layer_service(
                self.db_manager,
                self.redis_client,
                storage_config
            )
            await self.data_service.initialize()

            logger.info("Test setup completed successfully")

        except Exception as e:
            logger.error(f"Test setup failed: {e}")
            raise

    async def teardown(self):
        """Cleanup test environment."""
        try:
            if self.data_service:
                # Cleanup test data
                await self._cleanup_test_data()

            if self.redis_client:
                await self.redis_client.close()

            if self.db_manager:
                await self.db_manager.close()

            logger.info("Test teardown completed")

        except Exception as e:
            logger.error(f"Test teardown failed: {e}")

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests."""
        try:
            await self.setup()

            # Test basic data operations
            await self.test_basic_storage_operations()

            # Test execution data operations
            await self.test_execution_data_operations()

            # Test result data operations
            await self.test_result_data_operations()

            # Test summarizer compatibility
            await self.test_summarizer_compatibility()

            # Test search and analytics
            await self.test_search_and_analytics()

            # Test performance and optimization
            await self.test_performance_optimization()

            # Test health check
            await self.test_health_check()

            return self.test_results

        except Exception as e:
            logger.error(f"Integration test failed: {e}")
            self.test_results['overall_status'] = 'failed'
            self.test_results['error'] = str(e)
            return self.test_results

        finally:
            await self.teardown()

    async def test_basic_storage_operations(self):
        """Test basic storage operations."""
        test_name = "basic_storage_operations"
        logger.info(f"Running test: {test_name}")

        try:
            # Test data storage
            test_data = {
                'message': 'Hello, World!',
                'timestamp': datetime.utcnow().isoformat(),
                'numbers': [1, 2, 3, 4, 5],
                'nested': {'key': 'value', 'count': 42}
            }

            key = f"test_basic_{uuid.uuid4()}"

            # Track created data for cleanup
            self.created_storage_keys.append(key)

            # Store data
            success = await self.data_service.store_summarizer_data(key, test_data)
            assert success, "Failed to store data"

            # Retrieve data
            retrieved_data = await self.data_service.retrieve_summarizer_data(key)
            assert retrieved_data is not None, "Failed to retrieve data"
            assert retrieved_data['message'] == test_data['message'], "Data mismatch"

            # Test deletion functionality (but don't actually delete - let cleanup handle it)
            # This tests the delete method works, but we'll restore the data for cleanup
            deleted = await self.data_service.delete_summarizer_data(key)
            assert deleted, "Failed to delete data"

            # Verify deletion worked
            deleted_data = await self.data_service.retrieve_summarizer_data(key)
            assert deleted_data is None, "Data not properly deleted"

            # Re-store the data so cleanup can handle it properly
            await self.data_service.store_summarizer_data(key, test_data)

            self.test_results[test_name] = {
                'status': 'passed',
                'message': 'Basic storage operations working correctly'
            }
            logger.info(f"Test {test_name} passed")

        except Exception as e:
            self.test_results[test_name] = {
                'status': 'failed',
                'error': str(e)
            }
            logger.error(f"Test {test_name} failed: {e}")

    async def test_execution_data_operations(self):
        """Test execution data operations."""
        test_name = "execution_data_operations"
        logger.info(f"Running test: {test_name}")

        try:
            # Create test execution
            execution_id = str(uuid.uuid4())

            # Track created data for cleanup
            self.created_execution_ids.append(execution_id)

            context = ExecutionContext(
                execution_id=execution_id,
                task_id="test_task_001",
                user_id="test_user",
                session_id="test_session"
            )

            execution = ExecutionModel(
                execution_id=execution_id,
                context=context,
                execution_type="summarization",
                execution_mode=ExecutionMode.SEQUENTIAL,  # Add missing field
                status=ExecutionStatus.RUNNING,
                created_at=datetime.utcnow(),
                started_at=datetime.utcnow(),
                metadata={
                    'test': True,
                    'source': 'integration_test'
                }
            )

            # Save execution
            saved_id = await self.data_service.save_execution_data(execution, context)
            assert saved_id == execution_id, "Execution ID mismatch"

            # Retrieve execution
            retrieved_execution = await self.data_service.get_execution_data(execution_id)
            assert retrieved_execution is not None, "Failed to retrieve execution"
            assert retrieved_execution.execution_id == execution_id, "Execution ID mismatch"
            # Handle both enum and string status values
            expected_status = ExecutionStatus.RUNNING
            actual_status = retrieved_execution.status
            if hasattr(actual_status, 'value'):
                actual_status_value = actual_status.value
            else:
                actual_status_value = actual_status

            assert actual_status_value == expected_status.value, f"Status mismatch: expected {expected_status.value}, got {actual_status_value}"

            # Update execution status
            updated = await self.data_service.update_execution_status(
                execution_id, ExecutionStatus.COMPLETED
            )
            assert updated, "Failed to update execution status"

            # Get active executions
            active_executions = await self.data_service.get_active_executions("test_user")
            # Should be empty since we completed the execution

            self.test_results[test_name] = {
                'status': 'passed',
                'message': 'Execution data operations working correctly',
                'execution_id': execution_id
            }
            logger.info(f"Test {test_name} passed")

        except Exception as e:
            self.test_results[test_name] = {
                'status': 'failed',
                'error': str(e)
            }
            logger.error(f"Test {test_name} failed: {e}")

    async def test_result_data_operations(self):
        """Test result data operations."""
        test_name = "result_data_operations"
        logger.info(f"Running test: {test_name}")

        try:
            # Create test result
            execution_id = str(uuid.uuid4())
            result_id = str(uuid.uuid4())

            # Track created data for cleanup
            self.created_execution_ids.append(execution_id)
            self.created_result_ids.append(result_id)

            context = ExecutionContext(
                execution_id=execution_id,
                task_id="test_task_002",
                user_id="test_user",
                session_id="test_session"
            )

            result = ExecutionResult(
                result_id=result_id,
                execution_id=execution_id,
                step_id="step_001",
                status=ExecutionStatus.COMPLETED,
                success=True,  # Add missing field
                message="Test execution completed successfully",  # Add missing field
                result={  # Rename data to result
                    'summary': 'This is a test summary',
                    'key_points': ['Point 1', 'Point 2', 'Point 3'],
                    'confidence': 0.95
                },
                quality_score=0.85,
                confidence_score=0.90,
                execution_time_seconds=2.5,  # Rename processing_time to execution_time_seconds
                created_at=datetime.utcnow(),
                metadata={
                    'test': True,
                    'algorithm': 'test_algorithm'
                }
            )

            # Save result
            saved_id = await self.data_service.save_result_data(result, context)
            assert saved_id == result_id, "Result ID mismatch"

            # Retrieve result
            retrieved_result = await self.data_service.get_result_data(result_id)
            assert retrieved_result is not None, "Failed to retrieve result"
            assert retrieved_result.result_id == result_id, "Result ID mismatch"
            assert retrieved_result.quality_score == 0.85, "Quality score mismatch"

            # Get quality results
            quality_results = await self.data_service.get_quality_results(0.8, 10)
            assert len(quality_results) > 0, "No quality results found"

            # Get result analytics
            analytics = await self.data_service.get_result_analytics(result_id)
            assert isinstance(analytics, dict), "Analytics should be a dictionary"

            self.test_results[test_name] = {
                'status': 'passed',
                'message': 'Result data operations working correctly',
                'result_id': result_id
            }
            logger.info(f"Test {test_name} passed")

        except Exception as e:
            self.test_results[test_name] = {
                'status': 'failed',
                'error': str(e)
            }
            logger.error(f"Test {test_name} failed: {e}")

    async def test_summarizer_compatibility(self):
        """Test compatibility with existing summarizer patterns."""
        test_name = "summarizer_compatibility"
        logger.info(f"Running test: {test_name}")

        try:
            # Test summarizer-style data storage
            summarizer_data = {
                'document_id': 'doc_123',
                'original_text': 'This is a long document that needs to be summarized...',
                'summary': 'This is a summary of the document.',
                'metadata': {
                    'language': 'en',
                    'word_count': 150,
                    'summary_ratio': 0.3
                },
                'processing_info': {
                    'algorithm': 'extractive',
                    'model_version': '1.0',
                    'processing_time': 1.2
                }
            }

            # Store using summarizer pattern
            key = f"summarizer_test_{uuid.uuid4()}"

            # Track created data for cleanup
            self.created_storage_keys.append(key)

            stored = await self.data_service.store_summarizer_data(
                key, summarizer_data, {'source': 'summarizer_test'}
            )
            assert stored, "Failed to store summarizer data"

            # Retrieve using summarizer pattern
            retrieved = await self.data_service.retrieve_summarizer_data(key)
            assert retrieved is not None, "Failed to retrieve summarizer data"
            assert retrieved['document_id'] == 'doc_123', "Document ID mismatch"

            # Test task history (summarizer pattern)
            history = await self.data_service.get_task_execution_history("test_task_002")
            assert isinstance(history, list), "History should be a list"

            self.test_results[test_name] = {
                'status': 'passed',
                'message': 'Summarizer compatibility working correctly'
            }
            logger.info(f"Test {test_name} passed")

        except Exception as e:
            self.test_results[test_name] = {
                'status': 'failed',
                'error': str(e)
            }
            logger.error(f"Test {test_name} failed: {e}")

    async def test_search_and_analytics(self):
        """Test search and analytics functionality."""
        test_name = "search_and_analytics"
        logger.info(f"Running test: {test_name}")

        try:
            # Search executions
            execution_criteria = {
                'user_id': 'test_user',
                'status': 'completed'
            }
            executions = await self.data_service.search_executions(execution_criteria, 10)
            assert isinstance(executions, list), "Executions should be a list"

            # Search results
            result_criteria = {
                'min_quality_score': 0.7
            }
            results = await self.data_service.search_results(result_criteria, 10)
            assert isinstance(results, list), "Results should be a list"

            self.test_results[test_name] = {
                'status': 'passed',
                'message': 'Search and analytics working correctly'
            }
            logger.info(f"Test {test_name} passed")

        except Exception as e:
            self.test_results[test_name] = {
                'status': 'failed',
                'error': str(e)
            }
            logger.error(f"Test {test_name} failed: {e}")

    async def test_performance_optimization(self):
        """Test performance optimization features."""
        test_name = "performance_optimization"
        logger.info(f"Running test: {test_name}")

        try:
            # Get performance metrics
            metrics = await self.data_service.get_performance_metrics()
            assert isinstance(metrics, dict), "Metrics should be a dictionary"
            assert 'data_layer' in metrics, "Data layer metrics missing"

            # Test storage optimization
            optimization_result = await self.data_service.optimize_storage()
            assert isinstance(optimization_result, dict), "Optimization result should be a dictionary"

            self.test_results[test_name] = {
                'status': 'passed',
                'message': 'Performance optimization working correctly',
                'metrics': metrics
            }
            logger.info(f"Test {test_name} passed")

        except Exception as e:
            self.test_results[test_name] = {
                'status': 'failed',
                'error': str(e)
            }
            logger.error(f"Test {test_name} failed: {e}")

    async def test_health_check(self):
        """Test health check functionality."""
        test_name = "health_check"
        logger.info(f"Running test: {test_name}")

        try:
            health = await self.data_service.health_check()
            assert isinstance(health, dict), "Health check should return a dictionary"
            assert 'status' in health, "Health status missing"
            assert 'components' in health, "Component health missing"

            self.test_results[test_name] = {
                'status': 'passed',
                'message': 'Health check working correctly',
                'health': health
            }
            logger.info(f"Test {test_name} passed")

        except Exception as e:
            self.test_results[test_name] = {
                'status': 'failed',
                'error': str(e)
            }
            logger.error(f"Test {test_name} failed: {e}")

    async def _cleanup_test_data(self):
        """Cleanup test data created during tests."""
        try:
            logger.info("Starting test data cleanup...")
            cleanup_count = 0

            # Clean up storage data (summarizer data)
            for key in self.created_storage_keys:
                try:
                    deleted = await self.data_service.delete_summarizer_data(key)
                    if deleted:
                        cleanup_count += 1
                        logger.debug(f"Deleted storage data: {key}")
                    else:
                        logger.warning(f"Failed to delete storage data: {key}")
                except Exception as e:
                    logger.warning(f"Error deleting storage data {key}: {e}")

            # Clean up execution data
            for execution_id in self.created_execution_ids:
                try:
                    deleted = await self.data_service.task_repository.delete_execution(execution_id)
                    if deleted:
                        cleanup_count += 1
                        logger.debug(f"Deleted execution: {execution_id}")
                    else:
                        logger.warning(f"Failed to delete execution: {execution_id}")
                except Exception as e:
                    logger.warning(f"Error deleting execution {execution_id}: {e}")

            # Clean up result data
            for result_id in self.created_result_ids:
                try:
                    deleted = await self.data_service.result_repository.delete_result(result_id)
                    if deleted:
                        cleanup_count += 1
                        logger.debug(f"Deleted result: {result_id}")
                    else:
                        logger.warning(f"Failed to delete result: {result_id}")
                except Exception as e:
                    logger.warning(f"Error deleting result {result_id}: {e}")

            # Clear the tracking lists
            self.created_storage_keys.clear()
            self.created_execution_ids.clear()
            self.created_result_ids.clear()

            logger.info(f"Test data cleanup completed. Cleaned up {cleanup_count} items.")

        except Exception as e:
            logger.error(f"Failed to cleanup test data: {e}")


async def run_integration_test():
    """Run the complete integration test."""
    test = DataLayerIntegrationTest()
    results = await test.run_all_tests()

    # Print results
    print("\n" + "="*60)
    print("DATA LAYER INTEGRATION TEST RESULTS")
    print("="*60)

    passed_tests = 0
    total_tests = 0

    for test_name, result in results.items():
        if test_name in ['overall_status', 'error']:
            continue

        total_tests += 1

        # Handle case where result might be a string (error case)
        if isinstance(result, str):
            print(f"❌ {test_name}: FAILED")
            print(f"   Error: {result}")
        else:
            status = result.get('status', 'unknown')
            if status == 'passed':
                passed_tests += 1
                print(f"✅ {test_name}: PASSED")
                if 'message' in result:
                    print(f"   {result['message']}")
            else:
                print(f"❌ {test_name}: FAILED")
                if 'error' in result:
                    print(f"   Error: {result['error']}")
        print()

    print(f"Summary: {passed_tests}/{total_tests} tests passed")

    # Check for overall failure
    if 'overall_status' in results and results['overall_status'] == 'failed':
        print("❌ OVERALL TEST FAILURE")
        if 'error' in results:
            print(f"   Error: {results['error']}")
        print()

    if passed_tests == total_tests and results.get('overall_status') != 'failed':
        print("🎉 All tests passed! Data layer integration is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")

    print("="*60)

    return results


if __name__ == "__main__":
    # Run the integration test
    asyncio.run(run_integration_test())
