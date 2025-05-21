import os
import time
import threading
from PIL import ImageGrab, Image, ImageDraw, UnidentifiedImageError
import tempfile
import webbrowser
import logging
import sys
from datetime import datetime
import requests
import pystray
import psutil # Import psutil to check processes
import platform
import subprocess # For calling xclip and gnome-screenshot

# --- Configuration ---
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

TRAY_ICON_PATH = resource_path("my_icon.png")
LOG_FILE_NAME = "snipping_lens.log"

# OS Specific Configuration
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux" # Could be more specific for LMDE if needed

if IS_WINDOWS:
    SNIPPING_PROCESS_NAMES = ["SnippingTool.exe", "ScreenClippingHost.exe", "ScreenSketch.exe"]
    DEFAULT_SNIPPING_COMMAND = ["SnippingTool.exe"] # Or use "ms-screenclip:"
    # For ms-screenclip:
    # DEFAULT_SNIPPING_COMMAND = lambda: webbrowser.open("ms-screenclip:")
elif IS_LINUX:
    SNIPPING_PROCESS_NAMES = ["gnome-screenshot"]
    DEFAULT_SNIPPING_COMMAND = ["gnome-screenshot", "-c", "-a"]
else: # Fallback for other OS
    SNIPPING_PROCESS_NAMES = []
    DEFAULT_SNIPPING_COMMAND = []

PROCESS_SCAN_INTERVAL_SECONDS = 0.75
SNIP_PROCESS_TIMEOUT_SECONDS = 5.0 # Increased slightly for user action + clipboard propagation
# ---------------------

# Set up logging
log_file_path = LOG_FILE_NAME
try:
    # Try to place log file in a user-writable directory if frozen
    if getattr(sys, 'frozen', False):
        app_data_dir = os.path.join(os.path.expanduser('~'), '.SnippingLens')
        if not os.path.exists(app_data_dir):
            os.makedirs(app_data_dir)
        log_file_path = os.path.join(app_data_dir, LOG_FILE_NAME)
except Exception:
    pass # Fallback to current directory if user dir fails

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler(sys.stdout) # Keep console output for debugging
    ]
)

