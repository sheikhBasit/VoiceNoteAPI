"""
Audio Quality Analyzer with LLM Feedback

Analyzes audio quality using multiple metrics and gets LLM recommendations
for preprocessing improvements.
"""

import librosa
import numpy as np
import soundfile as sf
import noisereduce as nr
from typing import Dict, Any, Tuple
from groq import Groq
from app.utils.json_logger import JLogger
import os

class AudioQualityAnalyzer:
    """Analyzes audio quality and provides LLM-based recommendations."""
    
    def __init__(self, groq_api_key: str = None):
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        if self.groq_api_key:
            self.groq_client = Groq(api_key=self.groq_api_key)
            JLogger.info("AudioQualityAnalyzer initialized with Groq API")
        else:
            self.groq_client = None
            JLogger.warning("No Groq API key provided. LLM feedback will be disabled.")
    
    def analyze_audio_quality(self, audio_path: str) -> Dict[str, Any]:
        """
        Comprehensive audio quality analysis.
        
        Returns:
            dict: Audio quality metrics
        """
        try:
            JLogger.info("Starting audio quality analysis", audio_path=audio_path)
            # Load audio
            y, sr = librosa.load(audio_path, sr=None)
            JLogger.debug("Audio loaded", audio_path=audio_path, sample_rate=sr, samples=len(y))
            
            metrics = {}
            
            # 1. Loudness (RMS)
            rms = librosa.feature.rms(y=y)[0]
            metrics['loudness_rms'] = float(np.mean(rms))
            metrics['loudness_std'] = float(np.std(rms))
            metrics['loudness_db'] = float(20 * np.log10(metrics['loudness_rms'] + 1e-10))
            
            # 2. Signal-to-Noise Ratio (SNR) estimation
            # Use first 0.5s as noise reference (assuming silence/noise at start)
            noise_duration = min(0.5, len(y) / sr * 0.1)  # 10% or 0.5s
            noise_samples = int(noise_duration * sr)
            
            if len(y) > noise_samples:
                noise = y[:noise_samples]
                signal = y[noise_samples:]
                
                noise_power = np.mean(noise ** 2)
                signal_power = np.mean(signal ** 2)
                
                if noise_power > 0:
                    snr = 10 * np.log10(signal_power / noise_power)
                    metrics['snr_db'] = float(snr)
                else:
                    metrics['snr_db'] = float('inf')
            else:
                metrics['snr_db'] = None
            
            # 3. Clipping detection
            clipping_threshold = 0.99
            clipped_samples = np.sum(np.abs(y) > clipping_threshold)
            metrics['clipping_percentage'] = float(clipped_samples / len(y) * 100)
            
            # 4. Spectral flatness (noise vs tonal content)
            spectral_flatness = librosa.feature.spectral_flatness(y=y)[0]
            metrics['spectral_flatness_mean'] = float(np.mean(spectral_flatness))
            metrics['spectral_flatness_std'] = float(np.std(spectral_flatness))
            
            # 5. Zero-crossing rate (hiss/white noise detection)
            zcr = librosa.feature.zero_crossing_rate(y)[0]
            metrics['zero_crossing_rate_mean'] = float(np.mean(zcr))
            metrics['zero_crossing_rate_std'] = float(np.std(zcr))
            
            # 6. Speech activity ratio
            # Detect non-silent intervals
            intervals = librosa.effects.split(y, top_db=30)
            if len(intervals) > 0:
                speech_samples = sum(end - start for start, end in intervals)
                metrics['speech_activity_ratio'] = float(speech_samples / len(y))
            else:
                metrics['speech_activity_ratio'] = 0.0
            
            # 7. Dynamic range
            metrics['dynamic_range_db'] = float(20 * np.log10(np.max(np.abs(y)) / (np.min(np.abs(y[y != 0])) + 1e-10)))
            
            # 8. Silence ratio
            metrics['silence_ratio'] = 1.0 - metrics['speech_activity_ratio']
            
            # 9. Duration
            metrics['duration_seconds'] = float(len(y) / sr)
            
            # 10. Sample rate
            metrics['sample_rate'] = int(sr)
            
            # Quality assessment
            metrics['quality_score'] = self._calculate_quality_score(metrics)
            metrics['quality_category'] = self._categorize_quality(metrics['quality_score'])
            
            JLogger.info("Audio quality analysis complete", 
                        audio_path=audio_path, 
                        quality_score=metrics['quality_score'],
                        quality_category=metrics['quality_category'],
                        snr_db=metrics.get('snr_db'),
                        clipping_pct=metrics.get('clipping_percentage'))
            
            return metrics
            
        except Exception as e:
            JLogger.error("Error analyzing audio quality", audio_path=audio_path, error=str(e))
            return {"error": str(e)}
    
    def _calculate_quality_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate overall quality score (0-100).
        
        Based on:
        - SNR (higher is better)
        - Clipping (lower is better)
        - Speech activity (moderate is better)
        - Loudness (moderate is better)
        """
        score = 100.0
        
        # SNR penalty
        if metrics.get('snr_db') is not None:
            if metrics['snr_db'] < 10:
                score -= 30
            elif metrics['snr_db'] < 20:
                score -= 15
        
        # Clipping penalty
        if metrics['clipping_percentage'] > 1.0:
            score -= 40
        elif metrics['clipping_percentage'] > 0.1:
            score -= 20
        
        # Loudness penalty
        if metrics['loudness_db'] < -40:
            score -= 20  # Too quiet
        elif metrics['loudness_db'] > -10:
            score -= 15  # Too loud
        
        # Speech activity penalty
        if metrics['speech_activity_ratio'] < 0.3:
            score -= 15  # Too much silence
        
        return max(0.0, min(100.0, score))
    
    def _categorize_quality(self, score: float) -> str:
        """Categorize quality score."""
        if score >= 80:
            return "Excellent"
        elif score >= 60:
            return "Good"
        elif score >= 40:
            return "Fair"
        elif score >= 20:
            return "Poor"
        else:
            return "Very Poor"
    
    def get_llm_feedback(self, metrics: Dict[str, Any], audio_path: str = None) -> Dict[str, Any]:
        """
        Get LLM feedback on audio quality and preprocessing recommendations.
        
        Args:
            metrics: Audio quality metrics
            audio_path: Optional path to audio file
            
        Returns:
            dict: LLM analysis and recommendations
        """
        if not self.groq_client:
            return {
                "error": "Groq API key not configured",
                "recommendations": ["Configure GROQ_API_KEY to enable LLM feedback"]
            }
        
        # Build prompt
        prompt = self._build_analysis_prompt(metrics)
        
        try:
            # Call Groq LLM
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert audio engineer analyzing voice recordings. Provide concise, actionable feedback on audio quality and preprocessing recommendations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            llm_response = response.choices[0].message.content
            
            # Parse recommendations
            recommendations = self._parse_llm_recommendations(llm_response)
            
            return {
                "llm_analysis": llm_response,
                "recommendations": recommendations,
                "model": "llama-3.3-70b-versatile"
            }
            
        except Exception as e:
            JLogger.error(f"Error getting LLM feedback: {e}")
            return {
                "error": str(e),
                "recommendations": self._fallback_recommendations(metrics)
            }
    
    def _build_analysis_prompt(self, metrics: Dict[str, Any]) -> str:
        """Build prompt for LLM analysis."""
        prompt = f"""Analyze this audio recording and provide preprocessing recommendations:

