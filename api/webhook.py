"""
Telegram Bot Webhook Handler for Vercel
This is the entry point for webhook-based bot updates
"""
import json
import logging
import asyncio
from typing import Dict, Any

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer

from config import BOT_TOKEN, USE_LOCAL_API, LOCAL_API_URL, LOG_LEVEL
from middleware.auth import AuthMiddleware
from middleware.credits import CreditsMiddleware
from handlers import start, download, profile, settings, admin, inline

# Configure logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL.upper(), logging.INFO))
logger = logging.getLogger(__name__)

# Global instances
_bot = None
_dp = None

def get_bot_and_dispatcher():
    """Get or create bot and dispatcher instances"""
    global _bot, _dp

    if _bot is None:
        if USE_LOCAL_API:
            logger.info(f"Connecting to Local Bot API at {LOCAL_API_URL}")
            session = AiohttpSession(api=TelegramAPIServer.from_base(LOCAL_API_URL))
            _bot = Bot(token=BOT_TOKEN, session=session)
        else:
            _bot = Bot(token=BOT_TOKEN)

    if _dp is None:
        _dp = Dispatcher(storage=MemoryStorage())

        # Register Middleware
        _dp.message.outer_middleware(AuthMiddleware())
        _dp.callback_query.outer_middleware(AuthMiddleware())

        _dp.message.middleware(CreditsMiddleware())
        _dp.callback_query.middleware(CreditsMiddleware())

        # Register Routers
        _dp.include_router(admin.router)
        _dp.include_router(start.router)
        _dp.include_router(profile.router)
        _dp.include_router(settings.router)
        _dp.include_router(inline.router)
        _dp.include_router(download.router)

    return _bot, _dp

async def handle_update(update_data: Dict[str, Any]) -> None:
    """Process a single Telegram update"""
    try:
        bot, dp = get_bot_and_dispatcher()

        # Convert dict to Update object
        update = Update(**update_data)

        # Process the update
        await dp.feed_update(bot, update)

    except Exception as e:
        logger.error(f"Error processing update: {e}", exc_info=True)

def handler(request) -> Dict[str, Any]:
    """
    Main webhook handler for Vercel

    Receives POST requests from Telegram with update information
    Returns a 200 response to confirm receipt
    """

    if request.method == "GET":
        return {"status": "ok", "message": "Telegram bot webhook is active"}

    if request.method != "POST":
        return {"status": "error", "message": "Method not allowed"}, 405

    try:
        # Parse JSON body
        update_data = request.json

        logger.info(f"Received update: {update_data}")

        # Process update asynchronously
        # Note: Since this is a serverless function with time limits,
        # we can attempt to process but may not complete if it takes too long
        asyncio.run(handle_update(update_data))

        return {"status": "ok"}, 200

    except json.JSONDecodeError:
        logger.error("Invalid JSON in request")
        return {"status": "error", "message": "Invalid JSON"}, 400
    except Exception as e:
        logger.error(f"Error in webhook handler: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}, 500
