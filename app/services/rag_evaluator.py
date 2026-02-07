"""
RAG Evaluation Framework

Comprehensive evaluation metrics for Retrieval-Augmented Generation:
- Retrieval quality (Precision, Recall, MRR)
- Answer relevance (BLEU, ROUGE, semantic similarity)
- Embedding quality
"""

import logging
from dataclasses import dataclass
from typing import Dict, List

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RAGEvaluationResult:
    """Results from RAG evaluation."""

    precision_at_k: Dict[int, float]
    recall_at_k: Dict[int, float]
    mrr: float  # Mean Reciprocal Rank
    embedding_coherence: float
    answer_relevance: float
    retrieval_latency_ms: float
    total_queries: int


class RAGEvaluator:
    """Evaluates RAG system performance."""

    @staticmethod
    def precision_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
        """
        Calculate Precision@K.

        Args:
            retrieved: List of retrieved document IDs (ordered by relevance)
            relevant: List of ground truth relevant document IDs
            k: Number of top results to consider

        Returns:
            float: Precision@K score (0-1)
        """
        if k == 0 or not retrieved:
            return 0.0

        top_k = retrieved[:k]
        relevant_set = set(relevant)

        num_relevant = sum(1 for doc_id in top_k if doc_id in relevant_set)
        return num_relevant / k

    @staticmethod
    def recall_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
        """
        Calculate Recall@K.

        Args:
            retrieved: List of retrieved document IDs
            relevant: List of ground truth relevant document IDs
            k: Number of top results to consider

        Returns:
            float: Recall@K score (0-1)
        """
        if not relevant or not retrieved:
            return 0.0

        top_k = retrieved[:k]
        relevant_set = set(relevant)

        num_relevant = sum(1 for doc_id in top_k if doc_id in relevant_set)
        return num_relevant / len(relevant_set)

    @staticmethod
    def mean_reciprocal_rank(
        retrieved_lists: List[List[str]], relevant_lists: List[List[str]]
    ) -> float:
        """
        Calculate Mean Reciprocal Rank across multiple queries.

        Args:
            retrieved_lists: List of retrieved document lists (one per query)
            relevant_lists: List of relevant document lists (one per query)

        Returns:
            float: MRR score
        """
        if not retrieved_lists or not relevant_lists:
            return 0.0

        reciprocal_ranks = []

        for retrieved, relevant in zip(retrieved_lists, relevant_lists):
            relevant_set = set(relevant)

            # Find rank of first relevant document
            for rank, doc_id in enumerate(retrieved, start=1):
                if doc_id in relevant_set:
                    reciprocal_ranks.append(1.0 / rank)
                    break
            else:
                reciprocal_ranks.append(0.0)  # No relevant document found

        return (
            sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0
        )

    @staticmethod
    def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        if vec1 is None or vec2 is None:
            return 0.0

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    @staticmethod
    def embedding_coherence(
        embeddings: List[np.ndarray], labels: List[str] = None
    ) -> float:
        """
        Measure embedding quality via intra-cluster coherence.

        Args:
            embeddings: List of embedding vectors
            labels: Optional cluster labels

        Returns:
            float: Average cosine similarity within clusters (0-1)
        """
        if not embeddings or len(embeddings) < 2:
            return 0.0

        if labels is None:
            # Treat all as one cluster
            labels = [0] * len(embeddings)

        # Group by label
        clusters = {}
        for emb, label in zip(embeddings, labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(emb)

        # Calculate average intra-cluster similarity
        coherence_scores = []

        for cluster_embs in clusters.values():
            if len(cluster_embs) < 2:
                continue

            # Pairwise similarities
            similarities = []
            for i in range(len(cluster_embs)):
                for j in range(i + 1, len(cluster_embs)):
                    sim = RAGEvaluator.cosine_similarity(
                        cluster_embs[i], cluster_embs[j]
                    )
                    similarities.append(sim)

            if similarities:
                coherence_scores.append(np.mean(similarities))

        return np.mean(coherence_scores) if coherence_scores else 0.0

    @staticmethod
    def simple_bleu(reference: str, candidate: str) -> float:
        """
        Simple BLEU-like score (unigram overlap).

        Args:
            reference: Ground truth text
            candidate: Generated text

        Returns:
            float: Overlap score (0-1)
        """
        ref_tokens = set(reference.lower().split())
        cand_tokens = set(candidate.lower().split())

        if not ref_tokens or not cand_tokens:
            return 0.0

        overlap = len(ref_tokens & cand_tokens)
        return overlap / len(cand_tokens)

    @staticmethod
    def evaluate_rag_system(
        queries: List[str],
        retrieved_results: List[List[str]],
        ground_truth: List[List[str]],
        retrieval_times: List[float] = None,
    ) -> RAGEvaluationResult:
        """
        Comprehensive RAG evaluation.

        Args:
            queries: List of search queries
            retrieved_results: Retrieved document IDs for each query
            ground_truth: Relevant document IDs for each query
            retrieval_times: Optional retrieval latencies

        Returns:
            RAGEvaluationResult with all metrics
        """
        # Precision and Recall at different K values
        k_values = [1, 3, 5, 10]
        precision_at_k = {}
        recall_at_k = {}

        for k in k_values:
            precisions = [
                RAGEvaluator.precision_at_k(retrieved, relevant, k)
                for retrieved, relevant in zip(retrieved_results, ground_truth)
            ]
            recalls = [
                RAGEvaluator.recall_at_k(retrieved, relevant, k)
                for retrieved, relevant in zip(retrieved_results, ground_truth)
            ]

            precision_at_k[k] = np.mean(precisions) if precisions else 0.0
            recall_at_k[k] = np.mean(recalls) if recalls else 0.0

        # MRR
        mrr = RAGEvaluator.mean_reciprocal_rank(retrieved_results, ground_truth)

        # Average retrieval latency
        avg_latency = np.mean(retrieval_times) * 1000 if retrieval_times else 0.0

        return RAGEvaluationResult(
            precision_at_k=precision_at_k,
            recall_at_k=recall_at_k,
            mrr=mrr,
            embedding_coherence=0.0,  # Requires embeddings
            answer_relevance=0.0,  # Requires generated answers
            retrieval_latency_ms=avg_latency,
            total_queries=len(queries),
        )
