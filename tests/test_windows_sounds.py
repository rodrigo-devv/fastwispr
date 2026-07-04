from fastwispr.windows.sounds import play_recording_started, play_recording_stopped


class FakeWinsound:
    def __init__(self):
        self.calls = []

    def Beep(self, frequency: int, duration: int) -> None:
        self.calls.append((frequency, duration))


def test_play_recording_started_uses_short_rising_beep_sequence():
    winsound = FakeWinsound()

    assert play_recording_started(winsound_module=winsound, threaded=False) is True

    assert winsound.calls == [(880, 45), (1175, 65)]


def test_play_recording_stopped_uses_short_falling_beep_sequence():
    winsound = FakeWinsound()

    assert play_recording_stopped(winsound_module=winsound, threaded=False) is True

    assert winsound.calls == [(660, 55), (440, 65)]
