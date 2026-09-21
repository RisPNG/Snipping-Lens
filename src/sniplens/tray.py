import logging

from PySide6.QtGui import QCursor, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from sniplens import APP_NAME, theme

MENU_STYLE = f"""
QMenu {{
    background-color: {theme.MENU_BACKGROUND};
    color: {theme.MENU_TEXT};
    border: 1px solid {theme.MENU_BORDER};
    padding: 5px;
}}
QMenu::item {{
    padding: 5px 20px;
    background-color: transparent;
}}
QMenu::item:selected {{
    background-color: {theme.MENU_HIGHLIGHT};
}}
"""


class TrayController:
    """Tray icon whose actions only forward commands into the application
    controller; it holds no application logic or state of its own."""

    def __init__(self, commands, icon_path, snip_on_left_click):
        self._commands = commands
        self._snip_on_left_click = snip_on_left_click
        self.tray_icon = QSystemTrayIcon(QIcon(icon_path))
        self.tray_icon.setToolTip(APP_NAME)
        self.tray_icon.activated.connect(self._on_activated)

        self.menu = QMenu()
        self.menu.setStyleSheet(MENU_STYLE)
        if not snip_on_left_click:
            # menu-owned actions; parentless QActions would be collected by
            # Python and disappear from the menu
            snip_action = self.menu.addAction("Snip")
            snip_action.triggered.connect(
                lambda: self._commands.request_snip(from_app_trigger=True)
            )
        open_action = self.menu.addAction("Open App")
        open_action.triggered.connect(self._commands.open_config_window)
        self.menu.addSeparator()
        quit_action = self.menu.addAction("Exit")
        quit_action.triggered.connect(self._commands.quit)
        self.tray_icon.setContextMenu(self.menu)

    def show(self):
        self.tray_icon.show()
        if not self.tray_icon.isVisible():
            logging.warning("The system tray is not available on this desktop.")
        else:
            logging.info("Tray icon shown.")

    def shutdown(self):
        self.tray_icon.hide()
        self.tray_icon.deleteLater()
        self.menu.deleteLater()

    def _on_activated(self, reason):
        if reason != QSystemTrayIcon.ActivationReason.Trigger:
            return
        if self._snip_on_left_click:
            self._commands.request_snip(from_app_trigger=True)
        else:
            self.menu.popup(QCursor.pos())
