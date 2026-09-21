from types import SimpleNamespace

import pytest

from sniplens.app import SYSTEM_SNIP_HOTKEYS, ApplicationController
from sniplens.settings import ALWAYS_ON, PAUSED, TRAY_ONLY


def controller(**core):
    """A controller with only the attributes the policy methods read. The Qt
    base class is deliberately left uninitialised - these methods touch nothing
    but plain Python state."""
    values = {"tray_status": ALWAYS_ON, "alternate_hotkey": "", "alternate_hotkey_bypass": True}
    values.update(core)
    instance = ApplicationController.__new__(ApplicationController)
    instance._core = SimpleNamespace(**values)
    return instance


@pytest.mark.parametrize(
    "status,from_app_trigger,expected",
    [
        (PAUSED, True, False),
        (PAUSED, False, False),
        (TRAY_ONLY, True, True),
        (TRAY_ONLY, False, False),
        (ALWAYS_ON, True, True),
        (ALWAYS_ON, False, True),
    ],
)
def test_search_policy(status, from_app_trigger, expected):
    assert controller(tray_status=status)._should_search(from_app_trigger) is expected


def test_no_hotkeys_when_none_configured(monkeypatch):
    monkeypatch.setattr("sniplens.app.paths.IS_WINDOWS", False)
    assert controller()._hotkeys() == {}


def test_alternate_hotkey_is_registered(monkeypatch):
    monkeypatch.setattr("sniplens.app.paths.IS_WINDOWS", False)
    assert list(controller(alternate_hotkey="alt+ctrl+\\")._hotkeys()) == ["alt+ctrl+\\"]


def test_windows_also_watches_the_system_snip_keys(monkeypatch):
    """Windows reaches the Snipping Tool through keys we do not own, so the
    listener has to watch them to arm a transaction for those captures."""
    monkeypatch.setattr("sniplens.app.paths.IS_WINDOWS", True)
    hotkeys = controller(alternate_hotkey="ctrl+shift+s")._hotkeys()
    assert set(hotkeys) == {"ctrl+shift+s", *SYSTEM_SNIP_HOTKEYS}


def test_system_snip_keys_are_not_watched_on_linux(monkeypatch):
    monkeypatch.setattr("sniplens.app.paths.IS_WINDOWS", False)
    assert set(controller(alternate_hotkey="ctrl+shift+s")._hotkeys()) == {"ctrl+shift+s"}


def test_alternate_hotkey_follows_the_bypass_setting(monkeypatch):
    """With bypass off the alternate hotkey must count as a user snip, not an
    app-triggered one, so Tray Only mode does not search it."""
    monkeypatch.setattr("sniplens.app.paths.IS_WINDOWS", False)
    requested = []
    instance = controller(alternate_hotkey="ctrl+shift+s", alternate_hotkey_bypass=False)
    instance.request_snip = lambda from_app_trigger=True: requested.append(from_app_trigger)
    instance._hotkeys()["ctrl+shift+s"]()
    assert requested == [False]

    instance._core.alternate_hotkey_bypass = True
    instance._hotkeys()["ctrl+shift+s"]()
    assert requested == [False, True]
