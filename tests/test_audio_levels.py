from fastwispr.windows.audio import int16_rms_level


def test_int16_rms_level_returns_zero_for_silence():
    assert int16_rms_level(b"\x00\x00" * 8) == 0.0


def test_int16_rms_level_normalizes_loud_audio():
    assert int16_rms_level((32767).to_bytes(2, "little", signed=True) * 8) > 0.99
