# 🎥 Telegram Video Downloader Bot 🤖

A powerful Telegram bot for downloading and splitting videos from various websites with advanced queue management.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows-green)](https://www.python.org/downloads/)
[![Author](https://img.shields.io/badge/Author-AvroHere-orange)](https://github.com/AvroHere)

## 🔥 Key Features  

### 📥 Download & Processing  
- 🌐 **Multi-Site Support**: Works with YouTube, Twitter, TikTok, and 1000+ sites via `yt-dlp`  
- ✂️ **Smart Splitting**: Automatically splits videos >50MB into Telegram-friendly 45MB parts  
- ⚡ **Dual Download Modes**: Uses `aria2c` for speed, falls back to native yt-dlp  
- 🖼️ **Thumbnail Generation**: Extracts cover images for videos/parts  

### ⚙️ Advanced Controls  
- ⏱️ **Adjustable Timing**:  
  - Set delays between downloads (`/delay N`)  
  - Configure pauses between parts (`/slow N`)  
- 📝 **Caption Management**:  
  - Add temporary captions to next N videos (`/cap N text`)  
  - Set default caption for full videos (`/capedit text`)  

### 📊 Queue Management  
- 📂 **Bulk Processing**: Upload .txt files with multiple links  
- 🔄 **Queue Controls**:  
  - Skip specific links (`/skip N`)  
  - Cancel current download (`/cancel`)  
  - Clear entire queue (`/clean`)  
- 📡 **Real-Time Monitoring**:  
  - View remaining links (`/remain`)  
  - Get processing updates every 5 links  

### 🔒 Security & Convenience  
- 👑 **Admin-Only Access**: Restricted to authorized user IDs  
- 🔐 **Protected Content**: Uploads with anti-forwarding enabled  
- 📜 **Supported Sites**: View full list (`/support_file`)  

## 🛠️ Technical Details  
- Uses `ffmpeg` for video splitting and thumbnail generation  
- Implements async processing for efficient queue handling  
- Maintains persistent log of supported domains  

## 🚀 Quick Start  
1. Set up your `ADMIN_IDS` and `BOT_TOKEN` in config  
2. Deploy with Python 3.8+  
3. Send video links or .txt files to the bot  

```bash
python main.py

## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/AvroHere/Telegram-Video-Downloader-Bot.git
cd Telegram-Video-Downloader-Bot

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install ffmpeg (required for video processing)
# On Ubuntu/Debian
sudo apt-get install ffmpeg
# On macOS
brew install ffmpeg
# On Windows: Download from https://ffmpeg.org/download.html

# Set up your BOT_TOKEN in main.py
# Replace "7563249498:AAFr2iP35k8bBjMk-hchADIOn7Dv4SoPsVs" with your token

# Run the bot
python main.py
```

📋 Installation Steps
Clone the Repo 🐑: Use git clone to get the code.
Set Up Virtual Env 🛠️: Create and activate a Python virtual environment.
Install Dependencies 📦: Run pip install -r requirements.txt.
Install FFmpeg 🎬: Ensure ffmpeg and ffprobe are installed.
Configure Token 🔑: Add your Telegram Bot Token to main.py.
Run the Bot 🚀: Start the bot with python main.py.


```🧠 Usage
## 📚 Usage

> **How to Use the Bot**  
> Send URLs or a text file with URLs to the bot. Use admin commands to manage downloads, captions, and delays.

### 📋 Usage Methods
- **Send URLs** 🔗: Paste video URLs directly in the chat.
- **Upload Text File** 📄: Send a `.txt` file with URLs (one per line).
- **Admin Commands** 🛠️:
  - `/start` or `/menu`: Show command menu.
  - `/cap N text`: Add caption to next N videos.
  - `/capedit text`: Change default full video caption.
  - `/delay N`: Set delay between links (seconds).
  - `/slow N`: Set delay between parts (0-30s).
  - `/cancel`: Stop current download.
  - `/clean`: Cancel and clear queue.
  - `/skip N`: Skip N links.
  - `/remain`: Show remaining links.
  - `/support`: Show supported sites count.
  - `/support_file`: Get list of supported sites.

### 📋 Usage Steps
1. **Start Bot** 🚀: Ensure the bot is running (`python main.py`).
2. **Add Admin IDs** 🔒: Update `ADMIN_IDS` in `main.py` with your Telegram ID.
3. **Send Links** 🔗: Share video URLs or a text file with URLs.
4. **Use Commands** 🛠️: Control the bot with admin commands (e.g., `/cap 3 MyCaption`).
5. **Monitor Progress** 📊: Check queue status with `/remain` or `/support`.
```

## 📂 Folder Structure
```
Telegram-Video-Downloader-Bot/
├── LICENSE.txt         # MIT License file
├── README.md           # Project documentation
├── main.py             # Main bot script
├── requirements.txt    # Python dependencies
└── sitelog.txt         # List of supported sites (auto-generated)
```
## 🛠️ Built With

- **External Libraries**:
  - `yt-dlp`: Video downloading from multiple websites.
  - `python-telegram-bot`: Telegram API interaction.
  - `ffmpeg` (system): Video processing and splitting.

- **Standard Libraries**:
  - `os`: File and directory operations.
  - `sys`: System-specific parameters.
  - `asyncio`: Asynchronous operations.
  - `logging`: Logging bot activities.
  - `tempfile`: Temporary file management.
  - `subprocess`: Running FFmpeg commands.
  - `shutil`: File and directory cleanup.
  - `urllib.parse`: URL parsing.
```
## 🚀 Roadmap

- **🎨 Custom Thumbnail Styles**: Add options for thumbnail customization.
- **📈 Advanced Queue UI**: Display queue progress in a Telegram inline keyboard.
- **🔗 Batch URL Validation**: Validate URLs before adding to queue.
- **🔔 Notification System**: Notify admins of download failures.
- **📦 Docker Support**: Add Dockerfile for easy deployment.
- **🔍 Log Analysis**: Generate reports from bot activity logs.



