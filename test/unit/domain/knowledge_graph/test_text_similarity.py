"""
Unit tests for text similarity utilities
"""

import pytest
from aiecs.application.knowledge_graph.search.text_similarity import (
    BM25Scorer,
    TextSimilarity,
    jaccard_similarity,
    jaccard_similarity_text,
    cosine_similarity_text,
    levenshtein_distance,
    normalized_levenshtein_similarity,
    fuzzy_match,
)


class TestJaccardSimilarity:
    """Test Jaccard similarity functions"""
    
    def test_jaccard_similarity_identical(self):
        """Test Jaccard similarity with identical sets"""
        set1 = {1, 2, 3}
        set2 = {1, 2, 3}
        assert jaccard_similarity(set1, set2) == 1.0
    
    def test_jaccard_similarity_no_overlap(self):
        """Test Jaccard similarity with no overlap"""
        set1 = {1, 2, 3}
        set2 = {4, 5, 6}
        assert jaccard_similarity(set1, set2) == 0.0
    
    def test_jaccard_similarity_partial_overlap(self):
        """Test Jaccard similarity with partial overlap"""
        set1 = {1, 2, 3}
        set2 = {2, 3, 4}
        # Intersection: {2, 3} = 2, Union: {1, 2, 3, 4} = 4
        assert jaccard_similarity(set1, set2) == 0.5
    
    def test_jaccard_similarity_empty_sets(self):
        """Test Jaccard similarity with empty sets"""
        assert jaccard_similarity(set(), set()) == 1.0
        assert jaccard_similarity({1, 2}, set()) == 0.0
        assert jaccard_similarity(set(), {1, 2}) == 0.0
    
    def test_jaccard_similarity_text_identical(self):
        """Test Jaccard similarity with identical text"""
        text1 = "hello world"
        text2 = "hello world"
        assert jaccard_similarity_text(text1, text2) == 1.0
    
    def test_jaccard_similarity_text_different(self):
        """Test Jaccard similarity with different text"""
        text1 = "hello world"
        text2 = "goodbye universe"
        assert jaccard_similarity_text(text1, text2) == 0.0
    
    def test_jaccard_similarity_text_partial(self):
        """Test Jaccard similarity with partial overlap"""
        text1 = "hello world"
        text2 = "hello python"
        # Common: {"hello"}, All: {"hello", "world", "python"}
        score = jaccard_similarity_text(text1, text2)
        assert 0.0 < score < 1.0
    
    def test_jaccard_similarity_text_case_insensitive(self):
        """Test that Jaccard similarity is case insensitive"""
        text1 = "Hello World"
        text2 = "hello world"
        assert jaccard_similarity_text(text1, text2) == 1.0
    
    def test_jaccard_similarity_text_empty(self):
        """Test Jaccard similarity with empty strings"""
        assert jaccard_similarity_text("", "") == 1.0
        assert jaccard_similarity_text("hello", "") == 0.0


class TestCosineSimilarity:
    """Test cosine similarity functions"""
    
    def test_cosine_similarity_identical(self):
        """Test cosine similarity with identical text"""
        text1 = "hello world"
        text2 = "hello world"
        score = cosine_similarity_text(text1, text2)
        assert abs(score - 1.0) < 1e-10  # Account for floating point precision
    
    def test_cosine_similarity_no_overlap(self):
        """Test cosine similarity with no common words"""
        text1 = "hello world"
        text2 = "goodbye universe"
        assert cosine_similarity_text(text1, text2) == 0.0
    
    def test_cosine_similarity_partial_overlap(self):
        """Test cosine similarity with partial overlap"""
        text1 = "machine learning"
        text2 = "deep learning"
        score = cosine_similarity_text(text1, text2)
        assert 0.0 < score < 1.0
    
    def test_cosine_similarity_empty(self):
        """Test cosine similarity with empty strings"""
        assert cosine_similarity_text("", "") == 1.0
        assert cosine_similarity_text("hello", "") == 0.0
        assert cosine_similarity_text("", "hello") == 0.0
    
    def test_cosine_similarity_case_insensitive(self):
        """Test that cosine similarity is case insensitive"""
        text1 = "Hello World"
        text2 = "hello world"
        score = cosine_similarity_text(text1, text2)
        assert abs(score - 1.0) < 1e-10  # Account for floating point precision
    
    def test_cosine_similarity_different_lengths(self):
        """Test cosine similarity with texts of different lengths"""
        text1 = "hello"
        text2 = "hello world python"
        score = cosine_similarity_text(text1, text2)
        assert 0.0 < score < 1.0


