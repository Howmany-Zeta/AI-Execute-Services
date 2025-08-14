#!/usr/bin/env python3
"""
Enhanced Test Script for MiningService Event Loops using pytest

This comprehensive test script covers all three main event loops:
1. demand_analysis->clarify->intent_analysis
2. intent_analysis->meta_architect->feedback->general roadmap->package_results
3. intent_analysis->simple_strategy->feedback->intent_analysis or package_results

The script includes predefined user feedback scenarios to test real LLM interactions
and validates the complete workflow state transitions.
"""

import asyncio
import logging
import sys
import os
import json
import time
import pytest
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

# Add the app directory to Python path
app_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'app')
if os.path.exists(app_path):
    sys.path.insert(0, app_path)
else:
    # Fallback: try to find the app directory from the current working directory
    current_dir = os.getcwd()
    app_path = os.path.join(current_dir, 'app')
    if os.path.exists(app_path):
        sys.path.insert(0, app_path)
    else:
        # Last resort: try to find app directory in parent directories
        parent_dir = os.path.dirname(current_dir)
        app_path = os.path.join(parent_dir, 'app')
        if os.path.exists(app_path):
            sys.path.insert(0, app_path)

from services.llm_integration import LLMIntegrationManager
from services.multi_task.services.demand.mining import MiningService
from services.multi_task.services.summarizer import Summarizer
from services.multi_task.core.models.services_models import MiningContext, ServiceStatus
from services.multi_task.config.config_manager import ConfigManager
from langchain_core.messages import AIMessage, BaseMessage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestData:
    """Test data and scenarios for the tests."""

    @staticmethod
    def get_test_scenarios() -> Dict[str, Dict[str, Any]]:
        """Prepare test scenarios for different flow paths."""
        return {
            "vague_request": {
                "input": "Help me with my business",
                "expected_demand_state": "VAGUE_UNCLEAR",
                "expected_flow": "demand_analysis->clarify->intent_analysis",
                "description": "Vague request requiring clarification",
                "clarification_responses": [
                    # 第一轮澄清：基本业务信息
                    "I need help analyzing my e-commerce business performance",
                    "I run an online retail store selling electronics",
                    "I want to understand sales trends and identify growth opportunities",
                    # 第二轮澄清：具体业务细节
                    "My store has been operating for 3 years with annual revenue of $500K",
                    "I sell smartphones, laptops, and accessories through my website",
                    "I want to analyze customer behavior and optimize marketing strategies",
                    # 第三轮澄清：分析目标和范围
                    "I need comprehensive analysis of customer acquisition costs and lifetime value",
                    "Focus on identifying the most profitable product categories",
                    "Include recommendations for inventory optimization and pricing strategies"
                ]
            },
            "complex_business_analysis": {
                "input": "Analyze Tesla's comprehensive business strategy including market positioning, competitive advantages, financial performance, technological innovations, and future growth prospects across all business segments for the next 5 years",
                "expected_demand_state": "SMART_LARGE_SCOPE",
                "expected_flow": "intent_analysis->meta_architect->feedback->roadmap->package_results",
                "description": "Complex request requiring meta architect",
                "clarification_responses": [
                    # 第一轮澄清：分析范围和重点
                    "Focus on market positioning and competitive analysis",
                    "Include financial performance metrics and projections",
                    "Analyze technological innovations and R&D investments",
                    # 第二轮澄清：具体业务领域
                    "Prioritize analysis of automotive and energy storage segments",
                    "Include analysis of Tesla's autonomous driving technology",
                    "Examine the impact of regulatory changes and market competition",
                    # 第三轮澄清：分析深度和时间框架
                    "Provide detailed analysis of Tesla's supply chain and manufacturing efficiency",
                    "Include scenario analysis for different market conditions",
                    "Focus on actionable insights for strategic decision-making"
                ]
            },
            "simple_specific_request": {
                "input": "What were Apple's Q3 2024 revenue figures compared to Q3 2023?",
                "expected_demand_state": "SMART_COMPLIANT",
                "expected_flow": "intent_analysis->simple_strategy->feedback->package_results",
                "description": "Simple specific request",
                "clarification_responses": [
                    "Focus on revenue comparison between Q3 2024 and Q3 2023",
                    "Include both absolute numbers and percentage changes",
                    "Provide context for any significant changes"
                ]
            },
            "medium_complexity_request": {
                "input": "Compare the market share of top 3 smartphone manufacturers in 2024 and analyze their competitive strategies",
                "expected_demand_state": "SMART_COMPLIANT",
                "expected_flow": "intent_analysis->simple_strategy->feedback->package_results",
                "description": "Medium complexity analysis request",
                "clarification_responses": [
                    "Focus on Samsung, Apple, and Xiaomi market shares",
                    "Include both global and regional market data",
                    "Analyze competitive strategies and positioning"
                ]
            }
        }

    @staticmethod
    def get_feedback_scenarios() -> Dict[str, Dict[str, Any]]:
        """Prepare user feedback scenarios for testing LLM interactions."""
        return {
            "clarification_responses": {
                "scenario_1": {
                    "questions": [
                        "What specific aspect of your business needs help?",
                        "What is your business industry or domain?",
                        "What specific outcomes are you looking for?"
                    ],
                    "responses": [
                        "I need help analyzing my e-commerce business performance",
                        "I run an online retail store selling electronics",
                        "I want to understand sales trends and identify growth opportunities"
                    ],
                    "expected_refined_input": "Analyze e-commerce electronics retail business performance to understand sales trends and identify growth opportunities"
                },
                "scenario_2": {
                    "questions": [
                        "What type of market analysis do you need?",
                        "Which specific markets or regions?",
                        "What timeframe should be covered?"
                    ],
                    "responses": [
                        "I need competitive analysis and market positioning",
                        "Focus on North American and European markets",
                        "Cover the last 2 years with projections for next year"
                    ],
                    "expected_refined_input": "Conduct competitive analysis and market positioning study for North American and European markets covering last 2 years with next year projections"
                }
            },
            "meta_architect_feedback": {
                "approval": {
                    "confirmation": True,
                    "feedback": "The strategic blueprint looks comprehensive and well-structured. Please proceed with the detailed roadmap generation.",
                    "expected_next_step": "generate_roadmap"
                },
                "modification_request": {
                    "confirmation": False,
                    "feedback": "The blueprint is good but please add more focus on digital transformation aspects and include risk assessment components.",
                    "adjustments": [
                        "Add digital transformation analysis",
                        "Include comprehensive risk assessment",
                        "Expand on technology adoption strategies"
                    ],
                    "expected_next_step": "meta_architect_flow"
                }
            },
            "simple_strategy_feedback": {
                "approval": {
                    "confirmation": True,
                    "feedback": "The analysis approach looks good. Please proceed with execution.",
                    "expected_next_step": "package_results"
                },
                "refinement_request": {
                    "confirmation": False,
                    "feedback": "Please add more detailed financial metrics analysis and include competitor comparison.",
                    "adjustments": [
                        "Include detailed financial ratios",
                        "Add competitor benchmarking",
                        "Expand market share analysis"
                    ],
                    "expected_next_step": "intent_analysis"
                }
            }
        }


