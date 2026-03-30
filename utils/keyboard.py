from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import SUPPORTED_PLATFORMS
from utils.helpers import shortener

PLATFORM_EMOJIS = {
    "youtube": "🟥",
    "instagram": "📸",
    "twitter": "X",
    "spotify": "🎧",
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
            InlineKeyboardButton(text="🖼 Image", callback_data=f"type:image:{sid}"),
            InlineKeyboardButton(text="🎬 Video", callback_data=f"type:video:{sid}"),
            InlineKeyboardButton(text="🎵 Audio", callback_data=f"type:audio:{sid}")
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

def get_playlist_audio_quality_menu(url, scope):
    sid = shortener.shorten(url)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💎 High (320kbps)", callback_data=f"pl_aqual:320:{scope}:{sid}"),
            InlineKeyboardButton(text="🎧 Medium (192kbps)", callback_data=f"pl_aqual:192:{scope}:{sid}")
        ],
        [
            InlineKeyboardButton(text="💾 Low (128kbps)", callback_data=f"pl_aqual:128:{scope}:{sid}")
        ],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="delete")]
    ])
    return keyboard

def get_playlist_video_quality_menu(url, scope):
    sid = shortener.shorten(url)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎥 1080p", callback_data=f"pl_vqual:1080p:{scope}:{sid}"),
            InlineKeyboardButton(text="🎥 720p", callback_data=f"pl_vqual:720p:{scope}:{sid}")
        ],
        [
            InlineKeyboardButton(text="🎥 480p", callback_data=f"pl_vqual:480p:{scope}:{sid}"),
            InlineKeyboardButton(text="🎥 360p", callback_data=f"pl_vqual:360p:{scope}:{sid}")
        ],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="delete")]
    ])
    return keyboard

def get_back_button(callback_data="menu:main"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data=callback_data)]
    ])
