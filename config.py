import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in environment variables.")

LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID') or 0)


# Local Bot API Configuration
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
# Default to localhost if not set, but Docker will override this via env var
LOCAL_API_URL = os.getenv('LOCAL_API_URL', 'http://localhost:8081')
USE_LOCAL_API = bool(TELEGRAM_API_ID and TELEGRAM_API_HASH)

if USE_LOCAL_API:
    print(f"🚀 Local Bot API Enabled! URL: {LOCAL_API_URL}")
else:
    print("ℹ️ Standard API (Limit: 50MB). To enable 2GB, set API_ID/HASH.")

# Admin Configuration
ADMIN_USER_IDS = [int(id) for id in os.getenv('ADMIN_USER_IDS', '').split(',') if id]

# Supabase Configuration (Legacy/Unused but kept for env compatibility if needed, though replaced by PostgresClient)
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
SUPPORTED_PLATFORMS = ['youtube', 'instagram', 'twitter', 'reddit', 'spotify', 'facebook']
DOWNLOAD_TYPES = ['video', 'audio']

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# ========== VERCEL DEPLOYMENT CONFIGURATION ==========

# Database Configuration (PostgreSQL for Vercel)
DATABASE_URL = os.getenv('DATABASE_URL')
# If using local development, SQLite can still be used as fallback

# AWS S3 Configuration (for file storage on Vercel)
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_S3_BUCKET = os.getenv('AWS_S3_BUCKET')
AWS_S3_REGION = os.getenv('AWS_S3_REGION', 'us-east-1')

# Determine if running on Vercel/serverless
IS_VERCEL = os.getenv('VERCEL') == '1'
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# For Vercel webhook
if IS_VERCEL:
    print("🔵 Running on Vercel (serverless environment)")
    if not DATABASE_URL:
        print("⚠️  WARNING: DATABASE_URL not set. Using SQLite for local testing only.")
else:
    print("🟢 Running on local/traditional environment")

# Log storage configuration
HAS_S3 = bool(AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and AWS_S3_BUCKET)
if HAS_S3:
    print(f"📦 S3 Storage enabled: s3://{AWS_S3_BUCKET}/")
else:
    print("📁 Using local file storage (not recommended for Vercel)")