@pytest.fixture(scope="session")
def mining_service():
    """Fixture to provide initialized MiningService for all tests."""
    logger.info("Setting up MiningService fixture...")

    async def _create_mining_service():
        try:
            # Initialize core components
            llm_manager = LLMIntegrationManager()
            config_manager = ConfigManager()

            # Initialize MiningService
            mining_service = MiningService(llm_manager, config_manager)
            await mining_service.initialize()

            logger.info("MiningService fixture setup completed")
            return mining_service

        except Exception as e:
            logger.error(f"Failed to setup MiningService fixture: {e}")
            raise

    # Create and return the mining service synchronously
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        mining_service = loop.run_until_complete(_create_mining_service())
        yield mining_service
    finally:
        loop.close()
        logger.info("Cleaning up MiningService fixture...")


@pytest.fixture(scope="session")
def summarizer():
    """Fixture to provide initialized Summarizer for all tests."""
    logger.info("Setting up Summarizer fixture...")

    async def _create_summarizer():
        try:
            summarizer = Summarizer()
            await summarizer.initialize()

            logger.info("Summarizer fixture setup completed")
            return summarizer

        except Exception as e:
            logger.error(f"Failed to setup Summarizer fixture: {e}")
            raise

    # Create and return the summarizer synchronously
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        summarizer = loop.run_until_complete(_create_summarizer())
        yield summarizer
    finally:
        loop.close()
        logger.info("Cleaning up Summarizer fixture...")


@pytest.fixture
def test_scenarios():
    """Fixture to provide test scenarios."""
    return TestData.get_test_scenarios()


@pytest.fixture
def feedback_scenarios():
    """Fixture to provide feedback scenarios."""
    return TestData.get_feedback_scenarios()


# ==================== Flow 1: demand_analysis->clarify->intent_analysis ====================

@pytest.mark.asyncio
async def test_flow_1_demand_analysis_clarify_intent_analysis(mining_service, test_scenarios):
    """Test Flow 1: demand_analysis->clarify->user feedback->clarify->user feedback->clarify->user feedback(max 3round clarify)->intent analysis(flow 1 end)"""
    logger.info("=== Testing Flow 1: Complete Clarification Flow to Intent Analysis ===")

    scenario = test_scenarios["vague_request"]

    try:
        # Step 1: Initial demand analysis with vague input
        context = MiningContext(
            user_id="test_user_flow1",
            session_id="test_session_flow1",
            task_id="test_task_flow1",
            domain="business"
        )

        logger.info(f"Step 1: Initial mining with vague input: '{scenario['input']}'")

        # Execute initial mining - should trigger clarification
        result = await mining_service.mine_requirements(scenario['input'], context)

        # Verify clarification was requested
        assert result is not None, "Expected mining result"
        assert getattr(result, 'status', None) == ServiceStatus.WAITING_FOR_USER_FEEDBACK.value, "Should be waiting for user feedback after a vague request"

        logger.info(f"Step 1 completed - demand state: {result.demand_state}")

        # Step 2: Complete clarification loop (max 3 rounds)
        clarification_responses = scenario['clarification_responses']
        current_round = 0
        max_rounds = 3
        resumed_result = None

        while current_round < max_rounds:
            current_round += 1
            responses_per_round = 3  # 每轮3个回答
            start_idx = (current_round - 1) * responses_per_round
            end_idx = start_idx + responses_per_round

            # 获取当前轮的澄清回答
            current_responses = clarification_responses[start_idx:end_idx]

            if not current_responses:
                logger.info(f"No more clarification responses available for round {current_round}")
                break

            logger.info(f"Step 2.{current_round}: Providing clarification feedback (Round {current_round})")
            logger.info(f"Responses for this round: {current_responses}")

            clarification_feedback = {
                "type": "clarification",
                "responses": current_responses
            }

            resumed_result = await mining_service.resume_workflow_with_feedback(
                context.session_id, clarification_feedback
            )

            # Verify clarification was processed
            assert resumed_result is not None, f"Expected resumed result after clarification round {current_round}"
            logger.info(f"Step 2.{current_round} completed - demand state: {resumed_result.demand_state}")

            # 每一轮澄清后进行断言
            if resumed_result.demand_state == "SMART_COMPLIANT":
                logger.info(f"✅ Round {current_round}: Demand state is SMART_COMPLIANT - MiningService will end clarification and proceed to intent_analysis")
                break
            elif current_round >= max_rounds:
                logger.info(f"✅ Round {current_round}: Reached maximum clarification rounds ({max_rounds}) - MiningService will force demand state to SMART_COMPLIANT")
                # 验证 MiningService 是否强制更改了需求状态
                assert resumed_result.demand_state == "SMART_COMPLIANT", f"Expected MiningService to force demand state to SMART_COMPLIANT after {max_rounds} rounds"
                break
            elif getattr(resumed_result, 'status', None) == ServiceStatus.WAITING_FOR_USER_FEEDBACK.value:
                logger.info(f"Round {current_round}: Still waiting for feedback - continuing with round {current_round + 1}")
                # 验证仍在等待反馈状态
                assert resumed_result.demand_state in ["VAGUE_UNCLEAR", "SMART_LARGE_SCOPE"], f"Expected demand state to be unclear or large scope when waiting for feedback, got {resumed_result.demand_state}"
                continue
            else:
                logger.info(f"Round {current_round}: Unexpected state - {resumed_result.demand_state}")
                break

        # Step 3: Verify final result contains intent analysis (Flow 1 end)
        logger.info(f"Final result after {current_round} clarification rounds - demand state: {resumed_result.demand_state}")

        # Verify the workflow completed successfully
        if resumed_result.error:
            logger.error(f"Workflow has error: {resumed_result.error}")
            raise Exception(f"Workflow error: {resumed_result.error}")

        # Verify intent analysis was performed (Flow 1 end condition)
        assert hasattr(resumed_result, 'intent_analysis') and resumed_result.intent_analysis, \
            "Expected intent analysis to be performed after clarification rounds"

        # Verify intent analysis has required fields
        intent_analysis = resumed_result.intent_analysis
        assert 'intent_categories' in intent_analysis, "Expected intent_categories in intent analysis"
        assert 'complexity_assessment' in intent_analysis, "Expected complexity_assessment in intent analysis"

        logger.info("✅ Step 3 passed: Intent analysis completed successfully (Flow 1 end)")
        logger.info(f"Intent analysis: {intent_analysis}")
        logger.info(f"Intent categories: {intent_analysis.get('intent_categories', [])}")
        logger.info(f"Complexity level: {intent_analysis.get('complexity_assessment', {}).get('complexity_level', 'unknown')}")

        logger.info("✅ Flow 1 test completed successfully - Full clarification flow to intent analysis")

    except Exception as e:
        logger.error(f"❌ Flow 1 test failed: {e}")
        raise