class SnippingLens:
    def __init__(self):
        self.last_clipboard_hash = None
        self.is_running = True
        self.is_paused = False
        self.icon = None
        self.last_snip_process_seen_time = 0.0
        self.process_state_lock = threading.Lock()
        self.pause_lock = threading.Lock() # For pausing/resuming state

        if not os.path.exists(TRAY_ICON_PATH):
            logging.warning(f"Custom tray icon not found at {TRAY_ICON_PATH}. A default will be generated.")
            self.tray_icon_image = self.create_default_image()
        else:
            try:
                self.tray_icon_image = Image.open(TRAY_ICON_PATH)
                logging.info(f"Using custom tray icon: {TRAY_ICON_PATH}")
            except Exception as e:
                logging.error(f"Failed to load custom tray icon '{TRAY_ICON_PATH}': {e}. Using default.")
                self.tray_icon_image = self.create_default_image()

        self.setup_autostart()

    def setup_autostart(self):
        try:
            executable_path_arg = f'"{sys.executable}"'
            if getattr(sys, 'frozen', False): # PyInstaller bundle
                executable_path = sys.executable
            else: # Running as script
                script_path = os.path.abspath(sys.argv[0])
                # Prefer pythonw on Windows if available for no console
                if IS_WINDOWS:
                    pythonw_path = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
                    if os.path.exists(pythonw_path):
                        executable_path_arg = f'"{pythonw_path}" "{script_path}"'
                    else:
                        executable_path_arg = f'"{sys.executable}" "{script_path}"'
                else: # Linux
                     executable_path_arg = f'"{sys.executable}" "{script_path}"'
                executable_path = executable_path_arg # For logging

            if IS_WINDOWS:
                import winreg
                key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE) as registry_key:
                    winreg.SetValueEx(registry_key, "SnippingLens", 0, winreg.REG_SZ, executable_path if getattr(sys, 'frozen', False) else executable_path_arg)
                logging.info(f"Added to Windows startup: {executable_path if getattr(sys, 'frozen', False) else executable_path_arg}")
            elif IS_LINUX:
                autostart_dir = os.path.expanduser("~/.config/autostart")
                if not os.path.exists(autostart_dir):
                    os.makedirs(autostart_dir)
                
                desktop_file_path = os.path.join(autostart_dir, "snippinglens.desktop")
                desktop_entry_exec = executable_path if getattr(sys, 'frozen', False) else executable_path_arg
                
                # Ensure the icon path for .desktop is absolute if using a local file not in theme
                icon_path_for_desktop = TRAY_ICON_PATH if os.path.exists(TRAY_ICON_PATH) else "utilities-graphics" # Fallback icon name

                desktop_content = f"""[Desktop Entry]
Name=Snipping Lens
Exec={desktop_entry_exec}
Icon={icon_path_for_desktop}
Type=Application
Categories=Utility;Graphics;
Comment=Automatically search screenshots with Google Lens
X-GNOME-Autostart-enabled=true
"""
                with open(desktop_file_path, "w") as f:
                    f.write(desktop_content)
                logging.info(f"Added to Linux autostart: {desktop_file_path} with Exec={desktop_entry_exec}")

        except PermissionError: logging.error("Permission denied for autostart setup.")
        except Exception as e: logging.error(f"Failed to add to autostart: {e}")

    def create_default_image(self):
        width, height = 64, 64
        image = Image.new('RGB', (width, height), "black")
        dc = ImageDraw.Draw(image)
        dc.text((10, 20), "SL", fill="white") # SL for Snipping Lens
        return image

    def take_snippet_action(self, icon=None, item=None):
        logging.info("Take Snippet action triggered.")
        if not DEFAULT_SNIPPING_COMMAND:
            logging.warning("No snipping command configured for this OS.")
            return

        try:
            if callable(DEFAULT_SNIPPING_COMMAND): # For commands like webbrowser.open
                DEFAULT_SNIPPING_COMMAND()
            else:
                subprocess.Popen(DEFAULT_SNIPPING_COMMAND)
            logging.info(f"Launched snipping tool: {DEFAULT_SNIPPING_COMMAND}")
            # Give the tool a moment to register its process
            time.sleep(0.5)
            # Manually mark that a snipping process was "seen"
            # This helps if the process scan is too slow or Popen doesn't keep it in psutil briefly
            with self.process_state_lock:
                self.last_snip_process_seen_time = time.time()
        except FileNotFoundError:
            logging.error(f"Snipping command not found: {DEFAULT_SNIPPING_COMMAND[0]}")
        except Exception as e:
            logging.error(f"Failed to launch snipping tool: {e}")

    def toggle_pause_resume(self, icon, item):
        with self.pause_lock:
            self.is_paused = not self.is_paused
        status = "Paused" if self.is_paused else "Resumed"
        logging.info(f"Application {status.lower()}.")
        # Update menu item text - this requires recreating the menu or finding the item
        # For simplicity, pystray doesn't directly support dynamic menu item text update easily.
        # A common workaround is to rebuild the menu, or use a checkable item.
        # Let's try checkable item.
        # Or, more simply, the user knows they clicked it. We can log it.
        # For dynamic text, we'd need to stop and restart the icon with a new menu, or manipulate menu.items
        if self.icon:
             # This is a bit of a hack, assuming the menu structure
            current_menu_items = list(self.icon.menu.items)
            for i, menu_item in enumerate(current_menu_items):
                if hasattr(menu_item, 'text') and "Pause" in menu_item.text or "Resume" in menu_item.text:
                    current_menu_items[i] = pystray.MenuItem(
                        "Resume" if self.is_paused else "Pause",
                        self.toggle_pause_resume,
                        checked=lambda item: self.is_paused # Visually indicates paused state
                    )
                    break
            self.icon.menu = pystray.Menu(*current_menu_items)
            if hasattr(self.icon, 'update_menu'): # Some backends might support this
                 self.icon.update_menu()


    def show_logs(self, icon, item):
        logging.info("Show Logs action triggered.")
        try:
            if os.path.exists(log_file_path):
                webbrowser.open(log_file_path) # Opens with default text editor/viewer
            else:
                logging.warning(f"Log file not found at {log_file_path}")
        except Exception as e:
            logging.error(f"Failed to open log file: {e}")

    def run_tray_icon(self):
        menu_items = [
            pystray.MenuItem("Take Snippet & Search", self.take_snippet_action, default=True),
            pystray.MenuItem("Pause" if not self.is_paused else "Resume", self.toggle_pause_resume, checked=lambda item: self.is_paused),
            pystray.MenuItem("Show Logs", self.show_logs),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self.exit_app)
        ]
        menu = pystray.Menu(*menu_items)
        self.icon = pystray.Icon("SnippingLens", self.tray_icon_image, "Snipping Lens", menu)
        logging.info("Running system tray icon.")
        self.icon.run()

    def exit_app(self, icon=None, item=None):
        logging.info("Exit requested.")
        self.is_running = False
        if self.icon:
            try: self.icon.stop()
            except Exception as e: logging.warning(f"Icon stop error: {e}")
        logging.info("Exiting application...")
        time.sleep(0.5)
        os._exit(0) # Force exit as threads might be lingering

    def get_image_hash(self, image):
        if isinstance(image, Image.Image):
            try: return hash(image.tobytes())
            except Exception: return None
        elif isinstance(image, str): return hash(image) # For file paths
        return None

    def get_google_lens_url(self, image_path):
        try:
            catbox_url = "https://catbox.moe/user/api.php"
            filename = os.path.basename(image_path)
            logging.info(f"Uploading {image_path} to Catbox.moe...")
            with open(image_path, 'rb') as f:
                payload = {'reqtype': (None, 'fileupload'), 'userhash': (None, '')}
                files = {'fileToUpload': (filename, f)}
                headers = {'User-Agent': 'SnippingLensScript/1.1'} # Version bump
                response = requests.post(catbox_url, files=files, data=payload, headers=headers, timeout=60)
            response.raise_for_status()
            catbox_link = response.text.strip()
            if response.status_code == 200 and catbox_link.startswith('https://files.catbox.moe/'):
                logging.info(f"Image uploaded: {catbox_link}")
                return f"https://lens.google.com/uploadbyurl?url={catbox_link}"
            else:
                logging.error(f"Failed Catbox upload. Status: {response.status_code}, Response: {response.text[:200]}...")
                return None
        except requests.exceptions.Timeout: logging.error("Catbox upload timed out."); return None
        except requests.exceptions.RequestException as e:
            response_details = f"Network error: {e}"
            if hasattr(e, 'response') and e.response is not None:
                response_details = f"Status: {e.response.status_code}, Response: {e.response.text[:200]}..."
            logging.error(f"Error uploading to Catbox: {response_details}"); return None
        except Exception as e: logging.error(f"Unexpected Catbox/Lens error: {e}", exc_info=True); return None

    def monitor_processes(self):
        logging.info("Starting process monitor thread...")
        while self.is_running:
            if self.is_paused:
                time.sleep(1); continue

            found_snipping_process = False
            try:
                for proc in psutil.process_iter(['name']):
                    if proc.info['name'] in SNIPPING_PROCESS_NAMES:
                        logging.debug(f"Detected running snipping process: {proc.info['name']}")
                        found_snipping_process = True
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess): pass
            except Exception as e: logging.error(f"Error scanning processes: {e}", exc_info=False)

            if found_snipping_process:
                with self.process_state_lock:
                    self.last_snip_process_seen_time = time.time()
            time.sleep(PROCESS_SCAN_INTERVAL_SECONDS)
        logging.info("Process monitor thread stopped.")

    def get_clipboard_image_linux(self):
        """Attempts to get an image from clipboard using xclip."""
        try:
            # Check if xclip is installed
            if subprocess.call(['which', 'xclip'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
                logging.warning("xclip is not installed. Cannot fetch clipboard image on Linux this way.")
                return None

            # Use temp file for xclip output
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_f:
                temp_image_path = temp_f.name
            
            # Command to extract PNG image from clipboard
            # xclip -selection clipboard -t image/png -o > file.png
            proc = subprocess.Popen(['xclip', '-selection', 'clipboard', '-t', 'image/png', '-o'], stdout=open(temp_image_path, 'wb'))
            proc.wait(timeout=2) # Wait for xclip to finish

            if os.path.getsize(temp_image_path) > 0:
                try:
                    img = Image.open(temp_image_path)
                    # img.load() # Force loading image data to catch errors early
                    logging.debug(f"Image successfully retrieved from clipboard via xclip: {temp_image_path}")
                    return img # Return PIL image object
                except UnidentifiedImageError:
                    logging.debug("No valid image found in clipboard via xclip (UnidentifiedImageError).")
                    return None
                finally:
                    # Keep the temp file for processing, it will be handled by process_screenshot
                    # Or, if we return the PIL image, we can delete it here if it's not needed as a file path later.
                    # For now, process_screenshot can handle PIL Image directly.
                    # If process_screenshot always needs a path, we should return temp_image_path.
                    # Let's make process_screenshot save the PIL image if it receives one.
                    # So, we can delete the temp_image_path from xclip here.
                    # os.unlink(temp_image_path) # No, process_screenshot needs a path for catbox
                    # Let's return the path, and process_screenshot will handle it.
                    # No, the current structure is that clipboard returns PIL.Image or path.
                    # Let's return PIL.Image and let process_screenshot save it to its own temp file.
                    # This means we need to ensure the image data is loaded before unlinking.
                    # img_copy = img.copy()
                    # os.unlink(temp_image_path)
                    # return img_copy
                    # Simpler: let process_screenshot handle the temp file from xclip directly.
                    # So, return temp_image_path.
                    # This means get_clipboard_image_linux returns a path, not a PIL.Image.
                    # This changes the contract of clipboard_content.
                    # Let's stick to returning PIL.Image if possible.
                    # The issue is that Image.open() is lazy.
                    # To ensure it's loaded before temp file is gone:
                    img_copy = Image.open(temp_image_path)
                    img_copy.load() # Force load
                    os.unlink(temp_image_path) # Clean up xclip's temp file
                    return img_copy

            else:
                os.unlink(temp_image_path) # Clean up empty file
                logging.debug("No image data in clipboard via xclip (empty output).")
                return None
        except subprocess.TimeoutExpired:
            logging.warning("xclip command timed out.")
            if temp_image_path and os.path.exists(temp_image_path): os.unlink(temp_image_path)
            return None
        except FileNotFoundError: # Should be caught by 'which xclip' but as a safeguard
            logging.warning("xclip command not found during execution.")
            if temp_image_path and os.path.exists(temp_image_path): os.unlink(temp_image_path)
            return None
        except Exception as e:
            logging.error(f"Error getting clipboard image with xclip: {e}")
            if 'temp_image_path' in locals() and temp_image_path and os.path.exists(temp_image_path):
                 try: os.unlink(temp_image_path)
                 except OSError: pass
            return None


    def monitor_clipboard(self):
        logging.info("Starting clipboard monitor...")
        while self.is_running:
            if self.is_paused:
                time.sleep(1); continue

            try:
                clipboard_content = None
                if IS_WINDOWS:
                    clipboard_content = ImageGrab.grabclipboard()
                elif IS_LINUX:
                    # Try xclip first for explicit image copy
                    clipboard_content = self.get_clipboard_image_linux()
                    if clipboard_content is None:
                        # Fallback to Pillow's ImageGrab if xclip fails or no image via xclip
                        # ImageGrab on Linux might use gnome-screenshot or other tools
                        try:
                            clipboard_content = ImageGrab.grabclipboard()
                        except Exception as e:
                            if "gnome-screenshot" in str(e).lower() or "scrot" in str(e).lower():
                                logging.debug(f"ImageGrab.grabclipboard() on Linux failed (tool error): {e}")
                            else:
                                logging.warning(f"ImageGrab.grabclipboard() on Linux failed: {e}")
                            clipboard_content = None


                if clipboard_content is None:
                    if self.last_clipboard_hash is not None: self.last_clipboard_hash = None
                    time.sleep(1); continue

                current_hash, image_to_process = None, None
                if isinstance(clipboard_content, Image.Image): # PIL Image object
                    current_hash = self.get_image_hash(clipboard_content)
                    image_to_process = clipboard_content
                elif isinstance(clipboard_content, list): # List of file paths (Windows)
                     for filename in clipboard_content:
                         if isinstance(filename, str) and os.path.isfile(filename) and \
                            filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                             try:
                                 # Verify it's an image without fully loading if not necessary
                                 with Image.open(filename) as img_test: img_test.verify()
                                 current_hash = self.get_image_hash(filename) # Hash the path
                                 image_to_process = filename # Process the path
                                 break
                             except (UnidentifiedImageError, FileNotFoundError, Exception):
                                 continue
                     if not image_to_process and self.last_clipboard_hash is not None:
                         self.last_clipboard_hash = None # Reset if no valid image file found

                is_new_content = (image_to_process is not None) and \
                                 (current_hash != self.last_clipboard_hash or \
                                  (current_hash is None and self.last_clipboard_hash is not None))

                if is_new_content:
                    logging.debug(f"New clipboard content detected (Type: {type(image_to_process)}). Checking source...")
                    should_process = False
                    with self.process_state_lock:
                        time_since_process_seen = time.time() - self.last_snip_process_seen_time

                    if 0 < time_since_process_seen <= SNIP_PROCESS_TIMEOUT_SECONDS:
                         logging.info(f"Content appeared {time_since_process_seen:.2f}s after snipping process/action. Processing.")
                         should_process = True
                    else:
                         logging.debug(f"Ignoring content (time since process/action: {time_since_process_seen:.2f}s > {SNIP_PROCESS_TIMEOUT_SECONDS}s or process not seen recently).")

                    if should_process:
                        process_thread = threading.Thread(target=self.process_screenshot, args=(image_to_process,), daemon=True)
                        process_thread.start()
                        self.last_clipboard_hash = current_hash
                    else:
                        self.last_clipboard_hash = current_hash # Update hash even if ignored

            except ImportError: # Pillow's ImageGrab might raise this if backend missing
                if self.last_clipboard_hash is not None: self.last_clipboard_hash = None
                logging.error("ImportError during clipboard access, check Pillow backend (e.g., scrot on Linux).")
            except Exception as e:
                 is_clipboard_error = "pywintypes.error" in repr(e) and ("OpenClipboard" in str(e) or "GetClipboardData" in str(e))
                 if not is_clipboard_error and "clipboard is empty" not in str(e).lower():
                     logging.error(f"Error monitoring clipboard: {e}", exc_info=False)
                 if self.last_clipboard_hash is not None: # Reset on any error to be safe
                     self.last_clipboard_hash = None
            finally:
                time.sleep(0.5)

    def process_screenshot(self, screenshot_source):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        temp_file_path_generated = None # Path of temp file *we* create
        image_path_to_upload = None # Path of file to actually upload

        try:
            if isinstance(screenshot_source, Image.Image): # PIL Image
                try:
                    # Create a temp file to save this image
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.png', prefix=f'sl_{timestamp}_') as temp_file:
                        img_to_save = screenshot_source
                        if img_to_save.mode in ['RGBA', 'P']: # Convert to RGB for wider compatibility (e.g. JPEG)
                            img_to_save = img_to_save.convert('RGB')
                        img_to_save.save(temp_file, format='PNG')
                        temp_file_path_generated = temp_file.name
                    image_path_to_upload = temp_file_path_generated
                    logging.info(f"Screenshot (from PIL.Image) saved to temp file: {image_path_to_upload}")
                except Exception as save_err:
                    logging.error(f"Failed to save PIL Image to temp file: {save_err}", exc_info=True)
                    return
            elif isinstance(screenshot_source, str) and os.path.isfile(screenshot_source): # File path
                image_path_to_upload = screenshot_source
                logging.info(f"Processing screenshot file: {image_path_to_upload}")
            else:
                logging.warning(f"Invalid screenshot_source type: {type(screenshot_source)}")
                return

            if not image_path_to_upload:
                logging.error("No valid image path to upload.")
                return

            search_url = self.get_google_lens_url(image_path_to_upload)
            if search_url:
                logging.info(f"Opening Lens URL: {search_url}")
                webbrowser.open_new_tab(search_url)
            else:
                logging.error("Failed to get Lens URL for the screenshot.")

        except Exception as e:
            logging.error(f"Error processing screenshot: {e}", exc_info=True)
        finally:
            # Clean up the temp file *we* generated for PIL images
            if temp_file_path_generated and os.path.exists(temp_file_path_generated):
                try:
                    os.unlink(temp_file_path_generated)
                    logging.info(f"Deleted temp file: {temp_file_path_generated}")
                except OSError as e:
                    logging.error(f"Error deleting temp file {temp_file_path_generated}: {e}")
            # Note: If screenshot_source was a path, we don't delete it, as it might be user's file.

    def start(self):
        process_monitor_thread = threading.Thread(target=self.monitor_processes, daemon=True)
        process_monitor_thread.start()

        clipboard_thread = threading.Thread(target=self.monitor_clipboard, daemon=True)
        clipboard_thread.start()

        logging.info(f"Snipping Lens started (PID: {os.getpid()}). Mode: {'Windows' if IS_WINDOWS else 'Linux' if IS_LINUX else 'Unknown OS'}.")
        logging.info("Using process detection + Catbox.moe for Google Lens.")
        logging.info("Left-click tray icon or use system's snipping tool (e.g., Win+Shift+S, gnome-screenshot).")
        logging.info(f"Logs are being saved to: {log_file_path}")

        try:
            self.run_tray_icon() # Blocks until exit
        except Exception as tray_err:
             logging.error(f"Failed to run system tray icon: {tray_err}", exc_info=True)
             print(f"\nError: Could not start system tray icon: {tray_err}. Check logs at {log_file_path}. Exiting.")
             self.exit_app() # Try graceful exit
             sys.exit(1)
        logging.info("Shutting down Snipping Lens...")

if __name__ == "__main__":
    # Basic dependency check
    missing_deps = []
    try: import requests
    except ImportError: missing_deps.append("requests")
    try: import pystray
    except ImportError: missing_deps.append("pystray")
    try: import PIL
    except ImportError: missing_deps.append("Pillow")
    try: import psutil
    except ImportError: missing_deps.append("psutil")

    if IS_LINUX:
        if subprocess.call(['which', 'xclip'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
            print("Warning: 'xclip' command not found. Clipboard image detection on Linux might be limited.")
            logging.warning("'xclip' command not found. Please install it for full clipboard functionality on Linux (e.g., sudo apt install xclip).")
        if subprocess.call(['which', 'gnome-screenshot'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
            print("Warning: 'gnome-screenshot' command not found. The 'Take Snippet' action on Linux might not work.")
            logging.warning("'gnome-screenshot' command not found. Please install it for the 'Take Snippet' action on Linux (e.g., sudo apt install gnome-screenshot).")


    if missing_deps:
         print(f"\nError: Missing critical Python libraries: {', '.join(missing_deps)}.")
         print(f"Please install them, e.g., using: pip install {' '.join(missing_deps)}")
         sys.exit(1)

    # --- Single instance lock (Optional, but good for tray apps) ---
    # This is a simple file-based lock. More robust methods exist (e.g., using a named mutex on Windows, or a PID file on Linux).
    lock_file_path = os.path.join(tempfile.gettempdir(), "snippinglens.lock")
    if os.path.exists(lock_file_path):
        try:
            with open(lock_file_path, 'r') as f:
                pid = int(f.read())
            if psutil.pid_exists(pid): # Check if the process is actually running
                # Check if the running process is indeed this script
                # This is a bit heuristic, could be improved by checking cmdline
                try:
                    proc = psutil.Process(pid)
                    if "snipping_lens.py" in " ".join(proc.cmdline()) or "Snipping Lens" in " ".join(proc.cmdline()): # Check for script name or PyInstaller name
                        logging.error("Another instance of Snipping Lens is already running.")
                        print("Error: Another instance of Snipping Lens is already running.")
                        sys.exit(1)
                    else: # Stale lock file from a different process
                        logging.warning("Stale lock file found, but PID does not match Snipping Lens. Overwriting.")
                except (psutil.NoSuchProcess, psutil.AccessDenied): # PID doesn't exist or can't be accessed
                    logging.warning("Stale lock file found (process not running or inaccessible). Overwriting.")
            else: # Stale lock file
                 logging.warning("Stale lock file found (process not running). Overwriting.")
        except Exception as e: # Handle issues reading lock file
            logging.warning(f"Could not properly read lock file, proceeding with caution: {e}")

    try:
        with open(lock_file_path, 'w') as f:
            f.write(str(os.getpid()))
        
        # Ensure lock file is removed on exit
        import atexit
        atexit.register(lambda: os.path.exists(lock_file_path) and os.remove(lock_file_path))

        snippinglens = SnippingLens()
        snippinglens.start()
    except SystemExit: # Allow sys.exit(1) from lock check to pass through
        pass
    except Exception as e:
         logging.critical(f"Critical error during startup or runtime: {e}", exc_info=True)
         print(f"\nCritical error: {e}. Check logs at {log_file_path}. Exiting.")
         if os.path.exists(lock_file_path): # Clean up lock file on critical error
             os.remove(lock_file_path)
         sys.exit(1)
    finally:
        if os.path.exists(lock_file_path) and str(os.getpid()) in open(lock_file_path).read(): # Only remove if this instance created it
            try: os.remove(lock_file_path)
            except Exception as e: logging.warning(f"Could not remove lock file: {e}")