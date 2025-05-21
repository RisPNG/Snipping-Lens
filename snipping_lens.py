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
import platform # For OS detection
import subprocess # For calling external commands (snipping tools, xclip)
import shutil # For shutil.which to check for xclip

# --- Configuration ---
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

TRAY_ICON_PATH = resource_path("my_icon.png") # .png is fine for pystray on Win/Linux
LOG_FILE_NAME = "snipping_lens.log"

# OS-specific configurations
OS_TYPE = platform.system().lower()

if OS_TYPE == "windows":
    DEFAULT_SNIPPING_PROCESS_NAMES = ["SnippingTool.exe", "ScreenClippingHost.exe", "ScreenSketch.exe"]
    # Using ms-screenclip protocol for modern snipping experience
    SNIPPING_COMMAND = ["powershell", "-Command", "Start-Process ms-screenclip:"]
    # Fallback if ms-screenclip fails (though it's usually reliable on Win10+)
    # SNIPPING_COMMAND_FALLBACK = ["SnippingTool.exe"]
elif OS_TYPE == "linux":
    DEFAULT_SNIPPING_PROCESS_NAMES = ["gnome-screenshot"]
    SNIPPING_COMMAND = ["gnome-screenshot", "-c", "-a"] # Takes screenshot to clipboard, area selection
else: # Unsupported OS
    DEFAULT_SNIPPING_PROCESS_NAMES = []
    SNIPPING_COMMAND = []
    logging.warning(f"Unsupported OS: {OS_TYPE}. Some features may not work.")

PROCESS_SCAN_INTERVAL_SECONDS = 0.75
SNIP_PROCESS_TIMEOUT_SECONDS = 5.0 # Increased slightly for potentially slower Linux tools
# ---------------------

# Set up logging (to file and console)
log_file_path = os.path.join(tempfile.gettempdir(), LOG_FILE_NAME) if OS_TYPE != "windows" else LOG_FILE_NAME # Place in temp for Linux if not packaged nicely
if OS_TYPE == "windows" and hasattr(sys, 'frozen'): # For PyInstaller bundle on Windows
    log_file_path = os.path.join(os.path.dirname(sys.executable), LOG_FILE_NAME)
else: # Dev or Linux
    log_file_path = resource_path(LOG_FILE_NAME) # Place alongside script/executable

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path, mode='a', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logging.info(f"Logging to: {log_file_path}")


