#!/usr/bin/env python3
"""
Test the LLM Output Transformer with actual content from test_output1.log
"""

import sys
sys.path.append('/opt/startu/python-middleware')

from app.utils.LLM_output_structor import LLMOutputTransformer, format_confirmation_message

# Extract the actual LLM output from the log (lines 379-451)
llm_output = """### Comprehensive Request Analysis

#### Overall Task Summary
The user's request is for analytical support on their e-commerce business performance. This involves breaking down business data to uncover insights and provide actionable recommendations. The request is multifaceted, requiring data handling, insight generation, and strategic advice. No actual data is provided, so this analysis outlines a hypothetical approach based on the clarifications.

#### Identified Task Categories
Based on nuanced intent analysis, I've categorized the request into the following primary task types (from the allowed categories: answer, collect, process, analyze, generate). Each category is assigned to specific elements of the request for precision:
- **Collect**: Gathering necessary business data (e.g., sales records, customer metrics) – essential as a foundational step since no data is provided.
- **Process**: Organizing and cleaning the collected data for usability (e.g., aggregating sales by category or calculating metrics like CAC).
- **Analyze**: Examining data for patterns, trends, and metrics (e.g., sales trends, customer behavior, CAC/LTV, profitability).
- **Generate**: Creating recommendations and strategies based on analysis (e.g., marketing optimization, inventory/pricing suggestions, growth opportunities).
- **Answer**: Delivering the final, comprehensive response to the user, synthesizing all insights and recommendations.

The request leans heavily toward "analyze" and "generate" as core intents, with "collect" and "process" as prerequisites. "Answer" encompasses the overall output."""

# Also test with a confirmation message example
confirmation_content = """I have generated a detailed blueprint: Problem Analysis: {'complexity': 'medium', 'domain': 'business', 'intent_categories': ['answer', 'collect', 'process', 'analyze', 'generate'], 'analysis_focus': ['source_validation', 'data_analysis', 'solution_design', 'strategy_development'], 'key_entities': {'numbers': ['3'], 'capitalized': ['Help', 'Additional'], 'technical_terms': ['business', 'e-commerce', 'performance', 'electronics']}}. Meta architect output includes extensive strategic planning. Do you confirm to proceed, or would you like to provide feedback for adjustments?"""

# Initialize transformer
transformer = LLMOutputTransformer()

print("=" * 80)
print("ORIGINAL LLM OUTPUT (from test_output1.log lines 388-402):")
print("=" * 80)
print(llm_output)
print("\n")

print("=" * 80)
print("TRANSFORMED OUTPUT (with readability enhancements):")
print("=" * 80)
transformed = transformer.transform_message(llm_output, 'confirmation')
print(transformed)
print("\n")

print("=" * 80)
print("ORIGINAL CONFIRMATION MESSAGE:")
print("=" * 80)
print(confirmation_content)
print("\n")

print("=" * 80)
print("TRANSFORMED CONFIRMATION MESSAGE:")
print("=" * 80)
transformed_confirmation = transformer.transform_message(confirmation_content, 'confirmation')
print(transformed_confirmation)
print("\n")

# Test reasoning transformation
reasoning_sample = """The user's request 'Help me with my business' is a classic example of a vague and unclear demand. It lacks any specific details about the nature of the business, the type of help needed, or the desired outcome. It fails most SMART criteria: it is not Specific (what business? what help?), not Measurable (what defines 'help' or success?), not Achievable in its current form, and not Time-bound."""

print("=" * 80)
print("ORIGINAL REASONING:")
print("=" * 80)
print(reasoning_sample)
print("\n")

print("=" * 80)
print("TRANSFORMED REASONING (conversational style):")
print("=" * 80)
enhanced_reasoning = transformer._make_reasoning_conversational(reasoning_sample)
print(enhanced_reasoning)
