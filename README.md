#  Telegram Downloader Bot   🚀

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

A powerful Telegram bot for downloading videos and audio from YouTube, Instagram, Twitter, and Reddit with an intuitive interface and robust error handling. Powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp).

[🚀 Try the Bot](https://t.me/allvidodownloaderbot?start=7be21e73)

##  Features ✨

| Feature | Description |
|---------|-------------|
| 🎥 **Multi-Platform Support** | Download from YouTube, Instagram, Twitter, and Reddit |
| 🔄 **Multiple Resolutions** | Choose from various video resolutions |
| 🎵 **Audio Extraction** | Extract audio as high-quality MP3 |
| 🎮 **Inline Navigation** | Easy-to-use button-based interface |
| 🛡️ **Error Handling** | Robust handling of invalid links and unsupported content |
| 👥 **Referral System** | Invite friends and track referrals |
| ⚙️ **Admin Panel** | Dedicated Admin Bot for stats, broadcasting, and user management |

##  Quick Setup 🛠️

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd TelegramBots/Downloader
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   - Copy `.env.example` to `.env`
   - Fill in the required variables:
     ```env
     BOT_TOKEN=your_downloader_bot_token
     ADMIN_BOT_TOKEN=your_admin_bot_token
     ADMIN_USER_IDS=123456789,987654321
     ```

4. **Run the bots**:
   ```bash
   python run_all.py
   ```
   *(Or just `python main.py` / `python admin_main.py` individually)*

##  Usage Guide 📖

### 🤖 Downloader Bot
1. **Start**: Send `/start`
2. **Download**: Tap "📥 Download" -> Select Platform -> Send Link.

### 👑 Admin Bot
1. **Start**: Send `/start` (Must be an Admin).
2. **Dashboard**: View live stats (Users, Downloads).
3. **Broadcast**: Send messages to all users.
4. **Manage Users**: Search, add/remove credits, toggle premium.

##  Requirements 📋

- **Python**: 3.8 or higher
- **Telegram Bot Tokens**: Two tokens (one for Downloader, one for Admin)
- **FFmpeg**: For audio processing (handled by yt-dlp)
- **Internet Connection**: Required for downloading content

##  Production Deployment 🚀

### Option 1: Systemd Service (Linux)
Run the bot as a background service with auto-restart capabilities.

1. **Configure service file**:
   Edit `telegram-downloader.service` to match your system paths.

2. **Install and start**:
   ```bash
   sudo cp telegram-downloader.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable telegram-downloader
   sudo systemctl start telegram-downloader
   ```

3. **Monitor service**:
   ```bash
   sudo systemctl status telegram-downloader
   journalctl -u telegram-downloader -f
   ```

### Option 2: Docker Container
Deploy in an isolated container environment.

1. **Build and run**:
   ```bash
   docker-compose up -d --build
   ```

2. **View logs**:
   ```bash
   docker-compose logs -f
   ```

3. **Stop container**:
   ```bash
   docker-compose down
   ```

##  Contributing 🤝

Contributions are welcome! Please feel free to submit a Pull Request.

##  License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
