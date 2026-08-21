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


def to_pynput_hotkey(hotkey):
    parts = []
    for part in hotkey.split("+"):
        part = part.strip().lower()
        parts.append(MODIFIER_TO_PYNPUT.get(part, part))
    return "+".join(parts)


class HotkeyController:
    """Keeps exactly one pynput global hotkey listener armed for the hotkey
    currently stored in the settings."""

    def __init__(self, on_triggered):
        self._on_triggered = on_triggered
        self._listener = None
        self._current_hotkey = None

    def reconfigure(self, hotkey):
        if not HOTKEY_AVAILABLE or hotkey == self._current_hotkey:
            return
        self._stop_listener()
        self._current_hotkey = hotkey
        if not hotkey:
            logging.info("[Hotkey] No alternate hotkey set.")
            return
        try:
            self._listener = keyboard.GlobalHotKeys(
                {to_pynput_hotkey(hotkey): self._on_triggered}
            )
            self._listener.start()
            logging.info("[Hotkey] Listening for: %s", hotkey)
        except Exception as e:
            logging.error("[Hotkey] Error setting up hotkey '%s': %s", hotkey, e)
            self._listener = None
            self._current_hotkey = None

    def stop(self):
        self._stop_listener()
        self._current_hotkey = None

    def _stop_listener(self):
        if self._listener is not None:
            try:
                self._listener.stop()
                logging.info("[Hotkey] Stopped listener for: %s", self._current_hotkey)
            except Exception as e:
                logging.error("[Hotkey] Error stopping listener: %s", e)
            self._listener = None
