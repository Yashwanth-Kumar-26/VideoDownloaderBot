import os
import time
from aiogram import Router, types, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from utils.keyboard import get_platform_menu, get_download_type_menu, get_resolution_menu, get_main_menu, get_audio_quality_menu
from utils.keyboard import get_platform_menu, get_download_type_menu, get_resolution_menu, get_main_menu, get_audio_quality_menu
from utils.helpers import extract_platform, shortener, format_size, format_duration
from downloader import get_video_resolutions, download_video, download_audio, get_playlist_info
from database.supabase_client import db
from config import SUPPORTED_PLATFORMS, USE_LOCAL_API

from config import SUPPORTED_PLATFORMS
import logging

logger = logging.getLogger(__name__)

router = Router()

class DownloadStates(StatesGroup):
    waiting_for_url = State()

@router.callback_query(lambda c: c.data == "menu:download")
async def show_download_menu(callback: CallbackQuery):
    await callback.message.edit_text("Select a platform:", reply_markup=get_platform_menu())
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("platform:"))
async def platform_selected(callback: CallbackQuery, state: FSMContext):
    platform = callback.data.split(":")[1]
    await state.update_data(platform=platform)
    await state.set_state(DownloadStates.waiting_for_url)
    await callback.message.edit_text(
        f"Selected {platform.capitalize()}.\nNow send me the link:",
        reply_markup=None
    )
    await callback.answer()

# Fallback for direct URL messages (if not in state)
import re
@router.message(F.text.regexp(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+') | F.caption.regexp(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'))
async def handle_direct_url(message: Message, state: FSMContext):
    # Extract the first URL found in the text or caption
    content = message.text or message.caption or ""
    url_match = re.search(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content)
    if not url_match:
        return # Should not happen due to filter
    
    url = url_match.group(0)
    
    # Clear any existing state if a direct URL is sent
    await state.clear()

    platform = extract_platform(url)
    if not platform:
        await message.reply("Could not detect platform from the provided URL. Please try again or use the menu.")
        return

    # Check for playlist first
    playlist_info = await get_playlist_info(url)
    if playlist_info and playlist_info['count'] > 1:
        # It's a playlist!
        await message.reply(
            f"📑 **Playlist Detected:** {playlist_info['title']}\n"
            f"🔢 **Count:** {playlist_info['count']} items\n\n"
            "How do you want to proceed?",
            reply_markup=get_playlist_menu(url, playlist_info['count'])
        )
        return

    await message.reply("How do you want to download?", reply_markup=get_download_type_menu(url))


@router.message(DownloadStates.waiting_for_url)
async def process_url(message: Message, state: FSMContext):
    url = message.text.strip()
    
    # Basic validation
    # If explicit platform selected, verify it matches
    data = await state.get_data()
    selected_platform = data.get('platform')
    
    detected_platform = extract_platform(url)
    if selected_platform and detected_platform and detected_platform != selected_platform:
        # We can either warn or just switch payload. Let's auto-switch but warn.
        pass # Allow user logic
        
    if not detected_platform and not selected_platform:
         await message.reply("Could not detect platform. Please try again or use the menu.")
         return

    await state.clear() # Clear state as we have the URL
    await message.reply("How do you want to download?", reply_markup=get_download_type_menu(url))

    platform = extract_platform(url)
    if platform:
         # Check for playlist first
         playlist_info = await get_playlist_info(url)
         if playlist_info and playlist_info['count'] > 1:
             # It's a playlist!
             await message.reply(
                 f"📑 **Playlist Detected:** {playlist_info['title']}\n"
                 f"🔢 **Count:** {playlist_info['count']} items\n\n"
                 "How do you want to proceed?",
                 reply_markup=get_playlist_menu(url, playlist_info['count'])
             )
             return

         await message.reply("How do you want to download?", reply_markup=get_download_type_menu(url))

