from pathlib import Path
import wave

from fastwispr.audio_stats import analyze_wav


def write_wav(path: Path, samples: list[int], sample_rate: int = 16000) -> Path:
    with wave.open(str(path), "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(sample_rate)
        frames = b"".join(sample.to_bytes(2, "little", signed=True) for sample in samples)
        fh.writeframes(frames)
    return path


def test_analyze_wav_reports_duration_rms_and_peak(tmp_path: Path):
    path = write_wav(tmp_path / "voice.wav", [1000, -1000] * 8000)

    stats = analyze_wav(path)

    assert stats.valid is True
    assert stats.duration_seconds == 1.0
    assert 0.030 < stats.rms_level < 0.031
    assert 0.030 < stats.peak_level < 0.031
    assert stats.frame_count == 16000


def test_analyze_wav_handles_invalid_audio_as_silence(tmp_path: Path):
    path = tmp_path / "bad.wav"
    path.write_bytes(b"not a wav")

    stats = analyze_wav(path)

    assert stats.valid is False
    assert stats.duration_seconds == 0.0
    assert stats.rms_level == 0.0
    assert stats.peak_level == 0.0
