import logging

try:
    from pynput import keyboard

    HOTKEY_AVAILABLE = True
except ImportError:
    HOTKEY_AVAILABLE = False
    logging.warning("pynput not available. Alternate hotkey functionality disabled.")

MODIFIER_TO_PYNPUT = {
    "ralt": "<alt_r>",
    "lalt": "<alt_l>",
    "alt": "<alt>",
    "rctrl": "<ctrl_r>",
    "lctrl": "<ctrl_l>",
    "ctrl": "<ctrl>",
    "rshift": "<shift_r>",
    "lshift": "<shift_l>",
    "shift": "<shift>",
    "rwin": "<cmd_r>",
    "lwin": "<cmd_l>",
    "win": "<cmd>",
    "meta": "<cmd>",
}

# pynput reads anything outside angle brackets as a single character, so every
# key with a name rather than a character needs its own entry here or the
# listener refuses the whole combination.
NAMED_KEY_TO_PYNPUT = {
    "space": "<space>",
    "tab": "<tab>",
    "enter": "<enter>",
    "esc": "<esc>",
    "backspace": "<backspace>",
    "del": "<delete>",
    "ins": "<insert>",
    "home": "<home>",
    "end": "<end>",
    "pgup": "<page_up>",
    "pgdn": "<page_down>",
    "up": "<up>",
    "down": "<down>",
    "left": "<left>",
    "right": "<right>",
    "printscreen": "<print_screen>",
    "pause": "<pause>",
    "menu": "<menu>",
}
NAMED_KEY_TO_PYNPUT.update({f"f{number}": f"<f{number}>" for number in range(1, 21)})

MODIFIER_NAMES = frozenset(MODIFIER_TO_PYNPUT)
KEY_NAMES = frozenset(NAMED_KEY_TO_PYNPUT)


def to_pynput_hotkey(hotkey):
    parts = []
    for part in hotkey.split("+"):
        part = part.strip().lower()
        parts.append(
            MODIFIER_TO_PYNPUT.get(part) or NAMED_KEY_TO_PYNPUT.get(part, part)
        )
    return "+".join(parts)


class HotkeyController:
    """Keeps exactly one pynput global hotkey listener armed for the hotkeys
    the application currently wants. The listener does not suppress, so the
    keys it watches still reach the desktop."""

    def __init__(self):
        self._listener = None
        self._current = ()

    def reconfigure(self, hotkeys):
        """`hotkeys` maps a hotkey in the settings format to its callback. The
        callback for a given combination never varies, so comparing the
        combinations is enough to tell whether the listener must be rebuilt."""
        if not HOTKEY_AVAILABLE or tuple(hotkeys) == self._current:
            return
        self._stop_listener()
        self._current = tuple(hotkeys)
        if not hotkeys:
            logging.info("[Hotkey] No hotkeys to listen for.")
            return
        try:
            self._listener = keyboard.GlobalHotKeys(
                {to_pynput_hotkey(hotkey): callback for hotkey, callback in hotkeys.items()}
            )
            self._listener.start()
            logging.info("[Hotkey] Listening for: %s", ", ".join(hotkeys))
        except Exception as e:
            # a combination pynput refuses stays refused, so _current keeps the
            # attempt and the failure is not re-logged on every settings write
            logging.error("[Hotkey] Error setting up hotkeys %s: %s", ", ".join(hotkeys), e)
            self._listener = None

    def stop(self):
        self._stop_listener()
        self._current = ()

    def _stop_listener(self):
        if self._listener is not None:
            try:
                self._listener.stop()
                logging.info("[Hotkey] Stopped listener for: %s", ", ".join(self._current))
            except Exception as e:
                logging.error("[Hotkey] Error stopping listener: %s", e)
            self._listener = None
