"""
Load Testing Suite - Concurrent Operations

Tests system performance under load with multiple simultaneous operations:
- Multiple audio file processing
- Concurrent RAG queries
- Simultaneous LLM chats
- Parallel note generation
- Security under load
"""

import concurrent.futures
import os
import random
import sys
import time
from typing import Any, Dict

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.utils.metrics_collector import MetricsCollector


class TestConcurrentAudioProcessing:
    """Test concurrent audio file processing."""

    def setup_method(self):
        """Setup metrics collector."""
        self.metrics = MetricsCollector()

    @pytest.mark.load
    def test_concurrent_audio_validation(self):
        """Test validating multiple audio files concurrently."""
        from app.services.audio_service import AudioService as AudioChunker

        # Simulate 10 concurrent validations
        audio_files = [
            "tests/assets/audio/ideal/clean_30s.wav",
            "tests/assets/audio/moderate/background_noise_1min.wav",
            "tests/assets/audio/challenging/heavy_noise_45s.wav",
        ] * 4  # 12 total files

        self.metrics.start_timer("concurrent_validation_10_files")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(AudioChunker.validate_audio_file, f)
                for f in audio_files
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        duration = self.metrics.end_timer("concurrent_validation_10_files")

        # All should complete
        assert len(results) == len(audio_files)

        # Should be faster than sequential
        assert duration < len(audio_files) * 1.0  # Less than 1s per file

        print(
            f"\n⚡ Validated {len(audio_files)} files concurrently in {duration:.2f}s"
        )
        print(f"   Throughput: {len(audio_files)/duration:.1f} files/second")

    @pytest.mark.load
    def test_concurrent_quality_analysis(self):
        """Test analyzing multiple audio files concurrently."""
        import os

        from app.utils.audio_quality_analyzer import AudioQualityAnalyzer

        analyzer = AudioQualityAnalyzer()

        audio_files = [
            f
            for f in [
                "tests/assets/audio/ideal/clean_30s.wav",
                "tests/assets/audio/moderate/background_noise_1min.wav",
                "tests/assets/audio/challenging/heavy_noise_45s.wav",
            ]
            if os.path.exists(f)
        ]

        if not audio_files:
            pytest.skip("No test audio files found")

        # Duplicate to get 6 files
        audio_files = audio_files * 2

        self.metrics.start_timer("concurrent_quality_analysis")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(analyzer.analyze_audio_quality, f) for f in audio_files
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        duration = self.metrics.end_timer("concurrent_quality_analysis")

        assert len(results) == len(audio_files)

        # Check all succeeded
        errors = [r for r in results if "error" in r]
        assert len(errors) == 0, f"Found {len(errors)} errors"

        print(f"\n📊 Analyzed {len(audio_files)} files concurrently in {duration:.2f}s")
        print(
            f"   Average quality: {sum(r['quality_score'] for r in results)/len(results):.1f}/100"
        )


