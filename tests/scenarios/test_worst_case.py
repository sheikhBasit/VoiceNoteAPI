"""
Comprehensive Test Scenarios - Worst-Case Conditions

Tests system robustness under extreme and error conditions:
- Corrupted files
- Wrong formats
- Extreme file sizes
- Silent/empty audio
"""

import os

import pytest

from app.utils.audio_chunker import AudioChunker
from app.utils.metrics_collector import MetricsCollector

ASSETS_DIR = "tests/assets/audio/worst_case"


class TestWorstCaseConditions:
    """Test suite for worst-case scenarios and error handling."""

    def setup_method(self):
        """Setup metrics collector for each test."""
        self.metrics = MetricsCollector()

    def teardown_method(self):
        """Save metrics after each test."""
        self.metrics.save_to_file()

    def test_empty_file_handling(self):
        """Test handling of empty audio file."""
        audio_path = os.path.join(ASSETS_DIR, "empty.wav")

        if not os.path.exists(audio_path):
            pytest.skip(f"Test audio not found: {audio_path}")

        is_valid, error = AudioChunker.validate_audio_file(audio_path)

        assert not is_valid, "Empty file should fail validation"
        assert "empty" in error.lower() or "zero" in error.lower()

        self.metrics.record_metric(
            "error_handling_success", 1.0, "ratio", {"error_type": "empty_file"}
        )

    def test_corrupted_file_handling(self):
        """Test handling of corrupted audio file."""
        audio_path = os.path.join(ASSETS_DIR, "corrupted.wav")

        if not os.path.exists(audio_path):
            pytest.skip(f"Test audio not found: {audio_path}")

        is_valid, error = AudioChunker.validate_audio_file(audio_path)

        # Should either fail validation or handle gracefully
        if not is_valid:
            assert len(error) > 0, "Error message should be provided"
            self.metrics.record_metric("corrupted_file_detected", 1.0, "ratio")

    def test_wrong_format_handling(self):
        """Test handling of non-audio file with .wav extension."""
        audio_path = os.path.join(ASSETS_DIR, "wrong_format.wav")

        if not os.path.exists(audio_path):
            pytest.skip(f"Test audio not found: {audio_path}")

        is_valid, error = AudioChunker.validate_audio_file(audio_path)

        assert not is_valid, "Non-audio file should fail validation"
        assert "invalid" in error.lower() or "error" in error.lower()

        self.metrics.record_metric("wrong_format_detected", 1.0, "ratio")

    def test_very_short_audio_handling(self):
        """Test handling of very short audio (<1 second)."""
        audio_path = os.path.join(ASSETS_DIR, "very_short_0.5s.wav")

        if not os.path.exists(audio_path):
            pytest.skip(f"Test audio not found: {audio_path}")

        is_valid, error = AudioChunker.validate_audio_file(audio_path)

        # Very short audio should still be valid
        assert is_valid, f"Very short audio should be valid: {error}"

        # But should not be chunked
        should_chunk = AudioChunker.should_chunk(audio_path)
        assert not should_chunk

    def test_very_long_audio_chunking(self):
        """Test chunking of very long audio (10 minutes)."""
        audio_path = os.path.join(ASSETS_DIR, "very_long_10min.wav")

        if not os.path.exists(audio_path):
            pytest.skip(f"Test audio not found: {audio_path}")

        # Should require chunking
        should_chunk = AudioChunker.should_chunk(audio_path, max_duration_minutes=5)
        assert should_chunk, "10-minute audio should be chunked"

        # Test actual chunking
        self.metrics.start_timer("chunking_10min_audio")

        output_dir = "/tmp/test_chunks"
        os.makedirs(output_dir, exist_ok=True)

        try:
            chunks = AudioChunker.chunk_audio(audio_path, output_dir)

            duration = self.metrics.end_timer("chunking_10min_audio")

            assert len(chunks) >= 3, f"Expected at least 3 chunks, got {len(chunks)}"
            assert all(os.path.exists(c) for c in chunks), "All chunks should exist"

            self.metrics.record_metric(
                "chunks_created", len(chunks), "count", {"source_duration_min": 10}
            )

            self.metrics.record_metric(
                "chunking_latency", duration, "seconds", {"source_duration_min": 10}
            )

        finally:
            # Cleanup
            import shutil

            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)

    def test_silent_audio_handling(self):
        """Test handling of silent audio file."""
        audio_path = os.path.join(ASSETS_DIR, "silent_5s.wav")

        if not os.path.exists(audio_path):
            pytest.skip(f"Test audio not found: {audio_path}")

        is_valid, error = AudioChunker.validate_audio_file(audio_path)

        # Silent audio should be valid (has duration)
        assert is_valid, f"Silent audio should be valid: {error}"

    def test_pure_noise_handling(self):
        """Test handling of pure noise (no speech signal)."""
        audio_path = os.path.join(ASSETS_DIR, "pure_noise_30s.wav")

        if not os.path.exists(audio_path):
            pytest.skip(f"Test audio not found: {audio_path}")

        is_valid, error = AudioChunker.validate_audio_file(audio_path)

        # Pure noise should still be valid audio
        assert is_valid, f"Pure noise should be valid audio: {error}"

    def test_nonexistent_file_handling(self):
        """Test handling of non-existent file."""
        audio_path = "/nonexistent/path/to/audio.wav"

        is_valid, error = AudioChunker.validate_audio_file(audio_path)

        assert not is_valid, "Non-existent file should fail validation"
        assert "not exist" in error.lower() or "exist" in error.lower()

    @pytest.mark.performance
    def test_error_handling_performance(self):
        """Test that error handling is fast (no hanging)."""
        test_cases = ["empty.wav", "wrong_format.wav", "corrupted.wav"]

        for filename in test_cases:
            audio_path = os.path.join(ASSETS_DIR, filename)

            if not os.path.exists(audio_path):
                continue

            self.metrics.start_timer(f"error_validation_{filename}")

            is_valid, error = AudioChunker.validate_audio_file(audio_path)

            latency = self.metrics.end_timer(f"error_validation_{filename}")

            # Error handling should be fast
            assert (
                latency < 2.0
            ), f"Error validation too slow for {filename}: {latency}s"

    def test_graceful_degradation(self):
        """Test that system doesn't crash on any worst-case scenario."""
        test_files = [
            "empty.wav",
            "corrupted.wav",
            "wrong_format.wav",
            "very_short_0.5s.wav",
            "silent_5s.wav",
            "pure_noise_30s.wav",
        ]

        failures = []

        for filename in test_files:
            audio_path = os.path.join(ASSETS_DIR, filename)

            if not os.path.exists(audio_path):
                continue

            try:
                # Should not crash, even if validation fails
                is_valid, error = AudioChunker.validate_audio_file(audio_path)

                # Record result
                self.metrics.record_metric(
                    f"graceful_handling_{filename}",
                    1.0 if not is_valid else 0.5,
                    "score",
                )

            except Exception as e:
                failures.append((filename, str(e)))

        # No exceptions should be raised
        assert len(failures) == 0, f"System crashed on: {failures}"

        self.metrics.record_metric(
            "graceful_degradation_success_rate",
            1.0,
            "ratio",
            {"total_tests": len(test_files)},
        )
