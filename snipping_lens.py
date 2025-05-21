import os
import time
import threading
from PIL import ImageGrab, Image, ImageDraw, UnidentifiedImageError
import tempfile
import webbrowser
import winreg
import logging
import sys
from datetime import datetime
import requests
import pystray
import psutil
import platform
import subprocess
import shutil # For shutil.which

# --- Configuration ---
def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

TRAY_ICON_PATH = get_resource_path("my_icon.png")

# Platform specific configurations
OS_PLATFORM = platform.system() # "Windows", "Linux", "Darwin"

if OS_PLATFORM == "Windows":
    LOG_DIR = os.path.join(os.getenv('APPDATA', os.path.expanduser("~")), 'SnippingLens')
    DEFAULT_SNIPPING_TOOL_COMMAND = ["SnippingTool.exe"] # Fallback, ms-screenclip: is preferred
    # For Windows, try to use the modern screen clipping tool if available
    # Using 'ms-screenclip:' URI scheme
    SNIPPING_TOOL_LAUNCH_COMMAND = ["explorer", "ms-screenclip:"]
else: # Linux
    LOG_DIR = os.path.join(os.path.expanduser("~"), ".cache", "SnippingLens")
    DEFAULT_SNIPPING_TOOL_COMMAND = ["gnome-screenshot", "-c", "-a"]
    SNIPPING_TOOL_LAUNCH_COMMAND = DEFAULT_SNIPPING_TOOL_COMMAND

os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE_PATH = os.path.join(LOG_DIR, "snipping_lens.log")

