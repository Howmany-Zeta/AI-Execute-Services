"""
Test script for LangGraph Summarizer Service

This script provides basic testing functionality for the LangGraphSummarizer
to verify its implementation and integration with existing services.
"""

import asyncio
import json
import logging
from typing import Dict, Any
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the LangGraph Summarizer
from .summarizer import Summarizer, create_summarizer


class LangGraphSummarizerTester:
    """Test harness for LangGraph Summarizer Service."""

    def __init__(self):
        self.summarizer: Summarizer = None
        self.test_results = []
        self.setup_errors = []

    def _detect_errors_in_logs(self, content: str) -> list:
        """Detect error patterns in content."""
        error_patterns = [
            "ERROR:",
            "cannot run the event loop while another loop is running",
            "'dict' object has no attribute 'error'",
            "mining process failed",
            "failed to generate response",
            "langchain adapter sync llm call failed",
            "requirements mining failed"
        ]

        detected_errors = []
        content_lower = content.lower()

        for pattern in error_patterns:
            if pattern.lower() in content_lower:
                detected_errors.append(pattern)

        return detected_errors

    async def setup(self):
        """Initialize the summarizer for testing."""
        try:
            logger.info("Setting up LangGraph Summarizer for testing...")

            # Capture any setup errors by monitoring logs
            import io
            import sys
            from contextlib import redirect_stderr

            # Create a string buffer to capture stderr
            stderr_buffer = io.StringIO()

            with redirect_stderr(stderr_buffer):
                self.summarizer = await create_summarizer()

            # Check for errors in captured output
            captured_errors = stderr_buffer.getvalue()
            if captured_errors:
                setup_errors = self._detect_errors_in_logs(captured_errors)
                if setup_errors:
                    self.setup_errors.extend(setup_errors)
                    logger.error(f"Setup errors detected: {setup_errors}")

            logger.info("LangGraph Summarizer setup completed")
            return True
        except Exception as e:
            logger.error(f"Failed to setup LangGraph Summarizer: {e}")
            self.setup_errors.append(str(e))
            return False

    async def test_service_info(self):
        """Test service information retrieval."""
        try:
            logger.info("Testing service info...")

            service_info = self.summarizer.get_service_info()

            # Validate service info structure
            required_fields = ["name", "version", "description", "capabilities", "supported_domains"]
            for field in required_fields:
                assert field in service_info, f"Missing required field: {field}"

            logger.info(f"Service Info: {service_info['name']} v{service_info['version']}")
            logger.info(f"Capabilities: {len(service_info['capabilities'])} features")
            logger.info(f"Supported Domains: {len(service_info['supported_domains'])} domains")

            self.test_results.append({
                "test": "service_info",
                "status": "passed",
                "details": service_info
            })

            return True

        except Exception as e:
            logger.error(f"Service info test failed: {e}")
            self.test_results.append({
                "test": "service_info",
                "status": "failed",
                "error": str(e)
            })
            return False

    async def test_service_metrics(self):
        """Test service metrics retrieval."""
        try:
            logger.info("Testing service metrics...")

            metrics = await self.summarizer.get_service_metrics()

            # Validate metrics structure
            required_fields = ["service_name", "total_sessions", "successful_sessions", "success_rate"]
            for field in required_fields:
                assert field in metrics, f"Missing required metric: {field}"

            logger.info(f"Metrics: {metrics['total_sessions']} total sessions, {metrics['success_rate']:.2%} success rate")

            self.test_results.append({
                "test": "service_metrics",
                "status": "passed",
                "details": metrics
            })

            return True

        except Exception as e:
            logger.error(f"Service metrics test failed: {e}")
            self.test_results.append({
                "test": "service_metrics",
                "status": "failed",
                "error": str(e)
            })
            return False

    async def test_basic_streaming(self):
        """Test basic streaming functionality."""
        try:
            logger.info("Testing basic streaming...")

            # Prepare test input
            test_input = {
                "text": "Help me analyze the latest market trends in technology sector",
                "user_id": "test_user_001",
                "task_id": "test_task_001"
            }

            test_context = {
                "domain": "business_analysis",
                "priority": "normal"
            }

            # Collect streaming results
            stream_chunks = []
            error_chunks = []
            start_time = datetime.utcnow()

            async for chunk in self.summarizer.stream(test_input, test_context):
                stream_chunks.append(chunk)

                # Check for error indicators in chunks
                chunk_str = str(chunk).lower()
                if any(error_indicator in chunk_str for error_indicator in [
                    "error:", "failed:", "cannot run the event loop",
                    "dict' object has no attribute", "mining process failed"
                ]):
                    error_chunks.append(chunk)
                    logger.error(f"Error detected in streaming chunk: {chunk}")

                # Parse chunk to check format
                try:
                    chunk_data = json.loads(chunk)
                    if "choices" in chunk_data:
                        logger.info(f"Received streaming chunk: {len(chunk)} bytes")
                    # Check for error fields in JSON
                    if "error" in chunk_data or "failed" in chunk_data:
                        error_chunks.append(chunk)
                        logger.error(f"Error field detected in chunk: {chunk_data}")
                except json.JSONDecodeError:
                    # Non-JSON chunk (might be plain text)
                    logger.info(f"Received text chunk: {chunk[:50]}...")

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            # Check if errors were detected
            if error_chunks:
                logger.error(f"Streaming test failed: {len(error_chunks)} error chunks detected")
                self.test_results.append({
                    "test": "basic_streaming",
                    "status": "failed",
                    "error": f"Detected {len(error_chunks)} error chunks in streaming response",
                    "error_chunks": error_chunks[:3]  # Include first 3 error chunks for debugging
                })
                return False

            # Check if we got meaningful results (not just error responses)
            if len(stream_chunks) < 2:
                logger.error("Streaming test failed: Insufficient chunks received")
                self.test_results.append({
                    "test": "basic_streaming",
                    "status": "failed",
                    "error": "Insufficient streaming chunks received"
                })
                return False

            logger.info(f"Streaming test completed: {len(stream_chunks)} chunks in {duration:.2f} seconds")

            self.test_results.append({
                "test": "basic_streaming",
                "status": "passed",
                "details": {
                    "chunks_received": len(stream_chunks),
                    "duration_seconds": duration,
                    "input": test_input
                }
            })

            return True

        except Exception as e:
            logger.error(f"Basic streaming test failed: {e}")
            self.test_results.append({
                "test": "basic_streaming",
                "status": "failed",
                "error": str(e)
            })
            return False

    async def test_non_streaming_run(self):
        """Test non-streaming run method."""
        try:
            logger.info("Testing non-streaming run...")

            # Prepare test input
            test_input = {
                "text": "Create a summary of renewable energy technologies",
                "user_id": "test_user_002",
                "task_id": "test_task_002"
            }

            test_context = {
                "domain": "technology",
                "priority": "high"
            }

            start_time = datetime.utcnow()
            result = await self.summarizer.run(test_input, test_context)
            end_time = datetime.utcnow()

            duration = (end_time - start_time).total_seconds()

            # Validate result structure
            assert "success" in result, "Missing success field in result"
            assert "result" in result, "Missing result field in result"
            assert "service" in result, "Missing service field in result"

            # Check for error indicators in the result
            result_str = str(result).lower()
            if any(error_indicator in result_str for error_indicator in [
                "error:", "failed:", "cannot run the event loop",
                "dict' object has no attribute", "mining process failed"
            ]):
                logger.error(f"Error detected in non-streaming result: {result}")
                self.test_results.append({
                    "test": "non_streaming_run",
                    "status": "failed",
                    "error": "Error indicators found in result",
                    "result_content": result
                })
                return False

            # Check if the result indicates actual failure despite success=True
            if result.get('success') and len(result.get('result', '')) < 10:
                logger.error(f"Non-streaming test failed: Result too short, likely an error response")
                self.test_results.append({
                    "test": "non_streaming_run",
                    "status": "failed",
                    "error": "Result too short, likely an error response",
                    "result_content": result
                })
                return False

            # Check for error fields in nested structures
            if isinstance(result.get('result'), dict):
                if 'error' in result['result'] or 'failed' in result['result']:
                    logger.error(f"Error field found in result: {result['result']}")
                    self.test_results.append({
                        "test": "non_streaming_run",
                        "status": "failed",
                        "error": "Error field found in nested result",
                        "result_content": result
                    })
                    return False

            logger.info(f"Non-streaming test completed in {duration:.2f} seconds")
            logger.info(f"Result success: {result['success']}")
            logger.info(f"Result length: {len(result['result'])} characters")

            self.test_results.append({
                "test": "non_streaming_run",
                "status": "passed",
                "details": {
                    "duration_seconds": duration,
                    "success": result["success"],
                    "result_length": len(result["result"]),
                    "service": result["service"]
                }
            })

            return True

        except Exception as e:
            logger.error(f"Non-streaming run test failed: {e}")
            self.test_results.append({
                "test": "non_streaming_run",
                "status": "failed",
                "error": str(e)
            })
            return False

    async def test_session_management(self):
        """Test session state management."""
        try:
            logger.info("Testing session management...")

            # Test getting non-existent session
            non_existent_state = await self.summarizer.get_session_state("non_existent_session")
            assert non_existent_state is None, "Should return None for non-existent session"

            # Test updating feedback for non-existent session
            feedback_updated = await self.summarizer.update_session_feedback(
                "non_existent_session",
                {"type": "test", "content": "test feedback"}
            )
            assert not feedback_updated, "Should return False for non-existent session"

            logger.info("Session management tests passed")

            self.test_results.append({
                "test": "session_management",
                "status": "passed",
                "details": {
                    "non_existent_session_handled": True,
                    "feedback_update_handled": True
                }
            })

            return True

        except Exception as e:
            logger.error(f"Session management test failed: {e}")
            self.test_results.append({
                "test": "session_management",
                "status": "failed",
                "error": str(e)
            })
            return False

    async def run_all_tests(self):
        """Run all tests and return summary."""
        logger.info("Starting LangGraph Summarizer test suite...")

        # Setup
        setup_success = await self.setup()

        # Check for setup errors
        if self.setup_errors:
            logger.error(f"Setup completed with errors: {self.setup_errors}")
            self.test_results.append({
                "test": "setup_validation",
                "status": "failed",
                "error": f"Setup errors detected: {self.setup_errors}"
            })

        if not setup_success:
            return {
                "status": "setup_failed",
                "results": self.test_results,
                "setup_errors": self.setup_errors
            }

        # Run tests
        tests = [
            self.test_service_info,
            self.test_service_metrics,
            self.test_session_management,
            self.test_basic_streaming,
            self.test_non_streaming_run,
        ]

        passed = 0
        failed = 0

        for test in tests:
            try:
                if await test():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Test {test.__name__} crashed: {e}")
                self.test_results.append({
                    "test": test.__name__,
                    "status": "crashed",
                    "error": str(e)
                })
                failed += 1

        # Adjust counts if setup errors were detected
        if self.setup_errors:
            failed += 1

        # Generate summary
        total_tests = len(tests) + (1 if self.setup_errors else 0)
        summary = {
            "status": "completed",
            "total_tests": total_tests,
            "passed": passed,
            "failed": failed,
            "success_rate": passed / total_tests if total_tests else 0,
            "results": self.test_results,
            "setup_errors": self.setup_errors
        }

        logger.info(f"Test suite completed: {passed}/{total_tests} tests passed ({summary['success_rate']:.2%})")

        if self.setup_errors:
            logger.error(f"Critical setup errors detected: {self.setup_errors}")

        return summary


async def main():
    """Main test execution function."""
    tester = LangGraphSummarizerTester()
    summary = await tester.run_all_tests()

    print("\n" + "="*60)
    print("LANGGRAPH SUMMARIZER TEST SUMMARY")
    print("="*60)
    print(f"Status: {summary['status']}")
    print(f"Tests: {summary['passed']}/{summary['total_tests']} passed ({summary['success_rate']:.2%})")
    print("\nDetailed Results:")

    for result in summary['results']:
        status_icon = "✅" if result['status'] == 'passed' else "❌"
        print(f"{status_icon} {result['test']}: {result['status']}")
        if result['status'] == 'failed':
            print(f"   Error: {result.get('error', 'Unknown error')}")

    print("="*60)

    return summary


if __name__ == "__main__":
    # Run tests
    asyncio.run(main())
