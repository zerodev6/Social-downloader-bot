import yt_dlp
import os
import asyncio
import time
import re
import aiohttp
import json
import subprocess
import glob

# ─────────────────────────────────────────────────────────────────────────────
# COOKIES SETUP
# ─────────────────────────────────────────────────────────────────────────────

def get_cookie_file(filename: str, env_var: str) -> str | None:
    if os.path.exists(filename):
        return os.path.abspath(filename)
    
    content = os.environ.get(env_var, '').strip()
    if content:
        os.makedirs('cookies', exist_ok=True)
        path = f'cookies/{filename}'
        with open(path, 'w') as f:
            if not content.startswith('# Netscape'):
                f.write('# Netscape HTTP Cookie File\n')
            f.write(content)
        return os.path.abspath(path)
    return None

_YT_COOKIE_FILE = get_cookie_file('youtube.txt', 'YOUTUBE_COOKIES')

# ─────────────────────────────────────────────────────────────────────────────
# PLATFORM DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def is_youtube(url: str) -> bool:
    return any(x in url.lower() for x in ['youtube.com', 'youtu.be', 'yt.be'])

def is_tiktok(url: str) -> bool:
    return any(x in url.lower() for x in ['tiktok.com', 'vm.tiktok.com'])

def is_instagram(url: str) -> bool:
    return 'instagram.com' in url.lower()

def is_facebook(url: str) -> bool:
    return any(x in url.lower() for x in ['facebook.com', 'fb.com', 'fb.watch'])

def is_spotify(url: str) -> bool:
    # Basic check for common Spotify redirection or direct links
    return 'spotify.com' in url.lower() or 'googleusercontent.com/spotify' in url.lower()

def get_platform_name(url: str) -> str:
    if is_youtube(url):   return '▶️ YouTube'
    if is_tiktok(url):    return '🎵 TikTok'
    if is_instagram(url): return '📸 Instagram'
    if is_facebook(url):  return '📘 Facebook'
    if is_spotify(url):   return '🎧 Spotify'
    return '🌐 Web'

# ─────────────────────────────────────────────────────────────────────────────
# SPECIAL DOWNLOADERS
# ─────────────────────────────────────────────────────────────────────────────

async def download_tiktok_photo(url: str) -> tuple:
    os.makedirs('downloads', exist_ok=True)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url, allow_redirects=True) as resp:
            html = await resp.text()

    image_urls = re.findall(r'https://p[0-9]+(?:-sign)?\.tiktokcdn\.com/[^\s"\'\\]+\.(?:jpg|jpeg|png|webp)', html)
    if not image_urls:
        raise ValueError("No images found in this TikTok post.")

    downloaded = []
    async with aiohttp.ClientSession(headers=headers) as session:
        for i, img_url in enumerate(list(set(image_urls))[:10]):
            path = os.path.abspath(f"downloads/tt_{int(time.time())}_{i}.jpg")
            async with session.get(img_url) as r:
                if r.status == 200:
                    with open(path, 'wb') as f: f.write(await r.read())
                    downloaded.append(path)

    caption = f"<b>{get_platform_name(url)}</b> | 🖼 Slideshow\n\n<i>⚡ @ZeroDev_Bot</i>"
    return downloaded, caption

async def download_spotify(url: str) -> tuple:
    os.makedirs('downloads', exist_ok=True)
    output_dir = os.path.abspath("downloads")
    cmd = ["spotdl", "download", url, "--output", f"{output_dir}/{{title}} - {{artist}}.{{output-ext}}"]
    
    if _YT_COOKIE_FILE:
        cmd.extend(["--cookie-file", _YT_COOKIE_FILE])
    
    process = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=180)
        files = glob.glob(f"{output_dir}/*.mp3")
        if not files:
            raise Exception("Spotify download failed or timed out.")
        newest_file = max(files, key=os.path.getctime)
        return newest_file, f"<b>🎧 Spotify</b> | 🎵 Download Complete\n\n<i>⚡ @ZeroDev_Bot</i>"
    except Exception as e:
        if process: process.kill()
        raise e

# ─────────────────────────────────────────────────────────────────────────────
# CORE DOWNLOADER
# ─────────────────────────────────────────────────────────────────────────────

async def download_media(url: str, mode: str = 'video', quality: str = 'best') -> tuple:
    if is_tiktok(url) and '/photo/' in url:
        return await download_tiktok_photo(url)
    if is_spotify(url):
        return await download_spotify(url)

    os.makedirs('downloads', exist_ok=True)
    
    # --- SMART FORMAT SELECTOR ---
    # This logic says: "Try to find the best video up to my requested height, 
    # but if that specific height/codec combo fails, just give me the best available overall."
    if mode == 'mp3':
        format_str = 'bestaudio/best'
    else:
        # Fallback logic: bestvideo[height<=720] + bestaudio OR just the best available video
        format_str = f'bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality}]/best'

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'outtmpl': 'downloads/%(title).50s.%(ext)s',
        'format': format_str,
        'merge_output_format': 'mp4',
        'geo_bypass': True,
        'nocheckcertificate': True,
    }

    if mode == 'mp3':
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    if _YT_COOKIE_FILE and is_youtube(url):
        ydl_opts['cookiefile'] = _YT_COOKIE_FILE

    # Bypassing YouTube "Bot" restrictions
    if is_youtube(url):
        ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android', 'web']}}

    loop = asyncio.get_event_loop()
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
        file_path = ydl.prepare_filename(info)
        
        if mode == 'mp3':
            file_path = os.path.splitext(file_path)[0] + '.mp3'
            
        title = info.get('title', 'Media')
        platform = get_platform_name(url)
        caption = f"<b>{platform}</b> | 🎬 {title}\n\n<i>⚡ @ZeroDev_Bot</i>"
        
        return os.path.abspath(file_path), caption
