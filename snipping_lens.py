import os
import sys
import time
import threading
import tempfile
import logging
import webbrowser
import subprocess
import platform
import io
from datetime import datetime

# Third‑party libs -----------------------------------------------------------
try:
    from PIL import Image, ImageDraw, UnidentifiedImageError
except ImportError:
    print("Missing Pillow. Install with:  pip install Pillow")
    sys.exit(1)

try:
    # ImageGrab works only on Windows / X11; we import lazily later for Linux.
    from PIL import ImageGrab  # noqa: E402
except Exception:
    ImageGrab = None  # type: ignore

try:
    import psutil
except ImportError:
    print("Missing psutil. Install with:  pip install psutil")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("Missing requests. Install with:  pip install requests")
    sys.exit(1)

try:
    import pystray
except ImportError:
    print("Missing pystray. Install with:  pip install pystray")
    sys.exit(1)

# ---------------------------------------------------------------------------

# --------------------------- configuration ---------------------------------

def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

TRAY_ICON_PATH = resource_path("my_icon.png")

# Timing
PROCESS_SCAN_INTERVAL_SECONDS = 0.75  # How often to scan running processes
SNIP_PROCESS_TIMEOUT_SECONDS = 4.0    # Window after seeing snip‑proc during which clipboard images are accepted

# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


