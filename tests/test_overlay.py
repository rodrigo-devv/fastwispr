from fastwispr.windows.overlay import (
    append_level_history,
    display_segments,
    display_segments_from_history,
    idle_waveform_bar_heights,
    overlay_layout,
    overlay_theme,
    spinner_tick_angles,
    waveform_bar_heights,
    waveform_bar_heights_from_history,
)


def test_recording_layout_matches_compact_voice_reference():
    layout = overlay_layout("recording")

    assert layout["size"] == (141, 37)
    assert "icon" not in layout
    assert layout["pill"] == (0, 0, 141, 37)
    assert layout["waveform"] == (18, 9, 123, 28)
    assert layout["waveform_center_y"] == 18


def test_processing_layout_matches_compact_spinner_reference():
    layout = overlay_layout("processing")

    assert layout["size"] == (141, 37)
    assert layout["pill"] == (0, 0, 141, 37)
    assert layout["waveform"] == (18, 9, 98, 28)
    assert layout["waveform_center_y"] == 18
    assert layout["spinner_center"] == (122, 18)
    assert "icon" not in layout


def test_recording_and_processing_layouts_do_not_jump_between_states():
    recording = overlay_layout("recording")
    processing = overlay_layout("processing")

    assert processing["size"] == recording["size"]
    assert processing["pill"] == recording["pill"]
    assert processing["waveform_center_y"] == recording["waveform_center_y"]


def test_overlay_theme_is_black_compact_style():
    theme = overlay_theme()

    assert theme["transparent"] == "#010203"
    assert theme["panel"] == "#000000"
    assert theme["waveform"] == "#f2f2f2"
    assert theme["idle_waveform"] == "#8c8c8c"
    assert theme["spinner"] == "#bdbdbd"


def test_display_segments_shows_compact_idle_dots_for_silence():
    segments = display_segments(0.004, count=14)

    assert len(segments) == 14
    assert all(isinstance(value, int) for value in segments)
    assert 2 <= min(segments)
    assert max(segments) <= 4


def test_display_segments_activates_for_quiet_voice():
    idle = display_segments(0.004, count=14, phase=0)
    quiet_voice = display_segments(0.012, count=14, phase=0)

    assert max(quiet_voice) > max(idle)


def test_idle_waveform_bar_heights_have_subtle_motion():
    frame_a = idle_waveform_bar_heights(count=14, phase=0)
    frame_b = idle_waveform_bar_heights(count=14, phase=3)

    assert len(frame_a) == 14
    assert 2 <= min(frame_a)
    assert max(frame_a) <= 4
    assert frame_a != frame_b


def test_spinner_tick_angles_rotate_with_phase():
    frame_a = spinner_tick_angles(phase=0, count=8)
    frame_b = spinner_tick_angles(phase=2, count=8)

    assert frame_a[0] == 0
    assert len(frame_a) == 8
    assert frame_b[0] == 90


def test_waveform_bar_heights_grow_with_audio_level():
    quiet = waveform_bar_heights(0.1, count=5, phase=0)
    loud = waveform_bar_heights(0.8, count=5, phase=0)

    assert len(quiet) == 5
    assert len(loud) == 5
    assert max(loud) > max(quiet)
    assert min(loud) >= 2
    assert max(loud) == 16


def test_append_level_history_clamps_and_keeps_recent_values():
    history = append_level_history([0.1, 0.2], 1.5, limit=2)

    assert history == [0.2, 1.0]


def test_display_segments_from_history_uses_recent_voice_activity():
    silent = display_segments_from_history([0.003, 0.004], count=14)
    voiced = display_segments_from_history([0.003, 0.012, 0.004], count=14)

    assert len(silent) == 14
    assert max(silent) <= 4
    assert max(voiced) > max(silent)


def test_waveform_bar_heights_from_history_follows_actual_level_shape():
    heights = waveform_bar_heights_from_history([0.05, 0.65, 0.12], count=3, max_height=12)

    assert len(heights) == 3
    assert heights[1] > heights[0]
    assert heights[1] > heights[2]
