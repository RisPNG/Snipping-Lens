from sniplens.hotkey import to_pynput_hotkey


def test_plain_modifiers():
    assert to_pynput_hotkey("ctrl+shift+s") == "<ctrl>+<shift>+s"


def test_sided_modifiers():
    assert to_pynput_hotkey("ralt+rctrl+\\") == "<alt_r>+<ctrl_r>+\\"
    assert to_pynput_hotkey("lwin+lshift+p") == "<cmd_l>+<shift_l>+p"


def test_meta_alias():
    assert to_pynput_hotkey("meta+a") == "<cmd>+a"


def test_whitespace_tolerated():
    assert to_pynput_hotkey("ctrl + s") == "<ctrl>+s"


def test_single_key():
    assert to_pynput_hotkey("f9") == "f9"
