import sys
import threading
from PyQt5 import QtWidgets, QtGui, QtCore

class TrayApp(QtWidgets.QSystemTrayIcon):
    def __init__(self, app, icon_path, on_left_click, on_pause_resume, on_show_logs, on_exit, is_paused=False):
        icon = QtGui.QIcon(icon_path) if icon_path else QtGui.QIcon()
        super().__init__(icon)
        self.app = app
        self.is_paused = is_paused
        self.on_left_click = on_left_click
        self.on_pause_resume = on_pause_resume
        self.on_show_logs = on_show_logs
        self.on_exit = on_exit

        self.menu = QtWidgets.QMenu()
        self.pause_action = self.menu.addAction("Pause" if not self.is_paused else "Resume")
        self.pause_action.triggered.connect(self.toggle_pause)
        self.menu.addAction("Show Logs", self.on_show_logs)
        self.menu.addAction("Exit", self.on_exit)
        self.setContextMenu(self.menu)

        self.activated.connect(self.handle_click)

    def handle_click(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.Trigger:  # Left click
            if self.on_left_click:
                threading.Thread(target=self.on_left_click, daemon=True).start()
        elif reason == QtWidgets.QSystemTrayIcon.Context:  # Right click
            # Menu will be shown automatically
            pass

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        self.pause_action.setText("Pause" if not self.is_paused else "Resume")
        if self.on_pause_resume:
            self.on_pause_resume()

def run_tray_qt(icon_path, on_left_click, on_pause_resume, on_show_logs, on_exit, is_paused=False):
    app = QtWidgets.QApplication(sys.argv)
    tray = TrayApp(app, icon_path, on_left_click, on_pause_resume, on_show_logs, on_exit, is_paused)
    tray.show()
    sys.exit(app.exec_())