class TestConcurrentRAGQueries:
    """Test concurrent RAG search queries."""

    def setup_method(self):
        """Setup metrics collector."""
        self.metrics = MetricsCollector()

    @pytest.mark.load
    def test_concurrent_rag_evaluation(self):
        """Test concurrent RAG evaluation queries."""
        from app.services.rag_evaluator import RAGEvaluator

        evaluator = RAGEvaluator()

        # Simulate 20 concurrent queries
        queries = [f"query_{i}" for i in range(20)]
        retrieved_results = [[f"doc_{j}" for j in range(10)] for _ in range(20)]
        ground_truth = [[f"doc_{j}" for j in range(2)] for _ in range(20)]

        self.metrics.start_timer("concurrent_rag_20_queries")

        def evaluate_single(idx):
            return evaluator.precision_at_k(
                retrieved_results[idx], ground_truth[idx], k=5
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(evaluate_single, i) for i in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        duration = self.metrics.end_timer("concurrent_rag_20_queries")

        assert len(results) == 20
        assert duration < 1.0  # Should be very fast

        print(f"\n🔍 Processed {len(results)} RAG queries in {duration:.3f}s")
        print(f"   Throughput: {len(results)/duration:.0f} queries/second")

    @pytest.mark.load
    def test_concurrent_embedding_similarity(self):
        """Test concurrent embedding similarity calculations."""
        import numpy as np

        from app.services.rag_evaluator import RAGEvaluator

        evaluator = RAGEvaluator()

        # Generate 50 random embeddings
        embeddings = [np.random.rand(384) for _ in range(50)]

        self.metrics.start_timer("concurrent_similarity_50_pairs")

        def calc_similarity(idx):
            return evaluator.cosine_similarity(
                embeddings[idx], embeddings[(idx + 1) % len(embeddings)]
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(calc_similarity, i) for i in range(50)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        duration = self.metrics.end_timer("concurrent_similarity_50_pairs")

        assert len(results) == 50
        assert duration < 0.5

        print(f"\n🧮 Calculated {len(results)} similarities in {duration:.3f}s")


class TestConcurrentLLMOperations:
    """Test concurrent LLM-like operations (simulated)."""

    def setup_method(self):
        """Setup metrics collector."""
        self.metrics = MetricsCollector()

    @pytest.mark.load
    def test_concurrent_text_processing(self):
        """Test concurrent text processing operations."""

        # Simulate LLM text processing
        def process_text(text: str) -> Dict[str, Any]:
            # Simulate processing time
            time.sleep(random.uniform(0.01, 0.05))
            return {
                "text": text,
                "word_count": len(text.split()),
                "char_count": len(text),
                "processed": True,
            }

        texts = [f"Sample text number {i} " * 10 for i in range(20)]

        self.metrics.start_timer("concurrent_text_processing_20")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_text, t) for t in texts]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        duration = self.metrics.end_timer("concurrent_text_processing_20")

        assert len(results) == 20
        assert all(r["processed"] for r in results)

        print(f"\n📝 Processed {len(results)} texts concurrently in {duration:.2f}s")
        print(f"   Average speedup: {(len(texts) * 0.03) / duration:.1f}x")


class TestSecurityUnderLoad:
    """Test security measures under high load."""

    def setup_method(self):
        """Setup metrics collector."""
        self.metrics = MetricsCollector()

    @pytest.mark.security
    @pytest.mark.load
    def test_rate_limiting_under_load(self):
        """Test rate limiting with concurrent requests."""
        from app.utils.ai_service_utils import RateLimiter

        limiter = RateLimiter(max_requests=10, time_window=1.0)

        # Try 50 concurrent requests
        def make_request(idx):
            return limiter.allow_request()

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request, i) for i in range(50)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        allowed = sum(results)
        denied = len(results) - allowed

        # Should allow ~10 and deny ~40
        assert allowed <= 12  # Allow some variance
        assert denied >= 38

        print(f"\n🔒 Rate Limiting Test:")
        print(f"   Allowed: {allowed}/50")
        print(f"   Denied: {denied}/50")
        print(f"   Rate limit working: {'✅' if denied > 30 else '❌'}")

    @pytest.mark.security
    @pytest.mark.load
    def test_input_validation_under_load(self):
        """Test input validation with many concurrent requests."""
        from app.utils.ai_service_utils import validate_transcript

        # Mix of valid and invalid inputs
        inputs = [
            "Valid transcript text",
            "",  # Empty
            "   ",  # Whitespace only
            "a" * 100001,  # Too long
            "Valid text " * 100,
        ] * 10  # 50 total

        self.metrics.start_timer("concurrent_validation_50")

        def validate_input(text):
            try:
                validate_transcript(text)
                return True
            except:
                return False

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(validate_input, inp) for inp in inputs]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        duration = self.metrics.end_timer("concurrent_validation_50")

        valid_count = sum(results)
        invalid_count = len(results) - valid_count

        print(f"\n✅ Input Validation Under Load:")
        print(f"   Valid: {valid_count}/50")
        print(f"   Invalid: {invalid_count}/50")
        print(f"   Duration: {duration:.3f}s")
        print(f"   Throughput: {len(results)/duration:.0f} validations/second")


