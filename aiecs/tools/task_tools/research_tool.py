import logging
from typing import Dict, Any, List, Optional, Set
import spacy
from spacy.language import Language
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from collections import Counter
from scipy.stats import pearsonr  # type: ignore[import-untyped]
import os

from aiecs.tools.base_tool import BaseTool
from aiecs.tools import register_tool


# Exceptions
class ResearchToolError(Exception):
    """Base exception for ResearchTool errors."""


class FileOperationError(ResearchToolError):
    """Raised when file operations fail."""


@register_tool("research")
class ResearchTool(BaseTool):
    """
    Tool for causal inference using Mill's methods, advanced induction, deduction, and text summarization.

    Operations:
      - mill_agreement: Identify common factors in positive cases.
      - mill_difference: Identify factors present in positive but absent in negative cases.
      - mill_joint: Combine agreement and difference methods.
      - mill_residues: Identify residual causes after accounting for known causes.
      - mill_concomitant: Analyze correlation between factor and effect variations.
      - induction: Generalize patterns using spaCy-based clustering.
      - deduction: Validate conclusions using spaCy-based rule reasoning.
      - summarize: Summarize text using spaCy sentence ranking.

    Inherits from BaseTool.
    """

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the research tool
        
        Automatically reads from environment variables with RESEARCH_TOOL_ prefix.
        Example: RESEARCH_TOOL_SPACY_MODEL -> spacy_model
        """

        model_config = SettingsConfigDict(env_prefix="RESEARCH_TOOL_")

        max_workers: int = Field(
            default=min(32, (os.cpu_count() or 4) * 2),
            description="Maximum number of worker threads",
        )
        spacy_model: str = Field(default="en_core_web_sm", description="Default spaCy model to use")
        max_text_length: int = Field(default=10_000, description="Maximum text length for inputs")
        allowed_spacy_models: List[str] = Field(
            default=["en_core_web_sm", "zh_core_web_sm"],
            description="Allowed spaCy models",
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize ResearchTool with settings and resources.

        Args:
            config (Dict, optional): Configuration overrides for ResearchTool.
            **kwargs: Additional arguments passed to BaseTool (e.g., tool_name)

        Raises:
            ValueError: If config contains invalid settings.

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/research.yaml)
        3. Environment variables (via dotenv from .env files)
        4. Tool defaults (lowest priority)
        """
        super().__init__(config, **kwargs)

        # Configuration is automatically loaded by BaseTool into self._config_obj
        # Access config via self._config_obj (BaseSettings instance)
        self.config = self._config_obj if self._config_obj else self.Config()

        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        self._spacy_nlp: Optional[Language] = None

    def __del__(self):
        """Clean up resources when the object is destroyed."""
        if hasattr(self, "_spacy_nlp") and self._spacy_nlp is not None:
            self._spacy_nlp = None

    def _get_spacy(self) -> Language:
        """
        Get or cache a spaCy pipeline.

        Returns:
            Language: spaCy NLP object.

        Raises:
            ResearchToolError: If the spaCy model is invalid.
        """
        if self._spacy_nlp is None:
            if self.config.spacy_model not in self.config.allowed_spacy_models:
                raise ResearchToolError(f"Invalid spaCy model '{self.config.spacy_model}', expected {self.config.allowed_spacy_models}")
            self._spacy_nlp = spacy.load(self.config.spacy_model, disable=["textcat"])
        return self._spacy_nlp

    def mill_agreement(self, cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Identify attribute(s) common to all cases with a positive outcome using Mill's Method of Agreement.

        Args:
            cases (List[Dict[str, Any]]): List of cases with attributes and outcomes.

        Returns:
            Dict[str, Any]: Common factors {'common_factors': List[str]}.

        Raises:
            FileOperationError: If processing fails.
        """
        try:
            truthy = [c["attrs"] for c in cases if c.get("outcome")]
            if not truthy:
                return {"common_factors": []}
            common = set(k for k, v in truthy[0].items() if v)
            for attrs in truthy[1:]:
                common &= set(k for k, v in attrs.items() if v)
            return {"common_factors": list(common)}
        except Exception as e:
            raise FileOperationError(f"Failed to process mill_agreement: {str(e)}")

    def mill_difference(self, positive_case: Dict[str, Any], negative_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find attribute(s) present in positive case but absent in negative case using Mill's Method of Difference.

        Args:
            positive_case (Dict[str, Any]): Positive case with attributes and outcome.
            negative_case (Dict[str, Any]): Negative case with attributes and outcome.

        Returns:
            Dict[str, Any]: Difference factors {'difference_factors': List[str]}.

        Raises:
            FileOperationError: If processing fails.
        """
        try:
            pos = {k for k, v in positive_case.get("attrs", {}).items() if v}
            neg = {k for k, v in negative_case.get("attrs", {}).items() if v}
            diff = pos - neg
            return {"difference_factors": list(diff)}
        except Exception as e:
            raise FileOperationError(f"Failed to process mill_difference: {str(e)}")

    def mill_joint(
        self,
        positive_cases: List[Dict[str, Any]],
        negative_cases: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Combine Mill's Method of Agreement and Difference to identify causal factors.

        Args:
            positive_cases (List[Dict[str, Any]]): List of positive cases.
            negative_cases (List[Dict[str, Any]]): List of negative cases.

        Returns:
            Dict[str, Any]: Causal factors {'causal_factors': List[str]}.

        Raises:
            FileOperationError: If processing fails.
        """
        try:
            truthy = [c["attrs"] for c in positive_cases if c.get("outcome")]
            if not truthy:
                return {"causal_factors": []}
            common = set(k for k, v in truthy[0].items() if v)
            for attrs in truthy[1:]:
                common &= set(k for k, v in attrs.items() if v)
            falsy = [c["attrs"] for c in negative_cases if not c.get("outcome")]
            if not falsy:
                return {"causal_factors": list(common)}
            for attrs in falsy:
                common -= set(k for k, v in attrs.items() if v)
            return {"causal_factors": list(common)}
        except Exception as e:
            raise FileOperationError(f"Failed to process mill_joint: {str(e)}")

    def mill_residues(self, cases: List[Dict[str, Any]], known_causes: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        Identify residual causes after accounting for known causes using Mill's Method of Residues.

        Args:
            cases (List[Dict[str, Any]]): List of cases with attributes and effects.
            known_causes (Dict[str, List[str]]): Known causes for effects.

        Returns:
            Dict[str, Any]: Residual causes {'residual_causes': Dict[str, List[str]]}.

        Raises:
            FileOperationError: If processing fails.
        """
        try:
            residual = {}
            for case in cases:
                effects = case.get("effects", {})
                attrs = set(k for k, v in case.get("attrs", {}).items() if v)
                for effect in effects:
                    if effect in known_causes:
                        known = set(known_causes[effect])
                        residual[effect] = list(attrs - known)
                    else:
                        residual[effect] = list(attrs)
            return {"residual_causes": residual}
        except Exception as e:
            raise FileOperationError(f"Failed to process mill_residues: {str(e)}")

    def mill_concomitant(self, cases: List[Dict[str, Any]], factor: str, effect: str) -> Dict[str, Any]:
        """
        Analyze correlation between factor and effect variations using Mill's Method of Concomitant Variations.

        Args:
            cases (List[Dict[str, Any]]): List of cases with attributes.
            factor (str): Factor to analyze.
            effect (str): Effect to analyze.

        Returns:
            Dict[str, Any]: Correlation results {'correlation': float, 'pvalue': float}.

        Raises:
            FileOperationError: If processing fails.
        """
        try:
            factor_vals = [case["attrs"].get(factor, 0) for case in cases]
            effect_vals = [case["attrs"].get(effect, 0) for case in cases]
            if len(factor_vals) < 2:
                return {"correlation": 0.0, "pvalue": 1.0}

            # Convert to numpy arrays to avoid PyTorch compatibility issues
            import numpy as np

            factor_array = np.array(factor_vals, dtype=np.float64)
            effect_array = np.array(effect_vals, dtype=np.float64)

            # Calculate correlation using numpy if scipy fails
            try:
                corr, pval = pearsonr(factor_array, effect_array)
            except (AttributeError, ImportError) as e:
                # Fallback to numpy correlation calculation
                self.logger.warning(f"scipy pearsonr failed ({e}), using numpy fallback")
                corr = np.corrcoef(factor_array, effect_array)[0, 1]
                # Simple p-value approximation (not statistically rigorous but
                # functional)
                n = len(factor_array)
                if n <= 2:
                    pval = 1.0
                else:
                    # Approximate p-value using t-distribution
                    t_stat = corr * np.sqrt((n - 2) / (1 - corr**2 + 1e-10))
                    from scipy.stats import t  # type: ignore[import-untyped]

                    pval = 2 * (1 - t.cdf(abs(t_stat), n - 2))

            return {"correlation": float(corr), "pvalue": float(pval)}
        except Exception as e:
            raise FileOperationError(f"Failed to process mill_concomitant: {str(e)}")

    def induction(self, examples: List[str], max_keywords: int = 10) -> Dict[str, Any]:
        """
        Generalize patterns from examples using spaCy-based noun phrase clustering.

        Args:
            examples (List[str]): List of example texts.
            max_keywords (int): Maximum number of keywords to extract.

        Returns:
            Dict[str, Any]: Generalized patterns {'patterns': List[str]}.

        Raises:
            FileOperationError: If induction fails.
        """
        try:
            nlp = self._get_spacy()
            docs = [nlp(ex) for ex in examples]
            patterns = []
            for doc in docs:
                patterns.extend([chunk.text.lower() for chunk in doc.noun_chunks])
                patterns.extend([token.lemma_.lower() for token in doc if token.pos_ == "VERB"])
            counter = Counter(patterns)
            common = [word for word, count in counter.most_common() if count > 1][:max_keywords]
            return {"patterns": common}
        except Exception as e:
            raise FileOperationError(f"Failed to process induction: {str(e)}")

    def deduction(self, premises: List[str], conclusion: Optional[str]) -> Dict[str, Any]:
        """
        Validate if conclusion logically follows premises using spaCy dependency parsing.

        Args:
            premises (List[str]): List of premise statements.
            conclusion (Optional[str]): Conclusion to validate.

        Returns:
            Dict[str, Any]: Validation result {'valid': bool, 'conclusion': str, 'reason': str}.

        Raises:
            FileOperationError: If deduction fails.
        """
        try:
            nlp = self._get_spacy()
            premises_docs = [nlp(p) for p in premises]
            conclusion_doc = nlp(conclusion) if conclusion else None
            if not conclusion_doc:
                return {
                    "valid": False,
                    "conclusion": None,
                    "reason": "No conclusion provided",
                }
            premise_entities: Set[str] = set()
            premise_predicates: Set[str] = set()
            for doc in premises_docs:
                premise_entities.update(ent.text.lower() for ent in doc.ents)
                premise_predicates.update(token.lemma_.lower() for token in doc if token.pos_ == "VERB")
            conclusion_entities = set(ent.text.lower() for ent in conclusion_doc.ents)
            conclusion_predicates = set(token.lemma_.lower() for token in conclusion_doc if token.pos_ == "VERB")
            entities_valid = conclusion_entities.issubset(premise_entities)
            predicates_valid = conclusion_predicates.issubset(premise_predicates)
            valid = entities_valid and predicates_valid
            reason = (
                "Conclusion matches premise patterns."
                if valid
                else f"Conclusion contains unmatched {'entities' if not entities_valid else ''} "
                f"{'and ' if not entities_valid and not predicates_valid else ''}"
                f"{'predicates' if not predicates_valid else ''}."
            )
            return {"valid": valid, "conclusion": conclusion, "reason": reason}
        except Exception as e:
            raise FileOperationError(f"Failed to process deduction: {str(e)}")

    def summarize(self, text: str, max_length: int = 150, language: Optional[str] = None) -> str:
        """
        Summarize text using spaCy-based sentence ranking.

        Args:
            text (str): Text to summarize.
            max_length (int): Maximum length of the summary.
            language (Optional[str]): Language of the text.

        Returns:
            str: Summarized text.

        Raises:
            FileOperationError: If summarization fails.
        """
        try:
            nlp = self._get_spacy()
            doc = nlp(text)
            sentences = [sent.text for sent in doc.sents]
            if not sentences:
                return ""
            keywords = [token.lemma_.lower() for token in doc if token.pos_ in ("NOUN", "VERB", "ADJ") and not token.is_stop]
            keyword_freq = Counter(keywords)
            scores = []
            for sent in sentences:
                sent_doc = nlp(sent)
                sent_keywords = [token.lemma_.lower() for token in sent_doc if token.pos_ in ("NOUN", "VERB", "ADJ")]
                score = sum(keyword_freq.get(k, 0) for k in sent_keywords) / (len(sent_keywords) + 1)
                scores.append((sent, score))
            scores.sort(key=lambda x: x[1], reverse=True)
            selected = [sent for sent, _ in scores[: max(1, max_length // 50)]]
            summary = " ".join(selected)
            words = summary.split()
            if len(words) > max_length:
                summary = " ".join(words[:max_length]) + "..."
            return summary
        except Exception as e:
            raise FileOperationError(f"Failed to process summarize: {str(e)}")
