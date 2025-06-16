![RisPNG/Snipping-Lens](https://github.com/RisPNG/Snipping-Lens/blob/main/banner.png)
<p align="center">
<a href="https://github.com/RisPNG/Snipping-Lens/stargazers"><img alt="GitHub Repo Stars" src="https://img.shields.io/github/stars/RisPNG/Snipping-Lens?style=flat&color=limegreen"></a>
<a href="https://github.com/RisPNG/Snipping-Lens"><img alt="GitHub Last Commit" src="https://img.shields.io/github/last-commit/RisPNG/Snipping-Lens?style=flat&color=lightyellow"></a>
</p>

Snipping Lens is a cross-platform application that automatically detects when you take screenshots and searches them using Google Lens for quick information lookup and text extraction.

## Sections
1. [Installation](#installation)
1. [Usage](#usage)
2. [Requirements](#requirements)
2. [FAQ](#faq)
2. [Building from Source](#building-from-source)
3. [Support and Contributing](#support-and-contributing)
4. [Disclaimer](#disclaimer)

## Installation

Check [Releases](https://github.com/RisPNG/Snipping-Lens/releases) for the latest release and installation instructions.

## Usage

### Taking Screenshots

**Windows:**

- Use Win+Shift+S, or left-click the tray icon
- Screenshots are automatically detected and opened in Google Lens

**Linux:**

- Use `gnome-screenshot -c -a` or left-click the tray icon
- Screenshots are automatically detected and opened in Google Lens

### Tray Icon Actions

- **Left-click**: Takes a screenshot according to the system's snipping tool or equivalent.
- **Right-click**: Show context menu with options:
  - **Pause/Resume**: Temporarily disable/enable automatic screenshot detection. Left-clicking the tray icon will snap and search regardless of the pause state. 
  - **Show Logs**: View application logs in a text editor..
  - **Exit**: Close the application

## Requirements

### Windows

- Windows 10 or later
- Internet connection for Google Lens

### Linux

- XApp Status Applet (Tested and default on Linux Mint Debian Edition, other Linux distros may or may not work)
- xclip package
- gnome-screenshot package
- Internet connection for Google Lens

## FAQ

### Where are my screenshots uploaded? Are they stored permanently?

Screenshots are uploaded to [Litterbox](https://litterbox.catbox.moe/), a free and anonymous image hosting service, solely for the purpose of generating a URL that can be used with Google Lens. Images uploaded to Litterbox are not stored permanently—they automatically expire and are deleted after 1 hour. No user information is attached to the upload, and the application does not keep any record of your screenshots.

### Limitations & Longevity

As long as Litterbox returns the expected response (a direct image URL) and as long as the Google Lens endpoint `https://lens.google.com/uploadbyurl?url=<uploaded_image_url>` still exists and works, this program will continue to function as intended. If either service changes or is discontinued, the program's automatic search feature may no longer work.

## Building from Source

Python 3.11 is recommended. If you use the provided installation scripts (`build-windows.bat` or `build-linux.sh`), all required dependencies will be installed automatically.

## Support and Contributing

If you like this project, please leave a star 🌟, and share it with your friends! Consider donating on [PayPal](https://paypal.me/rispng) to support development.

If you encounter any issue:

1. Check the [Issues](https://github.com/RisPNG/Snipping-Lens/issues) page if issue has been raised. 
2. Create a new issue if necessary and provide in-depth details of the issue including the relevant logs (right-click tray icon > Show Logs).

## Disclaimer

This project comes with no guarantee or warranty. You are responsible for whatever happens from using this project. This is a personal project and is in no way affiliated with Google nor Microsoft.
