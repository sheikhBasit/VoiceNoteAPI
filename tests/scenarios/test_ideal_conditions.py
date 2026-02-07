"""
Comprehensive Test Scenarios - Ideal Conditions

Tests audio processing under ideal conditions:
- Clean audio, no background noise
- Single speaker, clear pronunciation
- Standard file formats and sizes
"""

import os

import pytest

from app.utils.audio_chunker import AudioChunker
from app.utils.metrics_collector import MetricsCollector

ASSETS_DIR = "tests/assets/audio/ideal"


class TestIdealConditions:
    """Test suite for ideal audio conditions."""

    def setup_method(self):
        """Setup metrics collector for each test."""
        self.metrics = MetricsCollector()

    def teardown_method(self):
        """Save metrics after each test."""
        self.metrics.save_to_file()

    def test_clean_short_audio_validation(self):
        """Test validation of clean 30-second audio."""
        audio_path = os.path.join(ASSETS_DIR, "clean_30s.wav")

        if not os.path.exists(audio_path):
            pytest.skip(f"Test audio not found: {audio_path}")

        is_valid, error = AudioChunker.validate_audio_file(audio_path)

        assert is_valid, f"Validation failed: {error}"
        assert error == ""

    def test_clean_short_audio_no_chunking_needed(self):
        """Test that short audio doesn't need chunking."""
        audio_path = os.path.join(ASSETS_DIR, "clean_30s.wav")

        if not os.path.exists(audio_path):
            pytest.skip(f"Test audio not found: {audio_path}")

        should_chunk = AudioChunker.should_chunk(audio_path, max_duration_minutes=5)

        assert not should_chunk, "Short audio should not be chunked"

    def test_clean_3min_audio_validation(self):
        """Test validation of 3-minute clean audio."""
        audio_path = os.path.join(ASSETS_DIR, "clean_3min.wav")

        if not os.path.exists(audio_path):
            pytest.skip(f"Test audio not found: {audio_path}")

        is_valid, error = AudioChunker.validate_audio_file(audio_path)

        assert is_valid, f"Validation failed: {error}"

    def test_clean_3min_audio_no_chunking(self):
        """Test that 3-minute audio doesn't need chunking (under 5min threshold)."""
        audio_path = os.path.join(ASSETS_DIR, "clean_3min.wav")

        if not os.path.exists(audio_path):
            pytest.skip(f"Test audio not found: {audio_path}")

        should_chunk = AudioChunker.should_chunk(audio_path, max_duration_minutes=5)

        assert (
            not should_chunk
        ), "3-minute audio should not be chunked with 5-minute threshold"

    def test_audio_format_conversion(self):
        """Test audio format conversion to WAV."""
        audio_path = os.path.join(ASSETS_DIR, "clean_30s.wav")

        if not os.path.exists(audio_path):
            pytest.skip(f"Test audio not found: {audio_path}")

        self.metrics.start_timer("audio_conversion")

        output_path = "/tmp/test_converted.wav"
        converted = AudioChunker.convert_to_supported_format(audio_path, output_path)

        duration = self.metrics.end_timer("audio_conversion")

        assert os.path.exists(converted)
        assert converted == output_path
        assert duration < 5.0, f"Conversion took too long: {duration}s"

        # Cleanup
        if os.path.exists(output_path):
            os.remove(output_path)

    @pytest.mark.performance
    def test_validation_performance(self):
        """Test audio validation performance."""
        audio_path = os.path.join(ASSETS_DIR, "clean_30s.wav")

        if not os.path.exists(audio_path):
            pytest.skip(f"Test audio not found: {audio_path}")

        self.metrics.start_timer("validation_latency")

        is_valid, error = AudioChunker.validate_audio_file(audio_path)

        latency = self.metrics.end_timer("validation_latency")

        assert is_valid
        assert latency < 1.0, f"Validation too slow: {latency}s (expected <1s)"

        self.metrics.record_metric(
            "validation_success_rate", 1.0, "ratio", {"scenario": "ideal"}
        )
