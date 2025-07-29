# -*- coding: utf-8 -*-
# Copyright 2023 OpenSPG Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied.

from app.services.scholar.kag_core.solver.prompt.deduce_choice import DeduceChoice
from app.services.scholar.kag_core.solver.prompt.deduce_entail import DeduceEntail
from app.services.scholar.kag_core.solver.prompt.deduce_extractor import DeduceExtractor
from app.services.scholar.kag_core.solver.prompt.deduce_judge import DeduceJudge
from app.services.scholar.kag_core.solver.prompt.deduce_multi_choice import DeduceMutiChoice
from app.services.scholar.kag_core.solver.prompt.expression_builder import ExpressionBuildr
from app.services.scholar.kag_core.solver.prompt.lf_static_planning_prompt import RetrieverLFStaticPlanningPrompt
from app.services.scholar.kag_core.solver.prompt.logic_form_plan import LogicFormPlanPrompt
from app.services.scholar.kag_core.solver.prompt.multi_hop_generator import MultiHopGeneratorPrompt
from app.services.scholar.kag_core.solver.prompt.question_ner import QuestionNER
from app.services.scholar.kag_core.solver.prompt.resp_extractor import RespExtractor
from app.services.scholar.kag_core.solver.prompt.resp_generator import RespGenerator
from app.services.scholar.kag_core.solver.prompt.resp_judge import RespJudge
from app.services.scholar.kag_core.solver.prompt.resp_reflector import RespReflector
from app.services.scholar.kag_core.solver.prompt.resp_verifier import RespVerifier
from app.services.scholar.kag_core.solver.prompt.rewrite_sub_query import DefaultRewriteSubQuery
from app.services.scholar.kag_core.solver.prompt.solve_question import SolveQuestion

from app.services.scholar.kag_core.solver.prompt.solve_question_without_docs import (
    SolveQuestionWithOutDocs,
)
from app.services.scholar.kag_core.solver.prompt.solve_question_without_spo import SolveQuestionWithOutSPO
from app.services.scholar.kag_core.solver.prompt.spo_retrieval import SpoRetrieval
from app.services.scholar.kag_core.solver.prompt.query_rewrite_prompt import QueryRewritePrompt
from app.services.scholar.kag_core.solver.prompt.reference_generator import ReferGeneratorPrompt
from app.services.scholar.kag_core.solver.prompt.retriever_static_planning_prompt import (
    RetrieverStaticPlanningPrompt,
)
from app.services.scholar.kag_core.solver.prompt.spo_retriever_decompose_prompt import (
    DefaultSPORetrieverDecomposePrompt,
)
from app.services.scholar.kag_core.solver.prompt.static_planning_prompt import DefaultStaticPlanningPrompt
from app.services.scholar.kag_core.solver.prompt.thought_iterative_planning_prompt import (
    DefaultIterativePlanningPrompt,
)
from app.services.scholar.kag_core.solver.prompt.sub_question_summary import SubQuestionSummary
from app.services.scholar.kag_core.solver.prompt.summary_question import SummaryQuestionWithOutSPO
from app.services.scholar.kag_core.solver.prompt.mcp_tool_call import MCPToolCallPrompt
from app.services.scholar.kag_core.solver.prompt.thought_then_answer import ThoughtThenAnswerPrompt
from app.services.scholar.kag_core.solver.prompt.without_reference_generator import WithOutReferGeneratorPrompt

__all__ = [
    "DeduceChoice",
    "DeduceExtractor",
    "DeduceEntail",
    "DeduceJudge",
    "DeduceMutiChoice",
    "LogicFormPlanPrompt",
    "QuestionNER",
    "RespExtractor",
    "RespGenerator",
    "RespJudge",
    "RespReflector",
    "RespVerifier",
    "SolveQuestion",
    "SolveQuestionWithOutDocs",
    "SolveQuestionWithOutSPO",
    "SpoRetrieval",
    "ExpressionBuildr",
    "DefaultRewriteSubQuery",
    "QueryRewritePrompt",
    "ReferGeneratorPrompt",
    "RetrieverStaticPlanningPrompt",
    "DefaultSPORetrieverDecomposePrompt",
    "DefaultStaticPlanningPrompt",
    "DefaultIterativePlanningPrompt",
    "SubQuestionSummary",
    "SummaryQuestionWithOutSPO",
    "RetrieverLFStaticPlanningPrompt",
    "MCPToolCallPrompt",
    "WithOutReferGeneratorPrompt",
    "ThoughtThenAnswerPrompt",
    "MultiHopGeneratorPrompt",
]
