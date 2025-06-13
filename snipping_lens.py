import os
import time

# Check for GUI environment (DISPLAY variable)
if os.name == "posix" and not os.environ.get("DISPLAY"):
    print("Warning: No DISPLAY environment variable found. The tray icon will not appear unless run in a graphical session.")
    import logging
    logging.warning("No DISPLAY environment variable found. The tray icon will not appear unless run in a graphical session.")

import threading
import tempfile
import webbrowser
import logging
import sys
import platform
import subprocess
from datetime import datetime
import requests
from PIL import Image, ImageDraw
from tray_qt import run_tray_qt

# Platform-specific imports
if platform.system() == "Windows":
    from PIL import ImageGrab
    import winreg
    import psutil
else:
    import psutil
    import signal
    from pathlib import Path

# --- Configuration ---
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

TRAY_ICON_PATH = resource_path("my_icon.png")
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"

# Windows-specific configuration
if IS_WINDOWS:
    SNIPPING_PROCESS_NAMES = ["SnippingTool.exe", "ScreenClippingHost.exe", "ScreenSketch.exe"]
    PROCESS_SCAN_INTERVAL_SECONDS = 0.75
    SNIP_PROCESS_TIMEOUT_SECONDS = 4.0
else:
    # Linux-specific configuration
    SNIPPING_PROCESS_NAMES = ["gnome-screenshot"]
    PROCESS_SCAN_INTERVAL_SECONDS = 0.5
    SNIP_PROCESS_TIMEOUT_SECONDS = 3.0

# Set up logging
class LogHandler:
    def __init__(self):
        self.logs = []
        self.max_logs = 1000
        
    def add_log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)
        if len(self.logs) > self.max_logs:
            self.logs.pop(0)
        print(log_entry)
    
    def get_logs(self):
        return "\n".join(self.logs)

log_handler = LogHandler()

# Custom logging formatter
class CustomFormatter(logging.Formatter):
    def format(self, record):
        formatted = super().format(record)
        log_handler.add_log(formatted)
        return formatted

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Replace the default formatter
for handler in logging.getLogger().handlers:
    handler.setFormatter(CustomFormatter())

