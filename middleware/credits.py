from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject

from config import ENABLE_CREDITS, ADMIN_USER_IDS
from database.supabase_client import db

class CreditsMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if not ENABLE_CREDITS:
            return await handler(event, data)

        # Only check credits for download actions
        if isinstance(event, CallbackQuery) and (
            event.data.startswith("type:") or 
            event.data.startswith("res:")
        ):
            user = data.get('db_user')
            if user:
                # Exempt Admins
                if user['id'] in ADMIN_USER_IDS:
                    return await handler(event, data)

                credits = user.get('credits', 0)
                is_premium = user.get('is_premium', False)
                
                if not is_premium and credits <= 0:
                    await event.answer("⚠️ You have 0 credits left. Wait for tomorrow or invite friends!", show_alert=True)
                    return
        
        return await handler(event, data)
