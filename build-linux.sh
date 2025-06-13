#!/bin/bash

# Snipping Lens - Linux Installation Script
# This script will install Snipping Lens and its dependencies on Linux Mint Debian Edition

set -e

echo "=== Snipping Lens Installation Script ==="
echo

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "Please do not run this script as root."
    exit 1
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for required system commands
echo "Checking system requirements..."

if ! command_exists python3; then
    echo "Error: python3 is not installed. Please install it first:"
    echo "sudo apt update && sudo apt install python3"
    exit 1
fi

if ! command_exists pip3; then
    echo "Installing pip3..."
    sudo apt update
    sudo apt install -y python3-pip
fi

# Install system dependencies
echo "Installing system dependencies..."
sudo apt update
sudo apt install -y xclip gnome-screenshot python3-tk python3-dev build-essential libayatana-appindicator3-1

# Install Python dependencies
echo "Installing Python dependencies..."
PYTHON_BIN="$(which python3)"
PIP_BIN="$(which pip3)"

echo "Using Python interpreter: $PYTHON_BIN"
echo "Using pip: $PIP_BIN"

"$PIP_BIN" install --user Pillow==11.1.0 psutil==7.0.0 pystray==0.19.5 requests==2.32.3 PyQt5==5.15.10

# Create application directory
APP_DIR="$HOME/.local/share/snipping-lens"
echo "Creating application directory: $APP_DIR"
mkdir -p "$APP_DIR"

# Copy the main script (assuming it's in the same directory as this install script)
if [ -f "snipping_lens.py" ]; then
    cp snipping_lens.py "$APP_DIR/"
    echo "Copied snipping_lens.py to $APP_DIR"
else
    echo "Error: snipping_lens.py not found in current directory"
    echo "Please make sure snipping_lens.py is in the same directory as this install script"
    exit 1
fi

# Copy tray_qt.py if it exists
if [ -f "tray_qt.py" ]; then
    cp tray_qt.py "$APP_DIR/"
    echo "Copied tray_qt.py to $APP_DIR"
else
    echo "Error: tray_qt.py not found in current directory"
    echo "Please make sure tray_qt.py is in the same directory as this install script"
    exit 1
fi

# Copy icon if it exists
if [ -f "my_icon.png" ]; then
    cp my_icon.png "$APP_DIR/"
    echo "Copied my_icon.png to $APP_DIR"
else
    echo "Warning: my_icon.png not found. The app will use a default icon."
fi

# Create executable wrapper script
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"

cat > "$BIN_DIR/snipping-lens" << EOF
#!/bin/bash
cd "$APP_DIR"
"$PYTHON_BIN" snipping_lens.py "\$@"
EOF

chmod +x "$BIN_DIR/snipping-lens"
echo "Created executable: $BIN_DIR/snipping-lens"

# Create desktop file
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_DIR/snipping-lens.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Snipping Lens
Exec=$BIN_DIR/snipping-lens
Icon=$APP_DIR/my_icon.png
Comment=Automatic Google Lens search for screenshots
Categories=Graphics;Photography;
Keywords=screenshot;lens;search;
StartupNotify=true
NoDisplay=false
EOF

echo "Created desktop file: $DESKTOP_DIR/snipping-lens.desktop"

# Create autostart entry
AUTOSTART_DIR="$HOME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"

cat > "$AUTOSTART_DIR/snipping-lens.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Snipping Lens
Exec=$BIN_DIR/snipping-lens
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Comment=Automatic Google Lens search for screenshots
EOF

echo "Created autostart entry: $AUTOSTART_DIR/snipping-lens.desktop"

# Update desktop database
if command_exists update-desktop-database; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo
    echo "WARNING: $HOME/.local/bin is not in your PATH."
    echo "Add the following line to your ~/.bashrc or ~/.profile:"
    echo "export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo
    echo "Then reload your shell with: source ~/.bashrc"
fi

echo
echo "=== Installation Complete! ==="
echo
echo "You can now:"
echo "1. Run 'snipping-lens' in terminal (if ~/.local/bin is in PATH)"
echo "2. Find 'Snipping Lens' in your applications menu"
echo "3. The app will start automatically on next login"
echo
echo "To start now: $BIN_DIR/snipping-lens"
echo
echo "The app will appear in your system tray. Left-click to take screenshots,"
echo "right-click for options (Pause/Resume, Show Logs, Exit)."
echo

# Ask if user wants to start now
read -p "Would you like to start Snipping Lens now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting Snipping Lens..."
    "$BIN_DIR/snipping-lens"
    echo "Snipping Lens started! Look for it in your system tray."
fi