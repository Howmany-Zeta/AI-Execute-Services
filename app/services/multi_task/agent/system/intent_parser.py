"""
Intent Parser Agent

Specialized agent for parsing user input and identifying intent categories.
Refactored to use LangChain framework and TaskFactory for complete configuration-driven behavior.
"""

import json
import logging
import re
from typing import Dict, List, Any

# LangChain dependencies
from langchain.agents import AgentExecutor
from langchain.tools import BaseTool
from langchain.schema import AgentAction, AgentFinish

# Import our system's core components
from ..base_agent import BaseAgent
from ...core.models.agent_models import AgentConfig
from app.services.llm_integration import LLMIntegrationManager
from ...config.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class IntentParserAgent(BaseAgent):
    """
    Agent specialized in parsing user intent and categorizing requests.

    Refactored to use LangChain framework and TaskFactory for complete configuration-driven behavior.
    Its task definition is provided by TaskFactory, and its LLM is dynamically
    configured by LLMIntegrationManager through the LangChain adapter.
    """

    def __init__(self, config: AgentConfig, config_manager: ConfigManager, llm_manager: LLMIntegrationManager, tool_integration_manager=None):
        """
        Initialize the intent parser agent.

        Args:
            config: Agent's basic configuration (such as agent_id, role)
            config_manager: Configuration manager for reading prompts.yaml and llm_bindings.yaml
            llm_manager: LLM integration manager for actual LLM calls
            tool_integration_manager: Optional tool integration manager for LangChain tools
        """
        # Call parent's initialization method, which handles role definition and LLM binding loading
        super().__init__(config, config_manager, llm_manager, tool_integration_manager)

        self.supported_categories = [
            "answer", "collect", "process", "analyze", "generate"
        ]

        # LangChain agent executor instance
        self._agent_executor: AgentExecutor = None

    async def initialize(self) -> None:
        """Initialize the intent parser agent."""
        logger.info(f"Intent parser agent initialized: {self.agent_id}")

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


    async def execute_task(self, task_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute intent parsing task using LangChain-based approach.
        """
        try:
            self.set_busy(context.get('task_id', 'unknown'))

            user_text = task_data.get("text", "")
            if not user_text:
                raise ValueError("No user text provided for intent parsing")

            # Create LangChain agent executor for this task
            agent_executor = await self.create_langchain_agent(context)

            # Prepare intent parsing input
            parsing_input = {
                "input": user_text,  # use real user text directly
                "task_description": f"""
                User Text: {user_text}

                Analyze the user's request and provide comprehensive intent parsing. You can choose to output in either JSON format or structured Markdown format.

                **Your Task:**
                1. Provide a complete, coherent, and logically compact analysis of the user's request/query
                2. Break down the request into detailed steps with clear categorization
                3. Map each step to the most appropriate category (answer, collect, process, analyze, generate)
                4. Decompose each step into atomic, independent subtasks that can be executed sequentially
                5. Ensure each step is clean and independent - if a step contains multiple sub-steps, continue iterative decomposition until each step is atomic
                6. Identify the primary intent that best represents the overall purpose

                **Category Definitions:**
                - answer: Questions requiring direct answers or explanations
                - collect: Requests to gather, find, or search for information/data
                - process: Requests to transform, clean, format, or convert data
                - analyze: Requests to examine, study, or provide insights
                - generate: Requests to create, write, produce, or build content

                **Option 1 - JSON Format (Preferred):**
                {{
                  "overall_intent": "A complete, coherent analysis of the user's request/query.",
                  "task_categories_identified": ["category1", "category2", "category3"],
                  "step_by_step_breakdown": [
                    {{
                      "step_name": "Step 1: Collect Financial Data",
                      "task_category": "collect",
                      "discription": "Gather all relevant financial documents and data for the specified company and time period",
                      "subtask_breakdown": [
                        "Retrieve official earnings press release",
                        "Access Form 10-Q report filed with SEC",
                        "Obtain quarterly earnings conference call transcript"
                      ]
                    }},
                    {{
                      "step_name": "Step 2: Process and Structure Data",
                      "task_category": "process",
                      "discription": "Extract, clean, and organize the collected data into a structured format suitable for analysis",
                      "subtask_breakdown": [
                        "Extract key financial figures",
                        "Tabulate revenue by product category",
                        "Organize historical data for comparative analysis"
                      ]
                    }}
                  ],
                  "primary_intent": "analyze"
                }}

                **Option 2 - Structured Markdown Format (Also Acceptable):**
                ## Overall Intent
                [Provide a complete, coherent analysis of the user's request]

                ## Task Categories Identified
                * `collect`
                * `process`
                * `analyze`
                * `generate`

                ## Step-by-Step Breakdown

                **Step 1: Collect Financial Data**
                * **Task Category:** `collect`
                * **Discription:** Gather all relevant financial documents and data
                * **subtask_breakdown:**
                  * Retrieve official earnings press release
                  * Access Form 10-Q report filed with SEC
                  * Obtain quarterly earnings conference call transcript

                Choose the format that works best for your analysis. Both will be properly processed.
                """,
                "expected_output": "A raw JSON object string with analysis_summary containing query_description, reasoning, sub_steps_identified, and primary_intent - NO MARKDOWN, NO EXTRA TEXT",
                "input_data": task_data
            }

            # Execute the intent parsing task using LangChain agent
            result = await agent_executor.ainvoke(parsing_input)

            # Extract the actual output from LangChain result
            actual_output = result.get('output', str(result))

            # DEBUG: Log the raw LLM output for debugging
            logger.debug(f"DEBUG_INTENT_PARSER: Raw LLM output: {actual_output}")
            logger.debug(f"DEBUG_INTENT_PARSER: Raw LLM output type: {type(actual_output)}")

            # Extract reasoning from LangChain's intermediate steps (Thought process)
            reasoning = ""
            if isinstance(result, dict):
                # Try to extract reasoning from LangChain's intermediate steps
                intermediate_steps = result.get('intermediate_steps', [])
                if intermediate_steps:
                    # Extract thoughts from intermediate steps
                    thoughts = []
                    for step in intermediate_steps:
                        if hasattr(step, 'log') and 'Thought:' in step.log:
                            # Extract the thought part from the log
                            thought_match = re.search(r'Thought:\s*(.*?)(?=\nAction:|$)', step.log, re.DOTALL)
                            if thought_match:
                                thoughts.append(thought_match.group(1).strip())
                    reasoning = ' '.join(thoughts) if thoughts else ""

                # Fallback: try other possible reasoning fields
                if not reasoning:
                    reasoning = result.get('reasoning', '') or result.get('thought', '')

            # Simple category extraction for basic functionality
            categories = self._extract_categories_from_text(actual_output)

            # Validate categories
            validated_categories = self._validate_categories(categories)

            # Build final result directly
            result = {
                'user_text': user_text,
                'reasoning': reasoning,
                'actual_output': actual_output,
                'categories': validated_categories,
                'timestamp': context.get('timestamp'),
                'confidence': self._calculate_confidence(user_text, validated_categories)
            }

            # Store in memory for future reference
            self.add_memory('last_parsed_intent', result)

            self.set_available()

            return result

        except Exception as e:
            self.set_available()
            logger.error(f"Intent parsing failed: {e}")
            raise

    def get_capabilities(self) -> List[str]:
        """Get the capabilities of this agent."""
        return [
            "intent_parsing",
            "category_identification",
            "request_analysis",
            "task_categorization"
        ]

    def _extract_categories_from_text(self, text: str) -> List[str]:
        """
        Extract categories from text when JSON parsing fails.

        Args:
            text: Text to extract categories from LLM output

        Returns:
            List of extracted categories
        """

        categories = []
        text_lower = text.lower()

        for category in self.supported_categories:
            if category in text_lower:
                categories.append(category)

        # If no categories found, default to answer
        if not categories:
            categories = ["answer"]

        return categories

    def _validate_categories(self, categories) -> List[str]:
        """
        Validate and filter categories.

        Args:
            categories: Categories to validate (can be list, dict, or other)

        Returns:
            List of valid categories
        """
        # Handle different input types
        if isinstance(categories, dict):
            # If it's a dict, try to extract categories field
            categories = categories.get("categories", [])

        if not isinstance(categories, list):
            return ["answer"]  # Default fallback

        valid_categories = []
        for category in categories:
            if isinstance(category, str) and category.lower() in self.supported_categories:
                valid_categories.append(category.lower())

        # Ensure at least one category
        if not valid_categories:
            valid_categories = ["answer"]

        # Remove duplicates while preserving order
        seen = set()
        unique_categories = []
        for category in valid_categories:
            if category not in seen:
                seen.add(category)
                unique_categories.append(category)

        return unique_categories

    def _parse_structured_text_output(self, text_output: str, user_text: str) -> Dict[str, Any]:
        """
        Parse structured text output from LLM (both legacy and new Markdown formats) into our expected JSON structure.

        Args:
            text_output: The structured text output from LLM
            user_text: Original user input

        Returns:
            Dictionary with parsed analysis_summary and categories
        """
        try:
            # Initialize result structure
            result = {
                'categories': [],
                'analysis_summary': {
                    'query_description': '',
                    'reasoning': '',
                    'sub_steps_identified': [],
                    'primary_intent': ''
                }
            }

            # Try to parse new Markdown format first
            if "## Overall Intent" in text_output and "## Task Categories Identified" in text_output:
                # Parse new Markdown format

                # Extract Overall Intent
                overall_intent_match = re.search(r'## Overall Intent\s*(.*?)(?=##|$)', text_output, re.DOTALL)
                if overall_intent_match:
                    overall_intent = overall_intent_match.group(1).strip()
                    result['analysis_summary']['query_description'] = overall_intent
                    result['analysis_summary']['reasoning'] = overall_intent

                # Extract Task Categories
                categories_match = re.search(r'## Task Categories Identified\s*(.*?)(?=##|$)', text_output, re.DOTALL)
                if categories_match:
                    categories_text = categories_match.group(1)
                    # Extract categories from bullet points with backticks
                    category_matches = re.findall(r'\*\s*`(\w+)`', categories_text)
                    result['categories'] = [cat.lower() for cat in category_matches if cat.lower() in self.supported_categories]

                # Extract Step-by-Step Breakdown
                steps_match = re.search(r'## Step-by-Step Breakdown\s*(.*?)$', text_output, re.DOTALL)
                if steps_match:
                    steps_text = steps_match.group(1)

                    # Parse individual steps in new format
                    step_pattern = r'\*\*Step \d+: ([^*]+)\*\*\s*\*\s*\*\*Task Category:\*\*\s*`(\w+)`\s*\*\s*\*\*Description:\*\*\s*(.*?)(?=\*\*Actions:\*\*|\*\*Step|\Z)'
                    step_matches = re.findall(step_pattern, steps_text, re.DOTALL)

                    for step_match in step_matches:
                        step_name = step_match[0].strip()
                        step_category = step_match[1].strip().lower()
                        step_description = step_match[2].strip()

                        # Extract actions
                        actions_pattern = rf'\*\*Step \d+: {re.escape(step_name)}\*\*.*?\*\*Actions:\*\*\s*(.*?)(?=\*\*Step|\Z)'
                        actions_match = re.search(actions_pattern, steps_text, re.DOTALL)
                        actions = []
                        if actions_match:
                            actions_text = actions_match.group(1).strip()
                            # Extract bullet points
                            action_items = re.findall(r'\*\s*([^\n*]+)', actions_text)
                            actions = [action.strip() for action in action_items]

                        # Create step object
                        step_obj = {
                            'step_name': f"Step: {step_name}",
                            'description': step_description,
                            'categories': [step_category] if step_category in self.supported_categories else ['answer'],
                            'purpose': step_description,
                            'actions': actions
                        }

                        result['analysis_summary']['sub_steps_identified'].append(step_obj)

            else:
                # Parse legacy format (Overall Intent, Task Categories Identified, Step-by-Step Breakdown)

                # Extract Overall Intent
                overall_intent_match = re.search(r'\*\*Overall Intent:\*\*\s*(.*?)(?=\n\n|\*\*|$)', text_output, re.DOTALL)
                if overall_intent_match:
                    result['analysis_summary']['query_description'] = overall_intent_match.group(1).strip()
                    result['analysis_summary']['reasoning'] = overall_intent_match.group(1).strip()

                # Extract Task Categories
                categories_section = re.search(r'\*\*Task Categories Identified:\*\*\s*(.*?)(?=\n\n|---|\*\*|$)', text_output, re.DOTALL)
                if categories_section:
                    categories_text = categories_section.group(1)
                    # Extract categories from bullet points
                    category_matches = re.findall(r'[*-]\s*`?(\w+)`?', categories_text)
                    result['categories'] = [cat.lower() for cat in category_matches if cat.lower() in self.supported_categories]

                # Extract Step-by-Step Breakdown
                steps_section = re.search(r'### Step-by-Step Breakdown\s*(.*?)$', text_output, re.DOTALL)
                if steps_section:
                    steps_text = steps_section.group(1)

                    # Parse individual steps
                    step_pattern = r'\*\*Step \d+: ([^*]+)\*\*\s*\*\s*\*\*Task Category:\*\*\s*`(\w+)`\s*\*\s*\*\*Description:\*\*\s*(.*?)(?=\*\*Actions:\*\*|\*\*Step|\Z)'
                    step_matches = re.findall(step_pattern, steps_text, re.DOTALL)

                    for step_match in step_matches:
                        step_name = step_match[0].strip()
                        step_category = step_match[1].strip().lower()
                        step_description = step_match[2].strip()

                        # Extract actions if present
                        actions_pattern = rf'\*\*Step \d+: {re.escape(step_name)}\*\*.*?\*\*Actions:\*\*\s*(.*?)(?=\*\*Step|\Z)'
                        actions_match = re.search(actions_pattern, steps_text, re.DOTALL)
                        actions = []
                        if actions_match:
                            actions_text = actions_match.group(1).strip()
                            # Extract bullet points
                            action_items = re.findall(r'[*-]\s*([^\n*]+)', actions_text)
                            actions = [action.strip() for action in action_items]

                        # Create step object
                        step_obj = {
                            'step_name': f"Step: {step_name}",
                            'description': step_description,
                            'categories': [step_category] if step_category in self.supported_categories else ['answer'],
                            'purpose': step_description,
                            'actions': actions
                        }

                        result['analysis_summary']['sub_steps_identified'].append(step_obj)

            # Determine primary intent
            if result['categories']:
                # Use the first category as primary intent, or 'analyze' if multiple categories
                result['analysis_summary']['primary_intent'] = result['categories'][0] if len(result['categories']) == 1 else 'analyze'
            else:
                result['analysis_summary']['primary_intent'] = 'answer'
                result['categories'] = ['answer']

            # Ensure we have categories
            if not result['categories']:
                result['categories'] = self._extract_categories_from_text(text_output)

            return result

        except Exception as e:
            logger.warning(f"Failed to parse structured text output: {e}")
            # Fallback to simple category extraction
            return {
                'categories': self._extract_categories_from_text(text_output),
                'analysis_summary': {
                    'query_description': f"Analysis of: {user_text}",
                    'reasoning': "Parsed from structured text output with fallback",
                    'sub_steps_identified': [],
                    'primary_intent': 'answer'
                }
            }

    def _calculate_confidence(self, user_text: str, categories: List[str]) -> float:
        """
        Calculate confidence score for the intent parsing.

        Args:
            user_text: Original user text
            categories: Identified categories

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Simple heuristic-based confidence calculation
        base_confidence = 0.7

        # Increase confidence for clear keywords
        keywords = {
            "answer": ["what", "how", "why", "when", "where", "who", "explain", "tell me"],
            "collect": ["gather", "collect", "find", "search", "scrape", "get data"],
            "process": ["process", "transform", "clean", "format", "convert"],
            "analyze": ["analyze", "examine", "study", "investigate", "insights"],
            "generate": ["create", "generate", "write", "produce", "make", "build"]
        }

        text_lower = user_text.lower()
        keyword_matches = 0
        total_keywords = 0

        for category in categories:
            if category in keywords:
                category_keywords = keywords[category]
                total_keywords += len(category_keywords)
                for keyword in category_keywords:
                    if keyword in text_lower:
                        keyword_matches += 1

        if total_keywords > 0:
            keyword_confidence = keyword_matches / total_keywords
            confidence = base_confidence + (keyword_confidence * 0.3)
        else:
            confidence = base_confidence

        return min(confidence, 1.0)

    def get_parsing_history(self) -> List[Dict[str, Any]]:
        """
        Get history of parsed intents.

        Returns:
            List of parsing history entries
        """
        history = []
        last_intent = self.get_memory('last_parsed_intent')
        if last_intent:
            history.append(last_intent)
        return history

    def analyze_intent_patterns(self) -> Dict[str, Any]:
        """
        Analyze patterns in parsed intents.

        Returns:
            Dictionary containing pattern analysis
        """
        # This could be expanded to analyze patterns across multiple requests
        last_intent = self.get_memory('last_parsed_intent')
        if not last_intent:
            return {"patterns": "No intent history available"}

        categories = last_intent.get('categories', [])
        return {
            "most_recent_categories": categories,
            "category_count": len(categories),
            "complexity": "high" if len(categories) > 2 else "medium" if len(categories) == 2 else "low"
        }

    async def parse_specialized_intent(self, intent_type: str, user_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse specialized intent based on specific intent type.

        Args:
            intent_type: Type of specialized intent parsing
            user_text: User text to parse
            context: Execution context

        Returns:
            Specialized intent parsing result
        """
        specialized_types = {
            "question_analysis": "Analyze question type and information needs",
            "task_decomposition": "Break down complex requests into subtasks",
            "domain_classification": "Classify request by domain or subject area",
            "urgency_assessment": "Assess urgency and priority level",
            "resource_requirements": "Identify required resources and capabilities"
        }

        if intent_type not in specialized_types:
            raise ValueError(f"Unsupported specialized intent type: {intent_type}")

        # Create specialized task data
        specialized_task_data = {
            "text": user_text,
            "intent_type": intent_type,
            "analysis_focus": specialized_types[intent_type]
        }

        return await self.execute_task(specialized_task_data, context)

    def classify_question_type(self, user_text: str) -> Dict[str, Any]:
        """
        Classify the type of question being asked.

        Args:
            user_text: User text to classify

        Returns:
            Question type classification
        """
        question_indicators = {
            "factual": ["what is", "define", "who is", "when did", "where is"],
            "procedural": ["how to", "how do", "steps to", "process of"],
            "causal": ["why", "because", "reason", "cause"],
            "comparative": ["compare", "difference", "versus", "better"],
            "analytical": ["analyze", "evaluate", "assess", "examine"],
            "creative": ["create", "design", "imagine", "brainstorm"]
        }

        text_lower = user_text.lower()
        question_types = []
        confidence_scores = {}

        for q_type, indicators in question_indicators.items():
            matches = sum(1 for indicator in indicators if indicator in text_lower)
            if matches > 0:
                question_types.append(q_type)
                confidence_scores[q_type] = min(matches / len(indicators), 1.0)

        # Default to factual if no specific type identified
        if not question_types:
            question_types = ["factual"]
            confidence_scores["factual"] = 0.5

        return {
            "question_types": question_types,
            "primary_type": max(confidence_scores.keys(), key=confidence_scores.get),
            "confidence_scores": confidence_scores,
            "is_question": any(indicator in text_lower for indicator in ["?", "what", "how", "why", "when", "where", "who"])
        }

    def extract_entities_and_keywords(self, user_text: str) -> Dict[str, Any]:
        """
        Extract entities and keywords from user text.

        Args:
            user_text: User text to analyze

        Returns:
            Extracted entities and keywords
        """
        # Simple keyword extraction (could be enhanced with NLP libraries)
        words = user_text.lower().split()

        # Filter out common stop words
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "is", "are", "was", "were", "be", "been", "have",
            "has", "had", "do", "does", "did", "will", "would", "could", "should"
        }

        keywords = [word.strip(".,!?;:") for word in words if word not in stop_words and len(word) > 2]

        # Identify potential entities (simple heuristics)
        entities = {
            "numbers": [word for word in words if word.isdigit()],
            "capitalized": [word for word in user_text.split() if word[0].isupper() and len(word) > 1],
            "technical_terms": [word for word in keywords if len(word) > 6],
            "action_words": [word for word in keywords if word.endswith(("ing", "ed", "er", "ly"))]
        }

        return {
            "keywords": keywords[:10],  # Top 10 keywords
            "entities": entities,
            "word_count": len(words),
            "unique_words": len(set(words)),
            "complexity_score": len(set(words)) / len(words) if words else 0
        }

    def assess_request_complexity(self, user_text: str, categories: List[str]) -> Dict[str, Any]:
        """
        Assess the complexity of the user request.

        Args:
            user_text: User text to assess
            categories: Identified categories

        Returns:
            Complexity assessment
        """
        complexity_factors = {
            "category_count": len(categories),
            "text_length": len(user_text),
            "word_count": len(user_text.split()),
            "question_marks": user_text.count("?"),
            "conjunctions": sum(1 for word in ["and", "or", "but", "also", "then"] if word in user_text.lower())
        }

        # Calculate complexity score
        complexity_score = 0.0

        # Multiple categories increase complexity
        if complexity_factors["category_count"] > 1:
            complexity_score += 0.3

        # Longer text suggests more complex requests
        if complexity_factors["word_count"] > 20:
            complexity_score += 0.2
        elif complexity_factors["word_count"] > 10:
            complexity_score += 0.1

        # Multiple questions increase complexity
        if complexity_factors["question_marks"] > 1:
            complexity_score += 0.2

        # Conjunctions suggest compound requests
        if complexity_factors["conjunctions"] > 0:
            complexity_score += 0.1 * min(complexity_factors["conjunctions"], 3)

        complexity_level = "high" if complexity_score > 0.6 else "medium" if complexity_score > 0.3 else "low"

        return {
            "complexity_score": min(complexity_score, 1.0),
            "complexity_level": complexity_level,
            "factors": complexity_factors,
            "estimated_effort": "high" if complexity_score > 0.7 else "medium" if complexity_score > 0.4 else "low",
            "recommended_approach": self._get_complexity_recommendations(complexity_level)
        }

    def _get_complexity_recommendations(self, complexity_level: str) -> List[str]:
        """Get recommendations based on complexity level."""
        recommendations = {
            "low": [
                "Single agent execution should be sufficient",
                "Direct processing recommended"
            ],
            "medium": [
                "Consider breaking into subtasks",
                "May benefit from specialized agents",
                "Monitor execution progress"
            ],
            "high": [
                "Decompose into multiple subtasks",
                "Use multiple specialized agents",
                "Implement step-by-step execution",
                "Consider workflow orchestration"
            ]
        }
        return recommendations.get(complexity_level, [])

    def suggest_execution_strategy(self, categories: List[str], complexity_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Suggest execution strategy based on categories and complexity.

        Args:
            categories: Identified categories
            complexity_assessment: Complexity assessment result

        Returns:
            Execution strategy suggestions
        """
        strategy = {
            "execution_mode": "sequential",
            "agent_requirements": [],
            "estimated_steps": len(categories),
            "parallel_execution": False,
            "workflow_needed": False
        }

        complexity_level = complexity_assessment.get("complexity_level", "low")

        # Determine agent requirements
        agent_mapping = {
            "answer": "researcher",
            "collect": "researcher",
            "process": "analyst",
            "analyze": "analyst",
            "generate": "writer"
        }

        required_agents = list(set(agent_mapping.get(cat, "researcher") for cat in categories))
        strategy["agent_requirements"] = required_agents

        # Adjust strategy based on complexity
        if complexity_level == "high":
            strategy["execution_mode"] = "workflow"
            strategy["workflow_needed"] = True
            strategy["estimated_steps"] = len(categories) * 2  # More detailed steps

        elif complexity_level == "medium" and len(categories) > 2:
            strategy["execution_mode"] = "parallel"
            strategy["parallel_execution"] = True

        # Special handling for specific category combinations
        if "collect" in categories and "analyze" in categories:
            strategy["execution_mode"] = "sequential"
            strategy["notes"] = "Data collection must precede analysis"

        if "process" in categories and "generate" in categories:
            strategy["execution_mode"] = "sequential"
            strategy["notes"] = "Data processing should precede content generation"

        return strategy

    def get_intent_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Get intent parsing templates for different types of requests.

        Returns:
            Dictionary of intent templates
        """
        return {
            "simple_question": {
                "description": "Direct questions requiring factual answers",
                "typical_categories": ["answer"],
                "keywords": ["what", "who", "when", "where"],
                "complexity": "low"
            },
            "research_request": {
                "description": "Requests for information gathering and research",
                "typical_categories": ["collect", "analyze"],
                "keywords": ["research", "find", "investigate", "study"],
                "complexity": "medium"
            },
            "data_processing": {
                "description": "Requests for data transformation and processing",
                "typical_categories": ["process", "analyze"],
                "keywords": ["clean", "transform", "process", "format"],
                "complexity": "medium"
            },
            "content_creation": {
                "description": "Requests for content generation and writing",
                "typical_categories": ["generate"],
                "keywords": ["create", "write", "generate", "produce"],
                "complexity": "medium"
            },
            "complex_workflow": {
                "description": "Multi-step requests requiring multiple capabilities",
                "typical_categories": ["collect", "process", "analyze", "generate"],
                "keywords": ["comprehensive", "complete", "full analysis"],
                "complexity": "high"
            }
        }


