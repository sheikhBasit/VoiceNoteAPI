"""
Audio Chunker Utility

Intelligently splits large audio files into manageable chunks for processing.
Handles various formats and preserves speaker continuity.
"""

import os
import math
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
import logging

logger = logging.getLogger(__name__)

class AudioChunker:
    """Handles intelligent audio chunking for large files."""
    
    # Configuration
    MAX_CHUNK_DURATION_MS = 180000  # 3 minutes in milliseconds
    MIN_CHUNK_DURATION_MS = 120000  # 2 minutes in milliseconds
    SILENCE_THRESH = -40  # dB threshold for silence detection
    MIN_SILENCE_LEN = 500  # Minimum silence length in ms
    
    @staticmethod
    def should_chunk(file_path: str, max_duration_minutes: int = 5) -> bool:
        """
        Determine if audio file should be chunked.
        
        Args:
            file_path: Path to audio file
            max_duration_minutes: Maximum duration before chunking (default 5 min)
            
        Returns:
            bool: True if file should be chunked
        """
        try:
            audio = AudioSegment.from_file(file_path)
            duration_minutes = len(audio) / 1000 / 60
            return duration_minutes > max_duration_minutes
        except Exception as e:
            logger.error(f"Error checking audio duration: {e}")
            return False
    
    @staticmethod
    def validate_audio_file(file_path: str) -> tuple[bool, str]:
        """
        Validate audio file format and integrity.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not os.path.exists(file_path):
            return False, "File does not exist"
        
        # Check file size (max 100MB)
        file_size = os.path.getsize(file_path)
        if file_size > 100 * 1024 * 1024:
            return False, f"File too large: {file_size / 1024 / 1024:.2f}MB (max 100MB)"
        
        if file_size == 0:
            return False, "File is empty"
        
        # Try to load audio
        try:
            audio = AudioSegment.from_file(file_path)
            if len(audio) == 0:
                return False, "Audio has zero duration"
            return True, ""
        except Exception as e:
            return False, f"Invalid audio file: {str(e)}"
    
    @staticmethod
    def chunk_audio(file_path: str, output_dir: str) -> list[str]:
        """
        Split audio file into intelligent chunks.
        
        Args:
            file_path: Path to input audio file
            output_dir: Directory to save chunks
            
        Returns:
            list: Paths to chunk files
        """
        # Validate first
        is_valid, error = AudioChunker.validate_audio_file(file_path)
        if not is_valid:
            raise ValueError(error)
        
        # Load audio
        audio = AudioSegment.from_file(file_path)
        total_duration = len(audio)
        
        logger.info(f"Chunking audio: {total_duration/1000:.2f}s total duration")
        
        # Calculate optimal chunk count
        num_chunks = math.ceil(total_duration / AudioChunker.MAX_CHUNK_DURATION_MS)
        target_chunk_duration = total_duration / num_chunks
        
        logger.info(f"Target: {num_chunks} chunks of ~{target_chunk_duration/1000:.2f}s each")
        
        # Detect non-silent regions for smarter splitting
        nonsilent_ranges = detect_nonsilent(
            audio,
            min_silence_len=AudioChunker.MIN_SILENCE_LEN,
            silence_thresh=AudioChunker.SILENCE_THRESH
        )
        
        # Create chunks
        chunks = []
        chunk_paths = []
        
        if num_chunks == 1:
            # No need to chunk
            return [file_path]
        
        # Find optimal split points (prefer silence)
        split_points = []
        for i in range(1, num_chunks):
            ideal_split = i * target_chunk_duration
            
            # Find nearest silence to ideal split point
            best_split = ideal_split
            min_distance = float('inf')
            
            for start, end in nonsilent_ranges:
                # Check gap before this nonsilent region
                if start > 0:
                    gap_center = start
                    distance = abs(gap_center - ideal_split)
                    if distance < min_distance and distance < 30000:  # Within 30s
                        min_distance = distance
                        best_split = gap_center
            
            split_points.append(int(best_split))
        
        # Create chunks based on split points
        split_points = [0] + split_points + [total_duration]
        
        os.makedirs(output_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        
        for i in range(len(split_points) - 1):
            start = split_points[i]
            end = split_points[i + 1]
            
            chunk = audio[start:end]
            chunk_path = os.path.join(output_dir, f"{base_name}_chunk_{i+1}.wav")
            
            chunk.export(chunk_path, format="wav")
            chunk_paths.append(chunk_path)
            
            logger.info(f"Created chunk {i+1}/{num_chunks}: {len(chunk)/1000:.2f}s")
        
        return chunk_paths
    
    @staticmethod
    def merge_transcripts(transcripts: list[str]) -> str:
        """
        Intelligently merge transcripts from multiple chunks.
        
        Args:
            transcripts: List of transcript strings
            
        Returns:
            str: Merged transcript
        """
        if not transcripts:
            return ""
        
        if len(transcripts) == 1:
            return transcripts[0]
        
        # Simple merge with paragraph breaks
        # TODO: Add speaker continuity detection
        merged = "\n\n".join(t.strip() for t in transcripts if t.strip())
        
        return merged
    
    @staticmethod
    def convert_to_supported_format(file_path: str, output_path: str = None) -> str:
        """
        Convert audio to supported format (WAV, 16kHz, mono).
        
        Args:
            file_path: Input file path
            output_path: Output file path (optional)
            
        Returns:
            str: Path to converted file
        """
        try:
            audio = AudioSegment.from_file(file_path)
            
            # Convert to mono
            if audio.channels > 1:
                audio = audio.set_channels(1)
            
            # Resample to 16kHz (optimal for Whisper)
            if audio.frame_rate != 16000:
                audio = audio.set_frame_rate(16000)
            
            # Determine output path
            if output_path is None:
                base = os.path.splitext(file_path)[0]
                output_path = f"{base}_converted.wav"
            
            # Export as WAV
            audio.export(output_path, format="wav")
            
            logger.info(f"Converted audio: {file_path} -> {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Audio conversion failed: {e}")
            raise
