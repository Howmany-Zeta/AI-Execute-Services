"""
Interacter Service

This service handles all user interactions and validates whether user requests
contain substantial requirements that warrant multi-task processing. It serves
as the entry point for user communication and determines if requests should
proceed to intent parsing or be redirected to general mode.

Key responsibilities:
1. Validate user input for substantial requirements
2. Filter out non-business, subjective, or inappropriate requests
3. Provide guidance for users with invalid requests
4. Interface with frontend chatbot for seamless user experience
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple

from ...core.models.services_models import RequestType, InteractionResult
from ...core.exceptions.services_exceptions import InteractionError
from app.services.llm_integration import LLMIntegrationManager, generate_with_context
from app.llm import LLMMessage, AIProvider

logger = logging.getLogger(__name__)


class InteracterService:
    """
    Service for handling user interactions and validating request substance.

    This service acts as the gatekeeper for the multi-task system, ensuring
    only appropriate requests proceed to intent parsing and execution.
    """

    def __init__(self, llm_manager: Optional[LLMIntegrationManager] = None):
        """
        Initialize the interacter service.

        Args:
            llm_manager: Optional LLM integration manager for AI-powered validation
        """
        self.llm_manager = llm_manager
        self.logger = logging.getLogger(__name__)
        self.memory = {}  # Simple memory storage for analysis results

        # SMART criteria demand states
        self.demand_states = {
            "SMART_COMPLIANT": "The user query is clearly expressed, in line with the SMART principle, and the intention is specific, measurable, achievable, relevant, and time-bound.",
            "SMART_LARGE_SCOPE": "The user query is clearly expressed and meet the SMART principle, but they are too large. The intention is clear, but the scope is wide, the time span is long, and multiple rounds of analysis and cross-domain data are required.",
            "VAGUE_UNCLEAR": "The user query is vague and does not conform to the SMART principle. The surface intention is vague and the real demand is hidden. It is necessary to dig deeper into the intention."
        }

        # Validation criteria patterns
        self._business_keywords = [
            "market", "business", "company", "industry", "revenue", "profit", "strategy",
            "analysis", "research", "data", "report", "study", "survey", "trends",
            "competition", "customer", "product", "service", "growth", "investment"
        ]

        self._research_keywords = [
            "research", "study", "analyze", "investigate", "examine", "explore",
            "compare", "evaluate", "assess", "review", "survey", "statistics",
            "data", "findings", "methodology", "hypothesis", "evidence"
        ]

        self._inappropriate_patterns = [
            r"\b(how to commit|illegal|crime|fraud|hack|steal)\b",
            r"\b(gambling|bet|casino|lottery)\b",
            r"\b(personal health|medical advice|diagnosis|treatment)\b",
            r"\b(relationship advice|dating|love|marriage)\b",
            r"\b(what are you|who are you|your capabilities|startudiscovery)\b"
        ]

        self._subjective_patterns = [
            r"\b(feel|feeling|emotion|personal opinion|what do you think)\b",
            r"\b(best|worst|favorite|prefer|like|dislike)\b",
            r"\b(should I|what should|personal decision)\b"
        ]

    async def validate_user_request(self, user_input: str, context: Dict[str, Any] = None) -> InteractionResult:
        """
        Validate if user request contains substantial requirements for multi-task processing.

        Args:
            user_input: Raw user input text
            context: Optional context information

        Returns:
            InteractionResult with validation outcome and guidance
        """
        try:
            self.logger.debug(f"Validating user request: {user_input[:100]}...")

            # Basic input validation
            if not user_input or len(user_input.strip()) < 10:
                return InteractionResult(
                    request_type=RequestType.NON_SUBSTANTIAL,
                    is_valid=False,
                    confidence=0.9,
                    reasoning="Input too short or empty",
                    guidance_message="Please provide a more detailed request with specific requirements.",
                    should_proceed=False
                )

            # Check for inappropriate content
            inappropriate_result = self._check_inappropriate_content(user_input)
            if inappropriate_result:
                return inappropriate_result

            # Check for subjective/personal questions
            subjective_result = self._check_subjective_content(user_input)
            if subjective_result:
                return subjective_result

            # Check for system inquiry
            system_inquiry_result = self._check_system_inquiry(user_input)
            if system_inquiry_result:
                return system_inquiry_result

            # Perform substantial requirement validation
            substantial_result = await self._validate_substantial_requirements(user_input, context)

            return substantial_result

        except Exception as e:
            self.logger.error(f"Error validating user request: {e}")
            return InteractionResult(
                request_type=RequestType.NON_SUBSTANTIAL,
                is_valid=False,
                confidence=0.5,
                reasoning=f"Validation error: {str(e)}",
                guidance_message="Unable to process request. Please try rephrasing your question.",
                should_proceed=False
            )

    async def provide_guidance(self, result: InteractionResult, user_input: str) -> str:
        """
        Provide user guidance based on validation result.

        Args:
            result: Validation result
            user_input: Original user input

        Returns:
            Guidance message for the user
        """
        if result.guidance_message:
            return result.guidance_message

        if result.request_type == RequestType.SUBSTANTIAL and result.should_proceed:
            return "Your request has been accepted for processing. Please wait while I analyze your requirements."

        # Generate contextual guidance based on request type
        guidance_templates = {
            RequestType.NON_SUBSTANTIAL: self._generate_substantial_guidance(),
            RequestType.INAPPROPRIATE: self._generate_appropriate_guidance(),
            RequestType.REDIRECT_GENERAL: self._generate_redirect_guidance()
        }

        return guidance_templates.get(result.request_type, "Please refine your request and try again.")

    def _check_inappropriate_content(self, user_input: str) -> Optional[InteractionResult]:
        """Check for inappropriate content patterns."""
        user_lower = user_input.lower()

        for pattern in self._inappropriate_patterns:
            if re.search(pattern, user_lower, re.IGNORECASE):
                return InteractionResult(
                    request_type=RequestType.INAPPROPRIATE,
                    is_valid=False,
                    confidence=0.8,
                    reasoning=f"Contains inappropriate content: {pattern}",
                    guidance_message="I cannot assist with requests involving illegal activities, gambling, personal health advice, or personal relationship matters. Please ask about business, research, or objective topics.",
                    should_proceed=False
                )

        return None

    def _check_subjective_content(self, user_input: str) -> Optional[InteractionResult]:
        """Check for subjective or personal questions."""
        user_lower = user_input.lower()

        for pattern in self._subjective_patterns:
            if re.search(pattern, user_lower, re.IGNORECASE):
                return InteractionResult(
                    request_type=RequestType.REDIRECT_GENERAL,
                    is_valid=False,
                    confidence=0.7,
                    reasoning=f"Contains subjective content: {pattern}",
                    guidance_message="Your question appears to be subjective or personal in nature. For such questions, you may want to try the general Q&A mode for more suitable assistance.",
                    should_proceed=False
                )

        return None

    def _check_system_inquiry(self, user_input: str) -> Optional[InteractionResult]:
        """Check for system capability or identity inquiries."""
        user_lower = user_input.lower()

        system_patterns = [
            r"\b(what are you|who are you|your capabilities|what can you do)\b",
            r"\b(startudiscovery|this system|this program|this ai)\b",
            r"\b(how do you work|explain yourself|your features)\b"
        ]

        for pattern in system_patterns:
            if re.search(pattern, user_lower, re.IGNORECASE):
                return InteractionResult(
                    request_type=RequestType.REDIRECT_GENERAL,
                    is_valid=False,
                    confidence=0.9,
                    reasoning=f"System inquiry detected: {pattern}",
                    guidance_message="Questions about the system capabilities or identity should be directed to the general Q&A mode. This multi-task mode is designed for business and research requests that require data collection, analysis, or content generation.",
                    should_proceed=False
                )

        return None

    async def _validate_substantial_requirements(self, user_input: str, context: Dict[str, Any] = None) -> InteractionResult:
        """
        Validate if the request contains substantial requirements using multiple criteria.

        Args:
            user_input: User input text
            context: Optional context

        Returns:
            InteractionResult with validation outcome
        """
        # Criteria for substantial requirements
        criteria_met = 0
        total_criteria = 6
        reasoning_parts = []

        # 1. Business purpose criterion
        business_score = self._check_business_purpose(user_input)
        if business_score > 0.5:
            criteria_met += 1
            reasoning_parts.append(f"Business purpose detected (score: {business_score:.2f})")

        # 2. Research nature criterion
        research_score = self._check_research_nature(user_input)
        if research_score > 0.5:
            criteria_met += 1
            reasoning_parts.append(f"Research nature detected (score: {research_score:.2f})")

        # 3. Objective nature criterion (non-subjective)
        if not self._is_subjective_question(user_input):
            criteria_met += 1
            reasoning_parts.append("Objective nature confirmed")

        # 4. Non-system inquiry criterion
        if not self._is_system_inquiry(user_input):
            criteria_met += 1
            reasoning_parts.append("Non-system inquiry confirmed")

        # 5. Appropriate content criterion
        if not self._contains_inappropriate_content(user_input):
            criteria_met += 1
            reasoning_parts.append("Appropriate content confirmed")

        # 6. Non-interactive system request criterion
        if not self._is_interactive_system_request(user_input):
            criteria_met += 1
            reasoning_parts.append("Non-interactive system request confirmed")

        # Determine if substantial (need at least 2 criteria)
        is_substantial = criteria_met >= 2
        confidence = criteria_met / total_criteria

        if is_substantial:
            return InteractionResult(
                request_type=RequestType.SUBSTANTIAL,
                is_valid=True,
                confidence=confidence,
                reasoning=f"Substantial requirements met ({criteria_met}/{total_criteria}): " + "; ".join(reasoning_parts),
                should_proceed=True
            )
        else:
            return InteractionResult(
                request_type=RequestType.NON_SUBSTANTIAL,
                is_valid=False,
                confidence=confidence,
                reasoning=f"Insufficient substantial requirements ({criteria_met}/{total_criteria}): " + "; ".join(reasoning_parts),
                guidance_message=self._generate_substantial_guidance(),
                should_proceed=False
            )

    def _check_business_purpose(self, user_input: str) -> float:
        """Check for business-related purpose."""
        user_lower = user_input.lower()
        matches = sum(1 for keyword in self._business_keywords if keyword in user_lower)
        return min(matches / 3, 1.0)  # Normalize to 0-1 scale

    def _check_research_nature(self, user_input: str) -> float:
        """Check for research-related nature."""
        user_lower = user_input.lower()
        matches = sum(1 for keyword in self._research_keywords if keyword in user_lower)
        return min(matches / 3, 1.0)  # Normalize to 0-1 scale

    def _is_subjective_question(self, user_input: str) -> bool:
        """Check if question is subjective."""
        user_lower = user_input.lower()
        return any(re.search(pattern, user_lower, re.IGNORECASE) for pattern in self._subjective_patterns)

    def _is_system_inquiry(self, user_input: str) -> bool:
        """Check if request is about system capabilities."""
        user_lower = user_input.lower()
        system_patterns = [
            r"\b(what are you|who are you|your capabilities)\b",
            r"\b(startudiscovery|this system|this ai)\b"
        ]
        return any(re.search(pattern, user_lower, re.IGNORECASE) for pattern in system_patterns)

    def _contains_inappropriate_content(self, user_input: str) -> bool:
        """Check if content is inappropriate."""
        user_lower = user_input.lower()
        return any(re.search(pattern, user_lower, re.IGNORECASE) for pattern in self._inappropriate_patterns)

    def _is_interactive_system_request(self, user_input: str) -> bool:
        """Check for requests that require interaction with external systems."""
        user_lower = user_input.lower()
        interactive_patterns = [
            r"\b(send email|post comment|make purchase|book|order|buy)\b",
            r"\b(create account|login|register|subscribe)\b",
            r"\b(publish|upload|download|install)\b"
        ]
        return any(re.search(pattern, user_lower, re.IGNORECASE) for pattern in interactive_patterns)

    def _generate_substantial_guidance(self) -> str:
        """Generate guidance for non-substantial requests."""
        return """Your request doesn't appear to contain substantial business or research requirements that multi-task mode is designed to handle.