class TestLevenshteinDistance:
    """Test Levenshtein distance functions"""
    
    def test_levenshtein_identical(self):
        """Test Levenshtein distance with identical strings"""
        assert levenshtein_distance("hello", "hello") == 0
    
    def test_levenshtein_one_character(self):
        """Test Levenshtein distance with one character difference"""
        assert levenshtein_distance("kitten", "sitten") == 1  # k -> s
        assert levenshtein_distance("sitten", "sittin") == 1  # e -> i
    
    def test_levenshtein_multiple_changes(self):
        """Test Levenshtein distance with multiple changes"""
        # kitten -> sitting: k->s, e->i, add g
        assert levenshtein_distance("kitten", "sitting") == 3
    
    def test_levenshtein_empty_strings(self):
        """Test Levenshtein distance with empty strings"""
        assert levenshtein_distance("", "") == 0
        assert levenshtein_distance("hello", "") == 5
        assert levenshtein_distance("", "hello") == 5
    
    def test_levenshtein_completely_different(self):
        """Test Levenshtein distance with completely different strings"""
        assert levenshtein_distance("abc", "xyz") == 3
    
    def test_normalized_levenshtein_similarity(self):
        """Test normalized Levenshtein similarity"""
        assert normalized_levenshtein_similarity("hello", "hello") == 1.0
        assert normalized_levenshtein_similarity("hello", "world") < 1.0
        assert normalized_levenshtein_similarity("", "") == 1.0
    
    def test_normalized_levenshtein_similarity_range(self):
        """Test that normalized similarity is between 0 and 1"""
        score = normalized_levenshtein_similarity("kitten", "sitting")
        assert 0.0 <= score <= 1.0


class TestBM25Scorer:
    """Test BM25 scorer"""
    
    def test_bm25_initialization(self):
        """Test BM25 scorer initialization"""
        corpus = [
            "The quick brown fox jumps over the lazy dog",
            "A quick brown dog jumps over a lazy fox",
            "The lazy dog sleeps all day"
        ]
        scorer = BM25Scorer(corpus)
        assert scorer.doc_count == 3
        assert scorer.avg_doc_length > 0
    
    def test_bm25_score_exact_match(self):
        """Test BM25 scoring with exact match"""
        corpus = [
            "The quick brown fox",
            "The lazy dog"
        ]
        scorer = BM25Scorer(corpus)
        scores = scorer.score("quick brown fox")
        
        # First document should have higher score
        assert scores[0] > scores[1]
        assert scores[0] > 0
    
    def test_bm25_score_no_match(self):
        """Test BM25 scoring with no match"""
        corpus = [
            "The quick brown fox",
            "The lazy dog"
        ]
        scorer = BM25Scorer(corpus)
        scores = scorer.score("completely different words")
        
        # All scores should be low or zero
        assert all(s >= 0 for s in scores)
    
    def test_bm25_get_top_n(self):
        """Test BM25 get_top_n method"""
        corpus = [
            "The quick brown fox jumps",
            "The lazy dog sleeps",
            "A quick brown dog runs"
        ]
        scorer = BM25Scorer(corpus)
        top_n = scorer.get_top_n("quick brown", n=2)
        
        assert len(top_n) == 2
        # Results should be sorted by score descending
        assert top_n[0][1] >= top_n[1][1]
        # Indices should be valid
        assert all(0 <= idx < len(corpus) for idx, _ in top_n)
    
    def test_bm25_empty_corpus(self):
        """Test BM25 with empty corpus"""
        scorer = BM25Scorer([])
        assert scorer.doc_count == 0
        scores = scorer.score("test query")
        assert scores == []
    
    def test_bm25_custom_tokenizer(self):
        """Test BM25 with custom tokenizer"""
        def custom_tokenizer(text):
            return text.split()
        
        corpus = ["hello world", "world python"]
        scorer = BM25Scorer(corpus, tokenizer=custom_tokenizer)
        scores = scorer.score("hello")
        assert len(scores) == 2


