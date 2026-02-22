import logging
import os

try:
    from pydub import AudioSegment, effects
except ImportError:
    AudioSegment = None
    effects = None
    print("Warning: pydub not available in audio.py, audio processing will fail.")


from app.utils.audio_quality_analyzer import AudioQualityAnalyzer
from app.utils.json_logger import JLogger

logger = logging.getLogger(__name__)

from scipy.signal import butter, lfilter


def highpass(audio, sr, cutoff=80):
    """Remove low-frequency rumble below the cutoff frequency."""
    b, a = butter(2, cutoff / (sr / 2), btype="high")
    return lfilter(b, a, audio)


def preprocess_audio_pipeline(input_path: str):
    """
    Advanced enhancement for distant speakers:
    Decode -> High-Pass Filter -> Noise Reduction -> Dynamic Compression -> Normalization
    """
    import librosa
    import noisereduce as nr
    import soundfile as sf

    # 0. TRANSCODE TO WAV IF NEEDED (e.g. m4a, 3gp, aac)
    base_path, ext = os.path.splitext(input_path)
    if ext.lower() not in [".wav", ".wave"]:
        try:
            temp_wav_input = f"{base_path}_converted.wav"
            JLogger.info(f"Transcoding {ext} to WAV for processing: {input_path}")
            audio = AudioSegment.from_file(input_path)
            audio.export(temp_wav_input, format="wav")
            input_path = temp_wav_input  # Use the converted file
        except Exception as e:
            JLogger.error(f"Failed to transcode {ext} file: {e}")
            raise e

    # 1. Load Audio at 16kHz (Optimal for STT)
    y, sr = librosa.load(input_path, sr=16000, mono=True)

    # 2. Rumble removal (HPF 80Hz)
    # Essential for cleaning up background noise and low-end hum
    y_hpf = highpass(y, sr, cutoff=80)

    # 3. Spectral Noise Reduction
    # Crucial for distant speakers: removes 'hiss' without distorting voice
    y_denoised = nr.reduce_noise(y=y_hpf, sr=sr, prop_decrease=0.8, n_fft=2048)

    # 4. Silence Removal (VAD)
    # Trimming helps the STT focus on speech only
    y_trimmed, _ = librosa.effects.trim(y_denoised, top_db=20)

    # 5. Save intermediate for Pydub's dynamic processing
    # Robust extension handling
    base_path, ext = os.path.splitext(input_path)
    temp_wav = f"{base_path}_temp.wav"
    sf.write(temp_wav, y_trimmed, sr)

    # 6. Dynamic Range Compression & Normalization
    # 'Magic' for distant voices: brings quiet sounds closer to loudest for clarity
    audio_segment = AudioSegment.from_wav(temp_wav)

    # Dynamic Compression
    compressed_audio = effects.compress_dynamic_range(
        audio_segment,
        threshold=-24.0,  # Target quiet sounds
        ratio=4.0,  # Compression intensity
        attack=5.0,  # Reaction in ms
        release=50.0,  # Recovery in ms
    )

    # 7. Final Peak Normalization to -0.1 dB
    # Stretch top signals to max safe volume
    final_audio = effects.normalize(compressed_audio, headroom=0.1)

    # 8. Quality Check: Gain Boost if still too quiet
    if final_audio.dBFS < -15:
        final_audio = final_audio + 10  # Boost by 10dB for distant speakers

    output_path = f"{base_path}_refined.wav"
    final_audio.export(output_path, format="wav")

    # 9. Quality Audit
    analyzer = AudioQualityAnalyzer()
    quality_report = analyzer.analyze_audio_quality(output_path)

    JLogger.info(
        "Preprocessing complete",
        input=input_path,
        output=output_path,
        quality_score=quality_report.get("quality_score"),
        quality_category=quality_report.get("quality_category"),
    )

    # Cleanup temp files
    for temp_file in [temp_wav, locals().get("temp_wav_input")]:
        if temp_file and os.path.exists(temp_file) and temp_file != output_path:
            try:
                os.remove(temp_file)
            except OSError:
                pass

    return output_path