class SnippingLens:
    def __init__(self):
        self.last_clipboard_hash = None
        self.is_running = True
        self.icon = None
        self.last_snip_process_seen_time = 0.0
        self.process_state_lock = threading.Lock()
        self.paused = False # For Pause/Resume functionality
        self.os_type = OS_TYPE
        self.current_snipping_process_names = DEFAULT_SNIPPING_PROCESS_NAMES

        if self.os_type == "linux" and not shutil.which("xclip"):
            logging.error("xclip command not found. Clipboard monitoring on Linux will not work. Please install xclip.")
            # Potentially exit or disable clipboard monitoring for Linux
            # For now, it will try and fail in monitor_clipboard
        if self.os_type == "linux" and not shutil.which(SNIPPING_COMMAND[0]):
            logging.warning(f"{SNIPPING_COMMAND[0]} not found. Left-click to snip may not work.")

        self.setup_autostart()

    def get_executable_path_for_autostart(self):
        if getattr(sys, 'frozen', False): # Bundled (PyInstaller)
            return f'"{sys.executable}"'
        else: # Running as script
            python_executable = sys.executable
            # Prefer pythonw.exe on Windows for no console if running script directly
            if self.os_type == "windows":
                pythonw_path = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
                if os.path.exists(pythonw_path):
                    python_executable = pythonw_path
            return f'"{python_executable}" "{os.path.abspath(sys.argv[0])}"'

    def setup_autostart(self):
        executable_path_cmd = self.get_executable_path_for_autostart()
        app_name = "SnippingLens"

        if self.os_type == "windows":
            try:
                key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE) as registry_key:
                    winreg.SetValueEx(registry_key, app_name, 0, winreg.REG_SZ, executable_path_cmd)
                logging.info(f"Added to Windows startup: {executable_path_cmd}")
            except PermissionError:
                logging.error("Permission denied writing to Windows registry for autostart.")
            except Exception as e:
                logging.error(f"Failed to add to Windows startup: {e}")
        elif self.os_type == "linux":
            autostart_dir = os.path.expanduser("~/.config/autostart/")
            desktop_file_path = os.path.join(autostart_dir, f"{app_name.lower()}.desktop")
            icon_path = resource_path("my_icon.png") # Ensure this icon is available

            if not os.path.exists(autostart_dir):
                os.makedirs(autostart_dir, exist_ok=True)

            desktop_entry_content = f"""[Desktop Entry]
Name={app_name}
Exec={executable_path_cmd}
Type=Application
Terminal=false
Icon={icon_path}
Comment=Capture screenshots and search with Google Lens
Categories=Utility;
X-GNOME-Autostart-enabled=true
"""
            try:
                with open(desktop_file_path, "w") as f:
                    f.write(desktop_entry_content)
                os.chmod(desktop_file_path, 0o755) # Make it executable
                logging.info(f"Created Linux autostart file: {desktop_file_path} with Exec={executable_path_cmd}")
            except Exception as e:
                logging.error(f"Failed to create Linux autostart file: {e}")

    def create_default_image(self):
        width = 64; height = 64; image = Image.new('RGB', (width, height), "black")
        dc = ImageDraw.Draw(image); dc.text((10, 20), "SL", fill="white"); return image # Changed to SL

    def launch_snipping_tool(self):
        if not SNIPPING_COMMAND:
            logging.warning("No snipping command configured for this OS.")
            return
        try:
            logging.info(f"Launching snipping tool with command: {' '.join(SNIPPING_COMMAND)}")
            subprocess.Popen(SNIPPING_COMMAND) # Use Popen for non-blocking
            # Immediately after launching, mark that a snipping tool *might* have been used.
            # This helps catch screenshots taken very quickly after manual trigger.
            with self.process_state_lock:
                self.last_snip_process_seen_time = time.time()
        except FileNotFoundError:
            logging.error(f"Snipping tool command not found: {SNIPPING_COMMAND[0]}. Please ensure it's installed and in PATH.")
        except Exception as e:
            logging.error(f"Failed to launch snipping tool: {e}")

    def toggle_pause(self, icon, item):
        self.paused = not self.paused
        logging.info(f"Application {'paused' if self.paused else 'resumed'}.")
        # To update menu item text, pystray requires menu reconstruction or specific item properties.
        # For simplicity, we use a single "Pause/Resume" item. User knows it's a toggle.
        # If pystray supported dynamic text updates easily, we'd do it here.
        # Example for pystray item's 'checked' state if it were a radio or checkbox style:
        # self.icon.update_menu() # If menu items needed to be visually updated beyond simple text

    def show_logs(self, icon, item):
        logging.info(f"Attempting to open log file: {log_file_path}")
        try:
            if self.os_type == "windows":
                os.startfile(log_file_path)
            elif self.os_type == "linux":
                # Try xdg-open first, then fallback to webbrowser
                if shutil.which("xdg-open"):
                    subprocess.run(["xdg-open", log_file_path])
                else:
                    webbrowser.open(f"file://{os.path.abspath(log_file_path)}")
            else: # Fallback for other systems
                 webbrowser.open(f"file://{os.path.abspath(log_file_path)}")
        except Exception as e:
            logging.error(f"Failed to open log file: {e}")

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

        menu_items = [
            pystray.MenuItem("Pause/Resume", self.toggle_pause),
            pystray.MenuItem("Show Logs", self.show_logs),
            pystray.MenuItem("Exit", self.exit_app)
        ]
        menu = pystray.Menu(*menu_items)

        self.icon = pystray.Icon(
            "SnippingLens",
            icon_image,
            "Snipping Lens - Click to Snip", # Tooltip
            menu=menu,
            # Left click action
            item_execute=self.launch_snipping_tool # This is not how pystray handles left click.
                                                 # pystray.Icon constructor does not have 'item_execute'.
                                                 # It has 'menu' which can have a default item, or you can pass
                                                 # action directly to the icon if it's the primary action.
                                                 # Let's try setting the action directly if no menu is desired on left-click.
                                                 # No, pystray expects the primary action on the icon itself if no menu given,
                                                 # or default action in menu.
                                                 # The most common way is to make the *first* item in the menu the default action for left-click.
                                                 # Or, have a specific handler.
                                                 # For pystray, a primary action is usually not mixed with a menu this way.
                                                 # We will make "Launch Snip" an explicit menu item, or rely on left-click on icon directly.
        )
        # To set a left-click action, it's often simpler to make it the default menu item.
        # Or, pystray.Icon can take the action as its main purpose if there isn't a menu.
        # If a menu exists, the left-click action is typically to show the menu.
        # A common pattern is:
        # self.icon.left_click_action = self.launch_snipping_tool (Not a pystray feature)

        # Let's create a menu where "Snip & Search" is the default (first) item if desired.
        # Or, we can have a specific menu item for it.
        # For clarity, let's add "Snip & Search" to the menu.
        # The request was "left clicking the tray icon will launch". pystray's behavior:
        # - If icon has menu, left-click shows menu.
        # - If icon has no menu, left-click triggers icon's default action (if any).
        # To achieve left-click launch WITH a menu for right-click:
        # This is often OS/tray specific. Some trays allow configuring left vs right click.
        # pystray itself might not directly support different actions for left/right click on the *same* icon if a menu is present.
        # The typical behavior is left-click opens the menu.
        # Let's try a workaround: make the icon itself clickable, and have the menu separate.
        # No, pystray.Icon has one primary purpose (run by left-click if no menu, or shows menu).
        # The simplest for pystray: Left-click shows the menu. First item is "Snip & Search".
        
        menu_items_for_pystray = [
            pystray.MenuItem("Snip & Search", self.launch_snipping_tool, default=True), # 'default=True' makes it action on left-click for some systems
            pystray.MenuItem("Pause/Resume", self.toggle_pause),
            pystray.MenuItem("Show Logs", self.show_logs),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self.exit_app)
        ]
        actual_menu = pystray.Menu(*menu_items_for_pystray)
        self.icon = pystray.Icon("SnippingLens", icon_image, "Snipping Lens", menu=actual_menu)


        logging.info("Running system tray icon.")
        self.icon.run() # This blocks

    def exit_app(self, icon=None, item=None):
        logging.info("Exit requested.")
        self.is_running = False
        if self.icon:
            try:
                self.icon.stop()
            except Exception as e:
                logging.warning(f"Icon stop error: {e}")
        logging.info("Exiting application..."); time.sleep(0.5); os._exit(0)

    def get_image_hash(self, image_obj_or_path):
        try:
            if isinstance(image_obj_or_path, Image.Image):
                return hash(image_obj_or_path.tobytes())
            elif isinstance(image_obj_or_path, str) and os.path.isfile(image_obj_or_path):
                with Image.open(image_obj_or_path) as img:
                    return hash(img.tobytes())
            return None
        except Exception as e:
            logging.debug(f"Could not get image hash: {e}")
            return None


    def get_google_lens_url(self, image_path):
        try:
            catbox_url = "https://catbox.moe/user/api.php"; filename = os.path.basename(image_path)
            logging.info(f"Uploading {image_path} to Catbox.moe...")
            with open(image_path, 'rb') as f:
                payload = {'reqtype': (None, 'fileupload'), 'userhash': (None, '')}
                files = {'fileToUpload': (filename, f)}; headers = {'User-Agent': 'SnippingLensScript/1.1'} # Version bump
                response = requests.post(catbox_url, files=files, data=payload, headers=headers, timeout=60)
            response.raise_for_status(); catbox_link = response.text.strip()
            if response.status_code == 200 and catbox_link.startswith('https://files.catbox.moe/'):
                logging.info(f"Image uploaded: {catbox_link}"); return f"https://lens.google.com/uploadbyurl?url={catbox_link}"
            else: logging.error(f"Failed Catbox upload. Status: {response.status_code}, Response: {response.text[:200]}..."); return None
        except requests.exceptions.Timeout: logging.error("Catbox upload timed out."); return None
        except requests.exceptions.RequestException as e:
            response_details = f"Network error: {e}"
            if hasattr(e, 'response') and e.response is not None: response_details = f"Status: {e.response.status_code}, Response: {e.response.text[:200]}..."
            logging.error(f"Error uploading to Catbox: {response_details}"); return None
        except Exception as e: logging.error(f"Unexpected Catbox/Lens error: {e}", exc_info=True); return None

    def monitor_processes(self):
        logging.info(f"Starting process monitor thread for: {self.current_snipping_process_names}...")
        while self.is_running:
            if self.paused:
                time.sleep(1); continue

            found_snipping_process = False
            if not self.current_snipping_process_names: # Skip if no processes to monitor
                time.sleep(PROCESS_SCAN_INTERVAL_SECONDS); continue
            try:
                for proc in psutil.process_iter(['name']):
                    if proc.info['name'] in self.current_snipping_process_names:
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

    def monitor_clipboard(self):
        logging.info("Starting clipboard monitor...")
        processed_clipboard_instance_id = None # To handle cases where clipboard content object is same but data changed

        if self.os_type == "linux" and not shutil.which("xclip"):
            logging.error("xclip not found. Linux clipboard monitoring disabled.")
            return # Stop this thread if xclip is not available

        while self.is_running:
            if self.paused:
                time.sleep(1); continue

            clipboard_image = None
            current_hash = None
            is_file_list = False # To track if content was a list of files

            try:
                if self.os_type == "windows":
                    clipboard_content = ImageGrab.grabclipboard()
                    if isinstance(clipboard_content, Image.Image):
                        clipboard_image = clipboard_content
                    elif isinstance(clipboard_content, list): # List of filenames
                        is_file_list = True
                        for filename in clipboard_content:
                            if isinstance(filename, str) and os.path.isfile(filename) and \
                               filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                                try:
                                    # For files, we'll open them to get a consistent hash and Image object
                                    # However, we process the file path directly to avoid re-saving
                                    # Let's re-evaluate if we pass path or Image object
                                    # For now, if it's a file, get its hash, and pass the path.
                                    # The `process_screenshot` handles paths.
                                    current_hash = self.get_image_hash(filename) # Get hash from file
                                    clipboard_image = filename # Keep as path
                                    break
                                except UnidentifiedImageError:
                                    logging.debug(f"File from clipboard is not a valid image: {filename}")
                                except Exception as e:
                                    logging.debug(f"Error processing file from clipboard {filename}: {e}")
                        if not clipboard_image and self.last_clipboard_hash is not None: # No valid image file found
                             self.last_clipboard_hash = None

                    if clipboard_image and not current_hash: # If it's an Image obj, get hash now
                        current_hash = self.get_image_hash(clipboard_image)

                elif self.os_type == "linux":
                    temp_xclip_image_path = None
                    try:
                        targets_proc = subprocess.run(
                            ["xclip", "-selection", "clipboard", "-t", "TARGETS", "-o"],
                            capture_output=True, text=True, timeout=0.5, check=True
                        )
                        targets = targets_proc.stdout.strip().split('\n')
                        
                        image_target = None
                        if "image/png" in targets: image_target = "image/png"
                        elif "image/jpeg" in targets: image_target = "image/jpeg"
                        # Add more image MIME types if necessary

                        if image_target:
                            # Create a temporary file to store the image from xclip
                            suffix = ".png" if image_target == "image/png" else ".jpg"
                            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_f:
                                temp_xclip_image_path = tmp_f.name
                            
                            # Pipe xclip output to the temporary file
                            with open(temp_xclip_image_path, 'wb') as f_out:
                                subprocess.run(
                                    ["xclip", "-selection", "clipboard", "-t", image_target, "-o"],
                                    stdout=f_out, timeout=1, check=True
                                )
                            
                            # Load the image from the temporary file to get a PIL Image object
                            # and its hash. The path itself can be passed for processing later if preferred.
                            # For consistency, let's load it as PIL image.
                            img = Image.open(temp_xclip_image_path)
                            img.load() # ensure data is read
                            clipboard_image = img 
                            current_hash = self.get_image_hash(clipboard_image)
                        else: # No image target
                             if self.last_clipboard_hash is not None: self.last_clipboard_hash = None

                    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                        # These are common if clipboard is empty or not image, or xclip issue
                        # logging.debug(f"xclip: Could not get image from clipboard: {e}")
                        if self.last_clipboard_hash is not None: self.last_clipboard_hash = None
                    except UnidentifiedImageError:
                        logging.debug(f"xclip: Content from clipboard is not a valid image format via {temp_xclip_image_path}")
                        if self.last_clipboard_hash is not None: self.last_clipboard_hash = None
                    except Exception as e:
                        logging.error(f"xclip: Error processing clipboard: {e}")
                        if self.last_clipboard_hash is not None: self.last_clipboard_hash = None
                    finally:
                        # If we loaded into PIL image, temp file from xclip can be deleted.
                        # If process_screenshot is going to use the path, it must be deleted later.
                        # Since clipboard_image is now a PIL.Image, we can delete it.
                        if temp_xclip_image_path and os.path.exists(temp_xclip_image_path):
                            if not isinstance(clipboard_image, str): # if it was loaded as PIL.Image
                                os.unlink(temp_xclip_image_path)
                            # If clipboard_image were to remain a path, deletion would be after processing.
                
                # Common logic for new content detection
                if clipboard_image is None:
                    if self.last_clipboard_hash is not None: self.last_clipboard_hash = None
                    time.sleep(1); continue # Check clipboard less frequently if empty

                # is_new_content: True if hash is different, or if hash is None now but wasn't before
                # Or if it's a file list and the file path itself is new (even if hash was same previously, unlikely)
                # The core idea is: is this specific clipboard instance/content new?
                is_new_content = (current_hash != self.last_clipboard_hash)

                if is_new_content:
                    logging.debug(f"New clipboard content detected (Type: {type(clipboard_image)}, Hash: {current_hash}). Checking source...")
                    should_process = False
                    with self.process_state_lock:
                        time_since_process_seen = time.time() - self.last_snip_process_seen_time

                    if 0 <= time_since_process_seen <= SNIP_PROCESS_TIMEOUT_SECONDS: # Allow 0 for manually triggered snips
                        logging.info(f"Image appeared {time_since_process_seen:.2f}s after snipping process trigger. Processing.")
                        should_process = True
                    else:
                        logging.debug(f"Ignoring image (time since process seen: {time_since_process_seen:.2f}s > {SNIP_PROCESS_TIMEOUT_SECONDS}s or process not seen recently).")

                    if should_process:
                        # Pass the PIL.Image object or the file path to process_screenshot
                        # The current process_screenshot can handle both
                        source_to_process = clipboard_image 
                        process_thread = threading.Thread(target=self.process_screenshot, args=(source_to_process,), daemon=True)
                        process_thread.start()
                        self.last_clipboard_hash = current_hash
                    else:
                        # Update hash even if ignored, to prevent re-evaluation of the same ignored content
                        self.last_clipboard_hash = current_hash
                
            except ImportError: # Pillow's ImageGrab might raise this if clipboard format is unsupported
                if self.last_clipboard_hash is not None: self.last_clipboard_hash = None
            except Exception as e:
                 # Filter out common, less critical clipboard errors (e.g. empty, access denied temporarily)
                 is_pywintypes_error = "pywintypes.error" in repr(e) and ("OpenClipboard" in str(e) or "GetClipboardData" in str(e))
                 is_empty_error = "clipboard is empty" in str(e).lower() or \
                                  (hasattr(e, 'args') and e.args and isinstance(e.args[0], str) and "format is not supported" in e.args[0].lower()) # ImageGrab error

                 if not is_pywintypes_error and not is_empty_error:
                     logging.error(f"Error monitoring clipboard: {e}", exc_info=False) # Log other errors
                 
                 if self.last_clipboard_hash is not None : self.last_clipboard_hash = None # Reset on error

            finally:
                time.sleep(0.5) # Clipboard check interval

    def process_screenshot(self, screenshot_source): # screenshot_source can be PIL Image or file path
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        temp_file_path_generated = None # Path of a temp file *this function* creates
        input_is_path = isinstance(screenshot_source, str)

        try:
            image_path_to_upload = None
            if isinstance(screenshot_source, Image.Image):
                try:
                    # Create a temp file to save the PIL Image
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.png', prefix=f'ss_{timestamp}_') as temp_file:
                        img_to_save = screenshot_source
                        if img_to_save.mode in ['RGBA', 'P']: # Convert to RGB for wider compatibility (e.g. JPEG)
                            img_to_save = img_to_save.convert('RGB')
                        img_to_save.save(temp_file, format='PNG')
                        temp_file_path_generated = temp_file.name
                    image_path_to_upload = temp_file_path_generated
                    logging.info(f"Screenshot (from PIL Image) saved to temp file: {image_path_to_upload}")
                except Exception as save_err:
                    logging.error(f"Failed to save PIL Image to temp file: {save_err}", exc_info=True); return
            elif input_is_path and os.path.isfile(screenshot_source):
                # If a path was given (e.g., from Windows file copy, or temp xclip file if we passed path)
                image_path_to_upload = screenshot_source
                logging.info(f"Processing screenshot from file: {image_path_to_upload}")
            else:
                logging.warning(f"Invalid screenshot_source type: {type(screenshot_source)} or path not found."); return

            if not image_path_to_upload:
                logging.error("No valid image path to upload."); return

            search_url = self.get_google_lens_url(image_path_to_upload)
            if search_url:
                logging.info(f"Opening Lens URL: {search_url}")
                webbrowser.open_new_tab(search_url)
            else:
                logging.error("Failed to get Lens URL for the screenshot.")

        except Exception as e:
            logging.error(f"Error processing screenshot: {e}", exc_info=True)
        finally:
            # Delete only the temp file *this function generated* for PIL images.
            # If a path was passed in, this function doesn't own its lifecycle unless specifically told.
            # The xclip temp file is handled in monitor_clipboard IF it passes a PIL.Image.
            # If monitor_clipboard passed the path of its xclip temp file, it should manage it or
            # this function needs a flag.
            # Current logic: monitor_clipboard (Linux) creates temp, loads to PIL, deletes temp, passes PIL.
            # So temp_file_path_generated is the only one this function would create and delete.
            if temp_file_path_generated and os.path.exists(temp_file_path_generated):
                try:
                    os.unlink(temp_file_path_generated)
                    logging.info(f"Deleted temp file created by process_screenshot: {temp_file_path_generated}")
                except OSError as e:
                    logging.error(f"Error deleting temp file {temp_file_path_generated}: {e}")

    def start(self):
        logging.info(f"Snipping Lens starting on {self.os_type.capitalize()}...")
        logging.info(f"Snipping command: {' '.join(SNIPPING_COMMAND) if SNIPPING_COMMAND else 'N/A'}")
        logging.info(f"Monitoring processes: {self.current_snipping_process_names}")

        process_monitor_thread = threading.Thread(target=self.monitor_processes, daemon=True)
        process_monitor_thread.start()

        clipboard_thread = threading.Thread(target=self.monitor_clipboard, daemon=True)
        clipboard_thread.start()

        logging.info("Snipping Lens services started.")
        logging.info("Use tray icon: Left-click/select 'Snip & Search', or right-click for options.")
        logging.info("Screenshots appearing after a snipping tool runs will be auto-searched.")

        try:
            self.run_tray_icon() # This blocks until exit
        except Exception as tray_err:
             logging.error(f"Failed to run system tray icon: {tray_err}", exc_info=True)
             print(f"\nError: Could not start system tray icon ({tray_err}). Exiting.")
             self.exit_app() # Attempt graceful shutdown
             sys.exit(1)
        logging.info("Shutting down Snipping Lens...")

if __name__ == "__main__":
    # Basic dependency check (psutil already in original imports)
    try:
        import requests, pystray, PIL, psutil, platform, shutil, subprocess
    except ImportError as import_err:
         print(f"\nError: Missing essential library: {import_err.name}. Please ensure all dependencies are installed.")
         sys.exit(1)
    
    # Prevent multiple instances (simple mechanism)
    # This is very basic. For robust singleton, use a named mutex or lock file.
    # For now, focusing on the core features.
    
    try:
        snippinglens_app = SnippingLens()
        snippinglens_app.start()
    except Exception as e:
         logging.critical(f"Critical error during startup or runtime: {e}", exc_info=True)
         print(f"\nCritical error: {e}. Check logs at {log_file_path if 'log_file_path' in globals() else 'snipping_lens.log'}. Exiting.")
         sys.exit(1)