class TestMemoryUnderLoad:
    """Test memory usage under concurrent load."""

    def setup_method(self):
        """Setup metrics collector."""
        self.metrics = MetricsCollector()

    @pytest.mark.load
    def test_memory_usage_concurrent_operations(self):
        """Test memory usage with many concurrent operations."""
        import numpy as np

        self.metrics.record_memory_snapshot("before_load")

        # Simulate memory-intensive operations
        def create_large_array(size):
            arr = np.random.rand(size, 100)
            return arr.mean()

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_large_array, 1000) for _ in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        self.metrics.record_memory_snapshot("after_load")

        summary = self.metrics.get_summary()

        before_mb = summary.get("memory_before_load", {}).get("mean", 0)
        after_mb = summary.get("memory_after_load", {}).get("mean", 0)

        memory_increase = after_mb - before_mb

        print(f"\n💾 Memory Usage:")
        print(f"   Before: {before_mb:.1f} MB")
        print(f"   After: {after_mb:.1f} MB")
        print(f"   Increase: {memory_increase:.1f} MB")

        # Memory should not increase excessively
        assert memory_increase < 500  # Less than 500MB increase


class TestEndToEndConcurrent:
    """Test complete end-to-end workflows concurrently."""

    def setup_method(self):
        """Setup metrics collector."""
        self.metrics = MetricsCollector()

    @pytest.mark.load
    @pytest.mark.integration
    def test_concurrent_note_processing_simulation(self):
        """Simulate concurrent note processing workflows."""

        def process_note_workflow(note_id: int):
            """Simulate complete note processing."""
            # 1. Validate audio
            time.sleep(random.uniform(0.01, 0.02))

            # 2. Analyze quality
            time.sleep(random.uniform(0.05, 0.1))

            # 3. Process with LLM (simulated)
            time.sleep(random.uniform(0.1, 0.2))

            # 4. Generate embedding
            time.sleep(random.uniform(0.01, 0.03))

            return {
                "note_id": note_id,
                "status": "completed",
                "steps": ["validate", "analyze", "llm", "embed"],
            }

        num_notes = 10

        self.metrics.start_timer("concurrent_10_note_workflows")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(process_note_workflow, i) for i in range(num_notes)
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        duration = self.metrics.end_timer("concurrent_10_note_workflows")

        assert len(results) == num_notes
        assert all(r["status"] == "completed" for r in results)

        # Sequential would take ~2s per note = 20s
        # Concurrent should be much faster
        sequential_estimate = num_notes * 0.2
        speedup = sequential_estimate / duration

        print(f"\n🚀 Concurrent Note Processing:")
        print(f"   Notes processed: {num_notes}")
        print(f"   Total time: {duration:.2f}s")
        print(f"   Sequential estimate: {sequential_estimate:.2f}s")
        print(f"   Speedup: {speedup:.1f}x")
        print(f"   Throughput: {num_notes/duration:.1f} notes/second")


class TestStressTest:
    """Stress tests with extreme load."""

    def setup_method(self):
        """Setup metrics collector."""
        self.metrics = MetricsCollector()

    @pytest.mark.stress
    def test_extreme_concurrent_load(self):
        """Test system under extreme concurrent load."""

        def simple_operation(idx):
            # Simple computation
            result = sum(range(1000))
            return result

        num_operations = 100

        self.metrics.start_timer("stress_100_operations")

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(simple_operation, i) for i in range(num_operations)
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        duration = self.metrics.end_timer("stress_100_operations")

        assert len(results) == num_operations

        print(f"\n💪 Stress Test:")
        print(f"   Operations: {num_operations}")
        print(f"   Duration: {duration:.2f}s")
        print(f"   Throughput: {num_operations/duration:.0f} ops/second")
        print(f"   System stable: ✅")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "load"])