**Audio Metrics:**
- Duration: {metrics.get('duration_seconds', 0):.2f} seconds
- Sample Rate: {metrics.get('sample_rate', 0)} Hz
- Loudness: {metrics.get('loudness_db', 0):.2f} dB
- Signal-to-Noise Ratio: {metrics.get('snr_db', 'N/A')} dB
- Clipping: {metrics.get('clipping_percentage', 0):.2f}%
- Speech Activity: {metrics.get('speech_activity_ratio', 0):.1%}
- Silence Ratio: {metrics.get('silence_ratio', 0):.1%}
- Spectral Flatness: {metrics.get('spectral_flatness_mean', 0):.4f}
- Zero Crossing Rate: {metrics.get('zero_crossing_rate_mean', 0):.4f}
- Quality Score: {metrics.get('quality_score', 0):.1f}/100 ({metrics.get('quality_category', 'Unknown')})

**Your Task:**
1. Assess the overall audio quality
2. Identify specific issues (noise, clipping, volume, etc.)
3. Recommend preprocessing steps in priority order
4. Suggest optimal parameters for each preprocessing step

**Format your response as:**
- Overall Assessment: [1-2 sentences]
- Issues Detected: [bullet list]
- Recommended Preprocessing: [numbered list with parameters]
- Expected Improvement: [brief statement]
"""
        return prompt
    
    def _parse_llm_recommendations(self, llm_response: str) -> list:
        """Parse LLM response into actionable recommendations."""
        recommendations = []
        
        # Extract lines that look like recommendations
        lines = llm_response.split('\n')
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                # Clean up the line
                clean_line = line.lstrip('0123456789.-•) ').strip()
                if clean_line:
                    recommendations.append(clean_line)
        
        return recommendations if recommendations else [llm_response]
    
    def _fallback_recommendations(self, metrics: Dict[str, Any]) -> list:
        """Fallback recommendations when LLM is unavailable."""
        recommendations = []
        
        # SNR-based recommendations
        if metrics.get('snr_db') and metrics['snr_db'] < 20:
            recommendations.append("Apply noise reduction (noisereduce library)")
        
        # Clipping recommendations
        if metrics.get('clipping_percentage', 0) > 0.1:
            recommendations.append("Reduce input gain or apply soft clipping")
        
        # Loudness recommendations
        if metrics.get('loudness_db', 0) < -40:
            recommendations.append("Apply normalization to increase volume")
        elif metrics.get('loudness_db', 0) > -10:
            recommendations.append("Apply compression to reduce volume")
        
        # Silence recommendations
        if metrics.get('silence_ratio', 0) > 0.5:
            recommendations.append("Trim excessive silence (librosa.effects.trim)")
        
        if not recommendations:
            recommendations.append("Audio quality is acceptable, no preprocessing needed")
        
        return recommendations
    
    def apply_recommended_preprocessing(self, audio_path: str, output_path: str, recommendations: list) -> str:
        """
        Apply recommended preprocessing steps.
        
        Args:
            audio_path: Input audio file
            output_path: Output audio file
            recommendations: List of preprocessing recommendations
            
        Returns:
            str: Path to processed audio
        """
        try:
            # Load audio
            y, sr = librosa.load(audio_path, sr=None)
            
            # Apply preprocessing based on recommendations
            for rec in recommendations:
                rec_lower = rec.lower()
                
                # Noise reduction
                if 'noise' in rec_lower and 'reduc' in rec_lower:
                    JLogger.info("Applying noise reduction...")
                    y = nr.reduce_noise(y=y, sr=sr)
                
                # Normalization
                if 'normal' in rec_lower or 'volume' in rec_lower:
                    JLogger.info("Applying normalization...")
                    y = librosa.util.normalize(y)
                
                # Trim silence
                if 'trim' in rec_lower or 'silence' in rec_lower:
                    JLogger.info("Trimming silence...")
                    y, _ = librosa.effects.trim(y, top_db=30)
            
            # Save processed audio
            sf.write(output_path, y, sr)
            JLogger.info(f"Processed audio saved to {output_path}")
            
            return output_path
            
        except Exception as e:
            JLogger.error(f"Error applying preprocessing: {e}")
            raise
    
    def full_analysis_with_feedback(self, audio_path: str) -> Dict[str, Any]:
        """
        Complete analysis with LLM feedback.
        
        Returns:
            dict: Complete analysis results
        """
        # Analyze quality
        metrics = self.analyze_audio_quality(audio_path)
        
        if "error" in metrics:
            return metrics
        
        # Get LLM feedback
        llm_feedback = self.get_llm_feedback(metrics, audio_path)
        
        # Combine results
        return {
            "metrics": metrics,
            "llm_feedback": llm_feedback,
            "audio_path": audio_path
        }
