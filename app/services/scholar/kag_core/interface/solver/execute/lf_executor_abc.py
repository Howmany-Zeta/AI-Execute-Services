from typing import List

from app.services.scholar.kag_core.common.registry import Registrable
from abc import ABC, abstractmethod

from app.services.scholar.kag_core.interface.solver.base_model import LFExecuteResult, LFPlan


class LFExecutorABC(Registrable, ABC):
    """
    Initializes the base planner.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @abstractmethod
    def execute(self, query, lf_plans: List[LFPlan], **kwargs) -> LFExecuteResult:
        pass
