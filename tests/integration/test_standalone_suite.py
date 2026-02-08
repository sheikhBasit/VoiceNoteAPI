"""
Standalone Test Suite - Audio Processing & Metrics

Tests that don't require full app imports.
"""

import os
import sys

import numpy as np
import pytest

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.rag_evaluator import RAGEvaluator
from app.services.audio_service import AudioService as AudioChunker
from app.utils.metrics_collector import MetricsCollector

ASSETS_DIR = "tests/assets/audio"


class TestAudioChunkerStandalone:
    """Standalone tests for AudioChunker."""

    def test_validation_empty_file(self):
        """Test empty file validation."""
        empty_path = os.path.join(ASSETS_DIR, "worst_case/empty.wav")
        if os.path.exists(empty_path):
            is_valid, error = AudioChunker.validate_audio_file(empty_path)
            assert not is_valid
            assert len(error) > 0

    def test_validation_nonexistent_file(self):
        """Test nonexistent file validation."""
        is_valid, error = AudioChunker.validate_audio_file("/nonexistent/file.wav")
        assert not is_valid
        assert "exist" in error.lower()

    def test_should_chunk_logic(self):
        """Test chunking decision logic."""
        long_audio = os.path.join(ASSETS_DIR, "worst_case/very_long_10min.wav")
        if os.path.exists(long_audio):
            should_chunk = AudioChunker.should_chunk(long_audio, max_duration_minutes=5)
            assert should_chunk

    def test_merge_transcripts(self):
        """Test transcript merging."""
        transcripts = ["First part.", "Second part.", "Third part."]
        merged = AudioChunker.merge_transcripts(transcripts)
        assert "First part" in merged
        assert "Second part" in merged
        assert "Third part" in merged


class TestMetricsCollectorStandalone:
    """Standalone tests for MetricsCollector."""

    def test_timer_basic(self):
        """Test basic timer functionality."""
        collector = MetricsCollector()
        collector.start_timer("test")
        import time

        time.sleep(0.1)
        duration = collector.end_timer("test")
        assert duration >= 0.1

    def test_record_metric(self):
        """Test metric recording."""
        collector = MetricsCollector()
        collector.record_metric("test_metric", 42.0, "units")
        summary = collector.get_summary()
        assert "test_metric" in summary
        assert summary["test_metric"]["mean"] == 42.0

    def test_memory_snapshot(self):
        """Test memory snapshot."""
        collector = MetricsCollector()
        collector.record_memory_snapshot("test")
        summary = collector.get_summary()
        assert "memory_test" in summary


class TestRAGEvaluatorStandalone:
    """Standalone tests for RAG Evaluator."""

    def test_precision_at_k(self):
        """Test Precision@K."""
        evaluator = RAGEvaluator()
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc1", "doc3"]

        p = evaluator.precision_at_k(retrieved, relevant, k=3)
        assert p == 2 / 3

    def test_recall_at_k(self):
        """Test Recall@K."""
        evaluator = RAGEvaluator()
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc1", "doc3", "doc4"]

        r = evaluator.recall_at_k(retrieved, relevant, k=3)
        assert r == 2 / 3

    def test_mrr(self):
        """Test Mean Reciprocal Rank."""
        evaluator = RAGEvaluator()
        retrieved_lists = [["doc1", "doc2"], ["doc3", "doc4"]]
        relevant_lists = [["doc1"], ["doc4"]]

        mrr = evaluator.mean_reciprocal_rank(retrieved_lists, relevant_lists)
        assert mrr == (1 / 1 + 1 / 2) / 2

    def test_cosine_similarity(self):
        """Test cosine similarity."""
        evaluator = RAGEvaluator()
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([1.0, 0.0, 0.0])

        sim = evaluator.cosine_similarity(vec1, vec2)
        assert sim == 1.0


class TestSystemRobustness:
    """Test system robustness and error handling."""

    def test_graceful_handling_corrupted_audio(self):
        """Test system doesn't crash on corrupted audio."""
        corrupted_path = os.path.join(ASSETS_DIR, "worst_case/corrupted.wav")
        if os.path.exists(corrupted_path):
            try:
                is_valid, error = AudioChunker.validate_audio_file(corrupted_path)
                # Should not crash
                assert True
            except Exception as e:
                pytest.fail(f"System crashed on corrupted audio: {e}")

    def test_graceful_handling_wrong_format(self):
        """Test system doesn't crash on wrong format."""
        wrong_format = os.path.join(ASSETS_DIR, "worst_case/wrong_format.wav")
        if os.path.exists(wrong_format):
            try:
                is_valid, error = AudioChunker.validate_audio_file(wrong_format)
                assert not is_valid
            except Exception as e:
                pytest.fail(f"System crashed on wrong format: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
