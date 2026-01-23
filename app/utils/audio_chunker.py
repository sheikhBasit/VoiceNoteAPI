"""
Audio Chunker Utility

Intelligently splits large audio files into manageable chunks for processing.
Handles various formats and preserves speaker continuity.
"""

import os
import math
from pydub import AudioSegment
from app.utils.json_logger import JLogger
from pydub.silence import detect_nonsilent

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
            JLogger.debug("Checking if audio should be chunked", file_path=file_path, max_duration_minutes=max_duration_minutes)
            audio = AudioSegment.from_file(file_path)
            duration_minutes = len(audio) / 1000 / 60
            should_chunk = duration_minutes > max_duration_minutes
            JLogger.info("Audio chunk decision", file_path=file_path, duration_minutes=duration_minutes, should_chunk=should_chunk)
            return should_chunk
        except Exception as e:
            JLogger.error("Error checking audio duration", file_path=file_path, error=str(e))
            return False
    
    @staticmethod
    def validate_audio_file(file_path: str) -> tuple[bool, str]:
        """
        Validate audio file format and integrity.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        JLogger.debug("Validating audio file", file_path=file_path)
        
        if file_path is None or file_path == "":
            JLogger.warning("Invalid file path provided", file_path=file_path)
            return False, "File path cannot be None or empty"
        
        if not os.path.exists(file_path):
            JLogger.warning("File does not exist", file_path=file_path)
            return False, "File does not exist"

        
        # Check file size (max 100MB)
        file_size = os.path.getsize(file_path)
        if file_size > 100 * 1024 * 1024:
            JLogger.warning("File too large", file_path=file_path, size_mb=file_size / 1024 / 1024)
            return False, f"File too large: {file_size / 1024 / 1024:.2f}MB (max 100MB)"
        
        if file_size == 0:
            JLogger.warning("Empty file detected", file_path=file_path)
            return False, "File is empty"
        
        # Try to load audio
        try:
            audio = AudioSegment.from_file(file_path)
            if len(audio) == 0:
                JLogger.warning("Audio has zero duration", file_path=file_path)
                return False, "Audio has zero duration"
            JLogger.info("Audio file validated successfully", file_path=file_path, duration_ms=len(audio), size_bytes=file_size)
            return True, ""
        except Exception as e:
            JLogger.error("Invalid audio file", file_path=file_path, error=str(e))
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
        JLogger.info("Starting audio chunking", file_path=file_path, output_dir=output_dir)
        audio = AudioSegment.from_file(file_path)
        total_duration = len(audio)
        
        JLogger.info("Audio loaded for chunking", file_path=file_path, total_duration_s=total_duration/1000)
        
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