class TestFuzzyMatch:
    """Test fuzzy matching functions"""
    
    def test_fuzzy_match_jaccard(self):
        """Test fuzzy matching with Jaccard method"""
        query = "python programming"
        candidates = ["python programming", "python code", "java programming", "ruby code"]
        matches = fuzzy_match(query, candidates, threshold=0.1, method="jaccard")
        
        assert len(matches) > 0
        # Results should be sorted by score
        scores = [score for _, score in matches]
        assert scores == sorted(scores, reverse=True)
        # Exact match should have highest score
        assert matches[0][0] == "python programming"
    
    def test_fuzzy_match_cosine(self):
        """Test fuzzy matching with cosine method"""
        query = "machine learning"
        candidates = ["machine learning", "deep learning", "artificial intelligence"]
        matches = fuzzy_match(query, candidates, threshold=0.3, method="cosine")
        
        assert len(matches) > 0
        # Exact match should have highest score
        assert matches[0][0] == "machine learning"
        assert abs(matches[0][1] - 1.0) < 1e-10  # Account for floating point precision
    
    def test_fuzzy_match_levenshtein(self):
        """Test fuzzy matching with Levenshtein method"""
        query = "python"
        candidates = ["python", "pyton", "pythn", "java"]
        matches = fuzzy_match(query, candidates, threshold=0.5, method="levenshtein")
        
        assert len(matches) > 0
        # Exact match should have highest score
        assert matches[0][0] == "python"
        assert matches[0][1] == 1.0
    
    def test_fuzzy_match_ratio(self):
        """Test fuzzy matching with ratio method"""
        query = "python"
        candidates = ["python", "pyton", "pythn", "java"]
        matches = fuzzy_match(query, candidates, threshold=0.5, method="ratio")
        
        assert len(matches) > 0
        # Exact match should have highest score
        assert matches[0][0] == "python"
        assert matches[0][1] == 1.0
    
    def test_fuzzy_match_threshold(self):
        """Test fuzzy matching threshold filtering"""
        query = "python"
        candidates = ["python", "pyton", "java", "ruby"]
        matches = fuzzy_match(query, candidates, threshold=0.9, method="jaccard")
        
        # With high threshold, should only get very similar matches
        assert len(matches) <= len(candidates)
        assert all(score >= 0.9 for _, score in matches)
    
    def test_fuzzy_match_no_matches(self):
        """Test fuzzy matching with no matches above threshold"""
        query = "python"
        candidates = ["java", "ruby", "javascript"]
        matches = fuzzy_match(query, candidates, threshold=0.9, method="jaccard")
        
        # Should return empty list if no matches above threshold
        assert len(matches) == 0
    
    def test_fuzzy_match_invalid_method(self):
        """Test fuzzy matching with invalid method"""
        query = "python"
        candidates = ["python"]
        
        with pytest.raises(ValueError, match="Unknown method"):
            fuzzy_match(query, candidates, method="invalid")


