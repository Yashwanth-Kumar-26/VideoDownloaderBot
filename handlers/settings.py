from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from database.supabase_client import db

router = Router()

def get_settings_keyboard(settings: dict):
    v_qual = settings.get("video_quality", "ask")
    a_qual = settings.get("audio_quality", "ask")
    
    # Helpers for status checks
    def check(val, target):
        return "✅" if val == target else ""

    kb = [
        [
            InlineKeyboardButton(text="🎬 VIDEO QUALITY", callback_data="noop")
        ],
        [
            InlineKeyboardButton(text=f"{check(v_qual, '1080p')} 1080p", callback_data="set:v:1080p"),
            InlineKeyboardButton(text=f"{check(v_qual, '720p')} 720p", callback_data="set:v:720p"),
            InlineKeyboardButton(text=f"{check(v_qual, 'ask')} Always Ask", callback_data="set:v:ask"),
        ],
        [
            InlineKeyboardButton(text="🎧 AUDIO QUALITY", callback_data="noop")
        ],
        [
            InlineKeyboardButton(text=f"{check(a_qual, '320')} 320kbps", callback_data="set:a:320"),
            InlineKeyboardButton(text=f"{check(a_qual, '192')} 192kbps", callback_data="set:a:192"),
            InlineKeyboardButton(text=f"{check(a_qual, 'ask')} Ask", callback_data="set:a:ask"),
        ],
        [
            InlineKeyboardButton(text="🔙 Back to Menu", callback_data="menu:main")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.message(Command("settings"))
async def cmd_settings(message: Message):
    user_id = message.from_user.id
    settings = await db.get_settings(user_id)
    
    text = (
        "⚙️ **Bot Settings**\n\n"
        "Configure your default download preferences here.\n"
        "If you select a specific quality, the bot will try to download that automatically without asking."
    )
    
    await message.answer(text, reply_markup=get_settings_keyboard(settings))

@router.callback_query(lambda c: c.data == "menu:settings")
async def cb_settings(callback: CallbackQuery):
    user_id = callback.from_user.id
    settings = await db.get_settings(user_id)
    
    text = (
        "⚙️ **Bot Settings**\n\n"
        "Configure your default download preferences here."
    )
    await callback.message.edit_text(text, reply_markup=get_settings_keyboard(settings))

@router.callback_query(lambda c: c.data.startswith("set:"))
async def setting_update(callback: CallbackQuery):
    user_id = callback.from_user.id
    _, valid_type, value = callback.data.split(":")
    
    key = "video_quality" if valid_type == "v" else "audio_quality"
    
    await db.update_settings(user_id, key, value)
    
    # Refresh menu
    settings = await db.get_settings(user_id)
    from aiogram.exceptions import TelegramBadRequest
    try:
        await callback.message.edit_reply_markup(reply_markup=get_settings_keyboard(settings))
    except TelegramBadRequest:
        pass # Ignore if settings didn't visually change
    await callback.answer("Settings updated!")

@router.callback_query(lambda c: c.data == "noop")
async def noop_callback(callback: CallbackQuery):
    await callback.answer() # Just acknowledge it

