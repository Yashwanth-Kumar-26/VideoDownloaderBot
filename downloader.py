import logging
import os
import tempfile
import asyncio
import yt_dlp
import shutil
import aiohttp
import uuid
import subprocess
from utils.helpers import sanitize_filename

TEMP_ROOT = os.path.join(os.getcwd(), 'temp_data')
os.makedirs(TEMP_ROOT, exist_ok=True)

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
        if 'spotify.com' in url:
            import tempfile
            import json
            import sys
            import subprocess
            import os
            
            with tempfile.NamedTemporaryFile(suffix='.spotdl', delete=False) as tf:
                meta_file = tf.name
                
            venv_bin = os.path.dirname(sys.executable)
            spotdl_path = os.path.join(venv_bin, "spotdl")
            cmd = [spotdl_path, "save", url, "--save-file", meta_file]
            if not os.path.exists(spotdl_path):
                cmd = [sys.executable, "-m", "spotdl", "save", url, "--save-file", meta_file]
                
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                with open(meta_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if data:
                    entries = []
                    for t in data:
                        track_name = t.get('name', 'Unknown Track')
                        # SpotDL JSON usually has an 'artists' list or 'artist' string
                        artist = t.get('artist', 'Unknown Artist')
                        if isinstance(t.get('artists'), list) and len(t['artists']) > 0:
                            artist = ", ".join(t['artists'])
                            
                        entries.append({
                            'title': f"{artist} - {track_name}",
                            'url': t.get('url', url)  # Fallback to the original URL if individual URL is missing
                        })
                    return {
                        'title': 'Spotify Playlist/Album',
                        'count': len(entries),
                        'entries': entries
                    }
            except Exception as e:
                logger.error(f"Error extracting Spotify playlist: {e}")
            finally:
                if os.path.exists(meta_file):
                    try:
                        os.remove(meta_file)
                    except:
                        pass
            return None

        ydl_opts = {
            'extract_flat': True,  # Don't download, just list
            'quiet': True,
            'ignoreerrors': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                if getattr(info, "get", lambda _: None)('entries'):
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


async def download_with_spotdl(url, output_dir=None):
    """Download Spotify tracks/playlists using spotDL"""
    import sys
    import shutil
    
    try:
        base_dir = output_dir or TEMP_ROOT
        run_dir = os.path.join(base_dir, f"spotdl_{uuid.uuid4().hex[:8]}")
        os.makedirs(run_dir, exist_ok=True)

        logger.info(f"Starting spotDL download for {url} → {run_dir}")

        # Construct the absolute path to spotdl in the virtual environment's bin folder
        import sys
        venv_bin = os.path.dirname(sys.executable)
        spotdl_path = os.path.join(venv_bin, "spotdl")
        
        if os.path.exists(spotdl_path):
            cmd = [
                spotdl_path,
                url,
                "--output-format", "mp3",
                "--download-threads", "4",
                "--output", run_dir,
            ]
        else:
            logger.warning(f"spotdl executable not found in {venv_bin}. Falling back to sys.executable -m spotdl")
            cmd = [
                sys.executable,
                "-m", "spotdl",
                url,
                "--output-format", "mp3",
                "--download-threads", "4",
                "--output", run_dir,
            ]

        logger.info(f"Running command: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if stderr:
            logger.warning(f"spotDL stderr: {stderr.decode()[:500]}")

        downloaded_files = [
            os.path.join(run_dir, f)
            for f in os.listdir(run_dir)
            if f.endswith(".mp3")
        ]

        logger.info(f"Found {len(downloaded_files)} MP3 files")

        if not downloaded_files:
            logger.error("spotDL failed: no files downloaded")
            return None

        if process.returncode != 0:
            logger.warning(
                f"spotDL completed with warnings "
                f"(return code {process.returncode})"
            )

        results = []
        for filepath in downloaded_files:
            filesize = os.path.getsize(filepath)
            results.append({
                "path": filepath,
                "size": filesize,
                "thumb": None,
                "title": os.path.splitext(os.path.basename(filepath))[0],
                "duration": 0,
                "artist": "Unknown",
            })

        if len(results) == 1:
            return results[0]

        return results

    except Exception as e:
        logger.error(f"spotDL download failed: {e}")
        return None

async def download_video(url, resolution, progress_callback=None, output_dir=None):
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
        
        target_dir = output_dir if output_dir else TEMP_ROOT
        
        ydl_opts = {
            'format': f'bestvideo[height<={height}][format_note!*=Premium]+bestaudio/best[height<={height}][format_note!*=Premium]/best',
            'outtmpl': os.path.join(target_dir, f'%(title)s_{run_id}.%(ext)s'),
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
        
    # Try yt-dlp
    result = await asyncio.to_thread(_download)
    if result:
        return result

    return None

async def download_audio(url, quality='192', progress_callback=None, output_dir=None):
    # Check if Spotify URL
    if 'spotify.com' in url:
        logger.info("Detected Spotify URL, using spotDL...")
        return await download_with_spotdl(url, output_dir)

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

        target_dir = output_dir if output_dir else TEMP_ROOT

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(target_dir, f'%(title)s_{run_id}.%(ext)s'),
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

    # Try yt-dlp
    result = await asyncio.to_thread(_download)
    if result:
        return result

    return None

async def download_image(url, progress_callback=None, output_dir=None):
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

        run_id = uuid.uuid4().hex[:8]
        target_dir = output_dir if output_dir else TEMP_ROOT

        ydl_opts = {
            'outtmpl': os.path.join(target_dir, f'%(title)s_{run_id}.%(ext)s'),
            'quiet': False,
            'verbose': True,
            'no_warnings': False,
            'progress_hooks': [progress_hook]
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
                # Since Instagram carousels might be playlists, we must handle multiples
                import glob
                downloaded_files = glob.glob(os.path.join(target_dir, f"*{run_id}*.*"))
                
                if not downloaded_files:
                    return None
                    
                filename = downloaded_files[0]

                return {
                    'path': filename,
                    'size': os.path.getsize(filename),
                    'thumb': filename,
                    'title': info.get('title', 'Image'),
                    'duration': 0,
                    'artist': info.get('artist', 'Unknown')
                }
            except Exception as e:
                logger.error(f"Error downloading image: {e}")
                return None

    result = await asyncio.to_thread(_download)
    return result
