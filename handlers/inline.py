from aiogram import Router, F
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from database import db
import uuid
from urllib.parse import quote

router = Router()

@router.inline_query(F.query == "share")
async def inline_share_handler(inline_query: InlineQuery):
    user_id = inline_query.from_user.id
    
    # Get referral code (might need to fetch from DB if not adaptable)
    # Since InlineQuery doesn't go through AuthMiddleware (usually), we might need to fetch directly.
    # But usually it's fast enough.
    
    # We can try to get from db helper
    referral_code = await db.ensure_referral_code(user_id)
    
    bot_username = (await inline_query.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={referral_code}"
    
    title = "Share Bot"
    description = "Send your referral link to friends!"
    message_text = f"Check out this awesome downloader bot! 👇\n{ref_link}"
    
    results = [
        InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title="🚀 Share Downloader Bot",
            description="Click to send your referral link",
            input_message_content=InputTextMessageContent(
                message_text=message_text,
                parse_mode="HTML" # or None, URL preview should work
            ),
            thumbnail_url="https://cdn-icons-png.flaticon.com/512/2111/2111646.png" # Optional generic icon
        )
    ]
    
    await inline_query.answer(results, cache_time=1, is_personal=True)
