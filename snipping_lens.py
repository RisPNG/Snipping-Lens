import os
import time
import threading
import tempfile
import webbrowser
import logging
import sys
import platform
import subprocess
import json
from datetime import datetime
import requests
import psutil  # Import psutil to check processes

# Platform-specific imports
if platform.system() == "Windows":
    import winreg
    from PIL import ImageGrab, Image, ImageDraw, UnidentifiedImageError
else:  # Linux
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, GLib, GdkPixbuf
    from PIL import Image, ImageDraw, UnidentifiedImageError
    import io
    import base64

# --- Configuration ---
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# Icon paths
TRAY_ICON_PATH = resource_path("my_icon.png")
LOG_FILE_PATH = os.path.join(os.path.expanduser("~"), ".snipping_lens.log")

# Platform specific settings
if platform.system() == "Windows":
    # Windows settings
    SNIPPING_PROCESS_NAMES = ["SnippingTool.exe", "ScreenClippingHost.exe", "ScreenSketch.exe"]
    PROCESS_SCAN_INTERVAL_SECONDS = 0.75  # How often to scan for running processes
    SNIP_PROCESS_TIMEOUT_SECONDS = 4.0    # How long after a snip process was seen to accept a clipboard image
    SNIPPING_COMMAND = "explorer ms-screenclip:"
