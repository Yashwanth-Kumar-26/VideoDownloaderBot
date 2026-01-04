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
   - Add your Telegram bot token: `BOT_TOKEN=your_token_here`

4. **Run the bot**:
   ```bash
   python main.py
   ```

##  Usage Guide 📖

1. **Start the bot**: Send `/start` to begin
2. **Download content**: Tap "📥 Download"
3. **Select platform**: Choose from available platforms
4. **Provide URL**: Send the link you want to download
5. **Choose format**: Select Video or MP3
6. **Video options**: Pick your preferred resolution
7. **Receive file**: Get your downloaded content instantly

##  Requirements 📋

- **Python**: 3.8 or higher
- **Telegram Bot Token**: Obtain from [@BotFather](https://t.me/botfather)
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
