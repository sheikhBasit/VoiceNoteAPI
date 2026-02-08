"""
Generate test audio files for comprehensive testing.

Creates synthetic audio samples across different quality tiers:
- Ideal: Clean, clear audio
- Moderate: Background noise, multiple speakers
- Challenging: Heavy noise, overlapping speech
- Worst-case: Corrupted, wrong format, extreme conditions
"""

import os
import numpy as np
from pydub import AudioSegment
from pydub.generators import Sine, WhiteNoise
import random

class TestAudioGenerator:
    """Generates test audio files for various scenarios."""
    
    OUTPUT_DIR = "tests/assets/audio"
    SAMPLE_RATE = 16000
    
    @staticmethod
    def generate_silence(duration_ms: int) -> AudioSegment:
        """Generate silence."""
        return AudioSegment.silent(duration=duration_ms)
    
    @staticmethod
    def generate_tone(frequency: int, duration_ms: int) -> AudioSegment:
        """Generate a pure tone."""
        return Sine(frequency).to_audio_segment(duration=duration_ms)
    
    @staticmethod
    def generate_white_noise(duration_ms: int, volume: int = -20) -> AudioSegment:
        """Generate white noise."""
        noise = WhiteNoise().to_audio_segment(duration=duration_ms)
        return noise + volume  # Adjust volume (dB)
    
    @staticmethod
    def generate_ideal_audio():
        """Generate ideal quality audio (clean, clear)."""
        output_dir = os.path.join(TestAudioGenerator.OUTPUT_DIR, "ideal")
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. Short clean audio (30 seconds)
        audio = TestAudioGenerator.generate_silence(500)
        audio += TestAudioGenerator.generate_tone(440, 1000)  # A4 note
        audio += TestAudioGenerator.generate_silence(500)
        audio += TestAudioGenerator.generate_tone(523, 1000)  # C5 note
        audio += TestAudioGenerator.generate_silence(27000)
        
        audio.export(os.path.join(output_dir, "clean_30s.wav"), format="wav")
        
        # 2. Medium length (3 minutes)
        audio_3min = TestAudioGenerator.generate_silence(180000)
        for i in range(10):
            pos = i * 18000
            tone = TestAudioGenerator.generate_tone(440 + i * 50, 2000)
            audio_3min = audio_3min.overlay(tone, position=pos)
        
        audio_3min.export(os.path.join(output_dir, "clean_3min.wav"), format="wav")
        
        print("✅ Generated ideal audio samples")
    
    @staticmethod
    def generate_moderate_audio():
        """Generate moderate quality audio (background noise)."""
        output_dir = os.path.join(TestAudioGenerator.OUTPUT_DIR, "moderate")
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. Audio with background noise
        base = TestAudioGenerator.generate_silence(60000)  # 1 minute
        
        # Add speech-like tones
        for i in range(20):
            pos = random.randint(0, 55000)
            freq = random.randint(200, 800)
            tone = TestAudioGenerator.generate_tone(freq, random.randint(500, 2000))
            base = base.overlay(tone, position=pos)
        
        # Add background noise
        noise = TestAudioGenerator.generate_white_noise(60000, volume=-30)
        audio_with_noise = base.overlay(noise)
        
        audio_with_noise.export(os.path.join(output_dir, "background_noise_1min.wav"), format="wav")
        
        # 2. Multiple speakers simulation (alternating frequencies)
        multi_speaker = TestAudioGenerator.generate_silence(90000)  # 1.5 minutes
        
        # Speaker 1 (lower frequency)
        for i in range(0, 90000, 10000):
            tone = TestAudioGenerator.generate_tone(300, 3000)
            multi_speaker = multi_speaker.overlay(tone, position=i)
        
        # Speaker 2 (higher frequency)
        for i in range(5000, 90000, 10000):
            tone = TestAudioGenerator.generate_tone(600, 3000)
            multi_speaker = multi_speaker.overlay(tone, position=i)
        
        multi_speaker.export(os.path.join(output_dir, "multi_speaker_90s.wav"), format="wav")
        
        print("✅ Generated moderate audio samples")
    
    @staticmethod
    def generate_challenging_audio():
        """Generate challenging audio (heavy noise, overlapping)."""
        output_dir = os.path.join(TestAudioGenerator.OUTPUT_DIR, "challenging")
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. Heavy background noise
        base = TestAudioGenerator.generate_silence(45000)
        
        # Add signal
        for i in range(15):
            pos = i * 3000
            tone = TestAudioGenerator.generate_tone(random.randint(200, 1000), 1500)
            base = base.overlay(tone, position=pos)
        
        # Add heavy noise (louder)
        heavy_noise = TestAudioGenerator.generate_white_noise(45000, volume=-15)
        challenging = base.overlay(heavy_noise)
        
        challenging.export(os.path.join(output_dir, "heavy_noise_45s.wav"), format="wav")
        
        # 2. Overlapping speech simulation
        overlapping = TestAudioGenerator.generate_silence(60000)
        
        # Multiple overlapping tones
        for i in range(30):
            pos = random.randint(0, 55000)
            freq = random.randint(200, 1200)
            duration = random.randint(1000, 4000)
            tone = TestAudioGenerator.generate_tone(freq, duration)
            overlapping = overlapping.overlay(tone, position=pos)
        
        overlapping.export(os.path.join(output_dir, "overlapping_60s.wav"), format="wav")
        
        print("✅ Generated challenging audio samples")
    
    @staticmethod
    def generate_worst_case_audio():
        """Generate worst-case scenarios."""
        output_dir = os.path.join(TestAudioGenerator.OUTPUT_DIR, "worst_case")
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. Empty/silent file
        silent = TestAudioGenerator.generate_silence(5000)
        silent.export(os.path.join(output_dir, "silent_5s.wav"), format="wav")
        
        # 2. Very short file (< 1 second)
        very_short = TestAudioGenerator.generate_tone(440, 500)
        very_short.export(os.path.join(output_dir, "very_short_0.5s.wav"), format="wav")
        
        # 3. Very long file (10 minutes)
        long_audio = TestAudioGenerator.generate_silence(600000)
        for i in range(0, 600000, 30000):
            tone = TestAudioGenerator.generate_tone(440, 1000)
            long_audio = long_audio.overlay(tone, position=i)
        
        long_audio.export(os.path.join(output_dir, "very_long_10min.wav"), format="wav")
        
        # 4. Pure noise (no signal)
        pure_noise = TestAudioGenerator.generate_white_noise(30000, volume=-10)
        pure_noise.export(os.path.join(output_dir, "pure_noise_30s.wav"), format="wav")
        
        # 5. Corrupted file (truncated)
        normal = TestAudioGenerator.generate_tone(440, 10000)
        corrupted_path = os.path.join(output_dir, "corrupted.wav")
        normal.export(corrupted_path, format="wav")
        
        # Truncate the file to corrupt it
        with open(corrupted_path, 'rb') as f:
            data = f.read()
        with open(corrupted_path, 'wb') as f:
            f.write(data[:len(data)//2])  # Write only half
        
        # 6. Wrong format (text file with .wav extension)
        wrong_format_path = os.path.join(output_dir, "wrong_format.wav")
        with open(wrong_format_path, 'w') as f:
            f.write("This is not an audio file")
        
        # 7. Empty file
        empty_path = os.path.join(output_dir, "empty.wav")
        open(empty_path, 'w').close()
        
        print("✅ Generated worst-case audio samples")
    
    @staticmethod
    def generate_all():
        """Generate all test audio files."""
        print("🎵 Generating test audio files...")
        TestAudioGenerator.generate_ideal_audio()
        TestAudioGenerator.generate_moderate_audio()
        TestAudioGenerator.generate_challenging_audio()
        TestAudioGenerator.generate_worst_case_audio()
        print("✅ All test audio files generated!")

if __name__ == "__main__":
    TestAudioGenerator.generate_all()