else:
    # Linux settings
    SNIPPING_PROCESS_NAMES = ["gnome-screenshot"]
    PROCESS_SCAN_INTERVAL_SECONDS = 0.75
    SNIP_PROCESS_TIMEOUT_SECONDS = 4.0
    SNIPPING_COMMAND = "gnome-screenshot -c -a"
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
        self.is_paused = False  # New pause state
        self.icon = None
        # --- State for process detection ---
        self.last_snip_process_seen_time = 0.0
        self.process_state_lock = threading.Lock()  # Lock for accessing shared time variable
        # ------------------------------------
        self.setup_autostart()

    def setup_autostart(self):
        """Set up the application to start automatically."""
        try:
            if platform.system() == "Windows":
                self._setup_windows_autostart()
            else:
                self._setup_linux_autostart()
        except Exception as e:
            logging.error(f"Failed to add to startup: {e}")

    def _setup_windows_autostart(self):
        """Set up autostart for Windows."""
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
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE) as registry_key:
                winreg.SetValueEx(registry_key, "SnippingLens", 0, winreg.REG_SZ, executable_path)
            logging.info(f"Added to Windows startup: {executable_path}")
        except PermissionError:
            logging.error("Permission denied writing to registry for autostart.")

    def _setup_linux_autostart(self):
        """Set up autostart for Linux."""
        try:
            autostart_dir = os.path.expanduser("~/.config/autostart")
            os.makedirs(autostart_dir, exist_ok=True)
            
            desktop_file_path = os.path.join(autostart_dir, "snipping-lens.desktop")
            
            # Get the path to the executable
            if getattr(sys, 'frozen', False):
                # If running as a bundled executable
                exec_path = sys.executable
            else:
                # If running as a Python script
                exec_path = f"{sys.executable} {os.path.abspath(sys.argv[0])}"
                
            desktop_file_content = f"""[Desktop Entry]
                                    Type=Application
                                    Name=Snipping Lens
                                    Comment=Automatically search screenshots with Google Lens
                                    Exec={exec_path}
                                    Icon={os.path.abspath(TRAY_ICON_PATH)}
                                    Terminal=false
                                    Categories=Utility;
                                    StartupNotify=true
                                    X-GNOME-Autostart-enabled=true
                                    """
            
            with open(desktop_file_path, "w") as f:
                f.write(desktop_file_content)
                
            # Set executable permission
            os.chmod(desktop_file_path, 0o755)
            
            logging.info(f"Added to Linux autostart: {desktop_file_path}")
        except Exception as e:
            logging.error(f"Failed to create Linux autostart file: {e}")

    def create_default_image(self):
        """Create a default icon if the custom one is not available."""
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), "black")
        dc = ImageDraw.Draw(image)
        dc.text((10, 20), "SL", fill="white")
        return image

    def _create_menu_items(self):
        """Create the system tray menu items."""
        if platform.system() == "Windows":
            return self._create_windows_menu_items()
        else:
            return self._create_linux_menu_items()

    def _create_windows_menu_items(self):
        """Create the system tray menu items for Windows."""
        import pystray
        pause_item = pystray.MenuItem(
            "Pause" if not self.is_paused else "Resume", 
            self.toggle_pause
        )
        logs_item = pystray.MenuItem("Show Logs", self.show_logs)
        exit_item = pystray.MenuItem("Exit", self.exit_app)
        return pystray.Menu(pause_item, logs_item, exit_item)

    def _create_linux_menu_items(self):
        """Create the system tray menu items for Linux."""
        menu = Gtk.Menu()
        
        pause_item = Gtk.MenuItem.new_with_label("Pause" if not self.is_paused else "Resume")
        pause_item.connect('activate', self.toggle_pause)
        menu.append(pause_item)
        
        logs_item = Gtk.MenuItem.new_with_label("Show Logs")
        logs_item.connect('activate', self.show_logs)
        menu.append(logs_item)
        
        separator = Gtk.SeparatorMenuItem()
        menu.append(separator)
        
        exit_item = Gtk.MenuItem.new_with_label("Exit")
        exit_item.connect('activate', self.exit_app)
        menu.append(exit_item)
        
        menu.show_all()
        return menu

    def _handle_icon_click(self, icon, button=1):
        """Handle click on the tray icon."""
        if button == 1:  # Left click
            self.launch_snipping_tool()

    def run_tray_icon(self):
        """Run the system tray icon."""
        icon_image = None
        if TRAY_ICON_PATH and os.path.exists(TRAY_ICON_PATH):
            try: 
                icon_image = Image.open(TRAY_ICON_PATH)
                logging.info(f"Using custom tray icon: {TRAY_ICON_PATH}")
            except Exception as e: 
                logging.error(f"Failed load custom tray icon '{TRAY_ICON_PATH}': {e}. Using default.")
        
        if icon_image is None: 
            logging.info("Using default generated tray icon.")
            icon_image = self.create_default_image()
            
        if platform.system() == "Windows":
            self._run_windows_tray_icon(icon_image)
        else:
            self._run_linux_tray_icon(icon_image)

    def _run_windows_tray_icon(self, icon_image):
        """Run the Windows system tray icon."""
        import pystray
        menu = self._create_menu_items()
        self.icon = pystray.Icon("SnippingLens", icon_image, "Snipping Lens", menu)
        self.icon.on_click = self._handle_icon_click
        logging.info("Running Windows system tray icon.")
        self.icon.run()

    def _run_linux_tray_icon(self, icon_image):
        """Run the Linux system tray icon."""
        # Convert PIL image to GdkPixbuf
        data = io.BytesIO()
        icon_image.save(data, format='PNG')
        loader = GdkPixbuf.PixbufLoader.new_with_type('png')
        loader.write(data.getvalue())
        loader.close()
        pixbuf = loader.get_pixbuf()
        
        self.linux_status_icon = Gtk.StatusIcon()
        self.linux_status_icon.set_from_pixbuf(pixbuf)
        self.linux_status_icon.set_tooltip_text("Snipping Lens")
        self.linux_status_icon.connect('popup-menu', self._show_linux_menu)
        self.linux_status_icon.connect('activate', lambda icon: self.launch_snipping_tool())
        
        # Set the AppIndicator name for XApp Status Applet
        self.linux_status_icon.set_name("SnippingLens")
        self.linux_status_icon.set_title("Snipping Lens")
        
        logging.info("Running Linux system tray icon.")
        Gtk.main()

    def _show_linux_menu(self, icon, button, time):
        """Show the Linux system tray menu."""
        menu = self._create_linux_menu_items()
        menu.popup(None, None, None, None, button, time)

    def toggle_pause(self, icon=None, item=None):
        """Toggle the pause state of the application."""
        self.is_paused = not self.is_paused
        logging.info(f"Application {'paused' if self.is_paused else 'resumed'}")
        
        # Update the menu item text
        if platform.system() == "Windows":
            self.icon.menu = self._create_menu_items()
        else:
            # For Linux, we'll just recreate the menu when it's shown
            pass

    def show_logs(self, icon=None, item=None):
        """Show the application logs."""
        try:
            if platform.system() == "Windows":
                os.startfile(LOG_FILE_PATH)
            else:
                subprocess.Popen(['xdg-open', LOG_FILE_PATH])
        except Exception as e:
            logging.error(f"Failed to open log file: {e}")

    def launch_snipping_tool(self):
        """Launch the appropriate snipping tool for the platform."""
        try:
            logging.info(f"Launching snipping tool with command: {SNIPPING_COMMAND}")
            if platform.system() == "Windows":
                os.system(SNIPPING_COMMAND)
            else:
                subprocess.Popen(SNIPPING_COMMAND, shell=True)
        except Exception as e:
            logging.error(f"Failed to launch snipping tool: {e}")

    def exit_app(self, icon=None, item=None):
        """Exit the application."""
        logging.info("Exit requested.")
        self.is_running = False
        
        if platform.system() == "Windows":
            if self.icon:
                try: 
                    self.icon.stop()
                except Exception as e: 
                    logging.warning(f"Icon stop error: {e}")
        else:
            Gtk.main_quit()
            
        logging.info("Exiting application...")
        time.sleep(0.5)
        os._exit(0)

    def get_image_hash(self, image):
        """Generate a hash for an image to detect changes."""
        if isinstance(image, Image.Image):
            try: 
                return hash(image.tobytes())
            except Exception: 
                return None
        elif isinstance(image, str): 
            return hash(image)
        return None

    def get_google_lens_url(self, image_path):
        """Upload the image to Catbox.moe and return a Google Lens URL."""
        try:
            catbox_url = "https://catbox.moe/user/api.php"
            filename = os.path.basename(image_path)
            logging.info(f"Uploading {image_path} to Catbox.moe...")
            
            with open(image_path, 'rb') as f:
                payload = {'reqtype': (None, 'fileupload'), 'userhash': (None, '')}
                files = {'fileToUpload': (filename, f)}
                headers = {'User-Agent': 'SnippingLensScript/1.0'}
                response = requests.post(
                    catbox_url, 
                    files=files, 
                    data=payload, 
                    headers=headers, 
                    timeout=60
                )
                
            response.raise_for_status()
            catbox_link = response.text.strip()
            
            if response.status_code == 200 and catbox_link.startswith('https://files.catbox.moe/'):
                logging.info(f"Image uploaded: {catbox_link}")
                return f"https://lens.google.com/uploadbyurl?url={catbox_link}"
            else: 
                logging.error(
                    f"Failed Catbox upload. Status: {response.status_code}, "
                    f"Response: {response.text[:200]}..."
                )
                return None
        except requests.exceptions.Timeout:
            logging.error("Catbox upload timed out.")
            return None
        except requests.exceptions.RequestException as e:
            response_details = f"Network error: {e}"
            if hasattr(e, 'response') and e.response is not None:
                response_details = (
                    f"Status: {e.response.status_code}, "
                    f"Response: {e.response.text[:200]}..."
                )
            logging.error(f"Error uploading to Catbox: {response_details}")
            return None
        except Exception as e:
            logging.error(f"Unexpected Catbox/Lens error: {e}", exc_info=True)
            return None

    def monitor_processes(self):
        """Periodically scan running processes for known snipping tool names."""
        logging.info("Starting process monitor thread...")
        while self.is_running:
            if not self.is_paused:
                found_snipping_process = False
                try:
                    # Iterate through running processes
                    for proc in psutil.process_iter(['name']):
                        if proc.info['name'] in SNIPPING_PROCESS_NAMES:
                            logging.debug(f"Detected running snipping process: {proc.info['name']}")
                            found_snipping_process = True
                            break  # Found one, no need to check further
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    # Ignore processes that ended or we can't access
                    pass
                except Exception as e:
                    logging.error(f"Error scanning processes: {e}", exc_info=False)

                # If found, update the timestamp
                if found_snipping_process:
                    with self.process_state_lock:
                        self.last_snip_process_seen_time = time.time()

            # Wait before scanning again
            time.sleep(PROCESS_SCAN_INTERVAL_SECONDS)
            
        logging.info("Process monitor thread stopped.")

    def monitor_clipboard_windows(self):
        """Monitor the clipboard on Windows."""
        from PIL import ImageGrab
        
        logging.info("Starting Windows clipboard monitor...")
        while self.is_running:
            if not self.is_paused:
                try:
                    clipboard_content = ImageGrab.grabclipboard()
                    if clipboard_content is None:
                        if self.last_clipboard_hash is not None:
                            self.last_clipboard_hash = None
                        time.sleep(1)
                        continue

                    current_hash, image_to_process = None, None
                    if isinstance(clipboard_content, Image.Image):
                        current_hash = self.get_image_hash(clipboard_content)
                        image_to_process = clipboard_content
                    elif isinstance(clipboard_content, list):
                        for filename in clipboard_content:
                            if (isinstance(filename, str) and 
                                os.path.isfile(filename) and 
                                filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))):
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
                        logging.debug(
                            f"New image content detected (Type: {type(image_to_process)}). "
                            f"Checking source..."
                        )
                        should_process = False
                        
                        with self.process_state_lock:
                            time_since_process_seen = time.time() - self.last_snip_process_seen_time

                        # Check if the image appeared within the timeout window
                        if 0 < time_since_process_seen <= SNIP_PROCESS_TIMEOUT_SECONDS:
                            logging.info(
                                f"Image appeared {time_since_process_seen:.2f}s after "
                                f"snipping process seen. Processing."
                            )
                            should_process = True
                        else:
                            logging.debug(
                                f"Ignoring image (time since process seen: "
                                f"{time_since_process_seen:.2f}s > "
                                f"{SNIP_PROCESS_TIMEOUT_SECONDS}s or "
                                f"process not seen recently)."
                            )

                        if should_process:
                            process_thread = threading.Thread(
                                target=self.process_screenshot,
                                args=(image_to_process,),
                                daemon=True
                            )
                            process_thread.start()
                            self.last_clipboard_hash = current_hash
                        else:
                            # Update hash even if ignored
                            self.last_clipboard_hash = current_hash

                except ImportError:
                    if self.last_clipboard_hash is not None:
                        self.last_clipboard_hash = None
                except Exception as e:
                    is_clipboard_error = ("pywintypes.error" in repr(e) and 
                                        ("OpenClipboard" in str(e) or 
                                        "GetClipboardData" in str(e)))
                    if not is_clipboard_error and "clipboard is empty" not in str(e).lower():
                        logging.error(f"Error monitoring clipboard: {e}", exc_info=False)
                        self.last_clipboard_hash = None
                    elif "clipboard is empty" in str(e).lower() and self.last_clipboard_hash is not None:
                        self.last_clipboard_hash = None
                
            time.sleep(0.5)  # Clipboard check interval

    def monitor_clipboard_linux(self):
        """Monitor the clipboard on Linux using xclip."""
        logging.info("Starting Linux clipboard monitor...")
        
        while self.is_running:
            if not self.is_paused:
                try:
                    # Use xclip to check if there's an image in the clipboard
                    xclip_check = subprocess.run(
                        ["xclip", "-selection", "clipboard", "-t", "TARGETS", "-o"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )
                    
                    if xclip_check.returncode != 0:
                        time.sleep(1)
                        continue
                        
                    targets = xclip_check.stdout.strip().split('\n')
                    
                    # Check if any image formats are available
                    image_formats = ["image/png", "image/jpeg", "image/bmp", "image/gif"]
                    has_image = any(fmt in targets for fmt in image_formats)
                    
                    if not has_image:
                        if self.last_clipboard_hash is not None:
                            self.last_clipboard_hash = None
                        time.sleep(1)
                        continue
                    
                    # Get the image data from clipboard
                    for fmt in image_formats:
                        if fmt in targets:
                            xclip_get = subprocess.run(
                                ["xclip", "-selection", "clipboard", "-t", fmt, "-o"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE
                            )
                            
                            if xclip_get.returncode == 0 and xclip_get.stdout:
                                img_data = io.BytesIO(xclip_get.stdout)
                                try:
                                    img = Image.open(img_data)
                                    current_hash = self.get_image_hash(img)
                                    
                                    if current_hash != self.last_clipboard_hash:
                                        with self.process_state_lock:
                                            time_since_process_seen = time.time() - self.last_snip_process_seen_time
                                            
                                        if 0 < time_since_process_seen <= SNIP_PROCESS_TIMEOUT_SECONDS:
                                            logging.info(
                                                f"Image appeared {time_since_process_seen:.2f}s after "
                                                f"gnome-screenshot process seen. Processing."
                                            )
                                            # Save the image and process it
                                            with tempfile.NamedTemporaryFile(
                                                delete=False, suffix='.png', 
                                                prefix=f'ss_{datetime.now().strftime("%Y-%m-%d_%H%M%S")}_'
                                            ) as temp_file:
                                                img.save(temp_file, format='PNG')
                                                temp_file_path = temp_file.name
                                                
                                            process_thread = threading.Thread(
                                                target=self.process_screenshot,
                                                args=(temp_file_path,),
                                                daemon=True
                                            )
                                            process_thread.start()
                                            self.last_clipboard_hash = current_hash
                                        else:
                                            logging.debug(
                                                f"Ignoring image (time since process seen: "
                                                f"{time_since_process_seen:.2f}s > "
                                                f"{SNIP_PROCESS_TIMEOUT_SECONDS}s or "
                                                f"process not seen recently)."
                                            )
                                            self.last_clipboard_hash = current_hash
                                            
                                    break  # Found and processed an image
                                except Exception as e:
                                    logging.error(f"Error processing clipboard image: {e}")
                
                except Exception as e:
                    logging.error(f"Error monitoring Linux clipboard: {e}", exc_info=True)
                    if self.last_clipboard_hash is not None:
                        self.last_clipboard_hash = None
                
            time.sleep(0.5)  # Clipboard check interval

    def process_screenshot(self, screenshot_source):
        """Process a screenshot and search it with Google Lens."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        temp_file_path = None
        
        try:
            image_path = None
            if isinstance(screenshot_source, Image.Image):
                try:
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix='.png', prefix=f'ss_{timestamp}_'
                    ) as temp_file:
                        img_to_save = screenshot_source
                        if img_to_save.mode in ['RGBA', 'P']:
                            img_to_save = img_to_save.convert('RGB')
                        img_to_save.save(temp_file, format='PNG')
                        temp_file_path = temp_file.name
                    image_path = temp_file_path
                    logging.info(f"Screenshot saved: {image_path}")
                except Exception as save_err:
                    logging.error(f"Failed save PIL Image: {save_err}", exc_info=True)
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
        """Start the service."""
        # Start the process monitor thread
        process_monitor_thread = threading.Thread(
            target=self.monitor_processes,
            daemon=True
        )
        process_monitor_thread.start()

        # Start the appropriate clipboard monitor thread
        if platform.system() == "Windows":
            clipboard_thread = threading.Thread(
                target=self.monitor_clipboard_windows,
                daemon=True
            )
        else:
            clipboard_thread = threading.Thread(
                target=self.monitor_clipboard_linux,
                daemon=True
            )
        clipboard_thread.start()

        platform_name = platform.system()
        logging.info(f"Snipping Lens started on {platform_name} (using process detection + Catbox.moe).")
        
        if platform_name == "Windows":
            logging.info("Take screenshots (e.g., using Win+Shift+S or Snipping Tool).")
        else:
            logging.info("Take screenshots (e.g., using gnome-screenshot or the tray icon).")
            
        logging.info("New screenshots appearing after tool runs will be searched on Google Lens.")
        logging.info("Use the system tray icon to launch the screenshot tool or exit.")

        try:
            self.run_tray_icon()  # Blocks until exit
        except Exception as tray_err:
            logging.error(f"Failed to run system tray icon: {tray_err}", exc_info=True)
            print("\nError: Could not start system tray icon. Exiting.")
            self.exit_app()
            sys.exit(1)
            
        logging.info("Shutting down Snipping Lens...")

# --- Main execution block ---
if __name__ == "__main__":
    # Check platform requirements
    if platform.system() == "Windows":
        try:
            import requests, pystray, PIL, psutil
        except ImportError as import_err:
            print(f"\nError: Missing library: {import_err.name}. Install with: pip install requests pystray Pillow psutil")
            sys.exit(1)
    else:  # Linux
        try:
            import requests, PIL, psutil, gi
            # Check for xclip
            xclip_check = subprocess.run(["which", "xclip"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if xclip_check.returncode != 0:
                print("\nError: xclip is not installed. Please install it with: sudo apt-get install xclip")
                sys.exit(1)
        except ImportError as import_err:
            print(f"\nError: Missing library: {import_err.name}. Install with: pip install requests Pillow psutil PyGObject")
            sys.exit(1)

    try:
        snippinglens = SnippingLens()
        snippinglens.start()
    except Exception as e:
        logging.error(f"Critical error during startup: {e}", exc_info=True)
        print(f"\nCritical startup error: {e}. Check logs at {LOG_FILE_PATH}")
        sys.exit(1)