class SnippingLens:
    """Cross‑platform clipboard‑to‑Google‑Lens helper."""

    def __init__(self) -> None:
        # Runtime state ------------------------------------------------------
        self.last_clipboard_hash: int | None = None
        self.is_running: bool = True
        self.icon: pystray.Icon | None = None
        self.last_snip_process_seen_time: float = 0.0
        self.process_state_lock = threading.Lock()

        # Platform detection -------------------------------------------------
        self.is_linux: bool = platform.system() == "Linux"
        self.is_windows: bool = platform.system() == "Windows"

        # Process names ------------------------------------------------------
        if self.is_windows:
            self.snipping_process_names = [
                "SnippingTool.exe",
                "ScreenClippingHost.exe",
                "ScreenSketch.exe",
            ]
        else:  # Linux / *nix
            self.snipping_process_names = [
                "gnome-screenshot",
                "cinnamon-screenshot",
                "flameshot",
            ]

        # Clipboard getter ---------------------------------------------------
        if self.is_windows:
            if ImageGrab is None:
                logging.error("ImageGrab unavailable on Windows!")
                sys.exit(1)
            self.clipboard_getter = self._grab_clipboard_windows
        else:
            self.clipboard_getter = self._grab_clipboard_linux

        # Autostart ----------------------------------------------------------
        self.setup_autostart()

    # --------------------------- autostart ---------------------------------
    def setup_autostart(self) -> None:
        """Add program to autostart (registry on Windows, .desktop on Linux)."""
        try:
            if self.is_windows:
                self._setup_autostart_windows()
            else:
                self._setup_autostart_linux()
        except Exception as e:
            logging.error(f"Failed to set autostart: {e}")

    def _setup_autostart_windows(self) -> None:
        import winreg  # Windows‑only

        if getattr(sys, "frozen", False):
            exec_path = sys.executable
            if not exec_path.lower().endswith(".exe"):
                pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
                exec_path = f'"{pythonw}" "{os.path.abspath(sys.argv[0])}"' if os.path.exists(pythonw) else f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
            else:
                exec_path = f'"{exec_path}"'
        else:
            pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            script = os.path.abspath(sys.argv[0])
            exec_path = f'"{pythonw}" "{script}"' if os.path.exists(pythonw) else f'"{sys.executable}" "{script}"'

        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, "SnippingLens", 0, winreg.REG_SZ, exec_path)
        logging.info("Added to Windows startup.")

    def _setup_autostart_linux(self) -> None:
        autostart_dir = os.path.expanduser("~/.config/autostart")
        os.makedirs(autostart_dir, exist_ok=True)
        desktop_file = os.path.join(autostart_dir, "snippinglens.desktop")

        exec_path = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
        desktop_entry = f"""[Desktop Entry]
Type=Application
Exec={exec_path}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=SnippingLens
"""
        with open(desktop_file, "w", encoding="utf-8") as f:
            f.write(desktop_entry)
        logging.info("Created autostart .desktop entry.")

    # --------------------------- tray icon ---------------------------------
    def create_default_image(self) -> Image.Image:
        width = 64
        height = 64
        img = Image.new("RGB", (width, height), "black")
        draw = ImageDraw.Draw(img)
        draw.text((10, 20), "SL", fill="white")
        return img

    def run_tray_icon(self) -> None:
        icon_image: Image.Image | None = None
        if TRAY_ICON_PATH and os.path.exists(TRAY_ICON_PATH):
            try:
                icon_image = Image.open(TRAY_ICON_PATH)
            except Exception as e:
                logging.warning(f"Custom icon failed to load: {e}")
        if icon_image is None:
            icon_image = self.create_default_image()

        menu = pystray.Menu(pystray.MenuItem("Exit", self.exit_app))
        self.icon = pystray.Icon("SnippingLens", icon_image, "Snipping Lens", menu)
        logging.info("System‑tray icon running.")
        self.icon.run()

    # --------------------------- exit --------------------------------------
    def exit_app(self, *_args) -> None:
        logging.info("Exit requested.")
        self.is_running = False
        if self.icon:
            try:
                self.icon.stop()
            except Exception as e:
                logging.debug(f"Icon stop error: {e}")
        logging.info("Application exiting…")
        time.sleep(0.5)
        os._exit(0)

    # --------------------------- helpers -----------------------------------
    @staticmethod
    def get_image_hash(image_or_path) -> int | None:
        if isinstance(image_or_path, Image.Image):
            try:
                return hash(image_or_path.tobytes())
            except Exception:
                return None
        elif isinstance(image_or_path, str):
            return hash(image_or_path)
        return None

    @staticmethod
    def get_google_lens_url(image_path: str) -> str | None:
        """Upload to Catbox and return Lens URL."""
        try:
            catbox_api = "https://catbox.moe/user/api.php"
            filename = os.path.basename(image_path)
            with open(image_path, "rb") as f:
                payload = {"reqtype": (None, "fileupload"), "userhash": (None, "")}
                files = {"fileToUpload": (filename, f)}
                headers = {"User-Agent": "SnippingLens/1.0"}
                resp = requests.post(catbox_api, data=payload, files=files, headers=headers, timeout=60)
            resp.raise_for_status()
            link = resp.text.strip()
            if resp.status_code == 200 and link.startswith("https://files.catbox.moe/"):
                return f"https://lens.google.com/uploadbyurl?url={link}"
            logging.error(f"Catbox upload failed: {resp.status_code} / {resp.text[:120]}")
        except Exception as e:
            logging.error(f"Catbox error: {e}")
        return None

    # ------------------------- process monitor -----------------------------
    def monitor_processes(self) -> None:
        logging.info("Process‑monitor thread started.")
        while self.is_running:
            found = False
            try:
                for proc in psutil.process_iter(["name"]):
                    if proc.info["name"] in self.snipping_process_names:
                        found = True
                        break
            except Exception:
                pass
            if found:
                with self.process_state_lock:
                    self.last_snip_process_seen_time = time.time()
            time.sleep(PROCESS_SCAN_INTERVAL_SECONDS)
        logging.info("Process‑monitor thread stopped.")

    # ------------------------- clipboard monitor ---------------------------
    def monitor_clipboard(self) -> None:
        logging.info("Clipboard‑monitor thread started.")
        while self.is_running:
            try:
                image_source, current_hash = self.clipboard_getter()
                if image_source is None:
                    if self.last_clipboard_hash is not None:
                        self.last_clipboard_hash = None
                    time.sleep(0.5)
                    continue

                is_new = (
                    current_hash != self.last_clipboard_hash
                    or (current_hash is None and self.last_clipboard_hash is not None)
                )

                if not is_new:
                    time.sleep(0.5)
                    continue

                # Was a snip‑proc seen very recently?
                with self.process_state_lock:
                    ago = time.time() - self.last_snip_process_seen_time
                if 0 < ago <= SNIP_PROCESS_TIMEOUT_SECONDS:
                    logging.info(f"Accepting clipboard image ({ago:.2f}s after snip‑proc).")
                    threading.Thread(
                        target=self.process_screenshot,
                        args=(image_source,),
                        daemon=True,
                    ).start()
                    self.last_clipboard_hash = current_hash
                else:
                    self.last_clipboard_hash = current_hash  # Ignore but record hash
            except Exception as e:
                logging.debug(f"Clipboard monitor error: {e}")
            time.sleep(0.5)
        logging.info("Clipboard‑monitor thread stopped.")

    # ----------------------- screenshot handler ----------------------------
    def process_screenshot(self, src) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        temp_path: str | None = None
        try:
            if isinstance(src, Image.Image):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png", prefix=f"ss_{timestamp}_") as tmp:
                    img = src.convert("RGB") if src.mode in ("RGBA", "P") else src
                    img.save(tmp, format="PNG", compress_level=0)  # lossless
                    temp_path = tmp.name
                image_path = temp_path
            elif isinstance(src, str) and os.path.isfile(src):
                image_path = src
            else:
                logging.warning("Invalid screenshot source.")
                return

            lens_url = self.get_google_lens_url(image_path)
            if lens_url:
                logging.info("Opening Google Lens…")
                webbrowser.open_new_tab(lens_url)
            else:
                logging.error("Could not obtain Lens URL.")
        except Exception as e:
            logging.error(f"Screenshot processing error: {e}")
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass

    # ----------------------- clipboard helpers -----------------------------
    def _grab_clipboard_windows(self):
        try:
            content = ImageGrab.grabclipboard()
            if isinstance(content, Image.Image):
                return content, self.get_image_hash(content)
            if isinstance(content, list):
                for fn in content:
                    if isinstance(fn, str) and os.path.isfile(fn) and fn.lower().endswith(
                        (".png", ".jpg", ".jpeg", ".bmp", ".gif")
                    ):
                        try:
                            with Image.open(fn) as im_test:
                                im_test.verify()
                            return fn, self.get_image_hash(fn)
                        except Exception:
                            continue
        except Exception:
            pass
        return None, None

    def _grab_clipboard_linux(self):
        # Prefer Xclip, fallback to wl‑paste (Wayland)
        def _run(cmd):
            return subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=1)

        try_cmds = [
            ["xclip", "-selection", "clipboard", "-t", "image/png", "-o"],
            ["wl-paste", "--type", "image/png"],
        ]
        for cmd in try_cmds:
            try:
                data = _run(cmd)
                if data:
                    img = Image.open(io.BytesIO(data))
                    return img, self.get_image_hash(img)
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                continue
            except UnidentifiedImageError:
                continue
            except Exception as e:
                logging.debug(f"Clipboard cmd error {cmd}: {e}")
        return None, None

    # ----------------------------- start -----------------------------------
    def start(self) -> None:
        threading.Thread(target=self.monitor_processes, daemon=True).start()
        threading.Thread(target=self.monitor_clipboard, daemon=True).start()

        logging.info("Snipping Lens started.")
        logging.info("Take screenshots with your OS tool; new clipboard images trigger Google Lens search.")
        try:
            self.run_tray_icon()
        except Exception as e:
            logging.error(f"Tray icon error: {e}")
            self.exit_app()


# ----------------------------- main ----------------------------------------
if __name__ == "__main__":
    try:
        snip = SnippingLens()
        snip.start()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.critical(f"Fatal error: {e}")
        print("Critical startup error. Check logs.")