Multi-task mode is best suited for:
• Business analysis and market research
• Data collection and processing tasks
• Objective research and investigation
• Content generation for business purposes
• Complex analytical workflows

For general questions or personal inquiries, please consider using the general Q&A mode."""

    def _generate_appropriate_guidance(self) -> str:
        """Generate guidance for inappropriate requests."""
        return """I cannot assist with requests involving:
• Illegal activities or criminal behavior
• Gambling or betting advice
• Personal health or medical advice
• Personal relationship or emotional counseling
• Harmful or dangerous activities

Please ask about business, research, or other objective topics that I can help you with."""

    def _generate_redirect_guidance(self) -> str:
        """Generate guidance for requests that should be redirected."""
        return """Your question would be better suited for the general Q&A mode, which is designed for:
• General knowledge questions
• Personal advice and opinions
• System capability inquiries
• Subjective discussions

Multi-task mode is specifically designed for business and research workflows that require data collection, analysis, and content generation."""

    async def get_interaction_statistics(self) -> Dict[str, Any]:
        """Get statistics about user interactions."""
        # This would typically be implemented with persistent storage
        return {
            "total_interactions": 0,
            "substantial_requests": 0,
            "redirected_requests": 0,
            "inappropriate_requests": 0,
            "success_rate": 0.0
        }

    def validate_input_format(self, input_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate the format of input data.

        Args:
            input_data: Input data to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(input_data, dict):
            return False, "Input must be a dictionary"

        if "text" not in input_data:
            return False, "Input must contain 'text' field"

        if not isinstance(input_data["text"], str):
            return False, "Text field must be a string"

        if len(input_data["text"].strip()) == 0:
            return False, "Text field cannot be empty"

        return True, ""

    def _extract_json_from_llm_output(self, llm_output: str) -> str:
        """
        From the LLM's raw output, extract a clean JSON string.
        Can handle cases with markdown code blocks (```json ... ```).
        """
        if not isinstance(llm_output, str):
            return ""

        # Use regex to find JSON content wrapped in ```json ... ``` or ```
        # re.DOTLALL allows '.' to match newlines, enabling multi-line JSON extraction
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", llm_output, re.DOTALL)

        if match:
            # If a match is found, return the first capturing group (the clean JSON)
            return match.group(1).strip()
        else:
            # IF no markdown block is found, assume the entire string is JSON
            return llm_output.strip()

    async def analyze_demand_state(self, user_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze user demand state according to SMART criteria.

        Args:
            user_text: User input text to analyze
            context: Execution context

        Returns:
            Demand state analysis result
        """
        try:
            # Prepare SMART criteria analysis prompt
            smart_analysis_prompt = f"""TASK TYPE: analyze_demand_state

            User Text: {user_text}

            Analyze the user's request according to SMART criteria (Specific, Measurable, Achievable, Relevant, Time-bound) and classify into one of these demand states:

            1. SMART_COMPLIANT: Clear requirements that meet SMART principles - specific, measurable, achievable, relevant, and time-bound
            Examples: "What new physics discoveries were made last week", "Analyze Apple's Q3 2024 financial report"

            2. SMART_LARGE_SCOPE: Clear requirements that meet SMART principles but are too large in scope - clear intent but broad range, long time span, requiring multi-round analysis and cross-domain data
            Examples: "Analyze Tesla's 5-year development", "Research AI's impact on global economy"

            3. VAGUE_UNCLEAR: Vague requirements that don't meet SMART principles - unclear surface intent, hidden real needs requiring deep intent mining
            Examples: "XXX brand sales decline reasons", "Give me a sales plan", "Help me analyze the market"

            Provide response in JSON format:
            {{
                "demand_state": "SMART_COMPLIANT|SMART_LARGE_SCOPE|VAGUE_UNCLEAR",
                "smart_analysis": {{
                    "specific": true/false,
                    "measurable": true/false,
                    "achievable": true/false,
                    "relevant": true/false,
                    "time_bound": true/false
                }},
                "confidence": 0.0-1.0,
                "reasoning": "Detailed explanation of the classification",
                "clarification_needed": ["List of questions to clarify unclear aspects"],
                "scope_assessment": {{
                    "complexity": "low|medium|high",
                    "time_span": "short|medium|long",
                    "domain_breadth": "narrow|medium|broad"
                }}
            }}"""

            # Execute the SMART analysis task using LLM manager directly
            if self.llm_manager:
                response = await self.llm_manager.generate_with_context(
                    smart_analysis_prompt,
                    context
                )
                actual_output = response.content
            else:
                raise ValueError("LLM manager not available for demand state analysis")

            # DEBUG: Log the raw LLM output for debugging
            logger.debug(f"DEBUG_INTERACTER: Raw LLM output: {actual_output}")
            logger.debug(f"DEBUG_INTERACTER: Raw LLM output type: {type(actual_output)}")

            # Clean LLM output to extract pure JSON
            cleaned_json_string = self._extract_json_from_llm_output(actual_output)

            # Parse the result
            if cleaned_json_string:  # Ensure cleaned string is not empty
                try:
                    # Use cleaned string for parsing
                    analysis_result = json.loads(cleaned_json_string)
                    logger.debug(f"DEBUG_INTERACTER: Successfully parsed JSON: {analysis_result}")

                    # makesure demand_state is always present
                    if 'demand_state' not in analysis_result:
                        logger.warning("DEBUG_INTERACTER: demand_state field missing from parsed JSON")
                        analysis_result['demand_state'] = "SMART_LARGE_SCOPE"  # Default fallback value

                except json.JSONDecodeError as e:
                    logger.error(f"DEBUG_INTERACTER: JSON decode error: {e}")
                    # Fallback: create structured result
                    analysis_result = self._create_fallback_smart_analysis(user_text, f"JSON decode error: {e}")
            else:
                logger.warning("DEBUG_INTERACTER: Empty cleaned JSON string")
                analysis_result = self._create_fallback_smart_analysis(user_text, "LLM returned empty output")

            # Finalize analysis result
            if analysis_result.get('demand_state') is None:
                logger.error("DEBUG_INTERACTER: CRITICAL - demand_state is None after parsing!")
                analysis_result['demand_state'] = "SMART_LARGE_SCOPE"  # Default fallback value

            # Store in memory for future reference
            self.add_memory('last_smart_analysis', {
                'user_text': user_text,
                'analysis_result': analysis_result,
                'timestamp': context.get('timestamp')
            })

            return analysis_result

        except Exception as e:
            logger.error(f"SMART criteria analysis failed: {e}")
            # Return fallback analysis
            return self._create_fallback_smart_analysis(user_text, str(e))

    def _create_fallback_smart_analysis(self, user_text: str, error_info: str) -> Dict[str, Any]:
        """
        Create fallback SMART analysis when parsing fails.
        makesure we all have a valid demand_state

        Args:
            user_text: Original user text
            error_info: Error information or unparsed output

        Returns:
            Fallback SMART analysis result
        """
        # Simple heuristic-based classification
        text_lower = user_text.lower()

        # Check for time indicators, more comprehensive time indicators
        time_indicators = [
            "today", "yesterday", "last week", "this month", "2024", "2025", "recent", "lately",
            "q1", "q2", "q3", "q4", "quarter", "quarterly", "annual", "year", "month", "week",
            "今天", "昨天", "上周", "本月", "最近", "近期", "季度", "年度"
        ]
        has_time = any(indicator in text_lower for indicator in time_indicators)

        # Check for specific indicators, more comprehensive specific indicators
        specific_indicators = [
            "analyze", "report", "data", "statistics", "compare", "evaluate", "performance",
            "financial", "revenue", "profit", "growth", "margin", "apple", "company",
            "分析", "报告", "数据", "统计", "比较", "评估", "业绩", "财务", "收入", "利润"
        ]
        has_specific = any(indicator in text_lower for indicator in specific_indicators)

        # Check for vague indicators, more comprehensive vague indicators
        vague_indicators = [
            "help me", "give me", "please help", "can you", "could you",
            "帮我", "给我", "请帮", "能否", "可以"
        ]
        has_vague = any(indicator in text_lower for indicator in vague_indicators)

        # More comprehensive word count for better analysis
        word_count = len(user_text.split())

        # Make sure we have a valid demand_state
        # Prioritize based on the presence of indicators and word count
        if has_vague:
            demand_state = "VAGUE_UNCLEAR"
            confidence = 0.7
        elif word_count < 4:
            demand_state = "VAGUE_UNCLEAR"
            confidence = 0.6
        elif has_specific and has_time:
            # Have both specific indicators and time indicators
            if word_count <= 25:
                demand_state = "SMART_COMPLIANT"
                confidence = 0.8
            else:
                demand_state = "SMART_LARGE_SCOPE"
                confidence = 0.7
        elif has_specific:
            # Have specific indicators but no time
            demand_state = "SMART_COMPLIANT"
            confidence = 0.6
        else:
            # Default case - ensure there's a value
            demand_state = "SMART_LARGE_SCOPE"
            confidence = 0.5

        logger.info(f"Fallback analysis: demand_state={demand_state}, confidence={confidence}")

        return {
            "demand_state": demand_state,
            "smart_analysis": {
                "specific": has_specific,
                "measurable": has_specific,
                "achievable": True,
                "relevant": True,
                "time_bound": has_time
            },
            "confidence": confidence,
            "reasoning": f"Fallback analysis based on text patterns. Original error: {error_info}",
            "clarification_needed": ["Please provide more specific requirements"] if demand_state == "VAGUE_UNCLEAR" else [],
            "scope_assessment": {
                "complexity": "high" if word_count > 20 else "medium" if word_count > 10 else "low",
                "time_span": "long" if "year" in text_lower else "medium",
                "domain_breadth": "broad" if word_count > 15 else "narrow"
            }
        }

    def add_memory(self, key: str, value: Any) -> None:
        """
        Store information in memory for future reference.

        Args:
            key: Memory key
            value: Value to store
        """
        self.memory[key] = value
        self.logger.debug(f"Stored memory: {key}")

    def get_memory(self, key: str, default: Any = None) -> Any:
        """
        Retrieve information from memory.

        Args:
            key: Memory key
            default: Default value if key not found

        Returns:
            Stored value or default
        """
        return self.memory.get(key, default)

    def clear_memory(self, key: Optional[str] = None) -> None:
        """
        Clear memory entries.

        Args:
            key: Specific key to clear, or None to clear all
        """
        if key:
            self.memory.pop(key, None)
            self.logger.debug(f"Cleared memory: {key}")
        else:
            self.memory.clear()
            self.logger.debug("Cleared all memory")
