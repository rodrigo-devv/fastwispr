from datetime import datetime

from fastwispr.gui.theme import (
    FOOTER_H,
    HUB_DEFAULT,
    HUB_INSET_BOTTOM,
    HUB_INSET_RIGHT,
    HUB_MAX,
    HUB_MIN,
    OVERLAY_BORDER,
    OVERLAY_FILL,
    OVERLAY_H,
    OVERLAY_TOP,
    history_group_label,
    history_meta_line,
    hotkey_keycaps,
    hub_top_left,
    model_chip_label,
    overlay_enter_pos,
    overlay_rest_pos,
    resolve_theme_name,
    theme_tokens,
)


def test_hub_geometry_contract():
    assert HUB_DEFAULT == (400, 560)
    assert HUB_MIN == (380, 520)
    assert HUB_MAX == (460, 620)
    assert hub_top_left(1920, 1040, 400, 560) == (1920 - 400 - HUB_INSET_RIGHT, 1040 - 560 - HUB_INSET_BOTTOM)
    assert HUB_INSET_RIGHT == 20
    assert HUB_INSET_BOTTOM == 16
    assert FOOTER_H == 34
    assert OVERLAY_TOP == 24


def test_overlay_motion_contract():
    assert OVERLAY_H == 38
    rest = overlay_rest_pos(0, 0, 1920, 228, 38)
    assert rest == (846, 24)
    start = overlay_enter_pos(1920, 0, 228, 38)
    assert start[0] > 1920
    assert start[1] == 24
    assert start[1] == rest[1]
    assert OVERLAY_FILL == "#111315"
    assert OVERLAY_BORDER == "#272A2E"


def test_home_copy_uses_real_model_and_ctrl_space():
    assert model_chip_label("small") == "whisper-small"
    assert model_chip_label("base") == "whisper-base"
    assert hotkey_keycaps("ctrl+space") == ["Ctrl", "Space"]


def test_lucide_icon_catalog_covers_chrome():
    from fastwispr.gui.icons import ICON_NAMES, ICON_PX

    for name in ("sun", "moon", "minus", "x", "copy", "chevron-left", "chevron-right", "chevron-down", "settings", "book", "quote", "mic", "trash", "pencil", "more"):
        assert name in ICON_NAMES
    assert ICON_PX == 15


def test_light_theme_keeps_same_geometry_tokens():
    dark = theme_tokens("dark")
    light = theme_tokens("light")
    assert dark["bg"] == "#090A0B"
    assert light["bg"] == "#FFFFFF"
    assert dark["accent"].startswith("#")
    assert light["accent"].startswith("#")
    assert "surface_2" in dark and "border_hover" in light
    assert resolve_theme_name("system", system_is_dark=True) == "dark"
    assert resolve_theme_name("system", system_is_dark=False) == "light"
    assert resolve_theme_name("light") == "light"


def test_history_grouping():
    now = datetime(2026, 9, 13, 18, 0, 0)
    assert history_group_label("2026-09-13 17:42:00", now) == "Today"
    assert history_group_label("2026-09-12 17:42:00", now) == "Yesterday"
    assert "13:42" in history_meta_line("2026-09-13 13:42:00", 4800, now)
    assert history_meta_line("2026-09-13 13:42:00", 4800, now, include_group=False) == "13:42 · 4.8s"


def test_language_chip_label():
    from fastwispr.gui.theme import language_chip_label

    assert language_chip_label("en") == "EN"
    assert language_chip_label("pt-br") == "PT"
    assert language_chip_label("auto") == ""
    assert language_chip_label(None) == ""


def test_footer_ghost_hover_is_subtle():
    from fastwispr.gui.theme import app_qss

    tokens = theme_tokens("dark")
    hover = app_qss(tokens).split("QPushButton#FooterGhost:hover")[1].split("QPushButton#FooterGhost:pressed")[0]
    assert tokens["accent"] not in hover
    assert tokens["accent_soft"] not in hover
    assert tokens["surface_hover"] in hover


def test_secondary_label_uses_text_secondary():
    from fastwispr.gui.theme import app_qss

    tokens = theme_tokens("dark")
    block = app_qss(tokens).split("QLabel#Secondary")[1].split("QLabel#Meta")[0]
    assert tokens["text_secondary"] in block
    assert tokens["text_muted"] not in block
