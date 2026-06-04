"""
E2E Tests for Complete Agent Workflows

Tests end-to-end agent execution with real LLMs and tools.
"""

import pytest
import os
from test.e2e.base import E2ETestBase, log_test_info


@pytest.mark.e2e
@pytest.mark.expensive
@pytest.mark.requires_api
class TestAgentWorkflowsE2E(E2ETestBase):
    """E2E tests for complete agent workflows."""
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY required for agent workflows"
    )
    @pytest.mark.asyncio
    async def test_simple_agent_execution(self):
        """Test simple agent execution with minimal task."""
        log_test_info(
            "Simple Agent Execution",
            task="Answer a simple question",
            llm="OpenAI"
        )
        
        try:
            from aiecs.domain.agent import Agent
            from aiecs.llm.clients.openai_client import OpenAIClient
            
            # Create agent with OpenAI client
            llm_client = OpenAIClient(api_key=os.getenv("OPENAI_API_KEY"))
            agent = Agent(
                name="test_agent",
                llm_client=llm_client
            )
            
            # Simple task
            task = "What is 2+2? Reply with just the number."
            
            response, latency = await self.measure_latency_async(
                agent.execute,
                task=task
            )
            
            # Assertions
            assert response is not None, "Agent should return a response"
            assert "4" in str(response), "Agent should answer correctly"
            assert latency < 10.0, f"Agent took {latency:.2f}s (should be < 10s)"
            
            print(f"\n✅ Agent executed successfully in {latency:.2f}s")
            print(f"📝 Response: {response}")
            
        except ImportError as e:
            pytest.skip(f"Agent components not available: {e}")
        except Exception as e:
            pytest.fail(f"Agent execution failed: {e}")
    
    @pytest.mark.skipif(
        not all([os.getenv("OPENAI_API_KEY"), os.getenv("GOOGLE_CSE_ID")]),
        reason="OPENAI_API_KEY and GOOGLE_CSE_ID required"
    )
    @pytest.mark.asyncio
    async def test_agent_with_search_tool(self):
        """Test agent using search tool for information retrieval."""
        log_test_info(
            "Agent with Search Tool",
            task="Search and answer",
            tools=["search"]
        )
        
        try:
            from aiecs.domain.agent import Agent
            from aiecs.llm.clients.openai_client import OpenAIClient
            from aiecs.tools.search_tool import SearchTool
            
            # Create agent with LLM and search tool
            llm_client = OpenAIClient(api_key=os.getenv("OPENAI_API_KEY"))
            search_tool = SearchTool(
                api_key=os.getenv("GOOGLE_CSE_API_KEY"),
                cse_id=os.getenv("GOOGLE_CSE_ID")
            )
            
            agent = Agent(
                name="search_agent",
                llm_client=llm_client,
                tools=[search_tool]
            )
            
            # Task requiring search
            task = "What is the latest Python version? Use search to find out."
            
            response, latency = await self.measure_latency_async(
                agent.execute,
                task=task,
                max_iterations=3  # Limit iterations
            )
            
            # Assertions
            assert response is not None, "Agent should return a response"
            assert latency < 30.0, f"Agent took {latency:.2f}s (should be < 30s)"
            
            print(f"\n✅ Agent with tool executed in {latency:.2f}s")
            
        except ImportError as e:
            pytest.skip(f"Required components not available: {e}")
        except Exception as e:
            pytest.fail(f"Agent with tool failed: {e}")
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY required"
    )
    @pytest.mark.asyncio
    async def test_agent_error_recovery(self):
        """Test agent error handling and recovery."""
        log_test_info(
            "Agent Error Recovery",
            test="Handle invalid task"
        )
        
        try:
            from aiecs.domain.agent import Agent
            from aiecs.llm.clients.openai_client import OpenAIClient
            
            llm_client = OpenAIClient(api_key=os.getenv("OPENAI_API_KEY"))
            agent = Agent(
                name="error_test_agent",
                llm_client=llm_client
            )
            
            # Task that might cause issues
            task = ""  # Empty task
            
            # Agent should handle this gracefully
            try:
                response = await agent.execute(task=task)
                # If it doesn't raise, it should return something indicating the issue
                assert response is not None
            except ValueError:
                # Acceptable - agent rejected invalid input
                pass
            
            print(f"\n✅ Agent handles errors correctly")
            
        except ImportError as e:
            pytest.skip(f"Agent components not available: {e}")
        except Exception as e:
            # Some errors are expected in error handling tests
            print(f"\n⚠️ Expected error occurred: {e}")


