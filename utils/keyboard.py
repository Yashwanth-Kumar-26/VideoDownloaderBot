from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import SUPPORTED_PLATFORMS
from utils.helpers import shortener

PLATFORM_EMOJIS = {
    "youtube": "🟥",
    "instagram": "📸",
    "twitter": "X",
    "tiktok": "🎵",
    "reddit": "🤖",
    "facebook": "📘"
}

def get_main_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📥 Download", callback_data="menu:download"),
            InlineKeyboardButton(text="👤 Profile", callback_data="menu:profile")
        ],
        [
            InlineKeyboardButton(text="👫 Invite Friend", callback_data="menu:profile"),
            InlineKeyboardButton(text="⚙️ Settings", callback_data="menu:settings")
        ]
    ])
    return keyboard

def get_platform_menu():
    buttons = []
    row = []
    for platform in SUPPORTED_PLATFORMS:
        emoji = PLATFORM_EMOJIS.get(platform, "🔗")
        row.append(InlineKeyboardButton(text=f"{emoji} {platform.capitalize()}", callback_data=f"platform:{platform}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_download_type_menu(url):
    sid = shortener.shorten(url)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎬 Video", callback_data=f"type:video:{sid}"),
            InlineKeyboardButton(text="🎵 Audio (MP3)", callback_data=f"type:audio:{sid}")
        ],
        [InlineKeyboardButton(text="🔙 Back", callback_data="menu:download")]
    ])
    return keyboard

def get_audio_quality_menu(url):
    sid = shortener.shorten(url)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💎 High (320kbps)", callback_data=f"aqual:320:{sid}"),
            InlineKeyboardButton(text="🎧 Medium (192kbps)", callback_data=f"aqual:192:{sid}")
        ],
        [
            InlineKeyboardButton(text="💾 Low (128kbps)", callback_data=f"aqual:128:{sid}")
        ],
        [InlineKeyboardButton(text="🔙 Back", callback_data=f"type:audio:{sid}")]
    ])
    return keyboard

def get_resolution_menu(resolutions, url):
    sid = shortener.shorten(url)
    buttons = []
    row = []
    for res in resolutions:
        row.append(InlineKeyboardButton(text=f"🎥 {res}", callback_data=f"res:{res}:{sid}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data=f"type:video:{sid}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_back_button(callback_data="menu:main"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data=callback_data)]
    ])
