# Test Assets README

## Audio Test Files

This directory contains synthetic audio files for comprehensive testing across different quality scenarios.

### Directory Structure

```
audio/
├── ideal/              # Clean, studio-quality audio
│   ├── clean_30s.wav   # 30 seconds, clear tones
│   └── clean_3min.wav  # 3 minutes, periodic tones
├── moderate/           # Realistic office/meeting conditions
│   ├── background_noise_1min.wav    # Background noise simulation
│   └── multi_speaker_90s.wav        # Multiple speaker simulation
├── challenging/        # Difficult conditions
│   ├── heavy_noise_45s.wav          # Heavy background noise
│   └── overlapping_60s.wav          # Overlapping speech simulation
└── worst_case/         # Edge cases and error conditions
    ├── silent_5s.wav                # Silent audio
    ├── very_short_0.5s.wav          # Very short duration
    ├── very_long_10min.wav          # 10 minutes (chunking test)
    ├── pure_noise_30s.wav           # Only noise, no signal
    ├── corrupted.wav                # Truncated/corrupted file
    ├── wrong_format.wav             # Text file with .wav extension
    └── empty.wav                    # Empty file (0 bytes)
```

### Test Scenarios

#### Ideal Conditions
- **Expected Accuracy**: 95%+
- **Use Case**: Baseline performance validation
- **Characteristics**: Clean audio, no noise, clear signal

#### Moderate Conditions
- **Expected Accuracy**: 85-90%
- **Use Case**: Typical office/meeting scenarios
- **Characteristics**: Background noise, multiple speakers

#### Challenging Conditions
- **Expected Accuracy**: 70-80%
- **Use Case**: Difficult real-world scenarios
- **Characteristics**: Heavy noise, overlapping speech

#### Worst-Case Conditions
- **Expected Behavior**: Graceful failure, no crashes
- **Use Case**: Error handling validation
- **Characteristics**: Corrupted files, wrong formats, extreme conditions

### Regenerating Test Files

```bash
python scripts/generate_test_audio.py
```

### Adding Real Audio Samples

To add real voice recordings:
1. Place files in appropriate quality tier directory
2. Use supported formats: mp3, wav, m4a, ogg, flac
3. Keep file sizes reasonable (<100MB)
4. Update test cases to reference new files
