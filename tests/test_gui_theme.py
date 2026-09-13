from datetime import datetime

from fastwispr.gui.theme import (
    HUB_DEFAULT,
    HUB_INSET_BOTTOM,
    HUB_INSET_RIGHT,
    HUB_MAX,
    HUB_MIN,
    OVERLAY_H,
    history_group_label,
    history_meta_line,
    hotkey_keycaps,
    hub_top_left,
    model_chip_label,
    overlay_enter_pos,
    overlay_rest_pos,
    resolve_theme_name,
)


def test_hub_geometry_contract():
    assert HUB_DEFAULT == (400, 560)
    assert HUB_MIN == (380, 520)
    assert HUB_MAX == (460, 620)
    assert hub_top_left(1920, 1040, 400, 560) == (1920 - 400 - HUB_INSET_RIGHT, 1040 - 560 - HUB_INSET_BOTTOM)
    assert HUB_INSET_RIGHT == 20
    assert HUB_INSET_BOTTOM == 16


def test_overlay_motion_contract():
    assert OVERLAY_H == 38
    assert overlay_rest_pos(1920, 168) == ((1920 - 168) // 2, 24)
    start = overlay_enter_pos(1920, 168)
    assert start[0] > 1920
    assert start[1] == 24


def test_home_copy_uses_real_model_and_ctrl_space():
    assert model_chip_label("small") == "whisper-small"
    assert model_chip_label("base") == "whisper-base"
    assert hotkey_keycaps("ctrl+space") == ["Ctrl", "Space"]


def test_theme_system_follows_os():
    assert resolve_theme_name("system", system_is_dark=True) == "dark"
    assert resolve_theme_name("system", system_is_dark=False) == "light"
    assert resolve_theme_name("light") == "light"


def test_history_grouping():
    now = datetime(2026, 9, 13, 18, 0, 0)
    assert history_group_label("2026-09-13 17:42:00", now) == "Today"
    assert history_group_label("2026-09-12 17:42:00", now) == "Yesterday"
    assert "13:42" in history_meta_line("2026-09-13 13:42:00", 4800, now)
