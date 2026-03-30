from aiogram import Router, types
from aiogram.types import CallbackQuery
from utils.keyboard import get_back_button
from database import db

router = Router()

@router.callback_query(lambda c: c.data == "menu:profile")
async def show_profile(callback: CallbackQuery, db_user: dict):
    user_id = callback.from_user.id
    stats = await db.get_user_stats(user_id)
    
    credits = db_user.get('credits', 0)
    referral_code = await db.ensure_referral_code(user_id)
    
    text = (
        f"👤 **Your Profile**\n\n"
        f"🆔 ID: `{user_id}`\n"
        f"💰 Credits: **{credits}**\n"
        f"📥 Total Downloads: **{stats.get('total_downloads', 0)}**\n\n"
        f"🔗 **Referral System**\n"
        f"Invite friends and earn credits!\n"
        f"Your code: `{referral_code}`\n"
        f"👥 Referrals: **{stats.get('total_referrals', 0)}**\n"
        f"💵 Earned from Refs: **{stats.get('total_ref_credits', 0)}**\n\n"
        f"Bot Link: https://t.me/{(await callback.bot.get_me()).username}?start={referral_code}"
    )
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from urllib.parse import quote

    import logging
    logger = logging.getLogger(__name__)

    bot_username = (await callback.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={referral_code}"
    
    # Put the link IN THE TEXT so it's 100% visible to the user
    share_text = f"Check out this awesome downloader bot! 👇\n{ref_link}"
    
    # We pass URL for preview, and Text (with link) for the message body
    share_url =  f"https://t.me/share/url?url={quote(ref_link)}&text={quote(share_text)}"
    
    logger.info(f"Generated Share URL for {user_id}: {share_url}")
    
    # We can just use the url directly for the button
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↗️ Share with Friends", url=share_url)],
        [InlineKeyboardButton(text="🔙 Back", callback_data="menu:main")]
    ])

    await callback.message.edit_text(
        text,
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()
