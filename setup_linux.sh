#!/bin/bash

set -euo pipefail

# Always run relative to the repo root (so autostart works).
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

download_to() {
    local url="$1"
    local out="$2"
    if command -v curl >/dev/null 2>&1; then
        curl -L -o "$out" "$url"
        return
    fi
    if command -v wget >/dev/null 2>&1; then
        wget -O "$out" "$url"
        return
    fi
    echo "Error: missing downloader (need curl or wget)"
    exit 1
}

extract_zip() {
    local zip="$1"
    local dest="$2"
    if command -v unzip >/dev/null 2>&1; then
        unzip -q "$zip" -d "$dest"
        return
    fi
    if command -v python3 >/dev/null 2>&1; then
        python3 -m zipfile -e "$zip" "$dest"
        return
    fi
    echo "Error: missing zip extractor (need unzip or python3)"
    exit 1
}

# Check if MsPy-3_11_14 folder exists and has the binary
PYTHON_BINARY="int/linux/MsPy-3_11_14/bin/python3.11"
MSPY_FOLDER="int/linux/MsPy-3_11_14"

if [ ! -d "$MSPY_FOLDER" ] || [ ! -f "$PYTHON_BINARY" ]; then
    echo "MsPy-3_11_14 not found or binary missing. Downloading..."

    # Delete the folder if it exists but is incomplete
    if [ -d "$MSPY_FOLDER" ]; then
        rm -rf "$MSPY_FOLDER"
    fi

    # Create linux directory if it doesn't exist
    mkdir -p int/linux

    # Download the zip file
    download_to "https://github.com/RisPNG/MsPy/releases/download/3.11.14/MsPy-3_11_14-linux.zip" "/tmp/MsPy-3_11_14-linux.zip"

    # Extract to int/linux directory
    extract_zip "/tmp/MsPy-3_11_14-linux.zip" "int/linux/"

    # Clean up zip file
    rm /tmp/MsPy-3_11_14-linux.zip

    # Verify binary exists
    if [ ! -f "$PYTHON_BINARY" ]; then
        echo "Error: Binary not found at $PYTHON_BINARY after extraction"
        exit 1
    fi

    echo "MsPy-3_11_14 successfully downloaded and extracted"
fi

# Check if venv exists and is valid (to determine if we need to run pip install)
VENV_NEWLY_CREATED=false
VENV_NEEDS_RECREATION=false

# Get the absolute path to our Python binary
EXPECTED_PYTHON_HOME=$(cd "$(dirname "$PYTHON_BINARY")" && pwd)

if [ ! -f "int/linux/venv/bin/python" ]; then
    VENV_NEEDS_RECREATION=true
elif [ -f "int/linux/venv/pyvenv.cfg" ]; then
    # Check if venv points to the correct Python home
    if ! grep -q "home = $EXPECTED_PYTHON_HOME" "int/linux/venv/pyvenv.cfg"; then
        echo "Virtual environment points to wrong Python location, recreating..."
        VENV_NEEDS_RECREATION=true
    fi
else
    VENV_NEEDS_RECREATION=true
fi

if [ "$VENV_NEEDS_RECREATION" = true ]; then
    VENV_NEWLY_CREATED=true
    echo "Creating new virtual environment..."

    # Remove existing venv if it exists but is incomplete/wrong platform
    if [ -d "int/linux/venv" ]; then
        rm -rf "int/linux/venv"
    fi

    $PYTHON_BINARY -m venv "int/linux/venv"
fi

# Activate the venv
. int/linux/venv/bin/activate

REQUIREMENTS_FILE="bin/linux/src/requirements.txt"
REQUIREMENTS_HASH_FILE="int/linux/venv/.requirements.sha256"

compute_sha256() {
    local file="$1"
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$file" | awk '{print $1}'
        return
    fi
    python3 - <<PY
import hashlib
path = r"""$file"""
h = hashlib.sha256()
with open(path, "rb") as f:
    for chunk in iter(lambda: f.read(1024 * 1024), b""):
        h.update(chunk)
print(h.hexdigest())
PY
}

REQ_HASH="$(compute_sha256 "$REQUIREMENTS_FILE")"
OLD_REQ_HASH=""
if [ -f "$REQUIREMENTS_HASH_FILE" ]; then
    OLD_REQ_HASH="$(cat "$REQUIREMENTS_HASH_FILE" || true)"
fi

if [ "$VENV_NEWLY_CREATED" = true ] || [ "$REQ_HASH" != "$OLD_REQ_HASH" ]; then
    echo "Installing/updating dependencies..."
    pip install --upgrade pip
    pip install -r "$REQUIREMENTS_FILE"
    echo "$REQ_HASH" > "$REQUIREMENTS_HASH_FILE"
else
    echo "Dependencies are up to date (skipping pip install)"
fi

# Run the script
python bin/linux/src/main.py