# Add get_playlist_menu to imports or define here (preferred in utils/keyboard.py but can be inline for now)
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
def get_playlist_menu(url: str, count: int):
    # Truncate URL if too long for callback data (Telegram limit 64 bytes)
    # We might need to store URL in state or db if it's long. 
    # For now, let's assume we use the shortener or if it's too long, we might fail.
    # Actually, let's use the shortener for the playlist URL too.
    sid = shortener.shorten(url)
    
    kb = [
        [
            InlineKeyboardButton(text=f"🎵 Audio (Top 10)", callback_data=f"pl:audio:10:{sid}"),
            InlineKeyboardButton(text=f"🎵 Audio (All)", callback_data=f"pl:audio:all:{sid}")
        ],
        [
            InlineKeyboardButton(text=f"🎬 Video (Top 10)", callback_data=f"pl:video:10:{sid}"),
            InlineKeyboardButton(text=f"🎬 Video (All)", callback_data=f"pl:video:all:{sid}")
        ],
        [
             InlineKeyboardButton(text="❌ Cancel", callback_data="delete")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def generate_progress_bar(percent, length=20):
    try:
        if isinstance(percent, str):
            percent = float(percent)
        filled_length = int(length * percent // 100)
        bar = '█' * filled_length + '░' * (length - filled_length)
        return bar
    except:
        return '░' * length

@router.callback_query(lambda c: c.data.startswith("pl:"))
async def playlist_selected(callback: CallbackQuery, db_user: dict):
    await callback.answer()
    parts = callback.data.split(":")
    dtype = parts[1] # audio/video
    scope = parts[2] # 10/all
    sid = parts[3]
    url = shortener.get_url(sid)
    
    if not url:
        await callback.message.edit_text("❌ Session expired.")
        return

    # Check settings for quality preference (reuse logic?)
    # For now, default to best/standard for playlist to avoid menu spam.
    # Audio: 192 (or 320 if user set 320), Video: 720p (default)
    
    settings = await db.get_settings(db_user['id'])
    v_qual = settings.get("video_quality", "720p") # Default 720p if ask
    if v_qual == "ask": v_qual = "720p" # Fallback for list
    
    a_qual = settings.get("audio_quality", "192") # Default 192
    if a_qual == "ask": a_qual = "192"

    await callback.message.edit_text("⏳ Fetching playlist details...")
    
    info = await get_playlist_info(url)
    if not info or not info['entries']:
        await callback.message.edit_text("❌ Failed to load playlist.")
        return

    entries = info['entries']
    if scope == "10":
        entries = entries[:10]
    
    total = len(entries)
    status_msg = callback.message # We will reuse this for progress
    
    await status_msg.edit_text(f"🚀 **Starting Playlist Download**\nFailed items will be skipped.\n\nType: {dtype.capitalize()}\nTotal: {total}")
    
    for i, entry in enumerate(entries):
        idx = i + 1
        video_url = entry['url']
        title = entry.get('title', f'Item {idx}')
        
        try:
             # Update status
             await status_msg.edit_text(
                 f"📑 **Playlist Progress: {idx}/{total}**\n"
                 f"Current: {title}\n"
                 f"⏬ Downloading..."
             )
             
             if dtype == "audio":
                 # We need to modify execute function to ACCEPT a message instead of callback.message
                 # Actually, we can pass status_msg, BUT execute functions might delete it or reply to it.
                 # Let's pass the ORIGINAL message (callback.message.reply_to_message) if possible, 
                 # OR better: Send a NEW message for each status? No, too much spam.
                 # Best: Send the file using `reply_audio` to the chat ID.
                 # We need to call the download logic directly.
                 
                 # To reuse code, we can call execute_audio_download but it expects a Message object to edit.
                 # If we pass status_msg, it will edit our progress message to "Downloading...", then "Sending...", then DELETE it.
                 # If it deletes it, we lose our progress message for the NEXT item.
                 
                 # Solution: Create a temporary message for each item? 
                 # "Downloading Item 1..." -> Done -> Delete.
                 # "Downloading Item 2..." -> ...
                 
                 # Let's send a TEMP message for the item.
                 temp_msg = await callback.message.answer(f"⏳ Processing: {title}...")
                 
                 if dtype == "audio":
                     await execute_audio_download(temp_msg, video_url, a_qual, db_user)
                 else:
                     await execute_video_download(temp_msg, video_url, v_qual, db_user)
                     
                 # execute_ functions delete the message on success. 
                 # If they fail, they edit it to Error. We should clean it up if it persists?
                 # ideally execute_* should return status.
                 
        except Exception as e:
            logger.error(f"Failed item {idx}: {e}")
            await callback.message.answer(f"❌ Failed: {title}")
            continue
            
    await callback.message.answer("✅ **Playlist Download Complete!**")
    await status_msg.delete() # Remove the main progress header handles



@router.callback_query(lambda c: c.data.startswith("type:"))
async def type_selected(callback: CallbackQuery, db_user: dict):
    await callback.answer()
    parts = callback.data.split(":", 2)
    dtype = parts[1]
    sid = parts[2]
    url = shortener.get_url(sid)
    
    if not url:
        await callback.message.edit_text("❌ Session expired. Please send the link again.")
        return
    
    if dtype == "video":
        settings = await db.get_settings(db_user['id'])
        pref_res = settings.get("video_quality", "ask")
        
        # If user has a preference and it's not "ask", try to auto-select
        if pref_res != "ask":
             # We need to verify if this resolution exists for this video? 
             # Or just try it? If we try and fail, we should fallback.
             # For now, let's just default to showing menu if "ask".
             # Actually, checking availability is slow. Let's just pass preference to execution.
             # But execution logic assumes resolution is valid.
             # Let's stick to "ask" behavior for now OR:
             pass 

        resolutions = await get_video_resolutions(url)
        
        if pref_res != "ask" and pref_res in resolutions:
             await callback.message.edit_text(f"🚀 Auto-selecting **{pref_res}** (Settings)...")
             await execute_video_download(callback.message, url, pref_res, db_user)
             return

        if not resolutions:
            await callback.message.edit_text("⚠️ Video streams unavailable.\n\n🔄 Switching to **Audio Mode**...", parse_mode="Markdown")
            await asyncio.sleep(1.5)
            # Check audio preference too?
            await callback.message.edit_text("Select audio quality:", reply_markup=get_audio_quality_menu(url))
            return
        await callback.message.edit_text("Select resolution:", reply_markup=get_resolution_menu(resolutions, url))
    elif dtype == "audio":
        settings = await db.get_settings(db_user['id'])
        pref_qual = settings.get("audio_quality", "ask")
        
        if pref_qual != "ask":
             await callback.message.edit_text(f"🚀 Auto-selecting **{pref_qual}kbps** (Settings)...")
             await execute_audio_download(callback.message, url, pref_qual, db_user)
             return

        # Show quality menu instead of instant download
        await callback.message.edit_text("Select audio quality:", reply_markup=get_audio_quality_menu(url))

@router.callback_query(lambda c: c.data.startswith("aqual:"))
async def audio_quality_selected(callback: CallbackQuery, db_user: dict):
    await callback.answer()
    parts = callback.data.split(":", 2)
    quality = parts[1]
    sid = parts[2]
    url = shortener.get_url(sid)
    
    if not url:
        await callback.message.edit_text("❌ Session expired. Please send the link again.")
        return
    
    await execute_audio_download(callback.message, url, quality, db_user)

async def execute_audio_download(message: Message, url: str, quality: str, db_user: dict):
    variant = f"audio:mp3-{quality}"
    
    # Check Cache
    cached_id = await db.get_cached_file(url, variant)
    if cached_id:
        await message.edit_text(f"🚀 Found in Server! Sending audio...")
        try:
             await message.reply_audio(cached_id)
             # Log credit deduction (still valid even if cached)
             await db.log_download(db_user['id'], url, "server", "audio", f"mp3-{quality}", 0)
             await db.update_credits(db_user['id'], -1)
             await message.delete()
             return
        except Exception as e:
             # Cache might be invalid (file id revoked), proceed to redownload
             pass

    await message.edit_text(f"⏳ Downloading audio ({quality}kbps)... please wait.")
    
    last_update_time = 0

    async def progress_handler(data):
        nonlocal last_update_time
        current_time = time.time()
        
        # Update only if 2 seconds passed or finished
        if current_time - last_update_time < 2 and data['percent'] != '100':
            return
            
        last_update_time = current_time
        bar = generate_progress_bar(data['percent'])
        text = (
            f"⏬ **Downloading...**\n"
            f"`[{bar}]` **{data['percent']}%**\n\n"
            f"🚀 **Speed:** {data['speed']}\n"
            f"📦 **Size:** {data['current']} / {data['total']}\n"
            f"⏳ **ETA:** {data['eta']}"
        )
        try:
            logger.info(f"DEBUG: Progress update: {data['percent']}%")
            await message.edit_text(text, parse_mode="Markdown")
        except Exception as e:
             # logger.error(f"DEBUG: Progress update failed: {e}")
             pass

    try:
        # returns dict now
        result = await download_audio(url, quality=quality, progress_callback=progress_handler)
    except Exception as e:
        await message.edit_text(f"❌ Error: {str(e)}")
        return
    
    if result and os.path.exists(result['path']):
        # Determine limit based on API mode
        limit_mb = 1950 if USE_LOCAL_API else 49
        limit_bytes = limit_mb * 1024 * 1024
        
        if result['size'] > limit_bytes:
            limit_msg = "2GB" if USE_LOCAL_API else "50MB"
            await message.edit_text(
                f"⚠️ **File too large!**\n\n"
                f"The file is **{format_size(result['size'])}**, but the limit is **{limit_msg}**.\n"
                f"Please try a lower quality."
            )
            # Cleanup
            if os.path.exists(result['path']):
                os.remove(result['path'])
            if result.get('thumb') and os.path.exists(result.get('thumb')):
                os.remove(result['thumb'])
            return

        file_path = result['path']
        thumb_path = result.get('thumb')
        try:
            logger.info("DEBUG: Attempting to upload audio to Telegram...")
            
            thumb = FSInputFile(thumb_path) if thumb_path and os.path.exists(thumb_path) else None
            audio_file = FSInputFile(file_path)
            
            caption = (
                f"🎧 <b>{result.get('title', 'Audio')}</b>\n"
                f"⏱ {format_duration(result.get('duration', 0))} | 💾 {format_size(result.get('size', 0))}"
            )

            # Increased timeout to 5 minutes (300s)
            msg = await message.reply_audio(
                audio_file, 
                thumbnail=thumb,
                title=result.get('title', 'Audio'),
                performer=shortener.get_url(shortener.shorten(url)), # Re-shorten for display logic? Or pass sid? 
                duration=result.get('duration', 0),
                caption=caption,
                parse_mode="HTML",
                request_timeout=300
            )
            
            # Save to Cache
            if msg.document:
                await db.save_cached_file(url, variant, msg.document.file_id)
            elif msg.audio:
                await db.save_cached_file(url, variant, msg.audio.file_id)

            # Log and deduct
            await db.log_download(db_user['id'], url, "unknown", "audio", f"mp3-{quality}", result['size'])
            await db.update_credits(db_user['id'], -1)
            await message.delete()
        except Exception as e:
             await message.edit_text(f"❌ Failed to send file. It might be too large.\nError: {e}")
        finally:
             if os.path.exists(file_path):
                 os.remove(file_path)
             if thumb_path and os.path.exists(thumb_path):
                 os.remove(thumb_path)
    else:
        await message.edit_text("❌ Failed to download audio.")
            

@router.callback_query(lambda c: c.data.startswith("res:"))
async def resolution_selected(callback: CallbackQuery, db_user: dict):
    await callback.answer()
    parts = callback.data.split(":", 2)
    res = parts[1]
    sid = parts[2]
    url = shortener.get_url(sid)

    if not url:
         await callback.message.edit_text("❌ Session expired. Please send the link again.")
         return
    
    await execute_video_download(callback.message, url, res, db_user)

async def execute_video_download(message: Message, url: str, res: str, db_user: dict):
    variant = f"video:{res}"
    
    # Check Cache
    cached_id = await db.get_cached_file(url, variant)
    if cached_id:
        await message.edit_text(f"🚀 Found in cache! Sending video...")
        try:
             await message.reply_video(cached_id)
             await db.log_download(db_user['id'], url, "cache", "video", res, 0)
             await db.update_credits(db_user['id'], -1)
             await message.delete()
             return
        except Exception:
             pass

    await message.edit_text(f"⏳ Downloading video ({res})... please wait.")
    
    await message.edit_text(f"⏳ Downloading video ({res})... please wait.")
    
    last_update_time = 0
    last_action_time = 0

    async def progress_handler(data):
        nonlocal last_update_time
        current_time = time.time()
        
        # Update only if 2 seconds passed
        if current_time - last_update_time < 2 and data['percent'] != '100':
            return
            
        # Send chat action (uploading video) every 4 seconds to keep it active
        if current_time - last_action_time > 4:
            last_action_time = current_time
            await message.bot.send_chat_action(message.chat.id, "upload_video")

        last_update_time = current_time
        bar = generate_progress_bar(data['percent'])
        
        # Simple spinner
        frames = ["🌑", "Dl", "🌓", "Dl", "🌔", "Dl", "🌕", "Dl"]
        frame = frames[int(current_time * 2) % len(frames)]
        if frame == "Dl": frame = "⏬" # simple hack

        text = (
            f"{frame} **Downloading...**\n"
            f"`[{bar}]` **{data['percent']}%**\n\n"
            f"🚀 **Speed:** {data['speed']}\n"
            f"📦 **Size:** {data['current']} / {data['total']}\n"
            f"⏳ **ETA:** {data['eta']}"
        )
        try:
            # logger.info(f"DEBUG: Progress update (Video): {data['percent']}%")
            await message.edit_text(text, parse_mode="Markdown")
        except:
             pass

    try:
        logger.info(f"DEBUG: Starting download for URL: {url} Res: {res}")
        # returns dict now
        result = await download_video(url, res, progress_callback=progress_handler)
        logger.info(f"DEBUG: Download finished. Path: {result.get('path')}")
    except Exception as e:
        logger.error(f"DEBUG: Download failed: {e}")
        await message.edit_text(f"❌ Error: {str(e)}")
        return
    
    if result and os.path.exists(result['path']):
        # Determine limit based on API mode
        limit_mb = 1950 if USE_LOCAL_API else 49
        limit_bytes = limit_mb * 1024 * 1024

        if result['size'] > limit_bytes:
            limit_msg = "2GB" if USE_LOCAL_API else "50MB"
            await message.edit_text(
                f"⚠️ **File too large!**\n\n"
                f"The video is **{format_size(result['size'])}**, but the limit is **{limit_msg}**.\n"
                f"Please try a lower resolution (e.g., 720p or 480p)."
            )
            # Cleanup
            if os.path.exists(result['path']):
                os.remove(result['path'])
            if result.get('thumb') and os.path.exists(result.get('thumb')):
                os.remove(result['thumb'])
            return

        file_path = result['path']
        thumb_path = result.get('thumb')
        try:
            logger.info("DEBUG: Attempting to upload to Telegram...")
            
            thumb = FSInputFile(thumb_path) if thumb_path and os.path.exists(thumb_path) else None
            video_file = FSInputFile(file_path)
            
            caption = (
                f"🎬 <b>{result.get('title', 'Video')}</b>\n"
                f"⏱ {format_duration(result.get('duration', 0))} | 💿 {result.get('width', 0)}x{result.get('height', 0)} | 📦 {format_size(result.get('size', 0))}"
            )

            # Increased timeout to 5 minutes (300s) for large uploads
            # Try sending as video first for streaming support
            msg = await message.reply_video(
                video_file,
                thumbnail=thumb,
                duration=result.get('duration', 0),
                width=result.get('width', 0),
                height=result.get('height', 0),
                caption=caption,
                parse_mode="HTML",
                supports_streaming=True,
                request_timeout=300
            )

            logger.info("DEBUG: Upload successful.")
            
            # Save Cache
            if msg.document:
                await db.save_cached_file(url, variant, msg.document.file_id)
            elif msg.video:
                await db.save_cached_file(url, variant, msg.video.file_id)

            # Log and deduct
            await db.log_download(db_user['id'], url, "unknown", "video", res, result['size'])
            await db.update_credits(db_user['id'], -1)
            await message.delete()
        except Exception as e:
             await message.edit_text(f"❌ Failed to send file. It might be too large.\nError: {e}")
        finally:
             if os.path.exists(file_path):
                 os.remove(file_path)
             if thumb_path and os.path.exists(thumb_path):
                 os.remove(thumb_path)
    else:
        await message.edit_text("❌ Failed to download video.")