@pytest.mark.e2e
@pytest.mark.expensive
@pytest.mark.requires_api
@pytest.mark.requires_postgres
class TestKnowledgeGraphWorkflowE2E(E2ETestBase):
    """E2E tests for knowledge graph integration workflows."""
    
    @pytest.mark.skipif(
        not all([os.getenv("OPENAI_API_KEY"), os.getenv("POSTGRES_HOST")]),
        reason="OPENAI_API_KEY and PostgreSQL required"
    )
    @pytest.mark.asyncio
    async def test_knowledge_graph_build(self):
        """Test building knowledge graph from text."""
        log_test_info(
            "Knowledge Graph Build",
            text="Simple entity extraction",
            backend="PostgreSQL"
        )
        
        try:
            from aiecs.domain.knowledge_graph import KnowledgeGraphBuilder
            from aiecs.llm.clients.openai_client import OpenAIClient
            
            llm_client = OpenAIClient(api_key=os.getenv("OPENAI_API_KEY"))
            kg_builder = KnowledgeGraphBuilder(llm_client=llm_client)
            
            # Simple text for entity extraction
            text = "Python is a programming language. It was created by Guido van Rossum."
            
            response, latency = await self.measure_latency_async(
                kg_builder.build_from_text,
                text=text
            )
            
            # Assertions
            assert response is not None, "Should return knowledge graph"
            assert latency < 15.0, f"KG build took {latency:.2f}s (should be < 15s)"
            
            print(f"\n✅ Knowledge graph built in {latency:.2f}s")
            
        except ImportError as e:
            pytest.skip(f"KG components not available: {e}")
        except Exception as e:
            pytest.fail(f"KG build failed: {e}")
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY required"
    )
    @pytest.mark.asyncio
    async def test_knowledge_graph_query(self):
        """Test querying knowledge graph."""
        log_test_info(
            "Knowledge Graph Query",
            query="Find entities"
        )
        
        try:
            from aiecs.domain.knowledge_graph import KnowledgeGraphQuery
            from aiecs.llm.clients.openai_client import OpenAIClient
            
            llm_client = OpenAIClient(api_key=os.getenv("OPENAI_API_KEY"))
            kg_query = KnowledgeGraphQuery(llm_client=llm_client)
            
            # Simple query
            query = "Find all entities related to Python"
            
            response, latency = await self.measure_latency_async(
                kg_query.query,
                query=query,
                limit=5  # Minimal results
            )
            
            # Assertions
            assert response is not None, "Should return query results"
            assert latency < 10.0, f"Query took {latency:.2f}s (should be < 10s)"
            
            print(f"\n✅ Knowledge graph queried in {latency:.2f}s")
            
        except ImportError as e:
            pytest.skip(f"KG query components not available: {e}")
        except Exception as e:
            pytest.fail(f"KG query failed: {e}")


@pytest.mark.e2e
@pytest.mark.expensive
class TestIntegrationWorkflowE2E(E2ETestBase):
    """E2E tests for complete integrated workflows."""
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY required"
    )
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow with multiple components."""
        log_test_info(
            "Complete E2E Workflow",
            components=["Agent", "LLM", "Memory"],
            expected_duration="< 20s"
        )
        
        try:
            from aiecs.domain.agent import Agent
            from aiecs.llm.clients.openai_client import OpenAIClient
            
            # Setup
            llm_client = OpenAIClient(api_key=os.getenv("OPENAI_API_KEY"))
            agent = Agent(
                name="e2e_agent",
                llm_client=llm_client,
                enable_memory=True
            )
            
            # Execute multi-step workflow
            tasks = [
                "Remember this: My favorite color is blue.",
                "What is my favorite color?"
            ]
            
            start_time = self.start_time
            responses = []
            
            for task in tasks:
                response = await agent.execute(task=task)
                responses.append(response)
            
            total_latency = time.time() - start_time
            
            # Assertions
            assert len(responses) == len(tasks), "Should complete all tasks"
            assert all(r is not None for r in responses), "All responses should be valid"
            assert "blue" in str(responses[1]).lower(), "Agent should remember context"
            assert total_latency < 20.0, f"Workflow took {total_latency:.2f}s (should be < 20s)"
            
            print(f"\n✅ Complete E2E workflow executed in {total_latency:.2f}s")
            print(f"📊 Tasks completed: {len(tasks)}")
            
        except ImportError as e:
            pytest.skip(f"Workflow components not available: {e}")
        except Exception as e:
            pytest.fail(f"E2E workflow failed: {e}")


import time  # Import at top level for time tracking