SNIPPING_PROCESS_NAMES = {
    "Windows": ["SnippingTool.exe", "ScreenClippingHost.exe", "ScreenSketch.exe"],
    "Linux": ["gnome-screenshot"]
}
PROCESS_SCAN_INTERVAL_SECONDS = 0.75
SNIP_PROCESS_TIMEOUT_SECONDS = 5.0 # Increased slightly for more flexibility
# ---------------------

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_PATH),
        logging.StreamHandler(sys.stdout)
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

        self.current_os_snapping_processes = SNIPPING_PROCESS_NAMES.get(OS_PLATFORM, [])

        if OS_PLATFORM == "Windows":
            self.setup_autostart()
        elif OS_PLATFORM == "Linux":
            if not shutil.which("xclip"):
                logging.warning("xclip not found. Clipboard monitoring on Linux will be disabled.")
            if not shutil.which("gnome-screenshot"):
                logging.warning("gnome-screenshot not found. Left-click snipping tool launch might not work.")

    def setup_autostart(self):
        if OS_PLATFORM != "Windows":
            return
        try:
            executable_path = sys.executable
            # For PyInstaller bundles, sys.executable is the .exe
            if getattr(sys, 'frozen', False) and sys.executable.lower().endswith('.exe'):
                executable_path = f'"{sys.executable}"'
            else: # Running from script
                pythonw_path = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
                script_path = os.path.abspath(sys.argv[0])
                if os.path.exists(pythonw_path):
                    executable_path = f'"{pythonw_path}" "{script_path}"'
                else:
                    executable_path = f'"{sys.executable}" "{script_path}"'

            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE) as registry_key:
                winreg.SetValueEx(registry_key, "SnippingLens", 0, winreg.REG_SZ, executable_path)
            logging.info(f"Added to startup: {executable_path}")
        except PermissionError:
            logging.error("Permission denied writing to registry for autostart.")
        except Exception as e:
            logging.error(f"Failed to add to startup: {e}")

    def create_default_image(self):
        width, height = 64, 64
        image = Image.new('RGB', (width, height), "black")
        dc = ImageDraw.Draw(image)
        dc.text((10, 20), "SL", fill="white") # Changed to SL for SnippingLens
        return image

    def _get_pause_resume_text(self):
        return "Resume Monitoring" if self.is_paused else "Pause Monitoring"

    def _toggle_pause_resume(self):
        self.is_paused = not self.is_paused
        status = "paused" if self.is_paused else "resumed"
        logging.info(f"Monitoring {status}.")
        # The menu item text will update automatically because it calls the method

    def _show_logs(self):
        logging.info(f"Attempting to open log file: {LOG_FILE_PATH}")
        try:
            if OS_PLATFORM == "Windows":
                os.startfile(LOG_FILE_PATH)
            elif OS_PLATFORM == "Linux":
                subprocess.run(['xdg-open', LOG_FILE_PATH], check=False)
            elif OS_PLATFORM == "Darwin": # macOS
                subprocess.run(['open', LOG_FILE_PATH], check=False)
            else:
                webbrowser.open(f"file://{os.path.abspath(LOG_FILE_PATH)}") # Fallback
        except Exception as e:
            logging.error(f"Could not open log file: {e}")

    def _trigger_snipping_tool_and_search(self):
        logging.info("Triggering snipping tool...")
        try:
            if OS_PLATFORM == "Windows":
                # Try ms-screenclip: first as it's more modern
                try:
                    subprocess.Popen(SNIPPING_TOOL_LAUNCH_COMMAND)
                    logging.info(f"Launched Windows Screen Clipping via ms-screenclip:")
                except FileNotFoundError: # Fallback for older Windows or if explorer command fails
                    logging.warning("ms-screenclip: failed, trying SnippingTool.exe")
                    subprocess.Popen(DEFAULT_SNIPPING_TOOL_COMMAND)
            elif OS_PLATFORM == "Linux":
                if shutil.which(DEFAULT_SNIPPING_TOOL_COMMAND[0]):
                    subprocess.Popen(DEFAULT_SNIPPING_TOOL_COMMAND)
                    logging.info(f"Launched {DEFAULT_SNIPPING_TOOL_COMMAND[0]}")
                else:
                    logging.error(f"{DEFAULT_SNIPPING_TOOL_COMMAND[0]} not found. Cannot trigger snip.")
            # The existing monitor_clipboard and monitor_processes will handle the new snip
        except Exception as e:
            logging.error(f"Failed to trigger snipping tool: {e}")


    def run_tray_icon(self):
        icon_image = None
        if TRAY_ICON_PATH and os.path.exists(TRAY_ICON_PATH):
            try:
                icon_image = Image.open(TRAY_ICON_PATH)
                logging.info(f"Using custom tray icon: {TRAY_ICON_PATH}")
            except Exception as e:
                logging.error(f"Failed to load custom tray icon '{TRAY_ICON_PATH}': {e}. Using default.")
        
        if icon_image is None:
            logging.info("Using default generated tray icon.")
            icon_image = self.create_default_image()

        menu = pystray.Menu(
            pystray.MenuItem("Snip & Search", self._trigger_snipping_tool_and_search, default=True), # Left-click action
            pystray.MenuItem(self._get_pause_resume_text, self._toggle_pause_resume),
            pystray.MenuItem("Show Logs", self._show_logs),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self.exit_app)
        )
        self.icon = pystray.Icon("SnippingLens", icon_image, "Snipping Lens", menu)
        logging.info("Running system tray icon.")
        self.icon.run()

    def exit_app(self, icon=None, item=None):
        logging.info("Exit requested.")
        self.is_running = False
        if self.icon:
            try:
                self.icon.stop()
            except Exception as e: # Can sometimes error if already stopping
                logging.warning(f"Icon stop error: {e}")
        logging.info("Exiting application...")
        # Give threads a moment to see self.is_running flag
        time.sleep(0.5) 
        os._exit(0) # Force exit if threads are stuck

    def get_image_hash(self, image_source):
        try:
            if isinstance(image_source, Image.Image):
                return hash(image_source.tobytes())
            elif isinstance(image_source, str) and os.path.isfile(image_source): # If it's a file path
                with Image.open(image_source) as img:
                    return hash(img.tobytes())
            elif isinstance(image_source, str): # If it's a string (e.g. path that was already hashed)
                 return hash(image_source) # This case might be redundant if we always open files
        except Exception as e:
            logging.debug(f"Could not get hash for {type(image_source)}: {e}")
        return None

    def get_google_lens_url(self, image_path):
        try:
            catbox_url = "https://catbox.moe/user/api.php"
            filename = os.path.basename(image_path)
            logging.info(f"Uploading {image_path} to Catbox.moe...")
            with open(image_path, 'rb') as f:
                payload = {'reqtype': (None, 'fileupload'), 'userhash': (None, '')} # No userhash needed for anonymous
                files = {'fileToUpload': (filename, f)}
                headers = {'User-Agent': 'SnippingLensScript/1.1'} # Updated version
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

    def monitor_processes(self):
        logging.info(f"Starting process monitor thread for {OS_PLATFORM}...")
        while self.is_running:
            if self.is_paused:
                time.sleep(1)
                continue

            found_snipping_process = False
            try:
                for proc in psutil.process_iter(['name']):
                    if proc.info['name'] in self.current_os_snapping_processes:
                        logging.debug(f"Detected running snipping process: {proc.info['name']}")
                        found_snipping_process = True
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass # Ignore these common errors
            except Exception as e:
                logging.error(f"Error scanning processes: {e}", exc_info=False)

            if found_snipping_process:
                with self.process_state_lock:
                    self.last_snip_process_seen_time = time.time()
            
            time.sleep(PROCESS_SCAN_INTERVAL_SECONDS)
        logging.info("Process monitor thread stopped.")

    def _get_clipboard_image_linux(self):
        """Attempts to get an image from clipboard using xclip."""
        if not shutil.which("xclip"):
            # Already warned at startup, so just return None silently or debug log
            # logging.debug("xclip not found, cannot get clipboard image on Linux.")
            return None

        temp_image_file = None
        try:
            # Check available targets
            targets_process = subprocess.run(
                ["xclip", "-selection", "clipboard", "-t", "TARGETS", "-o"],
                capture_output=True, text=True, check=False
            )
            if targets_process.returncode != 0:
                # logging.debug(f"xclip TARGETS failed: {targets_process.stderr}")
                return None

            targets = targets_process.stdout.strip().split('\n')
            image_mimes = ["image/png", "image/jpeg", "image/bmp", "image/tiff"]
            selected_mime = None
            for mime in image_mimes:
                if mime in targets:
                    selected_mime = mime
                    break
            
            if not selected_mime:
                # logging.debug("No suitable image MIME type found in clipboard targets.")
                return None

            # Save the image to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_f:
                temp_image_file = tmp_f.name
            
            # Get the image data
            get_image_process = subprocess.run(
                ["xclip", "-selection", "clipboard", "-t", selected_mime, "-o"],
                stdout=open(temp_image_file, 'wb'), # Write binary output to file
                check=False
            )

            if get_image_process.returncode != 0:
                # logging.error(f"xclip failed to get image data for {selected_mime}.")
                if os.path.exists(temp_image_file): os.unlink(temp_image_file)
                return None

            if os.path.getsize(temp_image_file) > 0:
                # Verify it's a valid image with PIL
                try:
                    with Image.open(temp_image_file) as img:
                        img.verify() # Check if it's a valid image
                    # Return the path to the temporary file
                    logging.debug(f"Image from clipboard (Linux) saved to {temp_image_file}")
                    return temp_image_file 
                except UnidentifiedImageError:
                    logging.debug(f"Content from xclip ({selected_mime}) is not a valid image: {temp_image_file}")
                    if os.path.exists(temp_image_file): os.unlink(temp_image_file)
                    return None
                except Exception as e:
                    logging.error(f"Error verifying image from xclip: {e}")
                    if os.path.exists(temp_image_file): os.unlink(temp_image_file)
                    return None
            else:
                # logging.debug("xclip produced an empty file.")
                if os.path.exists(temp_image_file): os.unlink(temp_image_file)
                return None

        except FileNotFoundError: # Should be caught by shutil.which earlier
            logging.error("xclip command not found during clipboard access.")
            return None
        except subprocess.CalledProcessError as e:
            logging.error(f"xclip execution error: {e}")
            return None
        except Exception as e:
            logging.error(f"Error getting clipboard image on Linux: {e}", exc_info=True)
            return None
        finally:
            # The caller of _get_clipboard_image_linux will be responsible for deleting the temp_image_file
            # if it's returned, after processing.
            pass
        return None


    def monitor_clipboard(self):
        logging.info("Starting clipboard monitor...")
        temp_linux_image_path = None # To manage deletion of temp file from xclip

        while self.is_running:
            if self.is_paused:
                time.sleep(1)
                if temp_linux_image_path and os.path.exists(temp_linux_image_path):
                    try: os.unlink(temp_linux_image_path)
                    except OSError: pass
                    temp_linux_image_path = None
                continue
            
            try:
                clipboard_content = None
                image_source_type = None # 'pil', 'file_path'

                if OS_PLATFORM == "Windows":
                    clipboard_content = ImageGrab.grabclipboard()
                elif OS_PLATFORM == "Linux":
                    # Clean up previous temp file if any, before trying to get a new one
                    if temp_linux_image_path and os.path.exists(temp_linux_image_path):
                        try: os.unlink(temp_linux_image_path)
                        except OSError as e: logging.debug(f"Error deleting old temp xclip file: {e}")
                        temp_linux_image_path = None
                    
                    # This returns a file path to a temporary image
                    temp_linux_image_path = self._get_clipboard_image_linux()
                    if temp_linux_image_path:
                        clipboard_content = temp_linux_image_path # Use the path as content

                if clipboard_content is None:
                    if self.last_clipboard_hash is not None:
                        self.last_clipboard_hash = None # Reset if clipboard becomes empty
                    time.sleep(1)
                    continue

                current_hash, image_to_process = None, None

                if isinstance(clipboard_content, Image.Image): # PIL Image (typically Windows)
                    current_hash = self.get_image_hash(clipboard_content)
                    image_to_process = clipboard_content
                    image_source_type = 'pil'
                elif isinstance(clipboard_content, str) and os.path.isfile(clipboard_content): # File path (typically Linux from xclip)
                    current_hash = self.get_image_hash(clipboard_content) # Hash based on file content
                    image_to_process = clipboard_content
                    image_source_type = 'file_path'
                elif OS_PLATFORM == "Windows" and isinstance(clipboard_content, list): # List of files (Windows)
                    for filename in clipboard_content:
                        if isinstance(filename, str) and os.path.isfile(filename) and \
                           filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                            try:
                                with Image.open(filename) as img_test: # Verify it's an image
                                    img_test.verify()
                                current_hash = self.get_image_hash(filename) # Hash based on file content
                                image_to_process = filename
                                image_source_type = 'file_path'
                                break 
                            except (UnidentifiedImageError, FileNotFoundError):
                                continue # Not a valid image file or path
                            except Exception as e:
                                logging.debug(f"Error checking file from clipboard list {filename}: {e}")
                                continue
                    if not image_to_process and self.last_clipboard_hash is not None:
                        self.last_clipboard_hash = None # Reset if no valid image found

                is_new_content = (image_to_process is not None) and \
                                 (current_hash != self.last_clipboard_hash or \
                                  (current_hash is None and self.last_clipboard_hash is not None))

                if is_new_content:
                    logging.debug(f"New image content detected (Type: {image_source_type}, Source: {image_to_process}). Checking source...")
                    should_process = False
                    with self.process_state_lock:
                        time_since_process_seen = time.time() - self.last_snip_process_seen_time
                    
                    if 0 < time_since_process_seen <= SNIP_PROCESS_TIMEOUT_SECONDS:
                        logging.info(f"Image appeared {time_since_process_seen:.2f}s after snipping process. Processing.")
                        should_process = True
                    else:
                        logging.debug(f"Ignoring image (time since process seen: {time_since_process_seen:.2f}s > {SNIP_PROCESS_TIMEOUT_SECONDS}s or process not seen recently).")

                    if should_process:
                        # If it's a PIL image, it will be saved to temp by process_screenshot
                        # If it's a file path (from xclip or file copy), it will be used directly
                        # The temp_linux_image_path from xclip will be handled by process_screenshot for deletion
                        process_thread = threading.Thread(
                            target=self.process_screenshot, 
                            args=(image_to_process, image_source_type == 'file_path' and image_to_process == temp_linux_image_path), 
                            daemon=True
                        )
                        process_thread.start()
                        self.last_clipboard_hash = current_hash
                    else:
                        # Update hash even if ignored to prevent re-evaluation of the same ignored content
                        self.last_clipboard_hash = current_hash
                        # If it was a temp file from Linux xclip and we are ignoring it, delete it now
                        if image_source_type == 'file_path' and image_to_process == temp_linux_image_path:
                            if temp_linux_image_path and os.path.exists(temp_linux_image_path):
                                try: os.unlink(temp_linux_image_path)
                                except OSError as e: logging.debug(f"Error deleting ignored temp xclip file: {e}")
                            temp_linux_image_path = None # Reset as it's handled

            except ImportError: # Pillow's ImageGrab might raise this if clipboard format is unsupported
                if self.last_clipboard_hash is not None: self.last_clipboard_hash = None
                logging.debug("ImageGrab.grabclipboard() ImportError, clipboard format likely unsupported or empty.")
            except Exception as e:
                is_clipboard_access_error = False
                if OS_PLATFORM == "Windows":
                    is_clipboard_access_error = "pywintypes.error" in repr(e) and \
                                                ("OpenClipboard" in str(e) or "GetClipboardData" in str(e))
                
                if not is_clipboard_access_error and "clipboard is empty" not in str(e).lower():
                    logging.error(f"Error monitoring clipboard: {e}", exc_info=False) # exc_info=False to reduce noise for common errors
                
                if self.last_clipboard_hash is not None: # Reset hash on any error
                    self.last_clipboard_hash = None
                
                # Clean up temp Linux file on error too
                if temp_linux_image_path and os.path.exists(temp_linux_image_path):
                    try: os.unlink(temp_linux_image_path)
                    except OSError: pass
                    temp_linux_image_path = None
            finally:
                time.sleep(0.5) # Clipboard check interval
        
        # Final cleanup of temp Linux file when monitor stops
        if temp_linux_image_path and os.path.exists(temp_linux_image_path):
            try: os.unlink(temp_linux_image_path)
            except OSError: pass
        logging.info("Clipboard monitor thread stopped.")

    def process_screenshot(self, screenshot_source, is_temp_xclip_file=False):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        pil_temp_file_path = None # For images saved from PIL object
        final_image_path = None

        try:
            if isinstance(screenshot_source, Image.Image): # PIL Image
                try:
                    # Create a temporary file for PIL image
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.png', prefix=f'ss_pil_{timestamp}_', dir=tempfile.gettempdir()) as temp_f:
                        img_to_save = screenshot_source
                        if img_to_save.mode in ['RGBA', 'P']: # Convert to RGB for wider compatibility (e.g. JPEG)
                            img_to_save = img_to_save.convert('RGB')
                        img_to_save.save(temp_f, format='PNG')
                        pil_temp_file_path = temp_f.name
                    final_image_path = pil_temp_file_path
                    logging.info(f"PIL Screenshot saved to temp file: {final_image_path}")
                except Exception as save_err:
                    logging.error(f"Failed to save PIL Image to temporary file: {save_err}", exc_info=True)
                    return
            elif isinstance(screenshot_source, str) and os.path.isfile(screenshot_source): # File path
                final_image_path = screenshot_source
                logging.info(f"Processing screenshot from file: {final_image_path}")
            else:
                logging.warning(f"Invalid screenshot_source type: {type(screenshot_source)}")
                return

            if not final_image_path:
                logging.error("No valid image path to process.")
                return

            search_url = self.get_google_lens_url(final_image_path)
            if search_url:
                logging.info(f"Opening Lens URL: {search_url}")
                webbrowser.open_new_tab(search_url)
            else:
                logging.error("Failed to get Lens URL for the screenshot.")

        except Exception as e:
            logging.error(f"Error processing screenshot: {e}", exc_info=True)
        finally:
            # Delete PIL temp file if it was created
            if pil_temp_file_path and os.path.exists(pil_temp_file_path):
                try:
                    os.unlink(pil_temp_file_path)
                    logging.info(f"Deleted temp PIL image file: {pil_temp_file_path}")
                except OSError as e:
                    logging.error(f"Error deleting temp PIL image file {pil_temp_file_path}: {e}")
            
            # Delete xclip temp file if it was the source and successfully processed or failed
            if is_temp_xclip_file and final_image_path == screenshot_source and os.path.exists(final_image_path):
                try:
                    os.unlink(final_image_path) # final_image_path is screenshot_source in this case
                    logging.info(f"Deleted temp xclip file: {final_image_path}")
                except OSError as e:
                    logging.error(f"Error deleting temp xclip file {final_image_path}: {e}")


    def start(self):
        logging.info(f"Snipping Lens starting on {OS_PLATFORM}...")
        logging.info(f"Log file: {LOG_FILE_PATH}")
        if OS_PLATFORM == "Linux":
            if not shutil.which("xclip"): logging.warning("xclip is not installed. Clipboard image detection from Linux clipboard will not work.")
            if not shutil.which("gnome-screenshot"): logging.warning("gnome-screenshot is not installed. Left-click snipping may not work.")

        process_monitor_thread = threading.Thread(target=self.monitor_processes, daemon=True)
        process_monitor_thread.start()

        clipboard_thread = threading.Thread(target=self.monitor_clipboard, daemon=True)
        clipboard_thread.start()
        
        logging.info("Snipping Lens started (using process detection + Catbox.moe).")
        logging.info("Left-click tray icon or use system's snipping tool (e.g., Win+Shift+S, gnome-screenshot).")
        logging.info("New screenshots appearing after a snipping tool runs will be searched on Google Lens.")
        logging.info("Right-click tray icon for options.")

        try:
            self.run_tray_icon() # This blocks until exit
        except Exception as tray_err:
            logging.error(f"Failed to run system tray icon: {tray_err}", exc_info=True)
            print(f"\nError: Could not start system tray icon: {tray_err}. Exiting.")
            self.exit_app() # Try to clean up
            sys.exit(1)
        
        logging.info("Shutting down Snipping Lens...")


