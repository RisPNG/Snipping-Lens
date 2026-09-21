import pytest
from pynput import keyboard

from sniplens.hotkey import NAMED_KEY_TO_PYNPUT, to_pynput_hotkey


def test_plain_modifiers():
    assert to_pynput_hotkey("ctrl+shift+s") == "<ctrl>+<shift>+s"


def test_sided_modifiers():
    assert to_pynput_hotkey("ralt+rctrl+\\") == "<alt_r>+<ctrl_r>+\\"
    assert to_pynput_hotkey("lwin+lshift+p") == "<cmd_l>+<shift_l>+p"


def test_meta_alias():
    assert to_pynput_hotkey("meta+a") == "<cmd>+a"


def test_whitespace_tolerated():
    assert to_pynput_hotkey("ctrl + s") == "<ctrl>+s"


def test_named_keys_are_bracketed():
    assert to_pynput_hotkey("f9") == "<f9>"
    assert to_pynput_hotkey("ctrl+space") == "<ctrl>+<space>"
    assert to_pynput_hotkey("ctrl+del") == "<ctrl>+<delete>"
    assert to_pynput_hotkey("alt+up") == "<alt>+<up>"
    assert to_pynput_hotkey("printscreen") == "<print_screen>"


def test_unknown_single_character_passes_through():
    assert to_pynput_hotkey("ctrl+\\") == "<ctrl>+\\"


@pytest.mark.parametrize("name", sorted(NAMED_KEY_TO_PYNPUT))
def test_every_named_key_is_accepted_by_pynput(name):
    keyboard.HotKey.parse(to_pynput_hotkey(f"ctrl+{name}"))


@pytest.mark.parametrize("hotkey", ["win+shift+s", "printscreen", "alt+ctrl+\\"])
def test_system_and_default_hotkeys_are_accepted_by_pynput(hotkey):
    keyboard.HotKey.parse(to_pynput_hotkey(hotkey))
