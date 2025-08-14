"""
Meta-Architect Agent

Specialized agent for analyzing complex problems and constructing strategic blueprints
using analytical frameworks and decomposition strategies.
Refactored to use LangChain framework and TaskFactory for complete configuration-driven behavior.
"""

import json
import logging
from typing import Dict, List, Any, Optional

# LangChain dependencies
from langchain.agents import AgentExecutor
from langchain.tools import BaseTool
from langchain.schema import AgentAction, AgentFinish

# Import our system's core components
from ..base_agent import BaseAgent
from ...core.models.agent_models import AgentConfig
from ...core.models.architect_models import (
    StrategicPlan, BlueprintConstructionRequest, BlueprintConstructionResult,
    FrameworkRecommendation, FrameworkStrategy, DecompositionResult
)
from ...config.config_manager import ConfigManager
from app.services.llm_integration import LLMIntegrationManager

logger = logging.getLogger(__name__)


class MetaArchitectAgent(BaseAgent):
    """
    Agent specialized in strategic blueprint construction and problem analysis.

    This agent is now a pure executor that relies entirely on external configuration
    and runtime context for its behavior. All prompts and LLM selection logic
    have been externalized to configuration files.
    Refactored to use LangChain framework for complete configuration-driven behavior.
    """

    def __init__(self, config: AgentConfig, config_manager: ConfigManager,
                 llm_manager: LLMIntegrationManager, tool_integration_manager=None):
        """
        Initialize the meta-architect agent.

        Args:
            config: Agent's basic configuration (such as agent_id, role)
            config_manager: Configuration manager for reading prompts.yaml and llm_bindings.yaml
            llm_manager: LLM integration manager for actual LLM calls
            tool_integration_manager: Optional tool integration manager for LangChain tools
        """
        # Call parent's initialization method, which handles role definition and LLM binding loading
        super().__init__(config, config_manager, llm_manager, tool_integration_manager)

        # Configuration-driven properties (no hardcoded values)
        self.max_recursion_depth = config.metadata.get('max_recursion_depth', 3) if config.metadata else 3

        # LangChain agent executor instance
        self._agent_executor: AgentExecutor = None

    async def initialize(self) -> None:
        """Initialize the meta-architect agent."""
        logger.info(f"Meta-architect agent initialized: {self.agent_id}")

    async def execute_task(self, task_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute blueprint construction task using LangChain-based configuration-driven approach.
        Enhanced to utilize targeted input from mining service.

        Args:
            task_data: Contains problem description and requirements with enhanced mining context
            context: Execution context

        Returns:
            Dictionary containing strategic blueprint result
        """
        try:
            self.set_busy(context.get('task_id', 'unknown'))

            # Parse input data with enhanced mining context
            problem_description = task_data.get("problem_description", "")
            domain = task_data.get("domain", "business")
            complexity = task_data.get("complexity", "medium")
            requirements = task_data.get("requirements", {})
            max_recursion_depth = task_data.get("max_recursion_depth", self.max_recursion_depth)

            if not problem_description:
                raise ValueError("No problem description provided for blueprint construction")

            # Extract enhanced mining context from requirements
            mining_context = self._extract_mining_context(requirements)

            # Determine task type based on requirements and mining context
            task_type = self._determine_task_type(task_data, context, mining_context)

            # Execute the appropriate task using enhanced context
            if task_type == "decomposition":
                result = await self._execute_decomposition_task(problem_description, context, mining_context)
            elif task_type == "blueprint_construction" or task_type == "detailed_blueprint_construction":
                result = await self._execute_enhanced_blueprint_construction_task(
                    problem_description, domain, complexity, requirements, mining_context, context
                )
            elif task_type == "generate_execution_roadmap":
                # Handle execution roadmap generation
                blueprint_result = task_data.get("blueprint_result", {})
                if not blueprint_result:
                    # If no blueprint result provided, create a basic one from the problem description
                    blueprint_result = {
                        "problem_description": problem_description,
                        "domain": domain,
                        "complexity": complexity,
                        "requirements": requirements
                    }
                result = self.generate_execution_roadmap(blueprint_result)
            elif task_type == "recursive_blueprint_task":
                # Handle recursive blueprint construction task
                result = await self._execute_recursive_blueprint_task(
                    problem_description, domain, complexity, requirements,
                    max_recursion_depth, context, mining_context
                )
            else:
                # Default to recursive blueprint construction with enhanced context
                result = await self._execute_recursive_blueprint_task(
                    problem_description, domain, complexity, requirements,
                    max_recursion_depth, context, mining_context
                )

            # Store in memory for future reference
            self.add_memory('last_blueprint', {
                'task_data': task_data,
                'result': result,
                'mining_context': mining_context,
                'timestamp': context.get('timestamp')
            })

            self.set_available()
            return result

        except Exception as e:
            self.set_available()
            logger.error(f"Blueprint construction failed: {e}")
            raise

    async def _execute_decomposition_task(self, problem_description: str, context: Dict[str, Any],
                                        mining_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute decomposition task using LangChain-based configuration-driven approach.
        Enhanced to use mining context when available and support recursive context.

        Args:
            problem_description: Problem to decompose
            context: Execution context
            mining_context: Enhanced context from mining service

        Returns:
            Decomposition result
        """
        # Create LangChain agent executor for this task
        agent_executor = await self.create_langchain_agent(context)

        # Check for recursive context
        is_recursive = mining_context and mining_context.get("recursive_context", False)
        parent_analysis = mining_context.get("parent_analysis") if mining_context else None
        recursion_depth = mining_context.get("recursion_depth", 1) if mining_context else 1

        # Prepare enhanced decomposition input if mining context is available
        if mining_context and mining_context.get("has_enhanced_context"):
            intent_categories = mining_context.get("intent_categories", [])
            framework_hints = mining_context.get("framework_hints", [])
            analysis_focus = mining_context.get("analysis_focus", [])

            # Build recursive context section
            recursive_context_section = ""
            if is_recursive and parent_analysis:
                recursive_context_section = f"""

                RECURSIVE CONTEXT (Depth {recursion_depth}):
                Parent Problem: {parent_analysis.get('problem', 'N/A')}
                Parent Strategy: {parent_analysis.get('strategy', 'N/A')}
                Parent Frameworks: {', '.join(parent_analysis.get('frameworks', []))}
                Parent Reasoning: {parent_analysis.get('reasoning', 'N/A')}

                IMPORTANT: Build upon the parent analysis above. Your decomposition should:
                - Reference and extend the parent's approach
                - Avoid duplicating parent frameworks unless specifically needed
                - Create sub-problems that logically follow from the parent analysis
                - Maintain consistency with the overall analytical direction
                """

            decomposition_input = {
                "input": f"Decompose complex problem using mining analysis insights{' and recursive context' if is_recursive else ''}",
                "task_description": f"""
                Problem Description: {problem_description}

                MINING CONTEXT:
                Intent Categories: {', '.join(intent_categories)}
                Suggested Frameworks: {', '.join(framework_hints)}
                Analysis Focus: {', '.join(analysis_focus)}
                {recursive_context_section}

                Analyze this complex problem using the mining insights{' and building upon parent analysis' if is_recursive else ''} and provide a targeted decomposition:

                1. INTENT-DRIVEN ANALYSIS:
                   - Focus decomposition on identified intent categories: {', '.join(intent_categories)}
                   - Align sub-problems with analysis focus areas: {', '.join(analysis_focus)}
                   {f'- Build upon parent strategy: {parent_analysis.get("strategy", "N/A")}' if is_recursive and parent_analysis else ''}

                2. FRAMEWORK-GUIDED DECOMPOSITION:
                   - Prioritize suggested frameworks: {', '.join(framework_hints)}
                   - Map frameworks to intent categories
                   {f'- Consider parent frameworks: {", ".join(parent_analysis.get("frameworks", []))}' if is_recursive and parent_analysis else ''}

                3. STRUCTURED BREAKDOWN:
                   - Identify sub-problems aligned with intent categories
                   - Recommend frameworks based on mining analysis
                   - Define dependencies considering analysis focus
                   {f'- Ensure logical progression from parent problem: {parent_analysis.get("problem", "N/A")[:100]}...' if is_recursive and parent_analysis else ''}

                Provide response in JSON format:
                {{
                    "rationale": "Decomposition reasoning based on mining analysis{' and parent context' if is_recursive else ''}",
                    "frameworks": [
                        {{
                            "framework_name": "Framework name (prioritize: {', '.join(framework_hints[:3])})",
                            "rationale": "Why this framework suits the identified intent categories{' and builds on parent analysis' if is_recursive else ''}",
                            "application_focus": "Specific aspect aligned with analysis focus",
                            "expected_outcome": "Expected results for intent categories",
                            "estimated_duration": "Time estimate",
                            "intent_alignment": ["intent_category_1", "intent_category_2"]
                            {f', "parent_relationship": "How this relates to parent frameworks: {", ".join(parent_analysis.get("frameworks", []))}"' if is_recursive and parent_analysis else ''}
                        }}
                    ],
                    "sub_problems": [
                        "Sub-problem aligned with intent categories{' and parent context' if is_recursive else ''}",
                        "Sub-problem focused on analysis areas"
                    ],
                    "dependencies": [
                        {{
                            "from": "Component A",
                            "to": "Component B",
                            "type": "prerequisite",
                            "intent_category": "relevant_intent"
                        }}
                    ],
                    "mining_integration": {{
                        "intent_categories_addressed": {intent_categories},
                        "frameworks_selected": "Based on mining hints{' and parent analysis' if is_recursive else ''}",
                        "analysis_focus_covered": {analysis_focus}
                        {f', "recursive_depth": {recursion_depth}, "parent_integration": "Built upon parent analysis"' if is_recursive else ''}
                    }}
                }}
                """,
                "expected_output": f"Mining-enhanced structured problem decomposition{' with recursive context' if is_recursive else ''}",
                "input_data": {
                    "problem_description": problem_description,
                    "mining_context": mining_context,
                    "recursive_context": {"is_recursive": is_recursive, "depth": recursion_depth, "parent_analysis": parent_analysis} if is_recursive else None
                }
            }
        else:
            # Standard decomposition input when no mining context
            decomposition_input = {
                "input": f"Decompose complex problem into manageable components",
                "task_description": f"""
                Problem Description: {problem_description}

                Analyze this complex problem and provide a structured decomposition including:
                1. Problem analysis and understanding
                2. Identification of sub-problems or components
                3. Recommended analytical frameworks for each component
                4. Rationale for the decomposition approach
                5. Dependencies and relationships between components

                Provide response in JSON format:
                {{
                    "rationale": "Detailed reasoning for decomposition approach",
                    "frameworks": [
                        {{
                            "framework_name": "Framework name",
                            "rationale": "Why this framework is suitable",
                            "application_focus": "What aspect it addresses",
                            "expected_outcome": "Expected results",
                            "estimated_duration": "Time estimate"
                        }}
                    ],
                    "sub_problems": [
                        "Sub-problem 1 description",
                        "Sub-problem 2 description"
                    ],
                    "dependencies": [
                        {{
                            "from": "Component A",
                            "to": "Component B",
                            "type": "prerequisite"
                        }}
                    ]
                }}
                """,
                "expected_output": "Structured problem decomposition with frameworks and sub-problems",
                "input_data": {"problem_description": problem_description}
            }

        # Execute the decomposition task using LangChain agent
        logger.debug(f"[META_ARCHITECT_DEBUG] _execute_decomposition_task - Invoking LangChain agent executor...")
        result = await agent_executor.ainvoke(decomposition_input)

        # Extract the actual output from LangChain result
        actual_output = result.get('output', str(result))

        # Parse the result
        if isinstance(actual_output, str):
            try:
                parsed_result = json.loads(actual_output)
            except json.JSONDecodeError:
                # Fallback: create structured result
                logger.warning("Failed to parse LLM output as JSON. Accepting raw string output.")
                parsed_result = actual_output
        else:
            parsed_result = actual_output

        return parsed_result


    async def _execute_enhanced_blueprint_construction_task(self, problem_description: str, domain: str,
                                                          complexity: str, requirements: Dict[str, Any],
                                                          mining_context: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute enhanced blueprint construction task using mining context for targeted analysis.

        Args:
            problem_description: Problem to analyze
            domain: Problem domain
            complexity: Problem complexity
            requirements: Additional requirements
            mining_context: Enhanced context from mining service
            context: Execution context

        Returns:
            Enhanced blueprint construction result
        """
        # Create LangChain agent executor for this task
        agent_executor = await self.create_langchain_agent(context)

        # Extract enhanced context
        intent_categories = mining_context.get("intent_categories", [])
        entities_keywords = mining_context.get("entities_keywords", {})
        framework_hints = mining_context.get("framework_hints", [])
        analysis_focus = mining_context.get("analysis_focus", [])
        intent_parsing_reasoning = mining_context.get("intent_parsing_reasoning", "")
        intent_parsing_output = mining_context.get("intent_parsing_output", "")
        complexity_assessment = mining_context.get("complexity_assessment", {"complexity_level": complexity})

        # Generate context-aware frameworks based on intent categories
        selected_frameworks = self._select_context_aware_frameworks(intent_categories, domain, entities_keywords)

        # Determine dynamic output template based on intent categories
        output_template = self._get_dynamic_output_template(intent_categories)

        # Generate context-specific examples
        context_examples = self._generate_context_examples(intent_categories, domain, problem_description)

        # Prepare enhanced blueprint construction input with strong constraints
        blueprint_input = {
            "input": f"MANDATORY: Analyze the SPECIFIC problem '{problem_description}' using provided mining context '{mining_context}' - DO NOT create your own example",
            "task_description": f"""
            **CRITICAL REQUIREMENTS - MUST FOLLOW:**
            1. You MUST analyze the EXACT problem: "{problem_description}"
            2. You MUST NOT create your own example problems or scenarios
            3. You MUST use the provided mining context to guide your analysis
            4. You MUST select frameworks based on intent_categories: {', '.join(intent_categories)}
            5. You MUST structure output according to the intent-specific template

            **SPECIFIC PROBLEM TO ANALYZE:** {problem_description}

            **MINING CONTEXT PROVIDED:**
            - Intent Categories: {intent_categories}
            - Intent Parsing Reasoning: {intent_parsing_reasoning}
            - Intent Parsing Output: {intent_parsing_output}
            - Key Entities: {entities_keywords.get('entities', [])}
            - Key Terms: {entities_keywords.get('keywords', [])}
            - Complexity Level: {complexity_assessment.get('complexity_level', 'medium')}
            - Domain: {domain}

            **CONTEXT-SELECTED FRAMEWORKS (use these, not generic ones):**
            {self._format_selected_frameworks(selected_frameworks)}

            **CONTEXT EXAMPLES FOR GUIDANCE:**
            {context_examples}

            **MANDATORY OUTPUT STRUCTURE:**
            {output_template}

            **VALIDATION CHECKLIST (your output MUST satisfy all):**
            ✓ Addresses the EXACT problem: "{problem_description}"
            ✓ Uses context-selected frameworks, not generic ones
            ✓ Incorporates entities: {entities_keywords.get('entities', [])}
            ✓ Aligns with intent categories: {', '.join(intent_categories)}
            ✓ Aligns with Intent Parsing Reasoning: {intent_parsing_reasoning}
            ✓ Aligns with Intent Parsing Output: {intent_parsing_output}
            ✓ Follows intent-specific output template
            ✓ Provides actionable, specific recommendations
            """,
            "expected_output": f"Context-aware strategic blueprint for the specific problem using intent-driven frameworks",
            "input_data": {
                "problem_description": problem_description,
                "domain": domain,
                "complexity": complexity,
                "mining_context": mining_context,
                "selected_frameworks": selected_frameworks,
                "output_template": output_template
            }
        }

        # Execute the enhanced blueprint construction task using LangChain agent
        result = await agent_executor.ainvoke(blueprint_input)

        # Extract the actual output from LangChain result
        actual_output = result.get('output', str(result))

        # Parse the result
        if isinstance(actual_output, str):
            try:
                parsed_result = json.loads(actual_output)
            except json.JSONDecodeError:
                # Fallback: create enhanced structured result
                logger.warning("Failed to parse LLM output as JSON. Accepting raw string output.")
                parsed_result = actual_output
        else:
            parsed_result = actual_output

        return parsed_result

    async def _execute_recursive_blueprint_task(self, problem_description: str, domain: str,
                                              complexity: str, requirements: Dict[str, Any],
                                              max_recursion_depth: int, context: Dict[str, Any],
                                              mining_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute recursive blueprint construction using LangChain-based configuration-driven approach.

        Args:
            problem_description: Problem to analyze
            domain: Problem domain
            complexity: Problem complexity
            requirements: Additional requirements
            max_recursion_depth: Maximum recursion depth
            context: Execution context

        Returns:
            Recursive blueprint result
        """
        import time
        start_time = time.time()

        try:
            logger.info(f"Initiating recursive blueprint construction for: {problem_description[:100]}...")

            # Start the recursive process from the top-level problem
            root_node = await self._recursive_construct_plan(
                problem_description=problem_description,
                domain=domain,
                complexity=complexity,
                current_depth=1,
                max_depth=max_recursion_depth,
                context=context,
                mining_context=mining_context
            )

            processing_time = (time.time() - start_time) * 1000

            # Create result using configuration-driven approach
            result = {
                "plan_tree_root": root_node.dict() if hasattr(root_node, 'dict') else root_node,
                "total_estimated_duration": self._calculate_tree_duration(root_node),
                "overall_complexity": self._determine_overall_complexity(root_node),
                "confidence_score": self._calculate_tree_confidence(root_node),
                "reasoning": "The strategic plan was constructed via recursive decomposition using LangChain-based configuration-driven approach.",
                "processing_time_ms": processing_time,
                "architect_version": "4.0-langchain-driven"
            }

            logger.info("Successfully constructed recursive strategic blueprint tree.")
            return result

        except Exception as e:
            logger.error(f"Recursive blueprint construction failed: {e}")
            raise

    async def _recursive_construct_plan(self, problem_description: str, domain: str, complexity: str,
                                      current_depth: int, max_depth: int, context: Dict[str, Any],
                                      mining_context: Dict[str, Any] = None, parent_analysis: Dict[str, Any] = None) -> StrategicPlan:
        """
        Recursively constructs a strategic plan node using LangChain-based configuration-driven approach.
        Enhanced to support mining context for targeted analysis and preserve previous analysis context.

        Args:
            problem_description: Current problem to analyze
            domain: Problem domain
            complexity: Problem complexity
            current_depth: Current recursion depth
            max_depth: Maximum recursion depth
            context: Execution context
            mining_context: Enhanced context from mining service
            parent_analysis: Analysis results from parent level for context continuity
        """
        # Termination Condition: Prevent infinite recursion
        if current_depth > max_depth:
            logger.warning(f"Max recursion depth reached at level {current_depth}. Treating as leaf node.")
            return StrategicPlan(
                problem_description=problem_description,
                strategy=FrameworkStrategy.APPLY_FRAMEWORKS,
                reasoning="Max depth reached; this problem should be addressed directly.",
                selected_frameworks=await self._get_default_frameworks(domain, complexity)
            )

        # Enhance mining context with parent analysis for recursive continuity
        enhanced_mining_context = mining_context.copy() if mining_context else {}
        if parent_analysis:
            enhanced_mining_context["parent_analysis"] = parent_analysis
            enhanced_mining_context["recursion_depth"] = current_depth
            enhanced_mining_context["recursive_context"] = True
            logger.debug(f"Enhanced mining context with parent analysis at depth {current_depth}")

        # Execute decomposition task using LangChain with enhanced context
        if enhanced_mining_context:
            logger.debug(f"[META_ARCHITECT_DEBUG] _recursive_construct_plan - Calling decomposition with enhanced context")
            decomposition_result = await self._execute_decomposition_task(problem_description, context, enhanced_mining_context)
        else:
            logger.debug(f"[META_ARCHITECT_DEBUG] _recursive_construct_plan - Calling decomposition without enhanced context")
            decomposition_result = await self._execute_decomposition_task(problem_description, context)

        # DEBUG: Log decomposition result
        logger.debug(f"[META_ARCHITECT_DEBUG] _recursive_construct_plan - Decomposition result: {decomposition_result}")

        sub_problems = decomposition_result.get("sub_problems", [])
        frameworks_data = decomposition_result.get("frameworks", [])

        # Create the current plan node with enhanced reasoning
        strategy = FrameworkStrategy.DECOMPOSITION if sub_problems else FrameworkStrategy.APPLY_FRAMEWORKS

        # Build reasoning that incorporates parent context
        reasoning = decomposition_result.get("rationale", "No rationale provided.")
        if parent_analysis and current_depth > 1:
            reasoning = f"Building on parent analysis: {reasoning}"

        current_plan_node = StrategicPlan(
            problem_description=problem_description,
            strategy=strategy,
            reasoning=reasoning,
            selected_frameworks=self._parse_framework_recommendations_from_result(frameworks_data)
        )

        # Store current analysis for child nodes
        current_analysis = {
            "problem": problem_description,
            "strategy": strategy.value if hasattr(strategy, 'value') else str(strategy),
            "frameworks": [f.framework_name for f in current_plan_node.selected_frameworks] if current_plan_node.selected_frameworks else [],
            "reasoning": reasoning,
            "depth": current_depth,
            "decomposition_result": decomposition_result
        }

        # Recursive Step: If there are sub-problems, recurse with enhanced context
        if strategy == FrameworkStrategy.DECOMPOSITION:
            import asyncio
            child_tasks = []
            for i, sub_problem in enumerate(sub_problems):
                # Create an awaitable task for each recursive call with parent analysis
                child_task = self._recursive_construct_plan(
                    problem_description=sub_problem,
                    domain=domain,
                    complexity=complexity,
                    current_depth=current_depth + 1,
                    max_depth=max_depth,
                    context=context,
                    mining_context=enhanced_mining_context,
                    parent_analysis=current_analysis  # Pass current analysis to child
                )
                child_tasks.append(child_task)

            # Execute recursive calls concurrently
            child_nodes = await asyncio.gather(*child_tasks)
            current_plan_node.sub_plans = child_nodes

            logger.debug(f"Completed recursive analysis at depth {current_depth} with {len(child_nodes)} child nodes")

        return current_plan_node

    def _extract_mining_context(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract enhanced mining context from requirements.
        Now handles flattened requirements structure and generates analysis_focus and framework_hints.

        Args:
            requirements: Requirements dictionary (flattened structure)

        Returns:
            Structured mining context for enhanced processing
        """
        # DEBUG: Log raw requirements structure
        logger.debug(f"[META_ARCHITECT_DEBUG] _extract_mining_context - Raw requirements: {requirements}")

        # Extract intent_categories for generating analysis_focus and framework_hints
        intent_categories = requirements.get("intent_categories", [])
        entities_keywords = requirements.get("entities_keywords", {})

        # Create intent_analysis structure for the helper methods
        intent_analysis = {
            "intent_categories": intent_categories,
            "complexity_assessment": {"complexity_level": requirements.get("complexity", "medium")}
        }

        # Generate analysis_focus and framework_hints using the new methods
        analysis_focus = self._extract_analysis_focus(intent_analysis)
        framework_hints = self._extract_framework_hints_from_intent_analysis(entities_keywords, intent_analysis)

        # Extract mining context with generated values
        mining_context = {
            "demand_state": requirements.get("demand_state"),
            "smart_analysis": requirements.get("smart_analysis", {}),
            "intent_categories": intent_categories,
            "intent_parsing_reasoning": requirements.get("intent_parsing_reasoning", ""),
            "intent_parsing_output": requirements.get("intent_parsing_output", ""),
            "complexity": requirements.get("complexity", "medium"),
            "entities_keywords": entities_keywords,
            "analysis_focus": analysis_focus,
            "framework_hints": framework_hints,
            "clarification_history": requirements.get("clarification_history", []),
            "has_enhanced_context": requirements.get("has_enhanced_context", True)
        }

        return mining_context

    def _extract_framework_hints_from_intent_analysis(self, entities_keywords: Dict[str, Any], intent_analysis: Dict[str, Any]) -> List[str]:
        """
        Extract framework hints based on entity keywords and intent analysis
        """
        framework_hints = []

        entities = entities_keywords.get("entities", [])
        keywords = entities_keywords.get("keywords", [])
        intent_categories = intent_analysis.get("intent_categories", [])

        # 基于实体和关键词推荐框架
        entity_text = " ".join(str(e).lower() for e in entities)
        keyword_text = " ".join(str(k).lower() for k in keywords)
        combined_text = f"{entity_text} {keyword_text}"

        # 财务相关框架
        if any(term in combined_text for term in ["financial", "revenue", "profit", "cost", "budget"]):
            framework_hints.extend(["Financial Ratio Analysis", "Cost-Benefit Analysis", "ROI Analysis"])

        # 性能相关框架
        if any(term in combined_text for term in ["performance", "kpi", "metric", "benchmark"]):
            framework_hints.extend(["Performance Gap Analysis", "Balanced Scorecard", "KPI Framework"])

        # 市场相关框架
        if any(term in combined_text for term in ["market", "customer", "competitor", "segment"]):
            framework_hints.extend(["Market Analysis", "Customer Segmentation", "Competitive Analysis"])

        # 策略相关框架
        if any(term in combined_text for term in ["strategy", "plan", "roadmap", "vision"]):
            framework_hints.extend(["Strategic Planning", "SWOT Analysis", "Scenario Planning"])

        # 流程相关框架
        if any(term in combined_text for term in ["process", "workflow", "procedure", "operation"]):
            framework_hints.extend(["Business Process Modeling", "Value Stream Mapping", "Lean Analysis"])

        # 基于intent categories添加框架
        if "analyze" in intent_categories:
            framework_hints.extend(["Root Cause Analysis", "Data Analysis Framework"])
        if "generate" in intent_categories:
            framework_hints.extend(["Content Strategy Framework", "Solution Design Framework"])
        if "process" in intent_categories:
            framework_hints.extend(["Process Optimization Framework", "Workflow Design"])

        return list(set(framework_hints))  # 去重并返回

    def _extract_framework_hints(self, mining_context: Dict[str, Any]) -> List[str]:
        """Extract framework hints from mining context."""
        # First check if framework_hints are directly provided
        direct_hints = mining_context.get("framework_hints", [])
        if direct_hints:
            return direct_hints

        hints = []
        intent_categories = mining_context.get("intent_categories", [])

        # Map intent categories to framework hints
        category_framework_map = {
            "collect": ["Data Collection Framework", "Information Gathering Framework"],
            "process": ["Data Processing Framework", "Workflow Optimization Framework"],
            "analyze": ["Analytical Framework", "SWOT Analysis", "Root Cause Analysis"],
            "generate": ["Content Generation Framework", "Creative Problem Solving"],
            "compare": ["Comparative Analysis Framework", "Benchmarking Framework"],
            "evaluate": ["Evaluation Framework", "Assessment Framework"],
            "plan": ["Strategic Planning Framework", "Project Planning Framework"],
            "monitor": ["Monitoring Framework", "Performance Tracking Framework"]
        }

        for category in intent_categories:
            if category in category_framework_map:
                hints.extend(category_framework_map[category])

        # Extract from smart_analysis if available
        smart_analysis = mining_context.get("smart_analysis", {})
        if smart_analysis:
            hints.extend(smart_analysis.get("framework_recommendations", []))

        return list(set(hints))  # Remove duplicates

    def _extract_analysis_focus(self, intent_analysis: Dict[str, Any]) -> List[str]:
        """
        从intent分析中提取分析焦点
        """
        analysis_focus = []

        intent_categories = intent_analysis.get("intent_categories", [])
        complexity_assessment = intent_analysis.get("complexity_assessment", {})

        # 基于intent categories确定分析焦点
        if "analyze" in intent_categories:
            analysis_focus.extend(["data_analysis", "performance_metrics", "trend_identification"])
        if "generate" in intent_categories:
            analysis_focus.extend(["content_creation", "strategy_development", "solution_design"])
        if "process" in intent_categories:
            analysis_focus.extend(["workflow_optimization", "process_improvement", "automation_opportunities"])
        if "collect" in intent_categories:
            analysis_focus.extend(["data_gathering", "information_consolidation", "source_validation"])

        # 基于复杂度添加焦点
        complexity_level = complexity_assessment.get("complexity_level", "medium")
        if complexity_level == "high":
            analysis_focus.extend(["stakeholder_analysis", "risk_assessment", "dependency_mapping"])
        elif complexity_level == "medium":
            analysis_focus.extend(["requirement_analysis", "feasibility_assessment"])

        return list(set(analysis_focus))  # 去重

    def _determine_analysis_focus(self, mining_context: Dict[str, Any]) -> List[str]:
        """Determine analysis focus areas from mining context."""
        # First check if analysis_focus is directly provided
        direct_focus = mining_context.get("analysis_focus", [])
        if direct_focus:
            return direct_focus

        focus_areas = []

        # Extract from sub_steps_identified
        sub_steps = mining_context.get("sub_steps_identified", [])
        for step in sub_steps:
            if "analyze" in step.lower():
                focus_areas.append("detailed_analysis")
            elif "plan" in step.lower():
                focus_areas.append("planning")
            elif "implement" in step.lower():
                focus_areas.append("implementation")

        # Extract from entities and keywords
        entities_keywords = mining_context.get("entities_keywords", {})
        entities = entities_keywords.get("entities", [])
        keywords = entities_keywords.get("keywords", [])

        # Business focus indicators
        business_indicators = ["revenue", "profit", "growth", "market", "customer", "sales"]
        if any(keyword.lower() in business_indicators for keyword in keywords):
            focus_areas.append("business_analysis")

        # Technical focus indicators
        technical_indicators = ["system", "data", "process", "automation", "integration"]
        if any(keyword.lower() in technical_indicators for keyword in keywords):
            focus_areas.append("technical_analysis")

        # Strategic focus indicators
        strategic_indicators = ["strategy", "plan", "roadmap", "vision", "goal"]
        if any(keyword.lower() in strategic_indicators for keyword in keywords):
            focus_areas.append("strategic_planning")

        return focus_areas if focus_areas else ["general_analysis"]

    def _determine_task_type(self, task_data: Dict[str, Any], context: Dict[str, Any], mining_context: Dict[str, Any] = None) -> str:
        """
        Simplified task type determination - primarily routes to enhanced blueprint construction.

        Args:
            task_data: Task input data
            context: Execution context
            mining_context: Enhanced mining context

        Returns:
            Task type string
        """
        # Check if task type is explicitly specified
        explicit_task_type = task_data.get("task_type")
        if explicit_task_type:
            if explicit_task_type == "generate_execution_roadmap":
                return "generate_execution_roadmap"
            elif explicit_task_type == "recursive_blueprint_task":
                return "recursive_blueprint_task"
            return explicit_task_type

        # Since mining service flow primarily uses enhanced blueprint construction,
        # default to that for most cases
        problem_description = task_data.get("problem_description", "")

        # Only use decomposition for explicit decomposition requests
        if any(keyword in problem_description.lower() for keyword in ["decompose", "break down", "components"]):
            return "decomposition"

        # Default to enhanced blueprint construction for all other cases
        return "detailed_blueprint_construction"

    def _create_fallback_decomposition_result(self, problem_description: str, result_text: str,
                                            mining_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create fallback decomposition result when JSON parsing fails.
        Enhanced to use mining context when available.
        """
        if mining_context and mining_context.get("has_enhanced_context"):
            framework_hints = mining_context.get("framework_hints", [])
            intent_categories = mining_context.get("intent_categories", [])

            return {
                "rationale": f"Mining-enhanced analysis of: {problem_description[:50]}... using intent categories: {', '.join(intent_categories)}",
                "frameworks": [
                    {
                        "framework_name": framework_hints[0] if framework_hints else "Generic Analysis Framework",
                        "rationale": f"Selected based on mining analysis for intent categories: {', '.join(intent_categories)}",
                        "application_focus": f"Focused on {', '.join(mining_context.get('analysis_focus', ['general analysis']))}",
                        "expected_outcome": "Mining-guided analysis results",
                        "estimated_duration": "1-2 weeks",
                        "intent_alignment": intent_categories
                    }
                ],
                "sub_problems": [],
                "dependencies": [],
                "mining_integration": {
                    "intent_categories_addressed": intent_categories,
                    "frameworks_selected": framework_hints[:3],
                    "analysis_focus_covered": mining_context.get("analysis_focus", [])
                }
            }
        else:
            return {
                "rationale": f"Analysis of: {problem_description[:50]}...",
                "frameworks": [
                    {
                        "framework_name": "Generic Analysis Framework",
                        "rationale": "Fallback framework for problem analysis",
                        "application_focus": "General problem solving",
                        "expected_outcome": "Structured analysis results",
                        "estimated_duration": "1-2 weeks"
                    }
                ],
                "sub_problems": [],
                "dependencies": []
            }

    def _create_enhanced_fallback_blueprint_result(self, problem_description: str, domain: str,
                                                 complexity: str, mining_context: Dict[str, Any],
                                                 result_text: str) -> Dict[str, Any]:
        """
        Create enhanced fallback blueprint result when JSON parsing fails.
        Uses mining context for targeted fallback.
        """
        framework_hints = mining_context.get("framework_hints", [])
        intent_categories = mining_context.get("intent_categories", [])
        analysis_focus = mining_context.get("analysis_focus", [])
        entities_keywords = mining_context.get("entities_keywords", {})

        return {
            "problem_analysis": {
                "complexity": complexity,
                "domain": domain,
                "intent_categories": intent_categories,
                "analysis_focus": analysis_focus,
                "key_entities": entities_keywords.get('entities', []),
                "key_terms": entities_keywords.get('keywords', []),
                "decomposition_potential": "medium",
                "key_challenges": ["Mining-guided analysis required"],
                "stakeholders": ["To be identified based on entities"]
            },
            "framework_selection": {
                "primary_frameworks": framework_hints[:3] if framework_hints else ["Generic Analysis Framework"],
                "framework_rationale": "Selected based on mining analysis and intent categories",
                "application_sequence": framework_hints[:2] if len(framework_hints) >= 2 else ["Primary Analysis"],
                "expected_outcomes": ["Mining-guided results", "Intent-aligned analysis"]
            },
            "tree_structure": {
                "root_problem": problem_description,
                "strategy": "mining_guided_framework_application",
                "reasoning": f"Strategy based on mining analysis with intent categories: {', '.join(intent_categories)}",
                "estimated_depth": 2,
                "estimated_breadth": len(intent_categories) if intent_categories else 1,
                "intent_alignment": intent_categories
            },
            "execution_guidance": {
                "recommended_sequence": "intent_category_driven",
                "critical_path": [f"Analysis for {cat}" for cat in intent_categories[:2]] if intent_categories else ["Analysis"],
                "monitoring_points": [f"Checkpoint for {focus}" for focus in analysis_focus[:2]] if analysis_focus else ["Phase completion"],
                "resource_allocation": "mining_complexity_based",
                "success_criteria": ["Intent category completion", "Mining goal achievement"]
            },
            "risk_assessment": {
                "complexity_risks": ["Mining context interpretation"],
                "domain_risks": [f"Domain-specific challenges in {domain}"],
                "mitigation_strategies": ["Leverage mining insights", "Focus on intent categories"]
            },
            "mining_integration": {
                "intent_categories_used": intent_categories,
                "entities_leveraged": entities_keywords.get('entities', []),
                "frameworks_applied": framework_hints,
                "analysis_focus_addressed": analysis_focus
            }
        }

    def _parse_framework_recommendations_from_result(self, frameworks_data: List[Dict]) -> List[FrameworkRecommendation]:
        """Safely parses framework data from the agent into a list of FrameworkRecommendation models."""
        recommendations = []
        if not isinstance(frameworks_data, list):
            return recommendations

        for fw_data in frameworks_data:
            if isinstance(fw_data, dict):
                try:
                    recommendation = FrameworkRecommendation(
                        framework_name=fw_data.get("framework_name", "Unknown Framework"),
                        rationale=fw_data.get("rationale", "Framework selected for analysis"),
                        application_focus=fw_data.get("application_focus", "General analysis"),
                        expected_outcome=fw_data.get("expected_outcome", "Analysis results"),
                        estimated_duration=fw_data.get("estimated_duration", "1-2 weeks")
                    )
                    recommendations.append(recommendation)
                except Exception as e:
                    logger.warning(f"Skipping malformed framework data: {fw_data}. Error: {e}")
        return recommendations

    async def _get_default_frameworks(self, domain: str, complexity: str) -> List[FrameworkRecommendation]:
        """Get default framework recommendations for leaf nodes."""
        return [
            FrameworkRecommendation(
                framework_name="Problem Analysis Framework",
                rationale="Default framework for direct problem analysis",
                application_focus="Comprehensive problem understanding",
                expected_outcome="Structured problem analysis",
                estimated_duration="1-2 weeks"
            )
        ]

    def _calculate_tree_duration(self, root_node: StrategicPlan) -> str:
        """Calculate total duration by traversing the tree structure."""
        def calculate_node_duration(node: StrategicPlan) -> int:
            # Base duration for this node (in weeks)
            base_duration = 2

            if not hasattr(node, 'sub_plans') or not node.sub_plans:
                return base_duration

            # For decomposed problems, calculate max duration of sub-plans
            max_sub_duration = max(calculate_node_duration(sub_plan) for sub_plan in node.sub_plans)
            return base_duration + max_sub_duration

        total_weeks = calculate_node_duration(root_node)

        if total_weeks <= 4:
            return f"{total_weeks}-{total_weeks + 2} weeks"
        elif total_weeks <= 8:
            return f"{total_weeks}-{total_weeks + 4} weeks"
        else:
            return f"{total_weeks}-{total_weeks + 6} weeks"

    def _determine_overall_complexity(self, root_node: StrategicPlan) -> str:
        """Determine overall complexity based on tree depth and breadth."""
        def calculate_tree_metrics(node: StrategicPlan, depth: int = 0) -> tuple:
            max_depth = depth
            total_nodes = 1

            if hasattr(node, 'sub_plans') and node.sub_plans:
                for sub_plan in node.sub_plans:
                    sub_depth, sub_nodes = calculate_tree_metrics(sub_plan, depth + 1)
                    max_depth = max(max_depth, sub_depth)
                    total_nodes += sub_nodes

            return max_depth, total_nodes

        max_depth, total_nodes = calculate_tree_metrics(root_node)

        if max_depth <= 1 and total_nodes <= 3:
            return "low"
        elif max_depth <= 2 and total_nodes <= 7:
            return "medium"
        else:
            return "high"

    def _calculate_tree_confidence(self, root_node: StrategicPlan) -> float:
        """Calculate confidence score for the entire tree."""
        def calculate_node_confidence(node: StrategicPlan) -> float:
            base_confidence = 0.8

            # Adjust based on framework availability
            if hasattr(node, 'selected_frameworks') and node.selected_frameworks:
                base_confidence += 0.1

            # Adjust based on reasoning quality
            if hasattr(node, 'reasoning') and node.reasoning and len(node.reasoning) > 20:
                base_confidence += 0.05

            # For leaf nodes, return base confidence
            if not hasattr(node, 'sub_plans') or not node.sub_plans:
                return min(base_confidence, 1.0)

            # For decomposed nodes, average with sub-plan confidences
            sub_confidences = [calculate_node_confidence(sub_plan) for sub_plan in node.sub_plans]
            avg_sub_confidence = sum(sub_confidences) / len(sub_confidences)

            return min((base_confidence + avg_sub_confidence) / 2, 1.0)

        return calculate_node_confidence(root_node)

    def get_capabilities(self) -> List[str]:
        """Get the capabilities of this agent."""
        return [
            "strategic_planning",
            "framework_selection",
            "problem_analysis",
            "blueprint_construction",
            "complexity_assessment",
            "stakeholder_analysis",
            "recursive_decomposition",
            "tree_based_planning",
            "configuration_driven_execution",
            "langchain_based_execution"
        ]

    def get_blueprint_history(self) -> List[Dict[str, Any]]:
        """
        Get history of constructed blueprints.

        Returns:
            List of blueprint history entries
        """
        history = []
        last_blueprint = self.get_memory('last_blueprint')
        if last_blueprint:
            history.append(last_blueprint)
        return history

    def get_recursive_capabilities(self) -> List[str]:
        """Get the recursive capabilities of this agent."""
        return [
            "recursive_strategic_planning",
            "problem_decomposition",
            "tree_based_planning",
            "concurrent_sub_problem_processing",
            "depth_controlled_recursion",
            "framework_selection_per_node",
            "confidence_scoring_across_tree",
            "langchain_driven_recursion"
        ]

    async def conduct_specialized_analysis(self, analysis_type: str, problem_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Conduct specialized analysis based on analysis type.

        Args:
            analysis_type: Type of specialized analysis
            problem_data: Problem data to analyze
            context: Execution context

        Returns:
            Specialized analysis result
        """
        analysis_types = {
            "stakeholder_analysis": "Comprehensive stakeholder identification and analysis",
            "risk_assessment": "Risk identification, assessment, and mitigation planning",
            "complexity_analysis": "Detailed complexity assessment and management strategies",
            "framework_selection": "Optimal framework selection for problem solving",
            "resource_planning": "Resource requirement analysis and allocation planning"
        }

        if analysis_type not in analysis_types:
            raise ValueError(f"Unsupported analysis type: {analysis_type}")

        # Create specialized analysis task data
        specialized_task_data = {
            **problem_data,
            "analysis_type": analysis_type,
            "analysis_focus": analysis_types[analysis_type]
        }

        return await self.execute_task(specialized_task_data, context)


    def generate_execution_roadmap(self, blueprint_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate execution roadmap from blueprint result.

        Args:
            blueprint_result: Blueprint construction result

        Returns:
            Execution roadmap
        """
        tree_structure = blueprint_result.get("tree_structure", {})
        execution_guidance = blueprint_result.get("execution_guidance", {})

        roadmap = {
            "phases": [],
            "milestones": [],
            "dependencies": [],
            "resource_requirements": [],
            "timeline": {},
            "success_criteria": []
        }

        # Generate phases based on tree structure
        strategy = tree_structure.get("strategy", "apply_frameworks")
        if strategy == "decomposition":
            estimated_depth = tree_structure.get("estimated_depth", 1)
            estimated_breadth = tree_structure.get("estimated_breadth", 1)

            for depth in range(estimated_depth):
                phase_name = f"Phase {depth + 1}: {'Analysis' if depth == 0 else 'Implementation'}"
                roadmap["phases"].append({
                    "name": phase_name,
                    "description": f"Level {depth + 1} problem analysis and solution development",
                    "estimated_duration": f"{2 + depth} weeks",
                    "deliverables": [f"Level {depth + 1} analysis", f"Solution components"]
                })

        # Generate milestones
        critical_path = execution_guidance.get("critical_path", ["Analysis", "Implementation"])
        for i, milestone in enumerate(critical_path):
            roadmap["milestones"].append({
                "name": milestone,
                "description": f"Completion of {milestone.lower()} phase",
                "target_date": f"Week {(i + 1) * 2}",
                "success_criteria": [f"{milestone} completed", "Quality standards met"]
            })

        # Add success criteria
        roadmap["success_criteria"] = blueprint_result.get("success_metrics", [
            "Problem fully analyzed",
            "Solution implemented",
            "Stakeholder satisfaction achieved"
        ])

        return roadmap

    # Context-Aware Framework Selection Methods for Meta-Architect
    def _select_context_aware_frameworks(self, intent_categories: List[str], domain: str, entities_keywords: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Select frameworks based on intent categories and domain context.

        Args:
            intent_categories: List of intent categories from mining context
            domain: Problem domain
            entities_keywords: Entities and keywords from mining context

        Returns:
            List of selected frameworks with rationale
        """
        selected_frameworks = []
        entities = entities_keywords.get('entities', [])
        keywords = entities_keywords.get('keywords', [])

        # Framework selection based on intent categories
        for intent in intent_categories:
            if intent == "analyze":
                if any(term in domain.lower() or any(term in str(e).lower() for e in entities) for term in ["financial", "revenue", "profit", "cost"]):
                    selected_frameworks.append({
                        "framework_name": "Financial Ratio Analysis",
                        "rationale": "Selected for financial analysis intent with financial entities",
                        "application_focus": "Financial performance metrics and trends"
                    })
                elif any(term in domain.lower() or any(term in str(e).lower() for e in entities) for term in ["performance", "kpi", "metric"]):
                    selected_frameworks.append({
                        "framework_name": "Performance Gap Analysis",
                        "rationale": "Selected for performance analysis intent",
                        "application_focus": "Performance metrics and improvement opportunities"
                    })
                elif any(term in domain.lower() or any(term in str(e).lower() for e in entities) for term in ["market", "competitor", "customer"]):
                    selected_frameworks.append({
                        "framework_name": "Market Analysis Framework",
                        "rationale": "Selected for market analysis intent with market-related entities",
                        "application_focus": "Market dynamics and competitive positioning"
                    })
                else:
                    selected_frameworks.append({
                        "framework_name": "Root Cause Analysis",
                        "rationale": "Selected for general analysis intent",
                        "application_focus": "Problem identification and causal analysis"
                    })

            elif intent == "generate":
                if any(term in domain.lower() or any(term in str(e).lower() for e in entities) for term in ["strategy", "plan", "roadmap"]):
                    selected_frameworks.append({
                        "framework_name": "Strategic Planning Framework",
                        "rationale": "Selected for strategy generation intent",
                        "application_focus": "Strategic plan development and roadmap creation"
                    })
                elif any(term in domain.lower() or any(term in str(e).lower() for e in entities) for term in ["content", "document", "report"]):
                    selected_frameworks.append({
                        "framework_name": "Content Strategy Framework",
                        "rationale": "Selected for content generation intent",
                        "application_focus": "Content structure and development approach"
                    })
                else:
                    selected_frameworks.append({
                        "framework_name": "Solution Design Framework",
                        "rationale": "Selected for general generation intent",
                        "application_focus": "Solution conceptualization and design"
                    })

            elif intent == "process":
                if any(term in domain.lower() or any(term in str(e).lower() for e in entities) for term in ["data", "information", "workflow"]):
                    selected_frameworks.append({
                        "framework_name": "Data Processing Pipeline",
                        "rationale": "Selected for data processing intent",
                        "application_focus": "Data workflow and processing optimization"
                    })
                else:
                    selected_frameworks.append({
                        "framework_name": "Business Process Modeling",
                        "rationale": "Selected for process intent",
                        "application_focus": "Process design and optimization"
                    })

            elif intent == "collect":
                selected_frameworks.append({
                    "framework_name": "Data Collection Strategy",
                    "rationale": "Selected for data collection intent",
                    "application_focus": "Data gathering methodology and validation"
                })

        # Ensure at least one framework is selected
        if not selected_frameworks:
            selected_frameworks.append({
                "framework_name": "Systems Thinking Framework",
                "rationale": "Default framework for complex problem analysis",
                "application_focus": "Holistic problem understanding and solution design"
            })

        return selected_frameworks

    def _get_dynamic_output_template(self, intent_categories: List[str]) -> str:
        """
        Generate dynamic output template based on intent categories.

        Args:
            intent_categories: List of intent categories from mining context

        Returns:
            JSON template string for the specific intent combination
        """
        primary_intent = intent_categories[0] if intent_categories else "analyze"

        if primary_intent == "analyze":
            return '''
            {
                "problem_analysis": {
                    "specific_problem": "EXACT problem from input",
                    "intent_categories": ["from mining context"],
                    "key_entities": ["from mining context"],
                    "complexity_level": "from mining context"
                },
                "analysis_framework": {
                    "selected_frameworks": ["context-specific frameworks"],
                    "framework_rationale": "why these frameworks for this specific problem",
                    "analysis_approach": "step-by-step analysis plan"
                },
                "analysis_results": {
                    "key_findings": ["specific findings for the problem"],
                    "insights": ["actionable insights"],
                    "recommendations": ["targeted recommendations"]
                },
                "execution_plan": {
                    "analysis_steps": ["specific steps"],
                    "data_requirements": ["what data is needed"],
                    "timeline": "estimated timeline"
                }
            }
            '''
        elif primary_intent == "generate":
            return '''
            {
                "problem_analysis": {
                    "specific_problem": "EXACT problem from input",
                    "intent_categories": ["from mining context"],
                    "generation_target": "what needs to be generated"
                },
                "generation_framework": {
                    "selected_approach": "context-specific generation approach",
                    "framework_rationale": "why this approach for this specific problem",
                    "generation_strategy": "step-by-step generation plan"
                },
                "content_structure": {
                    "output_format": "specific format for the generation",
                    "key_components": ["main components to generate"],
                    "quality_criteria": ["success criteria"]
                },
                "execution_plan": {
                    "generation_steps": ["specific steps"],
                    "resource_requirements": ["what resources are needed"],
                    "timeline": "estimated timeline"
                }
            }
            '''
        elif primary_intent == "process":
            return '''
            {
                "problem_analysis": {
                    "specific_problem": "EXACT problem from input",
                    "intent_categories": ["from mining context"],
                    "process_scope": "what needs to be processed"
                },
                "process_framework": {
                    "selected_methodology": "context-specific process approach",
                    "framework_rationale": "why this methodology for this specific problem",
                    "process_design": "step-by-step process plan"
                },
                "process_structure": {
                    "input_requirements": ["what inputs are needed"],
                    "process_steps": ["detailed process steps"],
                    "output_specifications": ["expected outputs"],
                    "quality_controls": ["validation checkpoints"]
                },
                "execution_plan": {
                    "implementation_steps": ["specific steps"],
                    "resource_requirements": ["what resources are needed"],
                    "timeline": "estimated timeline"
                }
            }
            '''
        else:
            # Default comprehensive template
            return '''
            {
                "problem_analysis": {
                    "specific_problem": "EXACT problem from input",
                    "intent_categories": ["from mining context"],
                    "key_entities": ["from mining context"],
                    "complexity_level": "from mining context"
                },
                "strategic_framework": {
                    "selected_frameworks": ["context-specific frameworks"],
                    "framework_rationale": "why these frameworks for this specific problem",
                    "strategic_approach": "step-by-step strategic plan"
                },
                "recommendations": {
                    "key_recommendations": ["specific recommendations for the problem"],
                    "implementation_priorities": ["priority order"],
                    "success_metrics": ["measurable outcomes"]
                },
                "execution_plan": {
                    "implementation_steps": ["specific steps"],
                    "resource_requirements": ["what resources are needed"],
                    "timeline": "estimated timeline"
                }
            }
            '''

    def _generate_context_examples(self, intent_categories: List[str], domain: str, problem_description: str) -> str:
        """
        Generate context-specific examples to guide the analysis.

        Args:
            intent_categories: List of intent categories from mining context
            domain: Problem domain
            problem_description: The specific problem to analyze

        Returns:
            Context-specific examples string
        """
        primary_intent = intent_categories[0] if intent_categories else "analyze"

        examples = f"""
        **EXAMPLE OF CORRECT APPROACH FOR YOUR SPECIFIC PROBLEM:**

        Problem: "{problem_description}"
        Intent: {primary_intent}
        Domain: {domain}

        """

        if primary_intent == "analyze":
            examples += f"""
            CORRECT: Focus on analyzing the specific elements mentioned in "{problem_description}"
            WRONG: Create a generic analysis example about customer retention or other unrelated topics

            Your analysis should:
            - Identify specific metrics/data points mentioned in the problem
            - Use analysis frameworks appropriate for the domain: {domain}
            - Provide actionable insights for the exact problem stated
            """
        elif primary_intent == "generate":
            examples += f"""
            CORRECT: Generate the specific content/strategy mentioned in "{problem_description}"
            WRONG: Create a generic generation example about unrelated topics

            Your generation should:
            - Create the exact type of content requested in the problem
            - Use generation frameworks appropriate for the domain: {domain}
            - Provide specific, implementable outputs
            """
        elif primary_intent == "process":
            examples += f"""
            CORRECT: Design a process for the specific workflow mentioned in "{problem_description}"
            WRONG: Create a generic process example about unrelated workflows

            Your process design should:
            - Address the specific process requirements in the problem
            - Use process frameworks appropriate for the domain: {domain}
            - Provide detailed, executable process steps
            """

        return examples

    def _format_selected_frameworks(self, selected_frameworks: List[Dict[str, str]]) -> str:
        """
        Format selected frameworks for inclusion in prompt.

        Args:
            selected_frameworks: List of selected frameworks with rationale

        Returns:
            Formatted string of frameworks
        """
        if not selected_frameworks:
            return "No specific frameworks selected"

        formatted = []
        for i, framework in enumerate(selected_frameworks, 1):
            formatted.append(f"""
            {i}. {framework['framework_name']}
               - Rationale: {framework['rationale']}
               - Focus: {framework['application_focus']}
            """)

        return "\n".join(formatted)

    def _validate_context_usage(self, result: Dict[str, Any], original_problem: str, mining_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that the output properly uses the mining context and addresses the specific problem.

        Args:
            result: The generated result to validate
            original_problem: The original problem description
            mining_context: The mining context that should be used

        Returns:
            Validation result with score and feedback
        """
        validation_result = {
            "is_valid": True,
            "score": 0.0,
            "issues": [],
            "recommendations": []
        }

        result_text = str(result).lower()
        problem_keywords = original_problem.lower().split()

        # Check problem specificity (30% of score)
        keyword_matches = sum(1 for keyword in problem_keywords if len(keyword) > 3 and keyword in result_text)
        problem_specificity_score = min(keyword_matches / max(len([k for k in problem_keywords if len(k) > 3]), 1), 1.0)

        if problem_specificity_score < 0.3:
            validation_result["issues"].append("Output does not adequately address the specific problem")
            validation_result["recommendations"].append("Ensure output directly references key elements from the original problem")

        # Check context utilization (40% of score)
        intent_categories = mining_context.get("intent_categories", [])
        entities = mining_context.get("entities_keywords", {}).get("entities", [])

        context_usage_score = 0.0
        if intent_categories:
            intent_mentions = sum(1 for intent in intent_categories if intent in result_text)
            context_usage_score += (intent_mentions / len(intent_categories)) * 0.5

        if entities:
            entity_mentions = sum(1 for entity in entities if str(entity).lower() in result_text)
            context_usage_score += (entity_mentions / len(entities)) * 0.5

        if context_usage_score < 0.3:
            validation_result["issues"].append("Output does not adequately use mining context")
            validation_result["recommendations"].append("Incorporate more elements from intent categories and identified entities")

        # Check framework appropriateness (30% of score)
        framework_score = 0.8  # Default good score if no obvious issues

        # Calculate overall score
        validation_result["score"] = (problem_specificity_score * 0.3 + context_usage_score * 0.4 + framework_score * 0.3)
        validation_result["is_valid"] = validation_result["score"] >= 0.7

        return validation_result
