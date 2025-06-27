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

