import librosa
import soundfile as sf
import numpy as np
import noisereduce as nr
from pydub import AudioSegment, effects
import os

def preprocess_audio_pipeline(input_path: str):
    """
    Advanced enhancement for distant speakers:
    Noise Reduction -> Dynamic Compression (AGC) -> Normalization -> Resampling
    """
    # 1. Load Audio at 16kHz (Optimal for Groq Whisper v3)
    # change to mono to simplify processing
    y, sr = librosa.load(input_path, sr=16000, mono=True)

    # 2. Stronger Spectral Noise Reduction
    # Crucial for distant speakers so we don't amplify the 'hiss' of the room
    y_denoised = nr.reduce_noise(y=y, sr=sr, prop_decrease=0.85, n_fft=2048)

    # 3. Aggressive Silence Removal (VAD)
    # Removing dead air helps the STT focus only on active speech segments
    yt, _ = librosa.effects.trim(y_denoised, top_db=20)

    # 4. Save intermediate for Pydub's heavy lifting
    temp_wav = input_path.replace(".mp3", "_temp.wav")
    sf.write(temp_wav, yt, sr)
    
    # 5. Dynamic Range Compression & Normalization
    # This is the "Magic" for distant voices
    audio_segment = AudioSegment.from_wav(temp_wav)
    
    # Compress the dynamic range:
    # This brings the quietest sounds closer to the loudest sounds
    # without crossing the 0dB distortion threshold.
    compressed_audio = effects.compress_dynamic_range(
        audio_segment, 
        threshold=-24.0, # Sounds quieter than this are targeted
        ratio=4.0,       # Compression intensity
        attack=5.0,      # Reaction speed in ms
        release=50.0     # Recovery speed in ms
    )

    # 6. Final Peak Normalization to -0.1 dB
    # This stretches the compressed audio to the maximum possible safe volume
    final_audio = effects.normalize(compressed_audio, headroom=0.1)

    # 7. Quality Check: Forced Gain Boost if still quiet
    if final_audio.dBFS < -15:
        final_audio = final_audio + 10 # Boost by 10dB if distant speakers are still low

    output_path = input_path.replace(".mp3", "_high_gain.wav")
    final_audio.export(output_path, format="wav")

    # Cleanup
    if os.path.exists(temp_wav):
        os.remove(temp_wav)

    return output_path