"""
Text Similarity Utilities

Provides various text similarity and matching functions for knowledge graph operations.
Includes BM25, Jaccard, cosine similarity, Levenshtein distance, and fuzzy matching.
"""

import re
import math
from typing import List, Optional, Tuple, Callable, Any
from collections import Counter
from difflib import SequenceMatcher


class BM25Scorer:
    """
    BM25 (Best Matching 25) scorer for text similarity

    BM25 is a ranking function used to estimate the relevance of documents
    to a given search query. It's an improvement over TF-IDF.

    Example::

        scorer = BM25Scorer(corpus=[
            "The quick brown fox jumps over the lazy dog",
            "A quick brown dog jumps over a lazy fox",
            "The lazy dog sleeps all day"
        ])

        scores = scorer.score("quick brown fox")
        # Returns scores for each document in corpus
    """

    def __init__(
        self,
        corpus: List[str],
        k1: float = 1.5,
        b: float = 0.75,
        tokenizer: Optional[Callable[[str], List[str]]] = None,
    ):
        """
        Initialize BM25 scorer

        Args:
            corpus: List of documents to score against
            k1: Term frequency saturation parameter (default: 1.5)
            b: Length normalization parameter (default: 0.75)
            tokenizer: Optional tokenizer function (default: simple word split)
        """
        self.k1 = k1
        self.b = b
        self.tokenizer = tokenizer or self._default_tokenizer

        # Tokenize corpus
        self.documents = [self.tokenizer(doc) for doc in corpus]
        self.doc_count = len(self.documents)

        # Calculate document lengths
        self.doc_lengths = [len(doc) for doc in self.documents]
        self.avg_doc_length = sum(self.doc_lengths) / self.doc_count if self.doc_count > 0 else 0

        # Build term frequency dictionary
        self.term_freqs = []
        self.doc_freqs: Counter[str] = Counter()

        for doc in self.documents:
            tf = Counter(doc)
            self.term_freqs.append(tf)
            for term in set(doc):
                self.doc_freqs[term] += 1

        # Calculate IDF (Inverse Document Frequency)
        self.idf = {}
        for term, df in self.doc_freqs.items():
            self.idf[term] = math.log((self.doc_count - df + 0.5) / (df + 0.5) + 1.0)

    def _default_tokenizer(self, text: str) -> List[str]:
        """Default tokenizer: lowercase and split on whitespace"""
        return re.findall(r"\w+", text.lower())

    def score(self, query: str) -> List[float]:
        """
        Score documents against query

        Args:
            query: Query string

        Returns:
            List of BM25 scores for each document
        """
        query_terms = self.tokenizer(query)
        scores = []

        for i, doc in enumerate(self.documents):
            score = 0.0
            doc_length = self.doc_lengths[i]
            term_freq = self.term_freqs[i]

            for term in query_terms:
                if term in term_freq:
                    tf = term_freq[term]
                    idf = self.idf.get(term, 0.0)

                    # BM25 formula
                    numerator = idf * tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * (doc_length / self.avg_doc_length))
                    score += numerator / denominator

            scores.append(score)

        return scores

    def get_top_n(self, query: str, n: int = 10) -> List[Tuple[int, float]]:
        """
        Get top N documents by BM25 score

        Args:
            query: Query string
            n: Number of top results to return

        Returns:
            List of (document_index, score) tuples, sorted by score descending
        """
        scores = self.score(query)
        indexed_scores = [(i, score) for i, score in enumerate(scores)]
        indexed_scores.sort(key=lambda x: x[1], reverse=True)
        return indexed_scores[:n]


def jaccard_similarity(set1: set, set2: set) -> float:
    """
    Calculate Jaccard similarity between two sets

    Jaccard similarity = (size of intersection) / (size of union)

    Args:
        set1: First set
        set2: Second set

    Returns:
        Jaccard similarity score (0.0 to 1.0)
    """
    if not set1 and not set2:
        return 1.0

    intersection = len(set1 & set2)
    union = len(set1 | set2)

    if union == 0:
        return 0.0

    return intersection / union


def jaccard_similarity_text(text1: str, text2: str, tokenizer: Optional[Callable[[str], Any]] = None) -> float:
    """
    Calculate Jaccard similarity between two text strings

    Args:
        text1: First text string
        text2: Second text string
        tokenizer: Optional tokenizer function (default: word split)

    Returns:
        Jaccard similarity score (0.0 to 1.0)
    """
    if tokenizer is None:

        def tokenizer(t):
            return set(re.findall(r"\w+", t.lower()))

    else:
        # Wrap tokenizer to ensure it returns a set
        original_tokenizer = tokenizer

        def tokenizer(t):
            return set(original_tokenizer(t))

    set1 = tokenizer(text1)
    set2 = tokenizer(text2)

    return jaccard_similarity(set1, set2)


