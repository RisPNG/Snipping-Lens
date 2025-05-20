A Windows tool to change the functionality of the default snipping tool into a Google Lens tool similar to Android.


IGNORE BELOW



snipping_lens.py

```
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
import psutil # Import psutil to check processes

# --- Configuration ---
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# Change this line:
TRAY_ICON_PATH = resource_path("my_icon.png")
# List of process names associated with snipping tools
SNIPPING_PROCESS_NAMES = ["SnippingTool.exe", "ScreenClippingHost.exe", "ScreenSketch.exe"]
PROCESS_SCAN_INTERVAL_SECONDS = 0.75 # How often to scan for running processes
SNIP_PROCESS_TIMEOUT_SECONDS = 4.0  # How long after a snip process was seen to accept a clipboard image
# ---------------------

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        # logging.FileHandler('snipping_lens.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class SnippingLens:
    def __init__(self):
        self.last_clipboard_hash = None
        self.is_running = True
        self.icon = None
        # --- State for process detection ---
        self.last_snip_process_seen_time = 0.0
        self.process_state_lock = threading.Lock() # Lock for accessing shared time variable
        # ------------------------------------
        self.setup_autostart()

    def setup_autostart(self):
        # (Setup autostart code remains the same)
        try:
            if getattr(sys, 'frozen', False):
                executable_path = sys.executable
                if not executable_path.lower().endswith('.exe'):
                     pythonw_path = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
                     if os.path.exists(pythonw_path): executable_path = f'"{pythonw_path}" "{os.path.abspath(sys.argv[0])}"'
                     else: executable_path = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
                else: executable_path = f'"{executable_path}"'
            else:
                pythonw_path = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
                script_path = os.path.abspath(sys.argv[0])
                if os.path.exists(pythonw_path): executable_path = f'"{pythonw_path}" "{script_path}"'
                else: executable_path = f'"{sys.executable}" "{script_path}"'
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE) as registry_key:
                winreg.SetValueEx(registry_key, "SnippingLens", 0, winreg.REG_SZ, executable_path)
            logging.info(f"Added to startup: {executable_path}")
        except PermissionError: logging.error("Permission denied writing to registry for autostart.")
        except Exception as e: logging.error(f"Failed to add to startup: {e}")

    def create_default_image(self):
        # (Create default icon code remains the same)
        width = 64; height = 64; image = Image.new('RGB', (width, height), "black")
        dc = ImageDraw.Draw(image); dc.text((10, 20), "SU", fill="white"); return image

    def run_tray_icon(self):
        # (Run tray icon code remains the same)
        icon_image = None
        if TRAY_ICON_PATH and os.path.exists(TRAY_ICON_PATH):
            try: icon_image = Image.open(TRAY_ICON_PATH); logging.info(f"Using custom tray icon: {TRAY_ICON_PATH}")
            except Exception as e: logging.error(f"Failed load custom tray icon '{TRAY_ICON_PATH}': {e}. Using default.")
        if icon_image is None: logging.info("Using default generated tray icon."); icon_image = self.create_default_image()
        menu = pystray.Menu(pystray.MenuItem("Exit", self.exit_app))
        self.icon = pystray.Icon("SnippingLens", icon_image, "Snipping Lens", menu)
        logging.info("Running system tray icon."); self.icon.run()

    def exit_app(self, icon=None, item=None):
        # (Exit app code remains the same)
        logging.info("Exit requested."); self.is_running = False
        # No hotkey listener to stop now
        if self.icon:
            try: self.icon.stop()
            except Exception as e: logging.warning(f"Icon stop error: {e}")
        logging.info("Exiting application..."); time.sleep(0.5); os._exit(0)

    def get_image_hash(self, image):
        # (Get image hash code remains the same)
        if isinstance(image, Image.Image):
            try: return hash(image.tobytes())
            except Exception: return None
        elif isinstance(image, str): return hash(image)
        return None

    def get_google_lens_url(self, image_path):
        # (Get google lens URL code using Catbox remains the same)
        try:
            catbox_url = "https://catbox.moe/user/api.php"; filename = os.path.basename(image_path)
            logging.info(f"Uploading {image_path} to Catbox.moe...")
            with open(image_path, 'rb') as f:
                payload = {'reqtype': (None, 'fileupload'), 'userhash': (None, '')}
                files = {'fileToUpload': (filename, f)}; headers = {'User-Agent': 'SnippingLensScript/1.0'}
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

    # --- NEW: Background thread to monitor for snipping processes ---
    def monitor_processes(self):
        """Periodically scans running processes for known snipping tool names."""
        logging.info("Starting process monitor thread...")
        while self.is_running:
            found_snipping_process = False
            try:
                # Iterate through running processes
                for proc in psutil.process_iter(['name']): # Request only 'name' for efficiency
                    if proc.info['name'] in SNIPPING_PROCESS_NAMES:
                        # Use lower case comparison for robustness?
                        # if proc.info['name'].lower() in [n.lower() for n in SNIPPING_PROCESS_NAMES]:
                        logging.debug(f"Detected running snipping process: {proc.info['name']}")
                        found_snipping_process = True
                        break # Found one, no need to check further in this iteration
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Ignore processes that ended or we can't access
                pass
            except Exception as e:
                logging.error(f"Error scanning processes: {e}", exc_info=False) # Log other errors less verbosely

            # If found, update the timestamp
            if found_snipping_process:
                with self.process_state_lock:
                    self.last_snip_process_seen_time = time.time()

            # Wait before scanning again
            time.sleep(PROCESS_SCAN_INTERVAL_SECONDS)
        logging.info("Process monitor thread stopped.")
    # -------------------------------------------------------------

    # --- MODIFIED: Monitor clipboard checking process seen time ---
    def monitor_clipboard(self):
        logging.info("Starting clipboard monitor (will process images seen after snipping tool runs)...")
        while self.is_running:
            try:
                clipboard_content = ImageGrab.grabclipboard()
                if clipboard_content is None:
                    if self.last_clipboard_hash is not None: self.last_clipboard_hash = None
                    time.sleep(1); continue

                current_hash, image_to_process = None, None
                if isinstance(clipboard_content, Image.Image):
                    current_hash = self.get_image_hash(clipboard_content)
                    image_to_process = clipboard_content
                elif isinstance(clipboard_content, list):
                     for filename in clipboard_content:
                         if isinstance(filename, str) and os.path.isfile(filename) and filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                             try:
                                 with Image.open(filename) as img_test: img_test.verify()
                                 current_hash = self.get_image_hash(filename); image_to_process = filename; break
                             except Exception: continue
                     if not image_to_process and self.last_clipboard_hash is not None: self.last_clipboard_hash = None

                is_new_content = (image_to_process is not None) and \
                                 (current_hash != self.last_clipboard_hash or \
                                  (current_hash is None and self.last_clipboard_hash is not None))

                if is_new_content:
                    logging.debug(f"New image content detected (Type: {type(image_to_process)}). Checking source...")
                    should_process = False
                    with self.process_state_lock: # Lock to read the shared time safely
                        time_since_process_seen = time.time() - self.last_snip_process_seen_time

                    # Check if the image appeared within the timeout window after a process was seen
                    if 0 < time_since_process_seen <= SNIP_PROCESS_TIMEOUT_SECONDS:
                         logging.info(f"Image appeared {time_since_process_seen:.2f}s after snipping process seen. Processing.")
                         should_process = True
                         # Don't reset last_snip_process_seen_time here, let the monitor thread update it naturally
                    else:
                         logging.debug(f"Ignoring image (time since process seen: {time_since_process_seen:.2f}s > {SNIP_PROCESS_TIMEOUT_SECONDS}s or process not seen recently).")

                    if should_process:
                        process_thread = threading.Thread(target=self.process_screenshot, args=(image_to_process,), daemon=True)
                        process_thread.start()
                        self.last_clipboard_hash = current_hash # Update hash only if processed
                    else:
                        # Update hash even if ignored to prevent re-evaluation
                        self.last_clipboard_hash = current_hash

            except ImportError:
                if self.last_clipboard_hash is not None: self.last_clipboard_hash = None
            except Exception as e:
                 is_clipboard_error = "pywintypes.error" in repr(e) and ("OpenClipboard" in str(e) or "GetClipboardData" in str(e))
                 if not is_clipboard_error and "clipboard is empty" not in str(e).lower():
                     logging.error(f"Error monitoring clipboard: {e}", exc_info=False)
                     self.last_clipboard_hash = None
                 elif "clipboard is empty" in str(e).lower() and self.last_clipboard_hash is not None:
                     self.last_clipboard_hash = None
            finally:
                time.sleep(0.5) # Clipboard check interval
    # ----------------------------------------------------------

    def process_screenshot(self, screenshot_source):
        # (Process screenshot code remains the same)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S"); temp_file_path = None
        try:
            image_path = None
            if isinstance(screenshot_source, Image.Image):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.png', prefix=f'ss_{timestamp}_') as temp_file:
                        img_to_save = screenshot_source;
                        if img_to_save.mode in ['RGBA', 'P']: img_to_save = img_to_save.convert('RGB')
                        img_to_save.save(temp_file, format='PNG'); temp_file_path = temp_file.name
                    image_path = temp_file_path; logging.info(f"Screenshot saved: {image_path}")
                except Exception as save_err: logging.error(f"Failed save PIL Image: {save_err}", exc_info=True); return
            elif isinstance(screenshot_source, str) and os.path.isfile(screenshot_source):
                image_path = screenshot_source; logging.info(f"Processing file: {image_path}")
            else: logging.warning(f"Invalid source type: {type(screenshot_source)}"); return
            if not image_path: logging.error("No valid image path."); return
            search_url = self.get_google_lens_url(image_path)
            if search_url: logging.info(f"Opening Lens URL: {search_url}"); webbrowser.open_new_tab(search_url)
            else: logging.error("Failed to get Lens URL.")
        except Exception as e: logging.error(f"Error processing screenshot: {e}", exc_info=True)
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try: os.unlink(temp_file_path); logging.info(f"Deleted temp file: {temp_file_path}")
                except OSError as e: logging.error(f"Error deleting temp file {temp_file_path}: {e}")

    # --- MODIFIED: Start method now starts process monitor ---
    def start(self):
        """Start the service."""

        # Start the process monitor thread
        process_monitor_thread = threading.Thread(target=self.monitor_processes, daemon=True)
        process_monitor_thread.start()

        # Start the clipboard monitor thread
        clipboard_thread = threading.Thread(target=self.monitor_clipboard, daemon=True)
        clipboard_thread.start()

        # No longer starting hotkey listener
        # self.start_hotkey_listener()

        logging.info("Snipping Lens started (using process detection + Catbox.moe).")
        logging.info("Take screenshots (e.g., using Win+Shift+S or Snipping Tool).")
        logging.info("New screenshots appearing after tool runs will be searched on Google Lens.")
        logging.info("Use the system tray icon to exit.")

        try:
            self.run_tray_icon() # Blocks until exit
        except Exception as tray_err:
             logging.error(f"Failed to run system tray icon: {tray_err}", exc_info=True)
             print("\nError: Could not start system tray icon. Exiting.")
             self.exit_app()
             sys.exit(1)
        logging.info("Shutting down Snipping Lens...")
    # -------------------------------------------------------

# --- Main execution block (No Lock Mechanism) ---
if __name__ == "__main__":
    try: # Basic dependency check
        import requests, pystray, PIL, psutil # Added psutil check
    except ImportError as import_err:
         print(f"\nError: Missing library: {import_err.name}. Install with: pip install requests pystray Pillow psutil")
         sys.exit(1)

    try:
        snippinglens = SnippingLens()
        snippinglens.start()
    except Exception as e:
         logging.error(f"Critical error during startup: {e}", exc_info=True)
         print(f"\nCritical startup error: {e}. Check logs."); sys.exit(1)
```

