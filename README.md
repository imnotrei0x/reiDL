# reiDL - A Video Downloader

reiDL is a lightweight yet powerful desktop application for downloading videos from popular platforms including YouTube, Twitter/X, and TikTok. Built with Python and customtkinter, it provides a modern interface with robust functionality for downloading videos in various qualities.

## Features

- 🎥 **Multi-platform Support**:
  - YouTube (including shorts)
  - Twitter/X 
  - TikTok

- 🎬 **Flexible Format Selection**:
  - HD/4K video quality options (platform dependent)
  - High-quality audio extraction
  - Automatic format detection

- ⏯️ **Advanced Download Management**:
  - Pause/Resume downloads
  - Cancel with automatic cleanup
  - Progress tracking with size/percentage display

- 🔄 **Smart Platform Detection**:
  - Automatic URL type recognition
  - Seamless switching between platforms
  - Format caching for improved performance
  
- 🎨 **Modern User Experience**:
  - Clean, dark-themed UI
  - System tray integration
  - Global hotkey support for quick access
  - Customizable download location

## Requirements

- Python 3.7+
- FFmpeg (included in releases or install separately)
- Required packages (install via pip):
  ```
  customtkinter>=5.2.0
  yt-dlp>=2024.5.31
  Pillow>=10.0.0
  keyboard>=0.13.5
  pystray>=0.19.4
  pynput>=1.7.6
  pywin32>=305 (Windows only)
  ```

## Installation

### Option 1: Run from Source

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/reidl.git
   cd reidl
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python reidl_ui.py
   ```

## Usage Guide

1. **Launch the application** - Either run from source or use the executable
2. **Paste a URL** - Support for YouTube, Twitter/X, and TikTok
3. **Select quality options** - Choose from available video and audio qualities
4. **Download** - Click the Download button to start
5. **Manage downloads** - Pause, resume or cancel as needed
6. **Access quickly** - Use the configurable global hotkey to show/hide the app

## Technical Details

ReiDL uses yt-dlp under the hood, providing:

- Adaptive format selection based on platform
- Reliable downloading with error handling
- Proper handling of platform-specific URLs and formats
- Efficient cleanup of partial files on cancellation
- Thread-based downloading for responsive UI

## Configuration

- Settings are stored in `config.json`
- Default download location: User's Downloads folder
- Global hotkey configurable through the settings menu (⚙️)
- Automatic filename generation based on platform

## Troubleshooting

- **File Format Issues**: Make sure FFmpeg is installed or included
- **Download Failures**: Check your internet connection or try a different format
- **Platform Support**: If a platform changes its API, update yt-dlp to the latest version

## Author

- [@imnotrei0x](https://x.com/imnotrei0x)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 