class TestTextSimilarity:
    """Test TextSimilarity convenience class"""
    
    def test_text_similarity_jaccard(self):
        """Test TextSimilarity jaccard method"""
        similarity = TextSimilarity()
        score = similarity.jaccard("hello world", "world hello")
        assert 0.0 <= score <= 1.0
        assert score == 1.0  # Same words, different order
    
    def test_text_similarity_cosine(self):
        """Test TextSimilarity cosine method"""
        similarity = TextSimilarity()
        score = similarity.cosine("machine learning", "deep learning")
        assert 0.0 <= score <= 1.0
        assert score > 0.0  # Should have some similarity
    
    def test_text_similarity_levenshtein(self):
        """Test TextSimilarity levenshtein method"""
        similarity = TextSimilarity()
        distance = similarity.levenshtein("kitten", "sitting")
        assert distance >= 0
        assert distance == 3
    
    def test_text_similarity_levenshtein_similarity(self):
        """Test TextSimilarity levenshtein_similarity method"""
        similarity = TextSimilarity()
        score = similarity.levenshtein_similarity("kitten", "sitting")
        assert 0.0 <= score <= 1.0
    
    def test_text_similarity_fuzzy_match(self):
        """Test TextSimilarity fuzzy_match method"""
        similarity = TextSimilarity()
        # Use levenshtein method which works better for single-word fuzzy matching
        matches = similarity.fuzzy_match(
            "python",
            ["python", "pyton", "pythn", "java"],
            threshold=0.5,
            method="levenshtein"
        )
        assert len(matches) > 0
        assert all(score >= 0.5 for _, score in matches)
        # Exact match should have highest score
        assert matches[0][0] == "python"
    
    def test_text_similarity_bm25(self):
        """Test TextSimilarity bm25 method"""
        similarity = TextSimilarity()
        corpus = ["hello world", "world python"]
        scorer = similarity.bm25(corpus)
        
        assert isinstance(scorer, BM25Scorer)
        scores = scorer.score("hello")
        assert len(scores) == 2
    
    def test_text_similarity_custom_tokenizer(self):
        """Test TextSimilarity with custom tokenizer"""
        def custom_tokenizer(text):
            return text.split()  # Returns list
        
        similarity = TextSimilarity(tokenizer=custom_tokenizer)
        score = similarity.jaccard("hello world", "world hello")
        # jaccard_similarity_text will convert list to set automatically
        assert score == 1.0


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_jaccard_similarity_unicode(self):
        """Test Jaccard similarity with Unicode characters"""
        text1 = "café"
        text2 = "cafe"
        score = jaccard_similarity_text(text1, text2)
        assert 0.0 <= score <= 1.0
    
    def test_cosine_similarity_special_characters(self):
        """Test cosine similarity with special characters"""
        text1 = "hello-world"
        text2 = "hello world"
        score = cosine_similarity_text(text1, text2)
        assert 0.0 <= score <= 1.0
    
    def test_levenshtein_unicode(self):
        """Test Levenshtein distance with Unicode"""
        distance = levenshtein_distance("café", "cafe")
        assert distance >= 0
    
    def test_bm25_single_word_documents(self):
        """Test BM25 with single-word documents"""
        corpus = ["hello", "world", "python"]
        scorer = BM25Scorer(corpus)
        scores = scorer.score("hello")
        assert scores[0] > scores[1]  # "hello" should score highest
    
    def test_bm25_repeated_words(self):
        """Test BM25 with repeated words"""
        corpus = ["hello hello hello", "world"]
        scorer = BM25Scorer(corpus)
        scores = scorer.score("hello")
        assert scores[0] > scores[1]
    
    def test_fuzzy_match_empty_candidates(self):
        """Test fuzzy matching with empty candidates list"""
        matches = fuzzy_match("python", [], threshold=0.5)
        assert matches == []
    
    def test_fuzzy_match_empty_query(self):
        """Test fuzzy matching with empty query"""
        candidates = ["python", "java"]
        matches = fuzzy_match("", candidates, threshold=0.0)
        # Should handle empty query gracefully
        assert isinstance(matches, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

