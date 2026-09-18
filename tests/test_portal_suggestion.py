import pytest

from sniplens.capture.portal import portal_unavailable_message


@pytest.mark.parametrize(
    "desktop,package",
    [
        ("GNOME", "xdg-desktop-portal-gnome"),
        ("ubuntu:GNOME", "xdg-desktop-portal-gnome"),
        ("KDE", "xdg-desktop-portal-kde"),
        ("sway", "xdg-desktop-portal-wlr"),
        ("Hyprland", "xdg-desktop-portal-hyprland"),
        ("XFCE", "xdg-desktop-portal-gtk"),
    ],
)
def test_suggests_backend_for_known_desktops(monkeypatch, desktop, package):
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", desktop)
    message = portal_unavailable_message()
    assert package in message
    assert "Screenshot interface" in message


def test_generic_hint_for_unknown_desktop(monkeypatch):
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "SomethingExotic")
    message = portal_unavailable_message()
    assert "xdg-desktop-portal-gnome" in message
    assert "-wlr" in message


def test_generic_hint_when_unset(monkeypatch):
    monkeypatch.delenv("XDG_CURRENT_DESKTOP", raising=False)
    message = portal_unavailable_message()
    assert "portal backend" in message