release.yml

```
name: Build and Release EXE

permissions:
  contents: write # Required to create a release and upload assets

on:
  push:
    branches:
      - main # Adjust to your desired branch

jobs:
  build:
    # Only run if the commit message contains "Release v"
    if: contains(github.event.head_commit.message, 'Release v')
    runs-on: windows-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Set up Python 3.13.2
        uses: actions/setup-python@v4
        with:
          python-version: "3.13.2" # Specify your required Python version

      - name: Install Dependencies
        run: pip install -r requirements.txt

      - name: Install PyInstaller
        run: pip install pyinstaller

      - name: Build executable
        run: pyinstaller --onefile --windowed --name "Snipping Lens" --icon="my_icon.ico" --add-data="my_icon.png;." snipping_lens.py

      - name: Extract release info from commit message
        id: extract_release_info
        shell: bash
        run: |
          # Get the latest commit message
          commit_msg=$(git log -1 --pretty=%B)
          echo "Commit message:"
          echo "$commit_msg"
        
          # Extract the version (matches digits and optional dash/letters)
          version=$(echo "$commit_msg" | sed -n 's/.*Release v\([[:alnum:].\-]\+\).*/\1/p')
        
          # Extract the description between the tilde markers.
          # This assumes the description is enclosed between lines containing only '~'
          description=$(echo "$commit_msg" | sed -n '/^~$/,/^~$/p' | sed '1d;$d')

          # Ensure a valid version was found
          if [ -z "$version" ]; then
            echo "No valid release version found in the commit message. Exiting."
            exit 1
          fi
        
          # Determine if it's a pre-release (if version contains a dash)
          if echo "$version" | grep -q '-'; then
            prerelease=true
          else
            prerelease=false
          fi

          echo "Version: $version"
          echo "Description: $description"
          echo "Prerelease: $prerelease"

          # Set outputs using the environment file method.
          echo "version=$version" >> $GITHUB_OUTPUT
          echo "description<<EOF" >> $GITHUB_OUTPUT
          echo "$description" >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT
          echo "prerelease=$prerelease" >> $GITHUB_OUTPUT

      - name: Create Release
        id: create_release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: v${{ steps.extract_release_info.outputs.version }}
          release_name: "v${{ steps.extract_release_info.outputs.version }}"
          body: ${{ steps.extract_release_info.outputs.description }}
          draft: false
          prerelease: ${{ steps.extract_release_info.outputs.prerelease }}

      - name: Upload Release Asset
        uses: actions/upload-release-asset@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          upload_url: ${{ steps.create_release.outputs.upload_url }}
          asset_path: "./dist/Snipping Lens.exe"
          asset_name: SnippingLens.exe
          asset_content_type: application/octet-stream
```

requirements.txt

```
Pillow==11.1.0
psutil==7.0.0
pystray==0.19.5
Requests==2.32.3
```

This is a Python project of mine called Snipping Lens. I want to improve a few things:

1. To implement this for Linux Mint Debian Edition as well, specifically Linux Mint Debian Edition. Make it use xclip to detect images from the clipboard.
2. For both Windows and Linux Mint Debian Edition, left clicking the tray icon will launch a snipping tool for Windows and run `gnome-screenshot -c -a` for Linux Mint Debian Edition, and it will search the image as usual.
3. For Linux Mint Debian Edition, make sure the app is visible in the XApp Status Applet upon start. (The default applet that the Linux Mint Debian Edition GUI uses)
4. Right-clicking the tray icon shows

* Pause/Resume
* Show Logs
* Exit (already exists, so keep it)

5. For Linux Mint Debian Edition, make sure it to not detect every image in the clipboard, just right after when the user uses `gnome-screenshot`.
6. Update the release.yml to build for Linux as well, either AppImage or Deb package. Make sure the build works right out of the box without the end user needing to install extra apt packages or python / python dependencies on their end.