class SnippingLens:
    def __init__(self):
        self.last_clipboard_hash = None
        self.is_running = True
        self.is_paused = False
        self.icon = None
        self.last_snip_process_seen_time = 0.0
        self.process_state_lock = threading.Lock()
        self.log_window = None
        
        if IS_WINDOWS:
            self.setup_autostart_windows()
        else:
            self.setup_autostart_linux()

    def setup_autostart_windows(self):
        """Setup autostart for Windows"""
        try:
            if getattr(sys, 'frozen', False):
                executable_path = sys.executable
                if not executable_path.lower().endswith('.exe'):
                    pythonw_path = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
                    if os.path.exists(pythonw_path):
                        executable_path = f'"{pythonw_path}" "{os.path.abspath(sys.argv[0])}"'
                    else:
                        executable_path = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
                else:
                    executable_path = f'"{executable_path}"'
            else:
                pythonw_path = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
                script_path = os.path.abspath(sys.argv[0])
                if os.path.exists(pythonw_path):
                    executable_path = f'"{pythonw_path}" "{script_path}"'
                else:
                    executable_path = f'"{sys.executable}" "{script_path}"'
            
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE) as registry_key:
                winreg.SetValueEx(registry_key, "SnippingLens", 0, winreg.REG_SZ, executable_path)
            logging.info(f"Added to Windows startup: {executable_path}")
        except PermissionError:
            logging.error("Permission denied writing to registry for autostart.")
        except Exception as e:
            logging.error(f"Failed to add to Windows startup: {e}")

    def setup_autostart_linux(self):
        """Setup autostart for Linux"""
        try:
            autostart_dir = os.path.expanduser("~/.config/autostart")
            os.makedirs(autostart_dir, exist_ok=True)
            
            desktop_file_path = os.path.join(autostart_dir, "snipping-lens.desktop")
            
            if getattr(sys, 'frozen', False):
                executable_path = sys.executable
            else:
                executable_path = f"python3 {os.path.abspath(sys.argv[0])}"
            
            desktop_content = f"""[Desktop Entry]
Type=Application
Name=Snipping Lens
Exec={executable_path}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Comment=Automatic Google Lens search for screenshots
"""
            
            with open(desktop_file_path, 'w') as f:
                f.write(desktop_content)
            
            os.chmod(desktop_file_path, 0o755)
            logging.info(f"Added to Linux autostart: {desktop_file_path}")
        except Exception as e:
            logging.error(f"Failed to add to Linux startup: {e}")

    def create_default_image(self):
        """Create a default tray icon"""
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), "black")
        dc = ImageDraw.Draw(image)
        dc.text((10, 20), "SL", fill="white")
        return image

    def take_screenshot(self):
        """Take a screenshot using platform-specific tools"""
        try:
            logging.info(f"take_screenshot called. Platform: {'Windows' if IS_WINDOWS else 'Linux'}")
            if IS_WINDOWS:
                # Launch Windows Snipping Tool
                logging.info("About to launch Windows Snipping Tool (ms-screenclip:)")
                subprocess.Popen(["ms-screenclip:"])
                logging.info("Launched Windows Snipping Tool")
            else:
                # Launch gnome-screenshot on Linux
                logging.info("About to launch gnome-screenshot with: gnome-screenshot -c -a")
                subprocess.Popen(["gnome-screenshot", "-c", "-a"])
                logging.info("Launched gnome-screenshot")
        except Exception as e:
            logging.error(f"Failed to launch screenshot tool: {e}")

    def force_snip_and_search(self, icon=None, item=None):
        """
        Force a snip and search, regardless of pause state.
        This is used for left-click tray icon action.
        """
        try:
            import time

            timeout = 10
            poll_interval = 0.3
            start_time = time.time()
            found_image = None

            if IS_WINDOWS:
                from PIL import ImageGrab
                # Get initial clipboard hash
                initial_clipboard = None
                try:
                    initial_clipboard = ImageGrab.grabclipboard()
                except Exception:
                    initial_clipboard = None
                initial_hash = self.get_image_hash(initial_clipboard)

                self.take_screenshot()

                while time.time() - start_time < timeout:
                    clipboard_content = None
                    try:
                        clipboard_content = ImageGrab.grabclipboard()
                    except Exception:
                        clipboard_content = None

                    current_hash = self.get_image_hash(clipboard_content)
                    if current_hash and current_hash != initial_hash:
                        if isinstance(clipboard_content, list):
                            for filename in clipboard_content:
                                if isinstance(filename, str) and os.path.isfile(filename) and \
                                    filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                                    found_image = filename
                                    break
                        elif isinstance(clipboard_content, Image.Image):
                            found_image = clipboard_content

                    if found_image:
                        break
                    time.sleep(poll_interval)
            else:
                # Linux: use get_clipboard_image_linux
                # Get initial clipboard hash
                initial_clipboard = self.get_clipboard_image_linux()
                initial_hash = self.get_image_hash(initial_clipboard)

                self.take_screenshot()

                while time.time() - start_time < timeout:
                    clipboard_content = self.get_clipboard_image_linux()
                    current_hash = self.get_image_hash(clipboard_content)
                    if clipboard_content is not None and current_hash != initial_hash:
                        found_image = clipboard_content
                        break
                    time.sleep(poll_interval)

            if found_image:
                logging.info("Snip detected from left-click, processing regardless of pause state.")
                process_thread = threading.Thread(target=self.process_screenshot, args=(found_image,), daemon=True)
                process_thread.start()
            else:
                logging.error("No snip detected in clipboard after left-click action.")

        except Exception as e:
            logging.error(f"Error in force_snip_and_search: {e}", exc_info=True)

    def toggle_pause(self):
        """Toggle pause/resume state"""
        self.is_paused = not self.is_paused
        state = "Paused" if self.is_paused else "Resumed"
        logging.info(f"Snipping Lens {state}")
        
        # Update the tray icon menu
        self.update_tray_menu()

    def show_logs(self):
        """Show logs in a simple text window"""
        try:
            logs = log_handler.get_logs()
            if IS_WINDOWS:
                # On Windows, create a temporary file and open with notepad
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write("=== Snipping Lens Logs ===\n\n")
                    f.write(logs)
                    temp_path = f.name
                subprocess.Popen(['notepad.exe', temp_path])
            else:
                # On Linux, try to open with default text editor
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write("=== Snipping Lens Logs ===\n\n")
                    f.write(logs)
                    temp_path = f.name
                
                # Try various text editors
                editors = ['gedit', 'kate', 'mousepad', 'leafpad', 'xed', 'nano']
                for editor in editors:
                    try:
                        subprocess.Popen([editor, temp_path])
                        break
                    except FileNotFoundError:
                        continue
                else:
                    # Fallback to xdg-open
                    subprocess.Popen(['xdg-open', temp_path])
        except Exception as e:
            logging.error(f"Failed to show logs: {e}")

    def update_tray_menu(self):
        """Update tray menu with current state"""
        if self.icon:
            pause_text = "Resume" if self.is_paused else "Pause"
            menu = pystray.Menu(
                pystray.MenuItem(pause_text, self.toggle_pause),
                pystray.MenuItem("Show Logs", self.show_logs),
                pystray.MenuItem("Exit", self.exit_app)
            )
            self.icon.menu = menu

    def run_tray_icon(self):
        """Run the system tray icon using PyQt5"""
        icon_path = TRAY_ICON_PATH if os.path.exists(TRAY_ICON_PATH) else None

        def on_left_click():
            self.force_snip_and_search()

        def on_pause_resume():
            self.toggle_pause()

        def on_show_logs():
            self.show_logs()

        def on_exit():
            self.exit_app()

        logging.info("Running system tray icon (PyQt5/QSystemTrayIcon).")
        run_tray_qt(
            icon_path=icon_path,
            on_left_click=on_left_click,
            on_pause_resume=on_pause_resume,
            on_show_logs=on_show_logs,
            on_exit=on_exit,
            is_paused=self.is_paused
        )

    def exit_app(self, icon=None, item=None):
        """Exit the application"""
        logging.info("Exit requested.")
        self.is_running = False
        
        if self.icon:
            try:
                self.icon.stop()
            except Exception as e:
                logging.warning(f"Icon stop error: {e}")
        
        logging.info("Exiting application...")
        time.sleep(0.5)
        os._exit(0)

    def get_image_hash(self, image):
        """Get hash of image for comparison"""
        if isinstance(image, Image.Image):
            try:
                return hash(image.tobytes())
            except Exception:
                return None
        elif isinstance(image, str):
            return hash(image)
        return None

    def get_google_lens_url(self, image_path):
        """Upload image to Catbox and get Google Lens URL"""
        try:
            catbox_url = "https://catbox.moe/user/api.php"
            filename = os.path.basename(image_path)
            logging.info(f"Uploading {image_path} to Catbox.moe...")
            
            with open(image_path, 'rb') as f:
                payload = {'reqtype': (None, 'fileupload'), 'userhash': (None, '')}
                files = {'fileToUpload': (filename, f)}
                headers = {'User-Agent': 'SnippingLensScript/1.0'}
                response = requests.post(catbox_url, files=files, data=payload, headers=headers, timeout=60)
            
            response.raise_for_status()
            catbox_link = response.text.strip()
            
            if response.status_code == 200 and catbox_link.startswith('https://files.catbox.moe/'):
                logging.info(f"Image uploaded: {catbox_link}")
                return f"https://lens.google.com/uploadbyurl?url={catbox_link}"
            else:
                logging.error(f"Failed Catbox upload. Status: {response.status_code}, Response: {response.text[:200]}...")
                return None
        except requests.exceptions.Timeout:
            logging.error("Catbox upload timed out.")
            return None
        except requests.exceptions.RequestException as e:
            response_details = f"Network error: {e}"
            if hasattr(e, 'response') and e.response is not None:
                response_details = f"Status: {e.response.status_code}, Response: {e.response.text[:200]}..."
            logging.error(f"Error uploading to Catbox: {response_details}")
            return None
        except Exception as e:
            logging.error(f"Unexpected Catbox/Lens error: {e}", exc_info=True)
            return None

    def get_clipboard_image_linux(self):
        """Get image from clipboard on Linux using xclip"""
        try:
            # Check if xclip is available
            result = subprocess.run(['which', 'xclip'], capture_output=True)
            if result.returncode != 0:
                logging.error("xclip not found. Please install it: sudo apt install xclip")
                return None
            
            # Get available clipboard targets
            result = subprocess.run(['xclip', '-selection', 'clipboard', '-t', 'TARGETS', '-o'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                return None
            
            targets = result.stdout.strip().split('\n')
            
            # Look for image targets
            image_targets = ['image/png', 'image/jpeg', 'image/jpg', 'image/bmp']
            available_image_target = None
            
            for target in image_targets:
                if target in targets:
                    available_image_target = target
                    break
            
            if not available_image_target:
                return None
            
            # Get the image data
            result = subprocess.run(['xclip', '-selection', 'clipboard', '-t', available_image_target, '-o'],
                                  capture_output=True)
            if result.returncode != 0 or not result.stdout:
                return None
            
            # Save to temporary file and open with PIL
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                temp_file.write(result.stdout)
                temp_path = temp_file.name
            
            try:
                image = Image.open(temp_path)
                # Convert to RGB if necessary
                if image.mode in ['RGBA', 'P']:
                    image = image.convert('RGB')
                return image
            except Exception as e:
                logging.error(f"Failed to open clipboard image: {e}")
                return None
            finally:
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
        except Exception as e:
            logging.error(f"Error getting clipboard image on Linux: {e}")
            return None

    def monitor_processes(self):
        """Monitor for snipping tool processes"""
        logging.info("Starting process monitor thread...")
        while self.is_running:
            if self.is_paused:
                time.sleep(PROCESS_SCAN_INTERVAL_SECONDS)
                continue
                
            found_snipping_process = False
            try:
                for proc in psutil.process_iter(['name']):
                    if proc.info['name'] in SNIPPING_PROCESS_NAMES:
                        logging.debug(f"Detected running snipping process: {proc.info['name']}")
                        found_snipping_process = True
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
            except Exception as e:
                logging.error(f"Error scanning processes: {e}", exc_info=False)

            if found_snipping_process:
                with self.process_state_lock:
                    self.last_snip_process_seen_time = time.time()

            time.sleep(PROCESS_SCAN_INTERVAL_SECONDS)
        logging.info("Process monitor thread stopped.")

    def monitor_clipboard(self):
        """Monitor clipboard for new images"""
        logging.info("Starting clipboard monitor...")
        while self.is_running:
            if self.is_paused:
                time.sleep(1)
                continue
                
            try:
                clipboard_content = None
                
                if IS_WINDOWS:
                    clipboard_content = ImageGrab.grabclipboard()
                else:
                    clipboard_content = self.get_clipboard_image_linux()
                
                if clipboard_content is None:
                    if self.last_clipboard_hash is not None:
                        self.last_clipboard_hash = None
                    time.sleep(1)
                    continue

                current_hash = None
                image_to_process = None
                
                if isinstance(clipboard_content, Image.Image):
                    current_hash = self.get_image_hash(clipboard_content)
                    image_to_process = clipboard_content
                elif isinstance(clipboard_content, list):
                    for filename in clipboard_content:
                        if isinstance(filename, str) and os.path.isfile(filename) and \
                           filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                            try:
                                with Image.open(filename) as img_test:
                                    img_test.verify()
                                current_hash = self.get_image_hash(filename)
                                image_to_process = filename
                                break
                            except Exception:
                                continue
                    if not image_to_process and self.last_clipboard_hash is not None:
                        self.last_clipboard_hash = None

                is_new_content = (image_to_process is not None) and \
                               (current_hash != self.last_clipboard_hash or \
                                (current_hash is None and self.last_clipboard_hash is not None))

                if is_new_content:
                    logging.debug(f"New image content detected (Type: {type(image_to_process)}). Checking source...")
                    should_process = False
                    
                    with self.process_state_lock:
                        time_since_process_seen = time.time() - self.last_snip_process_seen_time

                    if 0 < time_since_process_seen <= SNIP_PROCESS_TIMEOUT_SECONDS:
                        logging.info(f"Image appeared {time_since_process_seen:.2f}s after snipping process seen. Processing.")
                        should_process = True
                    else:
                        logging.debug(f"Ignoring image (time since process seen: {time_since_process_seen:.2f}s > {SNIP_PROCESS_TIMEOUT_SECONDS}s or process not seen recently).")

                    if should_process:
                        process_thread = threading.Thread(target=self.process_screenshot, args=(image_to_process,), daemon=True)
                        process_thread.start()
                        self.last_clipboard_hash = current_hash
                    else:
                        self.last_clipboard_hash = current_hash

            except Exception as e:
                if "clipboard is empty" not in str(e).lower():
                    logging.error(f"Error monitoring clipboard: {e}", exc_info=False)
                    self.last_clipboard_hash = None
                elif "clipboard is empty" in str(e).lower() and self.last_clipboard_hash is not None:
                    self.last_clipboard_hash = None
            finally:
                time.sleep(0.5)

    def process_screenshot(self, screenshot_source):
        """Process a screenshot and open in Google Lens"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        temp_file_path = None
        
        try:
            image_path = None
            if isinstance(screenshot_source, Image.Image):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.png', prefix=f'ss_{timestamp}_') as temp_file:
                        img_to_save = screenshot_source
                        if img_to_save.mode in ['RGBA', 'P']:
                            img_to_save = img_to_save.convert('RGB')
                        img_to_save.save(temp_file, format='PNG')
                        temp_file_path = temp_file.name
                    image_path = temp_file_path
                    logging.info(f"Screenshot saved: {image_path}")
                except Exception as save_err:
                    logging.error(f"Failed to save PIL Image: {save_err}", exc_info=True)
                    return
            elif isinstance(screenshot_source, str) and os.path.isfile(screenshot_source):
                image_path = screenshot_source
                logging.info(f"Processing file: {image_path}")
            else:
                logging.warning(f"Invalid source type: {type(screenshot_source)}")
                return
            
            if not image_path:
                logging.error("No valid image path.")
                return
            
            search_url = self.get_google_lens_url(image_path)
            if search_url:
                logging.info(f"Opening Lens URL: {search_url}")
                webbrowser.open_new_tab(search_url)
            else:
                logging.error("Failed to get Lens URL.")
                
        except Exception as e:
            logging.error(f"Error processing screenshot: {e}", exc_info=True)
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    logging.info(f"Deleted temp file: {temp_file_path}")
                except OSError as e:
                    logging.error(f"Error deleting temp file {temp_file_path}: {e}")

    def start(self):
        """Start the service"""
        # Start the process monitor thread
        process_monitor_thread = threading.Thread(target=self.monitor_processes, daemon=True)
        process_monitor_thread.start()

        # Start the clipboard monitor thread
        clipboard_thread = threading.Thread(target=self.monitor_clipboard, daemon=True)
        clipboard_thread.start()

        platform_name = "Windows" if IS_WINDOWS else "Linux"
        logging.info(f"Snipping Lens started on {platform_name} (using process detection + Catbox.moe).")
        
        if IS_WINDOWS:
            logging.info("Take screenshots using Win+Shift+S, Snipping Tool, or left-click the tray icon.")
        else:
            logging.info("Take screenshots using gnome-screenshot or left-click the tray icon.")
        
        logging.info("New screenshots will be automatically searched on Google Lens.")
        logging.info("Right-click the tray icon for options. Left-click to take a screenshot.")

        try:
            self.run_tray_icon()
        except Exception as tray_err:
            logging.error(f"Failed to run system tray icon: {tray_err}", exc_info=True)
            print("\nError: Could not start system tray icon. Exiting.")
            self.exit_app()
            sys.exit(1)
        
        logging.info("Shutting down Snipping Lens...")

# Main execution
if __name__ == "__main__":
    try:
        # Basic dependency check
        import requests
        from PIL import Image
        import psutil
        from tray_qt import run_tray_qt
        
        if IS_LINUX:
            # Check for xclip on Linux
            result = subprocess.run(['which', 'xclip'], capture_output=True)
            if result.returncode != 0:
                print("Error: xclip is required on Linux. Please install it:")
                print("sudo apt install xclip")
                sys.exit(1)
                
    except ImportError as import_err:
        required_packages = "requests pystray Pillow psutil"
        if IS_LINUX:
            required_packages += " (and system package: xclip)"
        print(f"\nError: Missing library: {import_err.name}. Install with: pip install {required_packages}")
        sys.exit(1)

    try:
        snippinglens = SnippingLens()
        snippinglens.start()
    except Exception as e:
        logging.error(f"Critical error during startup: {e}", exc_info=True)
        print(f"\nCritical startup error: {e}. Check logs.")
        sys.exit(1)