def cosine_similarity_text(text1: str, text2: str, tokenizer: Optional[Callable[[str], List[str]]] = None) -> float:
    """
    Calculate cosine similarity between two text strings

    Cosine similarity measures the cosine of the angle between two vectors
    in a multi-dimensional space. For text, vectors are TF-IDF representations.

    Args:
        text1: First text string
        text2: Second text string
        tokenizer: Optional tokenizer function (default: word split)

    Returns:
        Cosine similarity score (0.0 to 1.0)
    """
    if tokenizer is None:

        def tokenizer(t):
            return re.findall(r"\w+", t.lower())

    tokens1 = tokenizer(text1)
    tokens2 = tokenizer(text2)

    # Build vocabulary
    vocab = set(tokens1) | set(tokens2)

    if not vocab:
        return 1.0 if not text1 and not text2 else 0.0

    # Create term frequency vectors
    tf1 = Counter(tokens1)
    tf2 = Counter(tokens2)

    # Calculate dot product and magnitudes
    dot_product = sum(tf1.get(term, 0) * tf2.get(term, 0) for term in vocab)
    magnitude1 = math.sqrt(sum(tf1.get(term, 0) ** 2 for term in vocab))
    magnitude2 = math.sqrt(sum(tf2.get(term, 0) ** 2 for term in vocab))

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    similarity = dot_product / (magnitude1 * magnitude2)
    # Handle floating point precision issues
    return min(1.0, max(0.0, similarity))


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate Levenshtein distance (edit distance) between two strings

    Levenshtein distance is the minimum number of single-character edits
    (insertions, deletions, or substitutions) required to change one string
    into another.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Levenshtein distance (0 = identical, higher = more different)
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    # Use dynamic programming
    previous_row = list(range(len(s2) + 1))

    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def normalized_levenshtein_similarity(s1: str, s2: str) -> float:
    """
    Calculate normalized Levenshtein similarity (0.0 to 1.0)

    Args:
        s1: First string
        s2: Second string

    Returns:
        Normalized similarity score (1.0 = identical, 0.0 = completely different)
    """
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0

    distance = levenshtein_distance(s1, s2)
    return 1.0 - (distance / max_len)


def fuzzy_match(
    query: str,
    candidates: List[str],
    threshold: float = 0.6,
    method: str = "jaccard",
) -> List[Tuple[str, float]]:
    """
    Find fuzzy matches for a query string in a list of candidates

    Args:
        query: Query string to match
        candidates: List of candidate strings
        threshold: Minimum similarity threshold (0.0 to 1.0)
        method: Similarity method ("jaccard", "cosine", "levenshtein", "ratio")

    Returns:
        List of (candidate, similarity_score) tuples above threshold,
        sorted by score descending
    """
    results = []

    for candidate in candidates:
        if method == "jaccard":
            score = jaccard_similarity_text(query, candidate)
        elif method == "cosine":
            score = cosine_similarity_text(query, candidate)
        elif method == "levenshtein":
            score = normalized_levenshtein_similarity(query, candidate)
        elif method == "ratio":
            # Use SequenceMatcher ratio (built-in fuzzy matching)
            score = SequenceMatcher(None, query.lower(), candidate.lower()).ratio()
        else:
            raise ValueError(f"Unknown method: {method}. Use 'jaccard', 'cosine', 'levenshtein', or 'ratio'")

        if score >= threshold:
            results.append((candidate, score))

    # Sort by score descending
    results.sort(key=lambda x: x[1], reverse=True)
    return results


class TextSimilarity:
    """
    Convenience class for text similarity operations

    Provides a unified interface for various text similarity methods.

    Example::

        similarity = TextSimilarity()

        # Jaccard similarity
        score = similarity.jaccard("hello world", "world hello")

        # Cosine similarity
        score = similarity.cosine("machine learning", "deep learning")

        # Levenshtein distance
        distance = similarity.levenshtein("kitten", "sitting")

        # Fuzzy matching
        matches = similarity.fuzzy_match(
            "python",
            ["python3", "pyton", "java", "pythn"],
            threshold=0.7
        )
    """

    def __init__(self, tokenizer: Optional[Callable[[str], List[str]]] = None):
        """
        Initialize TextSimilarity

        Args:
            tokenizer: Optional tokenizer function for text processing
        """
        self.tokenizer = tokenizer

    def jaccard(self, text1: str, text2: str) -> float:
        """Calculate Jaccard similarity between two texts"""
        return jaccard_similarity_text(text1, text2, self.tokenizer)

    def cosine(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts"""
        return cosine_similarity_text(text1, text2, self.tokenizer)

    def levenshtein(self, text1: str, text2: str) -> int:
        """Calculate Levenshtein distance between two texts"""
        return levenshtein_distance(text1, text2)

    def levenshtein_similarity(self, text1: str, text2: str) -> float:
        """Calculate normalized Levenshtein similarity"""
        return normalized_levenshtein_similarity(text1, text2)

    def fuzzy_match(
        self,
        query: str,
        candidates: List[str],
        threshold: float = 0.6,
        method: str = "jaccard",
    ) -> List[Tuple[str, float]]:
        """Find fuzzy matches for a query"""
        return fuzzy_match(query, candidates, threshold, method)

    def bm25(self, corpus: List[str], k1: float = 1.5, b: float = 0.75) -> BM25Scorer:
        """Create a BM25 scorer for a corpus"""
        return BM25Scorer(corpus, k1=k1, b=b, tokenizer=self.tokenizer)