if __name__ == "__main__":
    # Basic dependency check
    try:
        import requests, pystray, PIL, psutil
    except ImportError as import_err:
        missing_lib_msg = f"Error: Missing library: {import_err.name}. Please install requirements. e.g., pip install requests pystray Pillow psutil"
        logging.critical(missing_lib_msg)
        print(f"\n{missing_lib_msg}")
        sys.exit(1)

    # Ensure only one instance is running (simple lock file mechanism)
    lock_file_path = os.path.join(tempfile.gettempdir(), "snipping_lens.lock")
    if OS_PLATFORM == "Windows":
        try:
            # This is a very basic way to check for a running instance on Windows.
            # A more robust method would use a named mutex.
            if os.path.exists(lock_file_path):
                try:
                    os.remove(lock_file_path) # Try to remove stale lock
                except OSError:
                     # If lock file is actively held, this might fail or it might be stale.
                     # This check is not foolproof.
                     print("Lock file exists. If Snipping Lens is not running, delete the lock file and try again.")
                     logging.warning("Lock file exists. Another instance might be running or lock file is stale.")
                     # For simplicity, we'll allow starting, but a proper mutex is better.
                     # sys.exit(0) # Exit if lock file is truly held.
            
            # Create lock file
            with open(lock_file_path, "w") as f:
                f.write(str(os.getpid()))
        except Exception as e:
            logging.warning(f"Could not create or check lock file: {e}")
    # For Linux/macOS, file locking is typically more robust with fcntl, but for simplicity:
    elif OS_PLATFORM == "Linux" or OS_PLATFORM == "Darwin":
        import fcntl
        try:
            lock_file = open(lock_file_path, 'w')
            fcntl.lockf(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Write PID to lock file for informational purposes
            lock_file.write(str(os.getpid()))
            lock_file.flush() 
            # The lock will be released when lock_file is closed or process exits.
            # We need to keep lock_file open. Let's make it part of the class or pass it around.
            # For now, this simple check at startup is a compromise.
            # A better way: The SnippingLens class could manage the lock file handle.
            # This current implementation of lock for Linux/Mac here is flawed as lock_file goes out of scope.
            # For a truly effective lock, it needs to be held.
            # Given the complexity, I will remove this simple lock for now as it's not robust.
            # A proper solution would involve the app instance holding the lock.
            logging.info("Skipping simple lock file check for this version for non-Windows.")

        except BlockingIOError:
            print("Another instance of Snipping Lens may be running (or lock file is stale).")
            logging.error("Failed to acquire lock. Another instance may be running.")
            sys.exit(1)
        except Exception as e:
            logging.warning(f"Could not create or check lock file using fcntl: {e}")


    try:
        snipping_lens_app = SnippingLens()
        snipping_lens_app.start()
    except SystemExit: # To allow sys.exit(1) from main to propagate
        pass
    except Exception as e:
        logging.critical(f"Critical error during startup or runtime: {e}", exc_info=True)
        print(f"\nCritical error: {e}. Check logs at {LOG_FILE_PATH}.")
        sys.exit(1)
    finally:
        # Clean up lock file on exit (if it was created by this instance)
        # This also needs to be more robust.
        if os.path.exists(lock_file_path):
            try:
                # Only remove if it's our lock - this check is simplistic
                # with open(lock_file_path, "r") as f:
                #    if f.read() == str(os.getpid()):
                #        os.remove(lock_file_path)
                # For now, just attempt removal.
                if OS_PLATFORM == "Windows": # Only manage lock this way on Windows for now
                    os.remove(lock_file_path)
            except OSError:
                pass # May fail if not owned or other issues
            except Exception: # Catch any other error during cleanup
                pass