#!/usr/bin/env python3
# Snipping Lens ─ area-screenshot → Google Lens
# ────────────────────────────────────────────────────────────────
# Linux        : AppIndicator3
#   • LEFT-click  → gnome-screenshot -c -a → Lens
#   • RIGHT-click → Control window (Pause/Resume · See logs · Exit)
#
# Windows      : pystray + Tk window (unchanged)
# Other OSes   : unsupported
#
# Dependencies : Pillow, requests,
#                (Linux) python3-gi gir1.2-gtk-3.0 gir1.2-appindicator3-0.1,
#                         xclip or wl-paste
#                (Windows) pystray
# ----------------------------------------------------------------

import os
import sys
import io
import time
import tempfile
import logging
import subprocess
import platform
import threading
from datetime import datetime
from typing import Optional, Union

from PIL import Image, ImageDraw, UnidentifiedImageError, ImageGrab  # type: ignore
import requests  # type: ignore

# ───────── optional platform-specific libs ─────────
try:
    import pystray
    from pystray import Menu, MenuItem
except ImportError:
    pystray = None

GTK = None
Ind = None
if platform.system() == "Linux":
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        gi.require_version("AppIndicator3", "0.1")
        from gi.repository import Gtk, GObject, AppIndicator3  # type: ignore

        GTK = Gtk
        Ind = AppIndicator3
    except Exception:
        GTK = None
        Ind = None

TK = None
if platform.system() == "Windows":
    try:
        import tkinter as tk  # type: ignore
        TK = tk
    except ImportError:
        TK = None

# ───────── logging & paths ─────────
def _res(path: str) -> str:
    return os.path.join(getattr(sys, "_MEIPASS", os.path.abspath(".")), path)


LOG_DIR = os.path.expanduser("~/.cache/snippinglens")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "snippinglens.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

TRAY_ICON_PATH = _res("my_icon.png")


# ───────── helpers ─────────
def _img_hash(obj: Union[Image.Image, str]) -> Optional[int]:
    try:
        return hash(obj.tobytes() if isinstance(obj, Image.Image) else obj)
    except Exception:
        return None


def _default_icon() -> str:
    if os.path.exists(TRAY_ICON_PATH):
        return TRAY_ICON_PATH
    fallback = os.path.join(LOG_DIR, "tray_fallback.png")
    if not os.path.exists(fallback):
        img = Image.new("RGB", (64, 64), "black")
        ImageDraw.Draw(img).text((10, 20), "SL", fill="white")
        img.save(fallback)
    return fallback


