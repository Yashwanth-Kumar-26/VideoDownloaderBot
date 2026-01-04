import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in environment variables.")

# Local Bot API Configuration
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
LOCAL_API_URL = os.getenv('LOCAL_API_URL', 'http://localhost:8081')
USE_LOCAL_API = bool(TELEGRAM_API_ID and TELEGRAM_API_HASH)

if USE_LOCAL_API:
    print(f"🚀 Local Bot API Enabled! URL: {LOCAL_API_URL}")
else:
    print("ℹ️ Standard API (Limit: 50MB). To enable 2GB, set API_ID/HASH.")

# Admin Configuration
ADMIN_USER_IDS = [int(id) for id in os.getenv('ADMIN_USER_IDS', '').split(',') if id]

# Supabase Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Feature Flags
ENABLE_CREDITS = os.getenv('ENABLE_CREDITS', 'true').lower() == 'true'
ENABLE_REFERRALS = os.getenv('ENABLE_REFERRALS', 'true').lower() == 'true'
FREE_DAILY_LIMIT = int(os.getenv('FREE_DAILY_LIMIT', '10'))
REFERRAL_REWARD_CREDITS = int(os.getenv('REFERRAL_REWARD_CREDITS', '5'))

# Download Settings
MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '50'))
DEFAULT_VIDEO_QUALITY = os.getenv('DEFAULT_VIDEO_QUALITY', '720p')
SUPPORTED_PLATFORMS = ['youtube', 'instagram', 'twitter', 'reddit', 'tiktok', 'facebook']
DOWNLOAD_TYPES = ['video', 'audio']

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
