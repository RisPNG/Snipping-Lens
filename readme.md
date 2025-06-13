# Snipping Lens

Snipping Lens is a cross-platform application that automatically detects when you take screenshots and searches them using Google Lens for quick information lookup.

## Features

- 🖼️ **Automatic Screenshot Detection**: Detects when you take screenshots using built-in tools
- 🔍 **Google Lens Integration**: Automatically opens screenshots in Google Lens for search
- 🖱️ **System Tray Integration**: Convenient access from your system tray
- ⚡ **Quick Screenshot**: Left-click tray icon to take instant screenshots
- ⏸️ **Pause/Resume**: Temporarily disable automatic detection
- 📝 **Log Viewing**: View application logs for troubleshooting
- 🚀 **Auto-start**: Starts automatically with your system
- 🌐 **Cross-platform**: Works on Windows and Linux Mint Debian Edition

## Supported Platforms

### Windows
- Windows 10/11
- Detects screenshots from:
  - Win+Shift+S (built-in snipping tool)
  - Snipping Tool application
  - Screen Sketch

### Linux Mint Debian Edition
- Requires xclip and gnome-screenshot
- Detects screenshots from gnome-screenshot

## Installation

### Windows

1. Download `SnippingLens.exe` from the [latest release](https://github.com/yourusername/snipping-lens/releases)
2. Run the executable
3. The app will appear in your system tray

### Linux Mint Debian Edition

#### Option 1: AppImage (Recommended)
1. Download `SnippingLens-x86_64.AppImage` from the [latest release](https://github.com/yourusername/snipping-lens/releases)
2. Make it executable: `chmod +x SnippingLens-x86_64.AppImage`
3. Run: `./SnippingLens-x86_64.AppImage`

#### Option 2: DEB Package
1. Download `snipping-lens.deb` from the [latest release](https://github.com/yourusername/snipping-lens/releases)
2. Install: `sudo dpkg -i snipping-lens.deb`
3. Fix dependencies if needed: `sudo apt-get install -f`
4. Run from applications menu or terminal: `snipping-lens`

#### Option 3: Manual Installation
1. Download the source code
2. Run the installation script: `bash install-linux.sh`
3. Follow the on-screen instructions

## Usage

### Taking Screenshots

**Windows:**
- Use Win+Shift+S, Snipping Tool, or left-click the tray icon
- Screenshots are automatically detected and opened in Google Lens

**Linux:**
- Use `gnome-screenshot -c -a` or left-click the tray icon
- Screenshots are automatically detected and opened in Google Lens

### Tray Icon Actions

- **Left-click**: Take a screenshot using the system's snipping tool
- **Right-click**: Show context menu with options:
  - **Pause/Resume**: Temporarily disable/enable automatic detection
  - **Show Logs**: View application logs in a text editor
  - **Exit**: Close the application

### Pause/Resume Feature

Use the Pause feature when you need to take screenshots without automatically opening them in Google Lens (e.g., for saving or editing).

## System Requirements

### Windows
- Windows 10 or later
- Internet connection for Google Lens

### Linux Mint Debian Edition
- Linux Mint Debian Edition (LMDE)
- xclip package
- gnome-screenshot package
- Internet connection for Google Lens

## Privacy & Security

- Screenshots are temporarily uploaded to Catbox.moe (a free image hosting service) to generate Google Lens URLs
- Temporary files are automatically deleted after processing
- No screenshots are stored permanently by this application
- The application only processes screenshots taken after snipping tools are detected running

## Troubleshooting

### Linux: "xclip not found" error
Install xclip:
```bash
sudo apt install xclip
```

### Linux: App not showing in system tray
Make sure you have a system tray applet installed:
```bash
sudo apt install xfce4-indicator-plugin
```

Or use the XApp Status Applet (pre-installed on Linux Mint).

### Windows: App not starting automatically
The application should automatically add itself to Windows startup. If not, you can manually add it through:
1. Win+R → `shell:startup`
2. Copy the executable to the startup folder

### General: Screenshots not being detected
1. Check if the application is paused (right-click tray icon)
2. View logs (right-click tray icon → Show Logs)
3. Ensure you're using supported screenshot tools

## Development

### Building from Source

#### Windows
```bash
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --onefile --windowed --name "Snipping Lens" --icon="my_icon.ico" --add-data="my_icon.png;." snipping_lens.py
```

#### Linux
```bash
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --onefile --name "snipping-lens" --add-data="my_icon.png:." snipping_lens.py
```

### Dependencies
- Pillow (PIL)
- psutil
- pystray
- requests
- xclip (Linux only, system package)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test on both Windows and Linux if possible
5. Submit a pull request

## Release Process

To trigger a release build, commit with a message containing "Release v" followed by the version number:

```
Release v1.0.0

~
- New feature: Cross-platform support
- New feature: Pause/Resume functionality  
- New feature: Log viewing
- Improved: Better screenshot detection
- Fixed: Various bug fixes
~
```

The GitHub Actions workflow will automatically:
- Build Windows executable
- Build Linux AppImage and DEB package
- Create a GitHub release with all artifacts

## License

MIT License - see LICENSE file for details

## Changelog

### v1.0.0
- ✨ Cross-platform support (Windows + Linux Mint Debian Edition)
- ✨ Left-click tray icon to take screenshots
- ✨ Pause/Resume functionality
- ✨ Log viewing capability
- ✨ Improved system tray integration
- ✨ AppImage and DEB package support for Linux
- 🐛 Various bug fixes and improvements

## Support

If you encounter issues:
1. Check the logs (right-click tray icon → Show Logs)
2. Check the [Issues](https://github.com/yourusername/snipping-lens/issues) page
3. Create a new issue with logs and system information