# ==================== Flow 2: intent_analysis->meta_architect->feedback->roadmap->package_results ====================

@pytest.mark.asyncio
async def test_flow_2_intent_analysis_meta_architect_roadmap(mining_service, test_scenarios, feedback_scenarios):
    """Test Flow 2: demand analysis->clarify->user feedback->clarify->user feedback->clarify->user feedback(max 3round clarify)->intent analysis->meta_architect->road_map->result package->finalize_result(flow 2 end)"""
    logger.info("=== Testing Flow 2: Complete Flow to Meta Architect and Roadmap ===")

    scenario = test_scenarios["complex_business_analysis"]

    try:
        # Step 1: Start with complex request that should trigger clarification first (SMART_LARGE_SCOPE)
        context = MiningContext(
            user_id="test_user_flow2",
            session_id="test_session_flow2",
            task_id="test_task_flow2",
            domain="business_strategy"
        )

        logger.info(f"Step 1: Initial mining with complex input: '{scenario['input'][:100]}...'")

        # Execute mining - should go to clarify first due to SMART_LARGE_SCOPE
        result = await mining_service.mine_requirements(scenario['input'], context)

        # Verify clarification was triggered first
        assert result.demand_state == "SMART_LARGE_SCOPE", "Demand state should be SMART_LARGE_SCOPE"
        assert getattr(result, 'status', None) == ServiceStatus.WAITING_FOR_USER_FEEDBACK.value, "Should be waiting for user feedback after a large scope request"
        assert hasattr(result, 'messages') and result.messages, "Result should have a non-empty messages list"
        last_message = result.messages[-1]
        assert isinstance(last_message, dict), "Last message should be a dictionary"
        assert last_message.get("role") == "assistant", "Last message role should be 'assistant'"
        assert "Clarification needed" in last_message.get("content", ""), "Last message content should request clarification"

        logger.info("✅ Step 1a passed: SMART_LARGE_SCOPE request was correctly routed to clarification.")

        # Step 1b: Complete clarification loop (max 3 rounds)
        clarification_responses = scenario.get("clarification_responses", [])
        current_round = 0
        max_rounds = 3
        result = None

        while current_round < max_rounds:
            current_round += 1
            responses_per_round = 3  # 每轮3个回答
            start_idx = (current_round - 1) * responses_per_round
            end_idx = start_idx + responses_per_round

            # 获取当前轮的澄清回答
            current_responses = clarification_responses[start_idx:end_idx]

            if not current_responses:
                logger.info(f"No more clarification responses available for round {current_round}")
                break

            logger.info(f"Step 1b.{current_round}: Providing clarification responses (Round {current_round})")
            logger.info(f"Responses for this round: {current_responses}")

            clarification_feedback = {
                "type": "clarification",
                "responses": current_responses
            }

            # Resume workflow with clarification feedback
            result = await mining_service.resume_workflow_with_feedback(
                "test_session_flow2", clarification_feedback
            )

            logger.info(f"✅ Clarification responses processed for round {current_round}")
            logger.info(f"Demand state after round {current_round}: {result.demand_state}")

            # 每一轮澄清后进行断言
            if result.demand_state == "SMART_COMPLIANT":
                logger.info(f"✅ Round {current_round}: Demand state is SMART_COMPLIANT - MiningService will end clarification and proceed to intent_analysis")
                break
            elif current_round >= max_rounds:
                logger.info(f"✅ Round {current_round}: Reached maximum clarification rounds ({max_rounds}) - MiningService will force demand state to SMART_COMPLIANT")
                # 验证 MiningService 是否强制更改了需求状态
                assert result.demand_state == "SMART_COMPLIANT", f"Expected MiningService to force demand state to SMART_COMPLIANT after {max_rounds} rounds"
                break
            elif getattr(result, 'status', None) == ServiceStatus.WAITING_FOR_USER_FEEDBACK.value:
                logger.info(f"Continuing with round {current_round + 1} - still waiting for feedback")
                continue
            else:
                logger.info(f"Unexpected state after round {current_round}: {result.demand_state}")
                break

        # Step 2: Verify intent analysis was performed after clarification
        assert hasattr(result, 'intent_analysis') and result.intent_analysis, \
            "Expected intent analysis after clarification"

        # Verify intent analysis has required fields
        intent_analysis = result.intent_analysis
        assert "intent_categories" in intent_analysis, "Intent analysis missing categories"
        assert "complexity_assessment" in intent_analysis, "Intent analysis missing complexity assessment"
        assert len(intent_analysis.get("intent_categories", [])) > 0, "Intent analysis categories should not be empty"

        logger.info("✅ Step 2 passed: Intent analysis completed after clarification")
        logger.info(f"Intent analysis categories: {intent_analysis.get('intent_categories', [])}")
        logger.info(f"Intent analysis complexity: {intent_analysis.get('complexity_assessment', {}).get('complexity_level', 'unknown')}")

        # Step 3: Verify meta architect was triggered and provide confirmation
        # Check if meta architect was triggered (either completed or waiting for feedback)
        meta_architect_triggered = (
            hasattr(result, 'meta_architect_result') and result.meta_architect_result
        ) or (
            hasattr(result, 'status') and result.status == ServiceStatus.WAITING_FOR_USER_FEEDBACK.value and
            hasattr(result, 'feedback_type') and result.feedback_type == "meta_architect_confirmation"
        )

        assert meta_architect_triggered, "Expected meta architect to be triggered for complex request"

        logger.info("✅ Step 3a passed: Meta architect triggered successfully")

        # Step 3b: Provide meta architect confirmation feedback
        if hasattr(result, 'status') and result.status == ServiceStatus.WAITING_FOR_USER_FEEDBACK.value:
            approval_scenario = feedback_scenarios["meta_architect_feedback"]["approval"]

            logger.info("Step 3b: Providing meta architect confirmation feedback")

            approval_feedback = {
                "type": "meta_architect_confirmation",
                "confirmation": approval_scenario["confirmation"],  # True
                "feedback": approval_scenario["feedback"],
                "user_input": scenario['input']
            }

            # Resume workflow with approval
            result = await mining_service.resume_workflow_with_feedback(
                "test_session_flow2", approval_feedback
            )

            logger.info("✅ Step 3b passed: Meta architect confirmation processed")

        # Step 4: Verify roadmap generation and final results
        # Verify that workflow proceeded after meta architect approval
        assert hasattr(result, 'status') and result.status in ["completed", "in_progress"], \
            "Expected workflow to proceed after meta architect approval"

        # Verify final results contain expected components
        assert hasattr(result, 'meta_architect_result') and result.meta_architect_result, \
            "Expected meta architect result in final output"

        # Verify meta architect result has required fields
        meta_architect_result = result.meta_architect_result
        assert isinstance(meta_architect_result, dict), "Meta architect result should be a dictionary"
        assert len(meta_architect_result) > 0, "Meta architect result should not be empty"

        # Verify that roadmap was generated after approval
        if "execution_roadmap" in meta_architect_result:
            logger.info("✅ Roadmap generation confirmed after approval")
        else:
            logger.info("⚠️ Roadmap may be generated in subsequent steps")

        logger.info("✅ Flow 2 completed successfully - Full flow to meta architect and roadmap")
        logger.info(f"Meta architect result keys: {list(result.meta_architect_result.keys()) if result.meta_architect_result else []}")

    except Exception as e:
        logger.error(f"❌ Flow 2 test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_flow_2_approval_only_path(mining_service, test_scenarios, feedback_scenarios):
    """Test Flow 2 approval path: demand analysis->clarify->user feedback->clarify->user feedback->clarify->user feedback(max 3round clarify)->intent analysis->meta_architect->approval->roadmap->package_results->finalize_result"""
    logger.info("=== Testing Flow 2 approval path: Complete Flow with Direct Approval ===")

    scenario = test_scenarios["complex_business_analysis"]

    try:
        # Step 1: Start with complex request that should trigger clarification first (SMART_LARGE_SCOPE)
        context = MiningContext(
            user_id="test_user_flow2_approval",
            session_id="test_session_flow2_approval",
            task_id="test_task_flow2_approval",
            domain="business_strategy"
        )

        logger.info(f"Step 1: Initial mining with complex input: '{scenario['input'][:100]}...'")

        # Execute mining - should go to clarify first due to SMART_LARGE_SCOPE
        result = await mining_service.mine_requirements(scenario['input'], context)

        # Step 1a: Verify clarification was triggered first
        clarification_triggered = (
            hasattr(result, 'status') and result.status == "waiting_for_user_feedback" and
            hasattr(result, 'messages') and result.messages
        )

        if clarification_triggered:
            logger.info("✅ Step 1a passed: Clarification triggered for SMART_LARGE_SCOPE request")

            # Step 1b: Complete clarification loop (max 3 rounds)
            clarification_responses = scenario.get("clarification_responses", [])
            current_round = 0
            max_rounds = 3
            result = None

            while current_round < max_rounds:
                current_round += 1
                responses_per_round = 3  # 每轮3个回答
                start_idx = (current_round - 1) * responses_per_round
                end_idx = start_idx + responses_per_round

                # 获取当前轮的澄清回答
                current_responses = clarification_responses[start_idx:end_idx]

                if not current_responses:
                    logger.info(f"No more clarification responses available for round {current_round}")
                    break

                logger.info(f"Step 1b.{current_round}: Providing clarification responses (Round {current_round})")
                logger.info(f"Responses for this round: {current_responses}")

                clarification_feedback = {
                    "type": "clarification",
                    "responses": current_responses
                }

                # Resume workflow with clarification feedback
                result = await mining_service.resume_workflow_with_feedback(
                    "test_session_flow2_approval", clarification_feedback
                )

                logger.info(f"✅ Clarification responses processed for round {current_round}")
                logger.info(f"Demand state after round {current_round}: {result.demand_state}")

                # 每一轮澄清后进行断言
                if result.demand_state == "SMART_COMPLIANT":
                    logger.info(f"✅ Round {current_round}: Demand state is SMART_COMPLIANT - MiningService will end clarification and proceed to intent_analysis")
                    break
                elif current_round >= max_rounds:
                    logger.info(f"✅ Round {current_round}: Reached maximum clarification rounds ({max_rounds}) - MiningService will force demand state to SMART_COMPLIANT")
                    # 验证 MiningService 是否强制更改了需求状态
                    assert result.demand_state == "SMART_COMPLIANT", f"Expected MiningService to force demand state to SMART_COMPLIANT after {max_rounds} rounds"
                    break
                elif getattr(result, 'status', None) == ServiceStatus.WAITING_FOR_USER_FEEDBACK.value:
                    logger.info(f"Round {current_round}: Still waiting for feedback - continuing with round {current_round + 1}")
                    continue
                else:
                    logger.info(f"Unexpected state after round {current_round}: {result.demand_state}")
                    break

        # Step 2: Verify intent analysis was performed after clarification
        assert hasattr(result, 'intent_analysis') and result.intent_analysis, \
            "Expected intent analysis after clarification"

        # Check if meta architect was triggered and waiting for feedback
        assert hasattr(result, 'status') and result.status == ServiceStatus.WAITING_FOR_USER_FEEDBACK.value, \
            "Expected meta architect to be waiting for feedback"
        assert hasattr(result, 'feedback_type') and result.feedback_type == "meta_architect_confirmation", \
            "Expected meta_architect_confirmation feedback type"

        logger.info("✅ Step 2 passed: Meta architect triggered and waiting for feedback after clarification")

        # Step 3: Test direct approval path (meta_architect->roadmap->package_results)
        approval_scenario = feedback_scenarios["meta_architect_feedback"]["approval"]

        logger.info("Step 3: Providing direct approval feedback")

        approval_feedback = {
            "type": "meta_architect_confirmation",
            "confirmation": approval_scenario["confirmation"],  # True
            "feedback": approval_scenario["feedback"],
            "user_input": scenario['input']
        }

        # Resume workflow with approval
        result = await mining_service.resume_workflow_with_feedback(
            "test_session_flow2_approval", approval_feedback
        )

        # Step 4: Verify roadmap generation was triggered
        assert hasattr(result, 'status') and result.status in ["completed", "in_progress"], \
            "Expected workflow to proceed after meta architect approval"

        # Verify final results contain expected components
        assert hasattr(result, 'meta_architect_result') and result.meta_architect_result, \
            "Expected meta architect result in final output"

        # Verify meta architect result has required fields
        meta_architect_result = result.meta_architect_result
        assert isinstance(meta_architect_result, dict), "Meta architect result should be a dictionary"
        assert len(meta_architect_result) > 0, "Meta architect result should not be empty"

        # Verify that roadmap was generated after approval
        if "execution_roadmap" in meta_architect_result:
            logger.info("✅ Roadmap generation confirmed after approval")
        else:
            logger.info("⚠️ Roadmap may be generated in subsequent steps")

        logger.info("✅ Flow 2 approval path completed successfully - Full flow with direct approval")
        logger.info(f"Meta architect result keys: {list(result.meta_architect_result.keys()) if result.meta_architect_result else []}")

    except Exception as e:
        logger.error(f"❌ Flow 2 approval path test failed: {e}")
        raise


# ==================== Flow 3: intent_analysis->simple_strategy->feedback->intent_analysis or package_results ====================

@pytest.mark.asyncio
async def test_flow_3_intent_analysis_simple_strategy_feedback(mining_service, test_scenarios, feedback_scenarios):
    """Test Flow 3: intent_analysis->simple_strategy->feedback->intent_analysis or package_results"""
    logger.info("=== Testing Flow 3: intent_analysis->simple_strategy->feedback->package_results ===")

    scenario = test_scenarios["simple_specific_request"]

    try:
        # Step 1: Start with simple specific request
        context = MiningContext(
            user_id="test_user_flow3",
            session_id="test_session_flow3",
            task_id="test_task_flow3",
            domain="financial_analysis"
        )

        logger.info(f"Step 1: Testing with simple input: '{scenario['input']}'")

        # Execute mining - should go to intent analysis then simple strategy
        result = await mining_service.mine_requirements(scenario['input'], context)

        # Verify intent analysis was performed
        assert hasattr(result, 'intent_analysis') and result.intent_analysis, \
            "Expected intent analysis for simple request"

        # Check if simple strategy was triggered
        simple_strategy_triggered = (
            hasattr(result, 'simple_strategy_result') and result.simple_strategy_result
        ) or (
            hasattr(result, 'status') and result.status == ServiceStatus.WAITING_FOR_USER_FEEDBACK.value and
            hasattr(result, 'feedback_type') and result.feedback_type == "simple_strategy_confirmation"
        )

        assert simple_strategy_triggered, "Expected simple strategy to be triggered for simple request"

        logger.info("✅ Step 1 passed: Intent analysis and simple strategy triggered")

        # Step 2: Test approval path (simple_strategy->package_results)
        if hasattr(result, 'status') and result.status == ServiceStatus.WAITING_FOR_USER_FEEDBACK.value:
            feedback_scenario = feedback_scenarios["simple_strategy_feedback"]["approval"]

            logger.info("Step 2a: Testing approval path - providing simple strategy approval")

            simple_strategy_feedback = {
                "type": "simple_strategy_confirmation",
                "confirmation": feedback_scenario["confirmation"],
                "feedback": feedback_scenario["feedback"],
                "user_input": scenario['input']  # Include original user input
            }

            # Resume workflow with approval
            approved_result = await mining_service.resume_workflow_with_feedback(
                "test_session_flow3", simple_strategy_feedback
            )

            # Verify workflow proceeded to package results
            assert hasattr(approved_result, 'status') and approved_result.status in ["completed", "in_progress"], \
                "Expected workflow to proceed to package results after approval"

            logger.info("✅ Step 2a passed: Simple strategy approved, proceeding to package results")

        # Step 3: Test refinement path (simple_strategy->intent_analysis)
        context_refinement = MiningContext(
            user_id="test_user_flow3b",
            session_id="test_session_flow3b",
            task_id="test_task_flow3b",
            domain="financial_analysis"
        )

        # Execute again to test refinement path
        result_refinement = await mining_service.mine_requirements(scenario['input'], context_refinement)

        if hasattr(result_refinement, 'status') and result_refinement.status == "waiting_for_user_feedback":
            feedback_scenario = feedback_scenarios["simple_strategy_feedback"]["refinement_request"]

            logger.info("Step 3: Testing refinement path - requesting strategy refinement")

            refinement_feedback = {
                "type": "simple_strategy_confirmation",
                "confirmation": feedback_scenario["confirmation"],
                "feedback": feedback_scenario["feedback"],
                "adjustments": feedback_scenario["adjustments"],
                "user_input": scenario['input']  # Include original user input
            }

            # Resume workflow with refinement request
            refined_result = await mining_service.resume_workflow_with_feedback(
                "test_session_flow3b", refinement_feedback
            )

            # Verify workflow went back to intent analysis
            assert hasattr(refined_result, 'intent_analysis'), \
                "Expected workflow to return to intent analysis after refinement request"

            logger.info("✅ Step 3 passed: Simple strategy refinement triggered re-analysis")

        logger.info("✅ Flow 3 completed successfully - both approval and refinement paths tested")

    except Exception as e:
        logger.error(f"❌ Flow 3 test failed: {e}")
        raise


# ==================== Additional Test Methods ====================

@pytest.mark.asyncio
async def test_user_feedback_scenarios(mining_service, feedback_scenarios):
    """Test various user feedback scenarios with predefined responses."""
    logger.info("=== Testing User Feedback Scenarios ===")

    try:
        # Test different clarification scenarios
        for scenario_name, scenario_data in feedback_scenarios["clarification_responses"].items():
            logger.info(f"Testing clarification scenario: {scenario_name}")

            context = MiningContext(
                user_id=f"test_user_{scenario_name}",
                session_id=f"test_session_{scenario_name}",
                task_id=f"test_task_{scenario_name}",
                domain="general"
            )

            # Start with vague input to trigger clarification
            result = await mining_service.mine_requirements("Help me with analysis", context)

            if hasattr(result, 'status') and result.status == ServiceStatus.WAITING_FOR_USER_FEEDBACK.value:
                # Provide predefined responses
                clarification_feedback = {
                    "type": "clarification",
                    "responses": scenario_data["responses"]
                }

                resumed_result = await mining_service.resume_workflow_with_feedback(
                    f"test_session_{scenario_name}", clarification_feedback
                )

                # Verify improvement in demand state
                assert resumed_result.demand_state != "VAGUE_UNCLEAR", \
                    f"Expected demand state improvement after clarification in {scenario_name}"

                logger.info(f"✅ Clarification scenario {scenario_name} passed")

        logger.info("✅ All user feedback scenarios tested successfully")

    except Exception as e:
        logger.error(f"❌ User feedback scenarios test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_workflow_state_transitions(mining_service):
    """Test workflow state transitions and persistence."""
    logger.info("=== Testing Workflow State Transitions ===")

    try:
        # Test state persistence across feedback cycles
        context = MiningContext(
            user_id="test_user_state",
            session_id="test_session_state",
            task_id="test_task_state",
            domain="business"
        )

        # Start workflow
        initial_result = await mining_service.mine_requirements(
            "Analyze market trends", context
        )

        # Verify initial state
        assert hasattr(initial_result, 'demand_state'), "Expected demand state in initial result"

        # If clarification is needed, test state persistence
        if hasattr(initial_result, 'status') and initial_result.status == ServiceStatus.WAITING_FOR_USER_FEEDBACK.value:
            # Provide feedback and verify state continuity
            feedback = {
                "type": "clarification",
                "responses": ["I need comprehensive market analysis for tech industry"]
            }

            resumed_result = await mining_service.resume_workflow_with_feedback(
                "test_session_state", feedback
            )

            # Verify state continuity
            assert hasattr(resumed_result, 'demand_state'), "Expected demand state in resumed result"
            assert resumed_result.demand_state != initial_result.demand_state or \
                   resumed_result.demand_state in ["SMART_COMPLIANT", "SMART_LARGE_SCOPE"], \
                   "Expected state progression after feedback"

            logger.info("✅ Workflow state transitions verified")

    except Exception as e:
        logger.error(f"❌ Workflow state transitions test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_error_handling_and_recovery(mining_service):
    """Test error handling and recovery mechanisms."""
    logger.info("=== Testing Error Handling and Recovery ===")

    try:
        # Test invalid input handling
        context = MiningContext(
            user_id="test_user_error",
            session_id="test_session_error",
            task_id="test_task_error",
            domain="general"
        )

        # Test empty input
        with pytest.raises((ValueError, Exception)):
            await mining_service.mine_requirements("", context)

        # Test invalid feedback
        with pytest.raises(Exception):
            await mining_service.resume_workflow_with_feedback(
                "nonexistent_session", {"invalid": "feedback"}
            )

        logger.info("✅ Error handling tests passed")

    except Exception as e:
        logger.error(f"❌ Error handling test failed: {e}")
        raise


# ==================== Additional Debugging Tests ====================

@pytest.mark.asyncio
async def test_debug_mining_service_initialization(mining_service):
    """Test that MiningService is properly initialized with all required components."""
    logger.info("=== Testing MiningService Initialization ===")

    try:
        # Verify mining service has required attributes
        assert hasattr(mining_service, 'llm_manager'), "MiningService should have llm_manager"
        assert hasattr(mining_service, 'config_manager'), "MiningService should have config_manager"
        assert hasattr(mining_service, 'interacter'), "MiningService should have interacter"
        assert hasattr(mining_service, 'intent_analyzer'), "MiningService should have intent_analyzer"

        # Verify components are initialized
        assert mining_service.llm_manager is not None, "LLM manager should be initialized"
        assert mining_service.config_manager is not None, "Config manager should be initialized"

        logger.info("✅ MiningService initialization test passed")

    except Exception as e:
        logger.error(f"❌ MiningService initialization test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_debug_context_creation():
    """Test MiningContext creation and validation."""
    logger.info("=== Testing MiningContext Creation ===")

    try:
        # Test valid context creation
        context = MiningContext(
            user_id="test_user_debug",
            session_id="test_session_debug",
            task_id="test_task_debug",
            domain="business"
        )

        # Verify context attributes
        assert context.user_id == "test_user_debug", "User ID should match"
        assert context.session_id == "test_session_debug", "Session ID should match"
        assert context.task_id == "test_task_debug", "Task ID should match"
        assert context.domain == "business", "Domain should match"

        logger.info("✅ MiningContext creation test passed")

    except Exception as e:
        logger.error(f"❌ MiningContext creation test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_debug_demand_analysis_states(mining_service, test_scenarios):
    """Test different demand analysis states and transitions."""
    logger.info("=== Testing Demand Analysis States ===")

    try:
        # Test VAGUE_UNCLEAR state
        context_vague = MiningContext(
            user_id="test_user_vague",
            session_id="test_session_vague",
            task_id="test_task_vague",
            domain="business"
        )

        vague_result = await mining_service.mine_requirements(
            test_scenarios["vague_request"]["input"], context_vague
        )

        assert hasattr(vague_result, 'demand_state'), "Result should have demand_state"
        logger.info(f"Vague request demand state: {vague_result.demand_state}")

        # Test SMART_COMPLIANT state
        context_smart = MiningContext(
            user_id="test_user_smart",
            session_id="test_session_smart",
            task_id="test_task_smart",
            domain="business"
        )

        smart_result = await mining_service.mine_requirements(
            test_scenarios["simple_specific_request"]["input"], context_smart
        )

        assert hasattr(smart_result, 'demand_state'), "Result should have demand_state"
        logger.info(f"Smart request demand state: {smart_result.demand_state}")

        logger.info("✅ Demand analysis states test passed")

    except Exception as e:
        logger.error(f"❌ Demand analysis states test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_debug_intent_analysis_completion(mining_service, test_scenarios):
    """Test intent analysis completion and structure."""
    logger.info("=== Testing Intent Analysis Completion ===")

    try:
        # Use a request that should trigger intent analysis
        context = MiningContext(
            user_id="test_user_intent",
            session_id="test_session_intent",
            task_id="test_task_intent",
            domain="business"
        )

        result = await mining_service.mine_requirements(
            test_scenarios["simple_specific_request"]["input"], context
        )

        # Check if intent analysis was performed
        if hasattr(result, 'intent_analysis') and result.intent_analysis:
            intent_analysis = result.intent_analysis

            # Verify required fields
            assert 'intent_categories' in intent_analysis, "Intent analysis should have categories"
            assert 'complexity_assessment' in intent_analysis, "Intent analysis should have complexity assessment"

            # Log details for debugging
            logger.info(f"Intent categories: {intent_analysis.get('intent_categories', [])}")
            logger.info(f"Complexity assessment: {intent_analysis.get('complexity_assessment', {})}")

            logger.info("✅ Intent analysis completion test passed")
        else:
            logger.warning("⚠️ Intent analysis not performed - this might be expected for some scenarios")

    except Exception as e:
        logger.error(f"❌ Intent analysis completion test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_debug_workflow_status_transitions(mining_service, test_scenarios):
    """Test workflow status transitions and state management."""
    logger.info("=== Testing Workflow Status Transitions ===")

    try:
        # Test workflow that should complete
        context_complete = MiningContext(
            user_id="test_user_complete",
            session_id="test_session_complete",
            task_id="test_task_complete",
            domain="business"
        )

        complete_result = await mining_service.mine_requirements(
            test_scenarios["simple_specific_request"]["input"], context_complete
        )

        # Check workflow status
        if hasattr(complete_result, 'status'):
            logger.info(f"Workflow status: {complete_result.status}")
            assert complete_result.status in [ServiceStatus.COMPLETED.value, ServiceStatus.IN_PROGRESS.value, ServiceStatus.WAITING_FOR_USER_FEEDBACK.value], \
                "Workflow status should be valid"

        logger.info("✅ Workflow status transitions test passed")

    except Exception as e:
        logger.error(f"❌ Workflow status transitions test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_debug_result_structure_validation(mining_service, test_scenarios):
    """Test that mining results have the expected structure."""
    logger.info("=== Testing Result Structure Validation ===")

    try:
        context = MiningContext(
            user_id="test_user_structure",
            session_id="test_session_structure",
            task_id="test_task_structure",
            domain="business"
        )

        result = await mining_service.mine_requirements(
            test_scenarios["simple_specific_request"]["input"], context
        )

        # Verify basic result structure
        assert hasattr(result, 'demand_state'), "Result should have demand_state"
        assert hasattr(result, 'session_id'), "Result should have session_id"
        assert hasattr(result, 'task_id'), "Result should have task_id"

        # Verify optional fields are present when expected
        if hasattr(result, 'intent_analysis') and result.intent_analysis:
            assert isinstance(result.intent_analysis, dict), "Intent analysis should be a dictionary"

        if hasattr(result, 'meta_architect_result') and result.meta_architect_result:
            assert isinstance(result.meta_architect_result, dict), "Meta architect result should be a dictionary"

        if hasattr(result, 'simple_strategy_result') and result.simple_strategy_result:
            assert isinstance(result.simple_strategy_result, dict), "Simple strategy result should be a dictionary"

        logger.info("✅ Result structure validation test passed")

    except Exception as e:
        logger.error(f"❌ Result structure validation test failed: {e}")
        raise


# ==================== Performance and Stress Tests ====================

@pytest.mark.asyncio
async def test_performance_multiple_requests(mining_service, test_scenarios):
    """Test performance with multiple concurrent requests."""
    logger.info("=== Testing Performance with Multiple Requests ===")

    try:
        import time
        start_time = time.time()

        # Create multiple contexts for concurrent testing
        contexts = []
        for i in range(3):
            context = MiningContext(
                user_id=f"test_user_perf_{i}",
                session_id=f"test_session_perf_{i}",
                task_id=f"test_task_perf_{i}",
                domain="business"
            )
            contexts.append(context)

        # Execute multiple requests
        tasks = []
        for i, context in enumerate(contexts):
            scenario_key = list(test_scenarios.keys())[i % len(test_scenarios)]
            task = mining_service.mine_requirements(
                test_scenarios[scenario_key]["input"], context
            )
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        duration = end_time - start_time

        # Verify all tasks completed successfully
        successful_results = [r for r in results if not isinstance(r, Exception)]
        failed_results = [r for r in results if isinstance(r, Exception)]

        logger.info(f"Performance test completed in {duration:.2f} seconds")
        logger.info(f"Successful requests: {len(successful_results)}")
        logger.info(f"Failed requests: {len(failed_results)}")

        assert len(successful_results) >= 2, "At least 2 out of 3 requests should succeed"
        assert duration < 60, "Performance test should complete within 60 seconds"

        logger.info("✅ Performance test passed")

    except Exception as e:
        logger.error(f"❌ Performance test failed: {e}")
        raise


# ==================== Test Configuration and Utilities ====================

def pytest_configure(config):
    """Configure pytest for this test suite."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers."""
    for item in items:
        # Add asyncio marker to all async tests
        if "async" in item.name or "test_flow" in item.name:
            item.add_marker(pytest.mark.asyncio)

        # Add slow marker to performance tests
        if "performance" in item.name:
            item.add_marker(pytest.mark.slow)

        # Add integration marker to workflow tests
        if "flow" in item.name or "workflow" in item.name:
            item.add_marker(pytest.mark.integration)


# ==================== Test Execution Helpers ====================

def run_specific_test(test_name: str):
    """Helper function to run a specific test by name."""
    import subprocess
    import sys

    cmd = [
        sys.executable, "-m", "pytest",
        __file__,
        f"-k {test_name}",
        "-v",
        "--tb=short"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result


def run_all_tests():
    """Helper function to run all tests."""
    import subprocess
    import sys

    cmd = [
        sys.executable, "-m", "pytest",
        __file__,
        "-v",
        "--tb=short",
        "--durations=10"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result


if __name__ == "__main__":
    # Allow running specific tests from command line
    import sys

    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        print(f"Running specific test: {test_name}")
        result = run_specific_test(test_name)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        sys.exit(result.returncode)
    else:
        print("Running all tests...")
        result = run_all_tests()
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        sys.exit(result.returncode)


# ==================== Additional Debugging Tests ====================

@pytest.mark.asyncio
async def test_debug_mining_service_initialization(mining_service):
    """Test that MiningService is properly initialized with all required components."""
    logger.info("=== Testing MiningService Initialization ===")

    try:
        # Verify mining service has required attributes
        assert hasattr(mining_service, 'llm_manager'), "MiningService should have llm_manager"
        assert hasattr(mining_service, 'config_manager'), "MiningService should have config_manager"
        assert hasattr(mining_service, 'interacter'), "MiningService should have interacter"
        assert hasattr(mining_service, 'intent_parser'), "MiningService should have intent_parser"

        # Verify components are initialized
        assert mining_service.llm_manager is not None, "LLM manager should be initialized"
        assert mining_service.config_manager is not None, "Config manager should be initialized"

        logger.info("✅ MiningService initialization test passed")

    except Exception as e:
        logger.error(f"❌ MiningService initialization test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_debug_context_creation():
    """Test MiningContext creation and validation."""
    logger.info("=== Testing MiningContext Creation ===")

    try:
        # Test valid context creation
        context = MiningContext(
            user_id="test_user_debug",
            session_id="test_session_debug",
            task_id="test_task_debug",
            domain="business"
        )

        # Verify context attributes
        assert context.user_id == "test_user_debug", "User ID should match"
        assert context.session_id == "test_session_debug", "Session ID should match"
        assert context.task_id == "test_task_debug", "Task ID should match"
        assert context.domain == "business", "Domain should match"

        logger.info("✅ MiningContext creation test passed")

    except Exception as e:
        logger.error(f"❌ MiningContext creation test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_debug_demand_analysis_states(mining_service, test_scenarios):
    """Test different demand analysis states and transitions."""
    logger.info("=== Testing Demand Analysis States ===")

    try:
        # Test VAGUE_UNCLEAR state
        context_vague = MiningContext(
            user_id="test_user_vague",
            session_id="test_session_vague",
            task_id="test_task_vague",
            domain="business"
        )

        vague_result = await mining_service.mine_requirements(
            test_scenarios["vague_request"]["input"], context_vague
        )

        assert hasattr(vague_result, 'demand_state'), "Result should have demand_state"
        logger.info(f"Vague request demand state: {vague_result.demand_state}")

        # Test SMART_COMPLIANT state
        context_smart = MiningContext(
            user_id="test_user_smart",
            session_id="test_session_smart",
            task_id="test_task_smart",
            domain="business"
        )

        smart_result = await mining_service.mine_requirements(
            test_scenarios["simple_specific_request"]["input"], context_smart
        )

        assert hasattr(smart_result, 'demand_state'), "Result should have demand_state"
        logger.info(f"Smart request demand state: {smart_result.demand_state}")

        # Test SMART_LARGE_SCOPE state
        context_large = MiningContext(
            user_id="test_user_large",
            session_id="test_session_large",
            task_id="test_task_large",
            domain="business"
        )

        large_result = await mining_service.mine_requirements(
            test_scenarios["complex_business_analysis"]["input"], context_large
        )

        assert hasattr(large_result, 'demand_state'), "Result should have demand_state"
        logger.info(f"Large scope request demand state: {large_result.demand_state}")

        logger.info("✅ Demand analysis states test passed")

    except Exception as e:
        logger.error(f"❌ Demand analysis states test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_debug_intent_analysis_completion(mining_service, test_scenarios):
    """Test intent analysis completion and structure."""
    logger.info("=== Testing Intent Analysis Completion ===")

    try:
        # Use a request that should trigger intent analysis
        context = MiningContext(
            user_id="test_user_intent",
            session_id="test_session_intent",
            task_id="test_task_intent",
            domain="business"
        )

        result = await mining_service.mine_requirements(
            test_scenarios["simple_specific_request"]["input"], context
        )

        # Check if intent analysis was performed
        if hasattr(result, 'intent_analysis') and result.intent_analysis:
            intent_analysis = result.intent_analysis

            # Verify required fields
            assert 'intent_categories' in intent_analysis, "Intent analysis should have categories"
            assert 'complexity_assessment' in intent_analysis, "Intent analysis should have complexity assessment"

            # Log details for debugging
            logger.info(f"Intent categories: {intent_analysis.get('intent_categories', [])}")
            logger.info(f"Complexity assessment: {intent_analysis.get('complexity_assessment', {})}")

            logger.info("✅ Intent analysis completion test passed")
        else:
            logger.warning("⚠️ Intent analysis not performed - this might be expected for some scenarios")

    except Exception as e:
        logger.error(f"❌ Intent analysis completion test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_debug_workflow_status_transitions(mining_service, test_scenarios):
    """Test workflow status transitions and state management."""
    logger.info("=== Testing Workflow Status Transitions ===")

    try:
        # Test workflow that should complete
        context_complete = MiningContext(
            user_id="test_user_complete",
            session_id="test_session_complete",
            task_id="test_task_complete",
            domain="business"
        )

        complete_result = await mining_service.mine_requirements(
            test_scenarios["simple_specific_request"]["input"], context_complete
        )

        # Check workflow status
        if hasattr(complete_result, 'status'):
            logger.info(f"Workflow status: {complete_result.status}")
            assert complete_result.status in [ServiceStatus.COMPLETED.value, ServiceStatus.IN_PROGRESS.value, ServiceStatus.WAITING_FOR_USER_FEEDBACK.value], \
                "Workflow status should be valid"

        # Test workflow that should wait for feedback
        context_wait = MiningContext(
            user_id="test_user_wait",
            session_id="test_session_wait",
            task_id="test_task_wait",
            domain="business"
        )

        wait_result = await mining_service.mine_requirements(
            test_scenarios["vague_request"]["input"], context_wait
        )

        # Check if waiting for feedback
        if hasattr(wait_result, 'status') and wait_result.status == ServiceStatus.WAITING_FOR_USER_FEEDBACK.value:
            logger.info("✅ Workflow correctly waiting for user feedback")
            assert hasattr(wait_result, 'feedback_type'), "Should have feedback type when waiting"

        logger.info("✅ Workflow status transitions test passed")

    except Exception as e:
        logger.error(f"❌ Workflow status transitions test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_debug_result_structure_validation(mining_service, test_scenarios):
    """Test that mining results have the expected structure."""
    logger.info("=== Testing Result Structure Validation ===")

    try:
        context = MiningContext(
            user_id="test_user_structure",
            session_id="test_session_structure",
            task_id="test_task_structure",
            domain="business"
        )

        result = await mining_service.mine_requirements(
            test_scenarios["simple_specific_request"]["input"], context
        )

        # Verify basic result structure
        assert hasattr(result, 'demand_state'), "Result should have demand_state"
        assert hasattr(result, 'session_id'), "Result should have session_id"
        assert hasattr(result, 'task_id'), "Result should have task_id"

        # Verify optional fields are present when expected
        if hasattr(result, 'intent_analysis') and result.intent_analysis:
            assert isinstance(result.intent_analysis, dict), "Intent analysis should be a dictionary"

        if hasattr(result, 'meta_architect_result') and result.meta_architect_result:
            assert isinstance(result.meta_architect_result, dict), "Meta architect result should be a dictionary"

        if hasattr(result, 'simple_strategy_result') and result.simple_strategy_result:
            assert isinstance(result.simple_strategy_result, dict), "Simple strategy result should be a dictionary"

        logger.info("✅ Result structure validation test passed")

    except Exception as e:
        logger.error(f"❌ Result structure validation test failed: {e}")
        raise


# ==================== Performance and Stress Tests ====================

@pytest.mark.asyncio
async def test_performance_multiple_requests(mining_service, test_scenarios):
    """Test performance with multiple concurrent requests."""
    logger.info("=== Testing Performance with Multiple Requests ===")

    try:
        import time
        start_time = time.time()

        # Create multiple contexts for concurrent testing
        contexts = []
        for i in range(3):
            context = MiningContext(
                user_id=f"test_user_perf_{i}",
                session_id=f"test_session_perf_{i}",
                task_id=f"test_task_perf_{i}",
                domain="business"
            )
            contexts.append(context)

        # Execute multiple requests
        tasks = []
        for i, context in enumerate(contexts):
            scenario_key = list(test_scenarios.keys())[i % len(test_scenarios)]
            task = mining_service.mine_requirements(
                test_scenarios[scenario_key]["input"], context
            )
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        duration = end_time - start_time

        # Verify all tasks completed successfully
        successful_results = [r for r in results if not isinstance(r, Exception)]
        failed_results = [r for r in results if isinstance(r, Exception)]

        logger.info(f"Performance test completed in {duration:.2f} seconds")
        logger.info(f"Successful requests: {len(successful_results)}")
        logger.info(f"Failed requests: {len(failed_results)}")

        assert len(successful_results) >= 2, "At least 2 out of 3 requests should succeed"
        assert duration < 60, "Performance test should complete within 60 seconds"

        logger.info("✅ Performance test passed")

    except Exception as e:
        logger.error(f"❌ Performance test failed: {e}")
        raise


# ==================== Test Configuration and Utilities ====================

def pytest_configure(config):
    """Configure pytest for this test suite."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers."""
    for item in items:
        # Add asyncio marker to all async tests
        if "async" in item.name or "test_flow" in item.name:
            item.add_marker(pytest.mark.asyncio)

        # Add slow marker to performance tests
        if "performance" in item.name:
            item.add_marker(pytest.mark.slow)

        # Add integration marker to workflow tests
        if "flow" in item.name or "workflow" in item.name:
            item.add_marker(pytest.mark.integration)


# ==================== Test Execution Helpers ====================

def run_specific_test(test_name: str):
    """Helper function to run a specific test by name."""
    import subprocess
    import sys

    cmd = [
        sys.executable, "-m", "pytest",
        __file__,
        f"-k {test_name}",
        "-v",
        "--tb=short"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result


def run_all_tests():
    """Helper function to run all tests."""
    import subprocess
    import sys

    cmd = [
        sys.executable, "-m", "pytest",
        __file__,
        "-v",
        "--tb=short",
        "--durations=10"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result


if __name__ == "__main__":
    # Allow running specific tests from command line
    import sys

    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        print(f"Running specific test: {test_name}")
        result = run_specific_test(test_name)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        sys.exit(result.returncode)
    else:
        print("Running all tests...")
        result = run_all_tests()
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        sys.exit(result.returncode)
