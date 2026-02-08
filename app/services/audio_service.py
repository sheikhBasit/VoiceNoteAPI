import os
import shutil
import time
from typing import List, Tuple

import librosa
import soundfile as sf
from app.utils.json_logger import JLogger

class AudioService:
    """Service for handling audio processing: validation, chunking, and merging."""

    @staticmethod
    def convert_to_supported_format(audio_path: str, output_path: str) -> str:
        """
        Converts audio file to supported WAV format.
        """
        try:
            y, sr = librosa.load(audio_path, sr=None)
            sf.write(output_path, y, sr)
            return output_path
        except Exception as e:
            JLogger.error(f"Failed to convert audio: {e}")
            return audio_path

    @staticmethod
    def validate_audio_file(audio_path: str) -> Tuple[bool, str]:
        """
        Validates that a file exists and is a valid audio file.
        
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if not audio_path:
            return False, "File path cannot be None or empty"

        if not os.path.exists(audio_path):
            return False, f"File does not exist: {audio_path}"
        
        file_size = os.path.getsize(audio_path)
        if file_size == 0:
            return False, "File is empty (zero bytes)"
        
        try:
            # Try loading small part to check format
            y, sr = librosa.load(audio_path, sr=None, duration=0.1)
            if len(y) == 0:
                return False, "File contains no audio data"
            return True, ""
        except Exception as e:
            return False, f"Invalid audio format: {str(e)}"

    @staticmethod
    def should_chunk(audio_path: str, max_duration_minutes: float = 5.0) -> bool:
        """Determines if the audio should be chunked based on duration."""
        try:
            duration = librosa.get_duration(path=audio_path)
            return duration > (max_duration_minutes * 60)
        except Exception:
            return False

    @staticmethod
    def chunk_audio(audio_path: str, output_dir: str, chunk_duration_minutes: float = 5.0) -> List[str]:
        """
        Splits audio into chunks of specified duration.
        
        Returns:
            List[str]: Paths to the created chunks
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        chunks = []
        try:
            y, sr = librosa.load(audio_path, sr=None)
            total_duration = len(y) / sr
            chunk_samples = int(chunk_duration_minutes * 60 * sr)
            
            for i in range(0, len(y), chunk_samples):
                chunk_y = y[i : i + chunk_samples]
                chunk_filename = f"chunk_{len(chunks)}.wav"
                chunk_path = os.path.join(output_dir, chunk_filename)
                sf.write(chunk_path, chunk_y, sr)
                chunks.append(chunk_path)
                
            JLogger.info(f"Chunked {audio_path} into {len(chunks)} parts")
        except Exception as e:
            JLogger.error(f"Failed to chunk audio: {e}")
            
        return chunks

    @staticmethod
    def merge_transcripts(transcripts: List[str]) -> str:
        """Merges multiple transcripts into one."""
        if not transcripts:
            return ""
        return "\n\n".join(transcripts)
