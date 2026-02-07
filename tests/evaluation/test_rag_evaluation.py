"""
RAG Evaluation Tests

Tests the Retrieval-Augmented Generation system:
- Search accuracy
- Embedding quality
- Answer relevance
"""

import numpy as np
import pytest

from app.services.rag_evaluator import RAGEvaluationResult, RAGEvaluator
from app.utils.metrics_collector import MetricsCollector


class TestRAGEvaluation:
    """Test suite for RAG evaluation metrics."""

    def setup_method(self):
        """Setup for each test."""
        self.metrics = MetricsCollector()
        self.evaluator = RAGEvaluator()

    def test_precision_at_k(self):
        """Test Precision@K calculation."""
        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        relevant = ["doc1", "doc3", "doc6"]

        # Precision@3: 2 relevant out of 3 retrieved = 0.667
        p_at_3 = self.evaluator.precision_at_k(retrieved, relevant, k=3)
        assert 0.66 < p_at_3 < 0.67

        # Precision@5: 2 relevant out of 5 retrieved = 0.4
        p_at_5 = self.evaluator.precision_at_k(retrieved, relevant, k=5)
        assert p_at_5 == 0.4

        self.metrics.record_metric("precision_at_3", p_at_3, "ratio")
        self.metrics.record_metric("precision_at_5", p_at_5, "ratio")

    def test_recall_at_k(self):
        """Test Recall@K calculation."""
        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        relevant = ["doc1", "doc3", "doc6"]

        # Recall@3: 2 found out of 3 relevant = 0.667
        r_at_3 = self.evaluator.recall_at_k(retrieved, relevant, k=3)
        assert 0.66 < r_at_3 < 0.67

        # Recall@5: 2 found out of 3 relevant = 0.667
        r_at_5 = self.evaluator.recall_at_k(retrieved, relevant, k=5)
        assert 0.66 < r_at_5 < 0.67

        self.metrics.record_metric("recall_at_3", r_at_3, "ratio")
        self.metrics.record_metric("recall_at_5", r_at_5, "ratio")

    def test_mean_reciprocal_rank(self):
        """Test MRR calculation."""
        # Query 1: First relevant at position 1
        retrieved_1 = ["doc1", "doc2", "doc3"]
        relevant_1 = ["doc1"]

        # Query 2: First relevant at position 3
        retrieved_2 = ["doc4", "doc5", "doc6"]
        relevant_2 = ["doc6"]

        # Query 3: No relevant found
        retrieved_3 = ["doc7", "doc8"]
        relevant_3 = ["doc9"]

        mrr = self.evaluator.mean_reciprocal_rank(
            [retrieved_1, retrieved_2, retrieved_3],
            [relevant_1, relevant_2, relevant_3],
        )

        # MRR = (1/1 + 1/3 + 0) / 3 = 0.444
        assert 0.44 < mrr < 0.45

        self.metrics.record_metric("mrr", mrr, "score")

    def test_cosine_similarity(self):
        """Test cosine similarity calculation."""
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([1.0, 0.0, 0.0])
        vec3 = np.array([0.0, 1.0, 0.0])

        # Identical vectors
        sim_identical = self.evaluator.cosine_similarity(vec1, vec2)
        assert sim_identical == 1.0

        # Orthogonal vectors
        sim_orthogonal = self.evaluator.cosine_similarity(vec1, vec3)
        assert sim_orthogonal == 0.0

        # Opposite vectors
        vec4 = np.array([-1.0, 0.0, 0.0])
        sim_opposite = self.evaluator.cosine_similarity(vec1, vec4)
        assert sim_opposite == -1.0

    def test_embedding_coherence(self):
        """Test embedding coherence measurement."""
        # Create clustered embeddings
        cluster1 = [
            np.array([1.0, 0.0, 0.0]),
            np.array([0.9, 0.1, 0.0]),
            np.array([0.8, 0.2, 0.0]),
        ]

        cluster2 = [
            np.array([0.0, 1.0, 0.0]),
            np.array([0.1, 0.9, 0.0]),
            np.array([0.0, 0.8, 0.2]),
        ]

        all_embeddings = cluster1 + cluster2
        labels = [0, 0, 0, 1, 1, 1]

        coherence = self.evaluator.embedding_coherence(all_embeddings, labels)

        # Should have high coherence (vectors in same cluster are similar)
        assert coherence > 0.7

        self.metrics.record_metric("embedding_coherence", coherence, "score")

    def test_simple_bleu(self):
        """Test simple BLEU score."""
        reference = "the quick brown fox jumps over the lazy dog"

        # Perfect match
        candidate1 = "the quick brown fox jumps over the lazy dog"
        score1 = self.evaluator.simple_bleu(reference, candidate1)
        assert score1 == 1.0

        # Partial match
        candidate2 = "the quick brown cat jumps over"
        score2 = self.evaluator.simple_bleu(reference, candidate2)
        assert 0.5 < score2 < 1.0

        # No match
        candidate3 = "completely different sentence"
        score3 = self.evaluator.simple_bleu(reference, candidate3)
        assert score3 == 0.0

    def test_full_rag_evaluation(self):
        """Test complete RAG evaluation pipeline."""
        # Simulate search results
        queries = ["query1", "query2", "query3"]

        retrieved_results = [
            ["doc1", "doc2", "doc3", "doc4", "doc5"],
            ["doc6", "doc7", "doc8", "doc9", "doc10"],
            ["doc11", "doc12", "doc13", "doc14", "doc15"],
        ]

        ground_truth = [["doc1", "doc3"], ["doc7", "doc10"], ["doc11"]]

        retrieval_times = [0.05, 0.08, 0.06]  # seconds

        result = self.evaluator.evaluate_rag_system(
            queries, retrieved_results, ground_truth, retrieval_times
        )

        assert isinstance(result, RAGEvaluationResult)
        assert result.total_queries == 3
        assert result.mrr > 0
        assert result.retrieval_latency_ms > 0

        # Record all metrics
        for k, precision in result.precision_at_k.items():
            self.metrics.record_metric(f"precision_at_{k}", precision, "ratio")

        for k, recall in result.recall_at_k.items():
            self.metrics.record_metric(f"recall_at_{k}", recall, "ratio")

        self.metrics.record_metric("mrr", result.mrr, "score")
        self.metrics.record_metric(
            "retrieval_latency", result.retrieval_latency_ms, "ms"
        )

    @pytest.mark.performance
    def test_evaluation_performance(self):
        """Test that RAG evaluation is fast."""
        # Generate large dataset
        queries = [f"query_{i}" for i in range(100)]
        retrieved_results = [[f"doc_{j}" for j in range(10)] for _ in range(100)]
        ground_truth = [[f"doc_{j}" for j in range(2)] for _ in range(100)]

        self.metrics.start_timer("rag_evaluation_100_queries")

        result = self.evaluator.evaluate_rag_system(
            queries, retrieved_results, ground_truth
        )

        duration = self.metrics.end_timer("rag_evaluation_100_queries")

        # Should complete in reasonable time
        assert duration < 5.0, f"Evaluation too slow: {duration}s"
        assert result.total_queries == 100
