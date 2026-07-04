from io import BytesIO
import wave

from fastwispr.windows.sounds import (
    START_CUE,
    STOP_CUE,
    build_cue_wav,
    play_recording_started,
    play_recording_stopped,
    sound_smoke,
)


class FakeWinsound:
    SND_MEMORY = 0x0004
    SND_NODEFAULT = 0x0002

    def __init__(self):
        self.play_sound_calls = []
        self.beep_calls = []

    def PlaySound(self, sound, flags: int) -> None:
        self.play_sound_calls.append((sound, flags))

    def Beep(self, frequency: int, duration: int) -> None:
        self.beep_calls.append((frequency, duration))


def wav_info(data: bytes) -> tuple[int, int, int, int]:
    with wave.open(BytesIO(data), "rb") as fh:
        return fh.getnchannels(), fh.getsampwidth(), fh.getframerate(), fh.getnframes()


def peak_sample(data: bytes) -> int:
    with wave.open(BytesIO(data), "rb") as fh:
        frames = fh.readframes(fh.getnframes())
    samples = [int.from_bytes(frames[i : i + 2], "little", signed=True) for i in range(0, len(frames), 2)]
    return max(abs(sample) for sample in samples)


def test_start_and_stop_cues_are_short_subtle_product_sounds():
    assert START_CUE == ((720, 32), (960, 42))
    assert STOP_CUE == ((880, 30), (587, 48))

    for cue in (START_CUE, STOP_CUE):
        data = build_cue_wav(cue)
        channels, sample_width, framerate, frames = wav_info(data)
        duration_ms = frames / framerate * 1000
        assert channels == 1
        assert sample_width == 2
        assert framerate == 22050
        assert 60 <= duration_ms <= 95
        assert peak_sample(data) < 5000


def test_play_recording_started_uses_generated_wav_not_legacy_beep():
    winsound = FakeWinsound()

    assert play_recording_started(winsound_module=winsound, threaded=False) is True

    assert len(winsound.play_sound_calls) == 1
    sound, flags = winsound.play_sound_calls[0]
    assert flags & winsound.SND_MEMORY
    assert flags & winsound.SND_NODEFAULT
    assert wav_info(sound)[:3] == (1, 2, 22050)
    assert winsound.beep_calls == []


def test_play_recording_stopped_uses_generated_wav_not_legacy_beep():
    winsound = FakeWinsound()

    assert play_recording_stopped(winsound_module=winsound, threaded=False) is True

    assert len(winsound.play_sound_calls) == 1
    sound, flags = winsound.play_sound_calls[0]
    assert flags & winsound.SND_MEMORY
    assert flags & winsound.SND_NODEFAULT
    assert wav_info(sound)[:3] == (1, 2, 22050)
    assert winsound.beep_calls == []


def test_sound_smoke_plays_both_cues():
    winsound = FakeWinsound()

    assert sound_smoke(winsound_module=winsound) is True

    assert len(winsound.play_sound_calls) == 2
    assert winsound.beep_calls == []
