import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer

from config import BOT_TOKEN, LOG_LEVEL, USE_LOCAL_API, LOCAL_API_URL
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

async def main():
    logger.info("Starting bot...")
    
    # Initialize bot and dispatcher
    if USE_LOCAL_API:
        logger.info(f"Connecting to Local Bot API at {LOCAL_API_URL}")
        session = AiohttpSession(api=TelegramAPIServer.from_base(LOCAL_API_URL))
        bot = Bot(token=BOT_TOKEN, session=session)
    else:
        bot = Bot(token=BOT_TOKEN)
        
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
    
    # Delete webhook/drop pending updates to avoid flooding
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Start polling
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error in polling: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