# ══════════════════ main class ══════════════════
class SnippingLens:
    def __init__(self) -> None:
        self.is_linux = platform.system() == "Linux"
        self.is_windows = platform.system() == "Windows"

        self.paused = False
        self.is_running = True
        self.expecting_clip = False
        self.last_hash: int | None = None

        self.tray = None

    # ─────────── platform autostart ───────────
    def _setup_autostart(self):
        try:
            if self.is_windows:
                import winreg
                exe = (
                    f'"{sys.executable}"'
                    if getattr(sys, "frozen", False)
                    else f'"{os.path.join(os.path.dirname(sys.executable), "pythonw.exe")}" "{os.path.abspath(sys.argv[0])}"'
                )
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
                    0,
                    winreg.KEY_WRITE,
                ) as k:
                    winreg.SetValueEx(k, "SnippingLens", 0, winreg.REG_SZ, exe)
            elif self.is_linux:
                auto = os.path.expanduser("~/.config/autostart")
                os.makedirs(auto, exist_ok=True)
                with open(
                    os.path.join(auto, "snippinglens.desktop"),
                    "w",
                    encoding="utf-8",
                ) as f:
                    f.write(
                        "[Desktop Entry]\n"
                        "Type=Application\n"
                        f'Exec="{sys.executable}" "{os.path.abspath(sys.argv[0])}"\n'
                        "X-GNOME-Autostart-enabled=true\n"
                        "Name=SnippingLens\n"
                    )
        except Exception as e:
            logging.debug(f"Autostart not set: {e}")

    # ───────────── GUI window ─────────────
    def _toggle_pause(self, ui_button=None):
        self.paused = not self.paused
        label = "Resume" if self.paused else "Pause"
        if TK and isinstance(ui_button, TK.Button):
            ui_button.config(text=label)
        elif GTK and isinstance(ui_button, GTK.Button):
            ui_button.set_label(label)

    def _open_logs(self):
        if self.is_windows:
            os.startfile(LOG_PATH)
        else:
            subprocess.Popen(["xdg-open", LOG_PATH])

    def _open_control(self, *_):
        # Windows: Tk
        if self.is_windows and TK:
            root = TK.Tk()
            root.title("Snipping Lens")
            root.geometry("320x160")
            TK.Label(
                root, text="Snipping Lens is running.", font=("Segoe UI", 12)
            ).pack(pady=8)

            btn_pause = TK.Button(root, text="Pause", width=12)
            btn_pause.pack(pady=4)
            btn_pause.configure(command=lambda b=btn_pause: self._toggle_pause(b))

            TK.Button(root, text="See logs", width=12, command=self._open_logs).pack(
                pady=4
            )
            TK.Button(root, text="Exit", width=12, command=self._exit).pack(pady=4)

            root.mainloop()
            return

        # Linux: GTK control window
        if GTK:
            win = GTK.Window(title="Snipping Lens")
            win.set_default_size(340, 140)
            box = GTK.Box(orientation=GTK.Orientation.VERTICAL, spacing=10, margin=12)
            win.add(box)
            box.pack_start(
                GTK.Label(label="Snipping Lens is running."), False, False, 0
            )

            btn_pause = GTK.Button(label="Pause")
            btn_pause.connect("clicked", lambda *_: self._toggle_pause(btn_pause))
            btn_logs = GTK.Button(label="See logs")
            btn_logs.connect("clicked", lambda *_: self._open_logs())
            btn_exit = GTK.Button(label="Exit")
            btn_exit.connect("clicked", lambda *_: self._exit())

            for b in (btn_pause, btn_logs, btn_exit):
                box.pack_start(b, False, False, 0)

            win.show_all()

    # ───────────── tray actions ─────────────
    def _take_screenshot(self, *_):
        if self.paused:
            return
        try:
            subprocess.run(["gnome-screenshot", "-c", "-a"], check=True)
            self.expecting_clip = True
        except subprocess.CalledProcessError:
            logging.info("Screenshot cancelled by user.")

    # ───────────── clipboard loop ─────────────
    def _clipboard_loop(self):
        while self.is_running:
            if self.paused:
                time.sleep(0.3)
                continue

            if self.is_windows:
                src, h = self._clip_windows()
            else:
                src, h = self._clip_linux()

            if src is None or h == self.last_hash:
                time.sleep(0.3)
                continue
            self.last_hash = h

            if self.is_linux and not self.expecting_clip:
                continue
            self.expecting_clip = False

            threading.Thread(
                target=self._process_image, args=(src,), daemon=True
            ).start()
            time.sleep(0.3)

    # ───────────── clipboard getters ─────────────
    def _clip_windows(self):
        try:
            item = ImageGrab.grabclipboard()
            if isinstance(item, Image.Image):
                return item, _img_hash(item)
            if isinstance(item, list):
                for f in item:
                    if isinstance(f, str) and f.lower().endswith(
                        (".png", ".jpg", ".jpeg", ".bmp", ".gif")
                    ):
                        with Image.open(f) as im:
                            im.verify()
                        return f, _img_hash(f)
        except Exception:
            pass
        return None, None

    def _clip_linux(self):
        def _run(cmd):
            return subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=1)

        for cmd in (
            ["xclip", "-selection", "clipboard", "-t", "image/png", "-o"],
            ["wl-paste", "--type", "image/png"],
        ):
            try:
                data = _run(cmd)
                if data:
                    img = Image.open(io.BytesIO(data))
                    return img, _img_hash(img)
            except Exception:
                continue
        return None, None

    # ───────────── Google Lens upload ─────────────
    def _process_image(self, src: Union[Image.Image, str]) -> None:
        tmp: Optional[str] = None
        try:
            if isinstance(src, Image.Image):
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".png"
                ) as f:
                    (src.convert("RGB") if src.mode in ("RGBA", "P") else src).save(
                        f, "PNG"
                    )
                    tmp = f.name
                path = tmp
            else:
                path = src

            with open(path, "rb") as f:
                resp = requests.post(
                    "https://catbox.moe/user/api.php",
                    data={"reqtype": (None, "fileupload"), "userhash": (None, "")},
                    files={"fileToUpload": (os.path.basename(path), f)},
                    timeout=60,
                    headers={"User-Agent": "SnippingLens/1.0"},
                )
            url = resp.text.strip()
            if resp.ok and url.startswith("https://files.catbox.moe/"):
                webbrowser.open_new_tab(
                    f"https://lens.google.com/uploadbyurl?url={url}"
                )
        finally:
            if tmp and os.path.exists(tmp):
                os.unlink(tmp)

    # ───────────── tray init ─────────────
    def _tray_linux(self):
        icon_path = _default_icon()
        ind = Ind.Indicator.new(
            "snipping-lens",
            icon_path,
            Ind.IndicatorCategory.APPLICATION_STATUS,
        )
        ind.set_status(Ind.IndicatorStatus.ACTIVE)

        menu = GTK.Menu()

        def mk(label, cb):
            item = GTK.MenuItem(label=label)
            item.connect("activate", cb)
            item.show()
            menu.append(item)

        mk("Take Screenshot", lambda *_: self._take_screenshot())
        mk("Open Control", lambda *_: self._open_control())
        mk("See Logs", lambda *_: self._open_logs())
        mk(self.paused and "Resume" or "Pause", lambda *_: self._toggle_pause())
        mk("Exit", lambda *_: self._exit())

        ind.set_menu(menu)
        self.tray = ind

    def _tray_windows(self):
        if not pystray:
            logging.error("pystray missing.")
            sys.exit(1)

        def _toggle(icon, item):
            self._toggle_pause()
            item.text = "Resume" if self.paused else "Pause"
            icon.update_menu()

        menu = Menu(
            MenuItem("Open", self._open_control, default=True),
            MenuItem("See logs", lambda *_: self._open_logs()),
            MenuItem("Pause", _toggle),
            MenuItem("Exit", lambda *_: self._exit()),
        )
        self.tray = pystray.Icon(
            "SnippingLens",
            Image.open(_default_icon()),
            "Snipping Lens",
            menu,
        )
        self.tray.run_detached()

    # ───────────── lifecycle ─────────────
    def _exit(self):
        self.is_running = False
        if self.is_linux and GTK:
            GTK.main_quit()
        elif self.tray and pystray:
            try:
                self.tray.stop()
            except Exception:
                pass
        sys.exit(0)

    def start(self) -> None:
        self._setup_autostart()
        threading.Thread(target=self._clipboard_loop, daemon=True).start()

        if self.is_linux and GTK and Ind:
            self._tray_linux()
            GTK.main()
        elif self.is_windows:
            self._tray_windows()
            while self.is_running:
                time.sleep(1)
        else:
            logging.error("Unsupported platform or missing libraries.")
            sys.exit(1)


# ───────────── entry ─────────────
if __name__ == "__main__":
    try:
        SnippingLens().start()
    except KeyboardInterrupt:
        pass
