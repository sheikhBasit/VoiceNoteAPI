"""
Test Audio Quality Analyzer with LLM Feedback
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.utils.audio_quality_analyzer import AudioQualityAnalyzer

ASSETS_DIR = "tests/assets/audio"


class TestAudioQualityAnalyzer:
    """Test audio quality analysis and LLM feedback."""

    def setup_method(self):
        """Setup analyzer."""
        self.analyzer = AudioQualityAnalyzer()

    def test_analyze_ideal_audio(self):
        """Test analysis of ideal quality audio."""
        audio_path = os.path.join(ASSETS_DIR, "ideal/clean_30s.wav")

        if not os.path.exists(audio_path):
            pytest.skip(f"Test audio not found: {audio_path}")

        metrics = self.analyzer.analyze_audio_quality(audio_path)

        assert "error" not in metrics
        assert "quality_score" in metrics
        assert "quality_category" in metrics
        assert metrics["quality_score"] >= 0
        assert metrics["quality_score"] <= 100

        print(
            f"\n✅ Ideal Audio Quality Score: {metrics['quality_score']:.1f}/100 ({metrics['quality_category']})"
        )
        print(f"   SNR: {metrics.get('snr_db', 'N/A')} dB")
        print(f"   Loudness: {metrics.get('loudness_db', 'N/A'):.2f} dB")
        print(f"   Clipping: {metrics.get('clipping_percentage', 0):.2f}%")

    def test_analyze_noisy_audio(self):
        """Test analysis of noisy audio."""
        audio_path = os.path.join(ASSETS_DIR, "moderate/background_noise_1min.wav")

        if not os.path.exists(audio_path):
            pytest.skip(f"Test audio not found: {audio_path}")

        metrics = self.analyzer.analyze_audio_quality(audio_path)

        assert "error" not in metrics
        assert "quality_score" in metrics

        print(
            f"\n📊 Noisy Audio Quality Score: {metrics['quality_score']:.1f}/100 ({metrics['quality_category']})"
        )
        print(f"   SNR: {metrics.get('snr_db', 'N/A')} dB")

    def test_analyze_worst_case_audio(self):
        """Test analysis of worst-case audio."""
        audio_path = os.path.join(ASSETS_DIR, "worst_case/pure_noise_30s.wav")

        if not os.path.exists(audio_path):
            pytest.skip(f"Test audio not found: {audio_path}")

        metrics = self.analyzer.analyze_audio_quality(audio_path)

        assert "error" not in metrics

        # Pure noise should have low quality score
        print(
            f"\n⚠️  Pure Noise Quality Score: {metrics['quality_score']:.1f}/100 ({metrics['quality_category']})"
        )

    def test_llm_feedback_fallback(self):
        """Test LLM feedback fallback when API key not available."""
        audio_path = os.path.join(ASSETS_DIR, "ideal/clean_30s.wav")

        if not os.path.exists(audio_path):
            pytest.skip(f"Test audio not found: {audio_path}")

        metrics = self.analyzer.analyze_audio_quality(audio_path)
        feedback = self.analyzer.get_llm_feedback(metrics)

        assert "recommendations" in feedback
        assert len(feedback["recommendations"]) > 0

        print(f"\n💡 Fallback Recommendations:")
        for i, rec in enumerate(feedback["recommendations"], 1):
            print(f"   {i}. {rec}")

    def test_full_analysis(self):
        """Test complete analysis pipeline."""
        audio_path = os.path.join(ASSETS_DIR, "moderate/background_noise_1min.wav")

        if not os.path.exists(audio_path):
            pytest.skip(f"Test audio not found: {audio_path}")

        result = self.analyzer.full_analysis_with_feedback(audio_path)

        assert "metrics" in result
        assert "llm_feedback" in result
        assert "audio_path" in result

        print(f"\n📋 Full Analysis Results:")
        print(f"   Quality: {result['metrics']['quality_score']:.1f}/100")
        print(f"   Category: {result['metrics']['quality_category']}")
        print(f"   Recommendations: {len(result['llm_feedback']['recommendations'])}")

    def test_quality_metrics_completeness(self):
        """Test that all expected metrics are present."""
        audio_path = os.path.join(ASSETS_DIR, "ideal/clean_30s.wav")

        if not os.path.exists(audio_path):
            pytest.skip(f"Test audio not found: {audio_path}")

        metrics = self.analyzer.analyze_audio_quality(audio_path)

        expected_metrics = [
            "loudness_rms",
            "loudness_db",
            "snr_db",
            "clipping_percentage",
            "spectral_flatness_mean",
            "zero_crossing_rate_mean",
            "speech_activity_ratio",
            "silence_ratio",
            "duration_seconds",
            "sample_rate",
            "quality_score",
            "quality_category",
        ]

        for metric in expected_metrics:
            assert metric in metrics, f"Missing metric: {metric}"

        print(f"\n✅ All {len(expected_metrics)} metrics present")

    @pytest.mark.performance
    def test_analysis_performance(self):
        """Test that analysis is fast."""
        audio_path = os.path.join(ASSETS_DIR, "ideal/clean_30s.wav")

        if not os.path.exists(audio_path):
            pytest.skip(f"Test audio not found: {audio_path}")

        import time

        start = time.time()

        metrics = self.analyzer.analyze_audio_quality(audio_path)

        duration = time.time() - start

        assert duration < 5.0, f"Analysis too slow: {duration}s"
        print(f"\n⚡ Analysis completed in {duration:.2f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
