"""
Telegram Bot API Handler for Vercel
Webhook-based bot using FastAPI (compatible with Vercel's Python runtime)
"""
import asyncio
import json
import logging
import sys
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, LOG_LEVEL
from middleware.auth import AuthMiddleware
from middleware.credits import CreditsMiddleware
from handlers import start, download, profile, settings, admin, inline

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Telegram Bot Downloader")

# Global instances
bot: Bot | None = None
dp: Dispatcher | None = None


def get_bot_and_dispatcher():
    """Initialize bot and dispatcher"""
    global bot, dp

    if bot is None:
        bot = Bot(token=BOT_TOKEN)

    if dp is None:
        dp = Dispatcher(storage=MemoryStorage())

        # Register Middleware
        dp.message.outer_middleware(AuthMiddleware())
        dp.callback_query.outer_middleware(AuthMiddleware())

        dp.message.middleware(CreditsMiddleware())
        dp.callback_query.middleware(CreditsMiddleware())

        # Register Routers
        dp.include_router(admin.router)
        dp.include_router(start.router)
        dp.include_router(profile.router)
        dp.include_router(settings.router)
        dp.include_router(inline.router)
        dp.include_router(download.router)

    return bot, dp


@app.post("/api/webhook")
async def webhook(request: Request):
    """
    Main webhook endpoint for Telegram updates
    This is where Telegram sends all bot updates (messages, callbacks, etc.)
    """
    try:
        update_data = await request.json()
        logger.info(f"Received update: {update_data.get('update_id')}")

        bot, dp = get_bot_and_dispatcher()

        # Convert dict to Update object and process
        update = Update(**update_data)
        await dp.feed_update(bot, update)

        return JSONResponse({"ok": True}, status_code=200)

    except json.JSONDecodeError:
        logger.error("Invalid JSON in request")
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    except Exception as e:
        logger.error(f"Error processing update: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/health")
async def health():
    """Health check endpoint"""
    from config import DATABASE_URL, AWS_S3_BUCKET

    return JSONResponse({
        "status": "healthy",
        "services": {
            "bot_token": "✓" if BOT_TOKEN else "✗",
            "database": "✓" if DATABASE_URL else "✗",
            "s3_storage": "✓" if AWS_S3_BUCKET else "✗",
        }
    }, status_code=200)


@app.get("/")
async def root():
    """Root endpoint"""
    return JSONResponse({"message": "Telegram Bot is running", "status": "ok"})


# Health check on startup
@app.on_event("startup")
async def startup():
    logger.info("🚀 Bot API started successfully")
    bot, dp = get_bot_and_dispatcher()
    logger.info("✅ Bot and dispatcher initialized")
