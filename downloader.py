import logging
import os
import tempfile
import asyncio
import yt_dlp
import shutil
import aiohttp
import uuid
from utils.helpers import sanitize_filename

logger = logging.getLogger(__name__)

# Check for aria2c
ARIA2_INSTALLED = shutil.which("aria2c") is not None
if ARIA2_INSTALLED:
    logger.info("aria2c found! High-speed downloading enabled.")
else:
    logger.info("aria2c not found. Using standard downloader.")

async def get_video_resolutions(url):
    def _get_resolutions():
        ydl_opts = {
            'listformats': True,
            'quiet': False,
            'verbose': True,
            'no_warnings': False,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                formats = info.get('formats', [])
                resolutions = []
                for f in formats:
                    if f.get('height') and f.get('ext') in ['mp4', 'webm']:
                        res = f"{f['height']}p"
                        if res not in resolutions:
                            resolutions.append(res)
                resolutions = sorted(set(resolutions), key=lambda x: int(x[:-1]), reverse=True)
                return resolutions[:5]
            except Exception as e:
                logger.error(f"Error getting resolutions: {e}")
                return []

    return await asyncio.to_thread(_get_resolutions)

    return await asyncio.to_thread(_get_resolutions)

async def get_playlist_info(url):
    def _extract():
        ydl_opts = {
            'extract_flat': True,  # Don't download, just list
            'quiet': True,
            'ignoreerrors': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info:
                    return {
                        'title': info.get('title', 'Playlist'),
                        'count': len(info['entries']),
                        'entries': [
                            {'title': e.get('title'), 'url': e.get('url')} 
                            for e in info['entries'] if e
                        ]
                    }
                return None
            except Exception as e:
                logger.error(f"Error extracting playlist: {e}")
                return None
    return await asyncio.to_thread(_extract)

async def download_with_cobalt(url, is_audio=False):
    """Fallback downloader using Cobalt API"""
    try:
        # Using a public instance - in production, self-hosting is recommended
        api_url = "https://api.cobalt.tools/api/json"
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        payload = {
            "url": url,
            "isAudioOnly": is_audio,
            # "vQuality": "720" # Defaulting for now
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload, headers=headers) as resp:
                data = await resp.json()
                
                if data.get('status') == 'error':
                    logger.error(f"Cobalt error: {data.get('text')}")
                    return None
                    
                download_url = data.get('url')
                if not download_url:
                    return None
                
                # Download the actual file
                async with session.get(download_url) as file_resp:
                    if file_resp.status != 200:
                        return None
                    
                    # Try to get filename from headers or URL
                    import cgi
                    content_disposition = file_resp.headers.get('Content-Disposition')
                    if content_disposition:
                        _, params = cgi.parse_header(content_disposition)
                        filename = params.get('filename', 'download')
                    else:
                        filename = f"download.{'mp3' if is_audio else 'mp4'}"
                    
                    # sanitize
                    filename = sanitize_filename(filename) 
                    if not filename.endswith(('.mp4', '.mp3', '.webm', '.m4a')):
                         filename += '.mp3' if is_audio else '.mp4'

                    filepath = os.path.join(tempfile.gettempdir(), filename)
                    
                    with open(filepath, 'wb') as f:
                        while True:
                            chunk = await file_resp.content.read(1024*1024)
                            if not chunk:
                                break
                            f.write(chunk)
                            
                filesize = os.path.getsize(filepath)
                return {
                    'path': filepath,
                    'size': filesize,
                    'thumb': None,
                    'title': filename,
                    'duration': 0,
                    'width': 0,
                    'height': 0
                }

    except Exception as e:
        logger.error(f"Cobalt download failed: {e}")
        return None

async def download_video(url, resolution, progress_callback=None):
    loop = asyncio.get_running_loop()
    
    def _download():
        def progress_hook(d):
            if d['status'] == 'downloading' and progress_callback:
                try:
                    p = d.get('_percent_str', '0%').replace('%','')
                    speed = d.get('_speed_str', 'N/A')
                    eta = d.get('_eta_str', 'N/A')
                    current = d.get('_downloaded_bytes_str', '0B')
                    total = d.get('_total_bytes_str', '0B')
                    
                    data = {
                        "percent": p,
                        "speed": speed,
                        "eta": eta,
                        "current": current,
                        "total": total
                    }
                    # Thread-safe execution
                    asyncio.run_coroutine_threadsafe(progress_callback(data), loop)
                except Exception:
                    pass

        height = int(resolution.replace('p', ''))
        # Generate unique run ID to prevent "already downloaded" errors
        run_id = uuid.uuid4().hex[:8]
        ydl_opts = {
            'format': f'bestvideo[height<={height}]+bestaudio/best[height<={height}]/best',
            'outtmpl': os.path.join(tempfile.gettempdir(), f'%(title)s_{run_id}.%(ext)s'),
            'quiet': False,
            'verbose': True,
            'no_warnings': False,
            'writethumbnail': True,
            'merge_output_format': 'mp4',
            'progress_hooks': [progress_hook] 
        }
        # ... (rest of logic)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                # Force check for the merged file
                if not os.path.exists(filename):
                     filename = os.path.splitext(filename)[0] + '.mp4'
                
                # Find thumbnail
                thumb_path = None
                base_name = os.path.splitext(filename)[0]
                for ext in ['.jpg', '.webp', '.png']:
                    if os.path.exists(base_name + ext):
                        thumb_path = base_name + ext
                        break
                
                return {
                    'path': filename,
                    'size': info.get('filesize', 0) or os.path.getsize(filename),
                    'thumb': thumb_path,
                    'title': info.get('title', 'Video'),
                    'duration': info.get('duration', 0),
                    'width': info.get('width', 0),
                    'height': info.get('height', 0)
                }
            except Exception as e:
                logger.error(f"Error downloading video: {e}")
                return None
        
    # Try yt-dlp first
    result = await asyncio.to_thread(_download)
    if result:
        return result
    
    # Fallback to Cobalt
    logger.info("yt-dlp failed, trying Cobalt backup...")
    return await download_with_cobalt(url, is_audio=False)

async def download_audio(url, quality='192', progress_callback=None):
    loop = asyncio.get_running_loop()
    
    def _download():
        def progress_hook(d):
             if d['status'] == 'downloading' and progress_callback:
                 try:
                    p = d.get('_percent_str', '0%').replace('%','')
                    data = {
                        "percent": p,
                        "speed": d.get('_speed_str', 'N/A'),
                        "eta": d.get('_eta_str', 'N/A'),
                        "current": d.get('_downloaded_bytes_str', '0B'),
                        "total": d.get('_total_bytes_str', '0B')
                    }
                    asyncio.run_coroutine_threadsafe(progress_callback(data), loop)
                 except Exception:
                    pass

        # Generate unique run ID
        run_id = uuid.uuid4().hex[:8]
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(tempfile.gettempdir(), f'%(title)s_{run_id}.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': quality,
            }],
            'writethumbnail': True,
            'quiet': False,
            'verbose': True,
            'no_warnings': False,
            'progress_hooks': [progress_hook]
        }
        
        if ARIA2_INSTALLED:
            ydl_opts['external_downloader'] = 'aria2c'
            ydl_opts['external_downloader_args'] = ['-x', '16', '-k', '1M', '-s', '16']

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                base = os.path.splitext(filename)[0]
                filename = base + '.mp3'
                
                # Find thumbnail
                thumb_path = None
                # Check original base name for thumb
                # Start with filename base
                base = os.path.splitext(filename)[0]
                for ext in ['.jpg', '.webp', '.png']:
                   if os.path.exists(base + ext):
                       thumb_path = base + ext
                       break
                
                return {
                    'path': filename,
                    'size': info.get('filesize', 0) or os.path.getsize(filename),
                    'thumb': thumb_path,
                    'title': info.get('title', 'Audio'),
                    'duration': info.get('duration', 0),
                    'artist': info.get('artist', 'Unknown')
                }
            except Exception as e:
                logger.error(f"Error downloading audio: {e}")
                return None

    # Try yt-dlp first
    result = await asyncio.to_thread(_download)
    if result:
        return result
        
    # Fallback to Cobalt
    logger.info("yt-dlp failed, trying Cobalt backup...")
    return await download_with_cobalt(url, is_audio=True)
