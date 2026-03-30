import os
import time
from aiogram import Router, types, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from utils.keyboard import get_platform_menu, get_download_type_menu, get_resolution_menu, get_main_menu, get_audio_quality_menu
from utils.keyboard import get_playlist_audio_quality_menu, get_playlist_video_quality_menu
from utils.helpers import extract_platform, shortener, format_size, format_duration
from downloader import get_playlist_info, download_video, download_audio, download_image
from database import db
from config import SUPPORTED_PLATFORMS, USE_LOCAL_API, LOG_CHANNEL_ID

import logging
import asyncio
from aiogram.exceptions import TelegramBadRequest

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
            InlineKeyboardButton(text=f"🖼 Image (Top 10)", callback_data=f"pl:image:10:{sid}"),
            InlineKeyboardButton(text=f"🖼 Image (All)", callback_data=f"pl:image:all:{sid}")
        ],
        [
            InlineKeyboardButton(text=f"🎬 Video (Top 10)", callback_data=f"pl:video:10:{sid}"),
            InlineKeyboardButton(text=f"🎬 Video (All)", callback_data=f"pl:video:all:{sid}")
        ],
        [
            InlineKeyboardButton(text=f"🎵 Audio (Top 10)", callback_data=f"pl:audio:10:{sid}"),
            InlineKeyboardButton(text=f"🎵 Audio (All)", callback_data=f"pl:audio:all:{sid}")
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

import tempfile
import shutil

TEMP_ROOT = os.path.join(os.getcwd(), 'temp_data')
os.makedirs(TEMP_ROOT, exist_ok=True)

@router.callback_query(lambda c: c.data.startswith("pl:"))
async def playlist_type_selected(callback: CallbackQuery, db_user: dict):
    await callback.answer()
    parts = callback.data.split(":")
    dtype = parts[1] # audio/video
    scope = parts[2] # 10/all
    sid = parts[3]
    url = shortener.get_url(sid)
    
    if not url:
        await callback.message.edit_text("❌ Session expired.")
        return

    settings = await db.get_settings(db_user['id'])
    
    if dtype == "audio":
        pref_qual = settings.get("audio_quality", "ask")
        if pref_qual != "ask":
            await execute_playlist_download(callback, url, "audio", pref_qual, scope, db_user)
            return
        await callback.message.edit_text("Select audio quality for playlist:", reply_markup=get_playlist_audio_quality_menu(url, scope))
    elif dtype == "video":
        pref_res = settings.get("video_quality", "ask")
        if pref_res != "ask":
            await execute_playlist_download(callback, url, "video", pref_res, scope, db_user)
            return
        await callback.message.edit_text("Select video resolution for playlist:", reply_markup=get_playlist_video_quality_menu(url, scope))
    elif dtype == "image":
        await execute_playlist_download(callback, url, "image", "best", scope, db_user)

@router.callback_query(lambda c: c.data.startswith("pl_aqual:"))
async def playlist_audio_quality_selected(callback: CallbackQuery, db_user: dict):
    await callback.answer()
    parts = callback.data.split(":")
    quality = parts[1]
    scope = parts[2]
    sid = parts[3]
    url = shortener.get_url(sid)
    if not url:
         await callback.message.edit_text("❌ Session expired.")
         return
    await execute_playlist_download(callback, url, "audio", quality, scope, db_user)

@router.callback_query(lambda c: c.data.startswith("pl_vqual:"))
async def playlist_video_quality_selected(callback: CallbackQuery, db_user: dict):
    await callback.answer()
    parts = callback.data.split(":")
    res = parts[1]
    scope = parts[2]
    sid = parts[3]
    url = shortener.get_url(sid)
    if not url:
         await callback.message.edit_text("❌ Session expired.")
         return
    await execute_playlist_download(callback, url, "video", res, scope, db_user)

async def execute_playlist_download(callback: CallbackQuery, url: str, dtype: str, quality: str, scope: str, db_user: dict):
    await callback.message.edit_text("⏳ Fetching playlist details...")
    
    info = await get_playlist_info(url)
    if not info or not info['entries']:
        await callback.message.edit_text("❌ Failed to load playlist.")
        return

    entries = info['entries']
    if scope == "10":
        entries = entries[:10]
    
    total = len(entries)
    status_msg = callback.message 
    
    await status_msg.edit_text(f"🚀 **Starting Playlist Download (ZIP)**\nType: {dtype.capitalize()}\nTotal: {total} items\n\n⏳ Please wait, this may take a while...")

    # Create temp directory for this playlist
    temp_dir = tempfile.mkdtemp(dir=TEMP_ROOT)
    
    success_count = 0
    fail_count = 0
    
    try:
        for i, entry in enumerate(entries):
            idx = i + 1
            video_url = entry['url']
            title = entry.get('title', f'Item {idx}')
            
            # Simple progress update (every item)
            await status_msg.edit_text(
                 f"📥 **Downloading Item {idx}/{total}**\n"
                 f"Current: {title}\n"
                 f"✅ Success: {success_count} | ❌ Failed: {fail_count}"
            )
            
            try:
                res = None
                if dtype == "audio":
                    res = await download_audio(video_url, quality=quality, output_dir=temp_dir)
                elif dtype == "video":
                    res = await download_video(video_url, resolution=quality, output_dir=temp_dir)
                elif dtype == "image":
                    # Assuming download_image function exists and returns a similar dict with 'path'
                    res = await download_image(video_url, output_dir=temp_dir)
                
                if res and os.path.exists(res['path']):
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                logger.error(f"Failed item {idx}: {e}")
                fail_count += 1
                continue
        
        if success_count == 0:
             await status_msg.edit_text("❌ All items failed to download.")
             return

        await status_msg.edit_text(f"📦 **Zipping {success_count} items...**")
        
        # Create ZIP
        zip_base = os.path.join(TEMP_ROOT, f"Playlist_{shortener.shorten(url)}")
        zip_path = shutil.make_archive(zip_base, 'zip', temp_dir)
        
        zip_size = os.path.getsize(zip_path)
        
        # Check limits
        limit_mb = 1950 if USE_LOCAL_API else 49
        limit_bytes = limit_mb * 1024 * 1024
        
        if zip_size > limit_bytes:
             await status_msg.edit_text(
                 f"⚠️ **ZIP too large!**\n\n"
                 f"Size: {format_size(zip_size)}\n"
                 f"Limit: {limit_mb}MB\n\n"
                 f"Sending unable to upload."
             )
             if os.path.exists(zip_path): os.remove(zip_path)
             return

        await status_msg.edit_text(f"⬆️ **Uploading ZIP ({format_size(zip_size)}) to Log Channel...**")
        
        # Upload
        zip_file = FSInputFile(zip_path)
        caption = (
            f"🎁 **Playlist: {info.get('title', 'Unknown')}**\n"
            f"📊 Items: {success_count} | 💾 Size: {format_size(zip_size)}"
        )
        
        # 1. Upload to Log Channel
        log_msg = await callback.message.bot.send_document(
            chat_id=LOG_CHANNEL_ID,
            document=zip_file,
            caption=caption,
            request_timeout=600
        )
        
        file_id = log_msg.document.file_id
        
        # 2. Serve to User
        await callback.message.reply_document(
            document=file_id,
            caption=caption
        )
        
        # Deduct credits (1 credit per playlist? or per item? User just said 'zip it', let's charge 1 for simplified bulk or maybe 2)
        # For fairness, let's charge 1 credit for the convenience.
        await db.update_credits(db_user['id'], -1)
        await status_msg.delete()
        
    except Exception as e:
        logger.error(f"Playlist error: {e}")
        await status_msg.edit_text(f"❌ Error processing playlist: {e}")
    finally:
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        if 'zip_path' in locals() and os.path.exists(zip_path):
            os.remove(zip_path)



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
            try:
                await callback.message.edit_text("⚠️ Video streams unavailable.\n\n🔄 Switching to **Audio Mode**...", parse_mode="Markdown")
            except TelegramBadRequest:
                pass
            await asyncio.sleep(1.5)
            # Check audio preference too?
            try:
                await callback.message.edit_text("Select audio quality:", reply_markup=get_audio_quality_menu(url))
            except TelegramBadRequest:
                pass
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
        
    elif dtype == "image":
        await execute_image_download(callback.message, url, db_user)

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
    
    if result and isinstance(result, list) and len(result) > 0:
        await message.edit_text(f"📦 Zipping {len(result)} tracks from Playlist...")
        zip_base = os.path.join(TEMP_ROOT, f"Spotify_{shortener.shorten(url)}")
        spotdl_output_dir = os.path.dirname(result[0]['path'])
        zip_path = shutil.make_archive(zip_base, 'zip', spotdl_output_dir)
        zip_size = os.path.getsize(zip_path)
        limit_mb = 1950 if USE_LOCAL_API else 49
        limit_bytes = limit_mb * 1024 * 1024
        
        if zip_size > limit_bytes:
            await message.edit_text(f"⚠️ **ZIP too large!**\nSize: {format_size(zip_size)}\nLimit: {limit_mb}MB")
            if os.path.exists(zip_path): os.remove(zip_path)
            return
            
        await message.edit_text(f"⬆️ **Uploading Spotify Playlist ZIP ({format_size(zip_size)})...**")
        try:
            zip_file = FSInputFile(zip_path)
            caption = f"🎁 **Spotify Playlist**\n📊 Items: {len(result)} | 💾 Size: {format_size(zip_size)}"
            log_msg = await message.bot.send_document(
                chat_id=LOG_CHANNEL_ID,
                document=zip_file,
                caption=caption,
                request_timeout=600
            )
            await message.reply_document(
                document=log_msg.document.file_id,
                caption=caption
            )
            await db.update_credits(db_user['id'], -1)
        except Exception as e:
            logger.error(f"ZIP Upload failed: {e}")
            await message.edit_text("❌ Failed to upload Spotify ZIP.")
        finally:
            if os.path.exists(zip_path): os.remove(zip_path)
        return

    if result and not isinstance(result, list) and os.path.exists(result['path']):
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
            logger.info("DEBUG: Attempting to upload audio to Log Channel...")
            
            thumb = FSInputFile(thumb_path) if thumb_path and os.path.exists(thumb_path) else None
            audio_file = FSInputFile(file_path)
            
            caption = (
                f"🎧 <b>{result.get('title', 'Audio')}</b>\n"
                f"⏱ {format_duration(result.get('duration', 0))} | 💾 {format_size(result.get('size', 0))}"
            )
            
            # 1. Upload to Log Channel
            log_msg = await message.bot.send_audio(
                chat_id=LOG_CHANNEL_ID,
                audio=audio_file,
                thumbnail=thumb,
                title=result.get('title', 'Audio'),
                performer=shortener.get_url(shortener.shorten(url)),
                duration=int(result.get('duration', 0)),
                caption=caption,
                parse_mode="HTML",
                request_timeout=300
            )
            
            file_id = log_msg.audio.file_id
            
            # 2. Save Cache (Using file_id from Log Channel)
            await db.save_cached_file(url, variant, file_id)
            
            # 3. Send to User using File ID (Zero Bandwidth)
            await message.reply_audio(
                audio=file_id, 
                caption=caption,
                parse_mode="HTML"
            )

            # Log and deduct
            await db.log_download(db_user['id'], url, "new", "audio", f"mp3-{quality}", result['size'])
            await db.update_credits(db_user['id'], -1)
            await message.delete()
        except Exception as e:
             await message.edit_text(f"❌ Failed to process file.\nError: {e}")
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
            logger.info("DEBUG: Attempting to upload to Log Channel...")
            
            thumb = FSInputFile(thumb_path) if thumb_path and os.path.exists(thumb_path) else None
            video_file = FSInputFile(file_path)
            
            caption = (
                f"🎬 <b>{result.get('title', 'Video')}</b>\n"
                f"⏱ {format_duration(result.get('duration', 0))} | 💿 {result.get('width', 0)}x{result.get('height', 0)} | 📦 {format_size(result.get('size', 0))}"
            )

            # 1. Upload to Log Channel
            log_msg = await message.bot.send_video(
                chat_id=LOG_CHANNEL_ID,
                video=video_file,
                thumbnail=thumb,
                duration=int(result.get('duration', 0)),
                width=int(result.get('width', 0)),
                height=int(result.get('height', 0)),
                caption=caption,
                parse_mode="HTML",
                supports_streaming=True,
                request_timeout=300
            )

            logger.info("DEBUG: Upload to Log Channel successful.")
            
            file_id = log_msg.video.file_id if log_msg.video else log_msg.document.file_id
            
            # 2. Save Cache
            await db.save_cached_file(url, variant, file_id)
            
            # 3. Send to User using File ID
            await message.reply_video(
                video=file_id,
                caption=caption,
                parse_mode="HTML",
                supports_streaming=True
            )

            # Log and deduct
            await db.log_download(db_user['id'], url, "new", "video", res, result['size'])
            await db.update_credits(db_user['id'], -1)
            await message.delete()
        except Exception as e:
             await message.edit_text(f"❌ Failed to process file.\nError: {e}")
        finally:
             if os.path.exists(file_path):
                 os.remove(file_path)
             if thumb_path and os.path.exists(thumb_path):
                 os.remove(thumb_path)
    else:
        await message.edit_text("❌ Failed to download video.")

async def execute_image_download(message: Message, url: str, db_user: dict):
    variant = "image:best"
    
    # Check Cache
    cached_id = await db.get_cached_file(url, variant)
    if cached_id:
        await message.edit_text(f"🚀 Found in Server! Sending image...")
        try:
             await message.reply_photo(cached_id)
             await db.log_download(db_user['id'], url, "server", "image", "best", 0)
             await db.update_credits(db_user['id'], -1)
             await message.delete()
             return
        except Exception:
             pass

    await message.edit_text("⏳ Downloading image(s)... please wait.")
    
    last_update_time = 0

    async def progress_handler(data):
        nonlocal last_update_time
        current_time = time.time()
        
        if current_time - last_update_time < 2 and data['percent'] != '100':
            return
            
        last_update_time = current_time
        bar = generate_progress_bar(data['percent'])

        text = (
            f"🖼 **Downloading...**\n"
            f"`[{bar}]` **{data['percent']}%**\n\n"
            f"🚀 **Speed:** {data['speed']}\n"
            f"📦 **Size:** {data['current']} / {data['total']}\n"
            f"⏳ **ETA:** {data['eta']}"
        )
        try:
            await message.edit_text(text, parse_mode="Markdown")
        except:
             pass

    try:
        logger.info(f"DEBUG: Starting download for URL: {url} Res: image")
        result = await download_image(url, progress_callback=progress_handler)
        if result:
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
                f"The image is **{format_size(result['size'])}**, but the limit is **{limit_msg}**.\n"
            )
            if os.path.exists(result['path']):
                os.remove(result['path'])
            return

        file_path = result['path']
        try:
            logger.info("DEBUG: Attempting to upload to Log Channel...")
            
            photo_file = FSInputFile(file_path)
            
            caption = (
                f"🖼 <b>{result.get('title', 'Image')}</b>\n"
                f"📦 {format_size(result.get('size', 0))}"
            )

            # 1. Upload to Log Channel
            log_msg = await message.bot.send_photo(
                chat_id=LOG_CHANNEL_ID,
                photo=photo_file,
                caption=caption,
                parse_mode="HTML",
                request_timeout=300
            )

            logger.info("DEBUG: Upload to Log Channel successful.")
            
            # For photos, telegram returns an array of different sizes. The last item is the largest.
            file_id = log_msg.photo[-1].file_id
            
            # 2. Save Cache
            await db.save_cached_file(url, variant, file_id)
            
            # 3. Send to User using File ID
            await message.reply_photo(
                photo=file_id,
                caption=caption,
                parse_mode="HTML"
            )

            # Log and deduct
            await db.log_download(db_user['id'], url, "new", "image", "best", result['size'])
            await db.update_credits(db_user['id'], -1)
            await message.delete()
        except Exception as e:
             await message.edit_text(f"❌ Failed to process file.\nError: {e}")
        finally:
             if os.path.exists(file_path):
                 os.remove(file_path)
    else:
        await message.edit_text("❌ Failed to download image.")
