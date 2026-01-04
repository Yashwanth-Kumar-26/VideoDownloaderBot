from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from aiogram.filters import CommandStart

from database.supabase_client import db

class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user:
            # Check if user exists in DB
            db_user = await db.get_user(user.id)
            
            import logging
            logger = logging.getLogger(__name__)
            # logger.info(f"Debug: Checking user {user.id}. Found: {bool(db_user)}")
            
            if not db_user:
                logger.info(f"Debug: User {user.id} not found. Registering...")
                
                # Handle referral if present in start command
                referrer_id = None
                if isinstance(event, Message) and event.text and event.text.startswith('/start'):
                    parts = event.text.split()
                    if len(parts) > 1:
                        ref_code = parts[1]
                        logger.info(f"Debug: Found referral code: {ref_code}")
                        
                        referrer = await db.get_user_by_referral_code(ref_code)
                        if referrer:
                            referrer_id = referrer['id']
                            logger.info(f"Debug: Valid referrer found: {referrer_id}")
                        else:
                            logger.warning(f"Debug: Referrer not found for code: {ref_code}")

                # Register new user
                db_user = await db.create_user(
                    telegram_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    referrer_id=referrer_id
                )
                logger.info(f"Debug: User created. Result: {bool(db_user)}")
            
            # Inject user into handler data
            data['db_user'] = db_user

        return await handler(event, data)
