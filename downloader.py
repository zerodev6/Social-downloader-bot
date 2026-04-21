import yt_dlp
import os
import asyncio
import glob
import subprocess
import shutil

# ─────────────────────────────────────────────────────────────────────────────
# COOKIES SETUP
# ─────────────────────────────────────────────────────────────────────────────

def _write_cookie_file(env_var: str, filename: str) -> str | None:
    content = os.environ.get(env_var, '').strip()
    if not content:
        return None
    os.makedirs('cookies', exist_ok=True)
    path = f'cookies/{filename}'
    if not os.path.exists(path):
        with open(path, 'w') as f:
            if not content.startswith('# Netscape'):
                f.write('# Netscape HTTP Cookie File\n')
            f.write(content)
    return path


_YT_COOKIE_FILE  = _write_cookie_file('YOUTUBE_COOKIES',   'youtube.txt')  or 'cookies/youtube.txt'
_IG_COOKIE_FILE  = _write_cookie_file('INSTAGRAM_COOKIES', 'instagram.txt') or 'cookies/instagram.txt'
_FB_COOKIE_FILE  = _write_cookie_file('FACEBOOK_COOKIES',  'facebook.txt')  or 'cookies/facebook.txt'
_TT_COOKIE_FILE  = _write_cookie_file('TIKTOK_COOKIES',    'tiktok.txt')    or 'cookies/tiktok.txt'
_PIN_COOKIE_FILE = _write_cookie_file('PINTEREST_COOKIES', 'pinterest.txt') or 'cookies/pinterest.txt'
_TWI_COOKIE_FILE = _write_cookie_file('TWITTER_COOKIES',   'twitter.txt')   or 'cookies/twitter.txt'


# ─────────────────────────────────────────────────────────────────────────────
# PLATFORM DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def is_youtube(url: str) -> bool:
    return any(x in url for x in ['youtube.com', 'youtu.be', 'yt.be', 'youtube-nocookie.com'])

def is_instagram(url: str) -> bool:
    return 'instagram.com' in url

def is_tiktok(url: str) -> bool:
    return any(x in url for x in ['tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com'])

def is_facebook(url: str) -> bool:
    return any(x in url for x in ['facebook.com', 'fb.com', 'fb.watch', 'm.facebook.com'])

def is_spotify(url: str) -> bool:
    return 'open.spotify.com' in url

def is_pinterest(url: str) -> bool:
    return any(x in url for x in ['pinterest.com', 'pin.it', 'pinterest.co'])

def is_twitter(url: str) -> bool:
    return any(x in url for x in ['twitter.com', 'x.com', 't.co'])

def is_snapchat(url: str) -> bool:
    return 'snapchat.com' in url

def is_reddit(url: str) -> bool:
    return any(x in url for x in ['reddit.com', 'redd.it'])

def is_vimeo(url: str) -> bool:
    return 'vimeo.com' in url

def is_dailymotion(url: str) -> bool:
    return 'dailymotion.com' in url

def get_platform_name(url: str) -> str:
    if is_youtube(url):    return '▶️ YouTube'
    if is_tiktok(url):     return '🎵 TikTok'
    if is_instagram(url):  return '📸 Instagram'
    if is_facebook(url):   return '📘 Facebook'
    if is_spotify(url):    return '🎧 Spotify'
    if is_pinterest(url):  return '📌 Pinterest'
    if is_twitter(url):    return '🐦 Twitter/X'
    if is_snapchat(url):   return '👻 Snapchat'
    if is_reddit(url):     return '🤖 Reddit'
    if is_vimeo(url):      return '🎬 Vimeo'
    if is_dailymotion(url):return '📺 Dailymotion'
    return '🌐 Web'


# ─────────────────────────────────────────────────────────────────────────────
# BASE OPTIONS
# ─────────────────────────────────────────────────────────────────────────────

def get_ydl_base_opts() -> dict:
    return {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'ignoreerrors': False,
        'user_agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        ),
        'referer': 'https://www.google.com/',
        'outtmpl': 'downloads/%(title).60s.%(ext)s',
        'merge_output_format': 'mp4',
        'retries': 5,
        'fragment_retries': 5,
        'http_headers': {
            'Accept-Language': 'en-US,en;q=0.9',
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# BUILD OPTIONS PER PLATFORM
# ─────────────────────────────────────────────────────────────────────────────

def build_ydl_opts(url: str, mode: str = 'video', quality: str = 'best') -> dict:
    opts = get_ydl_base_opts()

    # ── Cookie helper ─────────────────────────────────────────────────────────
    def apply_cookies(cookie_file: str):
        if os.path.exists(cookie_file):
            opts['cookiefile'] = cookie_file

    # ── MP3 mode ──────────────────────────────────────────────────────────────
    if mode == 'mp3':
        opts['format'] = 'bestaudio/best'
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
        if is_youtube(url):   apply_cookies(_YT_COOKIE_FILE)
        elif is_instagram(url): apply_cookies(_IG_COOKIE_FILE)
        elif is_facebook(url):  apply_cookies(_FB_COOKIE_FILE)
        elif is_twitter(url):   apply_cookies(_TWI_COOKIE_FILE)
        return opts

    # ── IMAGE mode ────────────────────────────────────────────────────────────
    if mode == 'image':
        opts['format'] = 'bestvideo/best'
        opts['outtmpl'] = 'downloads/%(title).60s_%(autonumber)s.%(ext)s'
        if is_instagram(url):  apply_cookies(_IG_COOKIE_FILE)
        elif is_pinterest(url): apply_cookies(_PIN_COOKIE_FILE)
        elif is_twitter(url):   apply_cookies(_TWI_COOKIE_FILE)
        elif is_tiktok(url):    apply_cookies(_TT_COOKIE_FILE)
        elif is_facebook(url):  apply_cookies(_FB_COOKIE_FILE)
        return opts

    # ── VIDEO mode ────────────────────────────────────────────────────────────

    if is_youtube(url):
        apply_cookies(_YT_COOKIE_FILE)
        if quality == 'best':
            opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best'
        else:
            h = quality
            opts['format'] = (
                f'bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/'
                f'bestvideo[height<={h}]+bestaudio/'
                f'best[height<={h}]/best'
            )

    elif is_tiktok(url):
        apply_cookies(_TT_COOKIE_FILE)
        # Handle both video and photo slideshows
        opts['format'] = 'bestvideo[vcodec!=none]+bestaudio/best'
        opts['user_agent'] = (
            'com.zhiliaoapp.musically/2022600030 '
            '(Linux; U; Android 11; en_US; Pixel 4; '
            'Build/RQ3A.210805.001.A1; Cronet/58.0.2991.0)'
        )
        opts['http_headers']['Referer'] = 'https://www.tiktok.com/'
        # Download all slides if photo post
        opts['outtmpl'] = 'downloads/%(title).60s_%(autonumber)s.%(ext)s'

    elif is_instagram(url):
        apply_cookies(_IG_COOKIE_FILE)
        # Handles reels, posts, carousels, stories
        opts['format'] = 'bestvideo+bestaudio/best'
        opts['outtmpl'] = 'downloads/%(title).60s_%(autonumber)s.%(ext)s'
        opts['http_headers'].update({
            'Referer': 'https://www.instagram.com/',
            'Origin':  'https://www.instagram.com',
        })

    elif is_facebook(url):
        apply_cookies(_FB_COOKIE_FILE)
        opts['format'] = 'bestvideo+bestaudio/best'
        opts['outtmpl'] = 'downloads/%(title).60s_%(autonumber)s.%(ext)s'
        opts['http_headers']['Referer'] = 'https://www.facebook.com/'

    elif is_pinterest(url):
        apply_cookies(_PIN_COOKIE_FILE)
        # Pinterest: images and videos
        opts['format'] = 'bestvideo+bestaudio/best'
        opts['outtmpl'] = 'downloads/%(title).60s_%(autonumber)s.%(ext)s'
        opts['http_headers']['Referer'] = 'https://www.pinterest.com/'

    elif is_twitter(url):
        apply_cookies(_TWI_COOKIE_FILE)
        opts['format'] = 'bestvideo+bestaudio/best'
        opts['http_headers']['Referer'] = 'https://twitter.com/'

    elif is_snapchat(url):
        opts['format'] = 'bestvideo+bestaudio/best'
        opts['http_headers']['Referer'] = 'https://www.snapchat.com/'

    elif is_reddit(url):
        opts['format'] = 'bestvideo+bestaudio/best'
        opts['http_headers']['Referer'] = 'https://www.reddit.com/'

    elif is_vimeo(url):
        opts['format'] = (
            f'bestvideo[height<={quality}]+bestaudio/best'
            if quality != 'best' else 'bestvideo+bestaudio/best'
        )

    else:
        opts['format'] = 'bestvideo+bestaudio/best'

    return opts


# ─────────────────────────────────────────────────────────────────────────────
# SPOTIFY DOWNLOAD (via spotdl)
# Install: pip install spotdl
# ─────────────────────────────────────────────────────────────────────────────

async def download_spotify(url: str) -> tuple:
    """Downloads Spotify track/album/playlist using spotdl."""
    os.makedirs('downloads', exist_ok=True)

    if not shutil.which('spotdl'):
        # Try to install spotdl automatically
        proc = await asyncio.create_subprocess_exec(
            'pip', 'install', 'spotdl',
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc.wait()

    loop = asyncio.get_event_loop()

    def _run_spotdl():
        result = subprocess.run(
            ['spotdl', url, '--output', 'downloads/{title}.{output-ext}'],
            capture_output=True,
            text=True,
            timeout=120
        )
        return result

    try:
        result = await loop.run_in_executor(None, _run_spotdl)
        # Find newest mp3
        matches = glob.glob('downloads/*.mp3')
        if not matches:
            raise FileNotFoundError("Spotify download failed — no MP3 found.")
        file_path = max(matches, key=os.path.getmtime)
        caption = f'<b>🎧 Spotify</b>  |  🎵 MP3\n\n<i>⚡ @FullSaveMe_z_Bot</i>'
        return os.path.abspath(file_path), caption
    except Exception as e:
        raise RuntimeError(f"Spotify download failed: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# METADATA FETCH
# ─────────────────────────────────────────────────────────────────────────────

async def get_media_info(url: str) -> dict:
    if is_spotify(url):
        return {}

    opts = get_ydl_base_opts()
    opts['skip_download'] = True

    if is_youtube(url)   and os.path.exists(_YT_COOKIE_FILE):  opts['cookiefile'] = _YT_COOKIE_FILE
    elif is_instagram(url) and os.path.exists(_IG_COOKIE_FILE): opts['cookiefile'] = _IG_COOKIE_FILE
    elif is_facebook(url)  and os.path.exists(_FB_COOKIE_FILE): opts['cookiefile'] = _FB_COOKIE_FILE
    elif is_tiktok(url)    and os.path.exists(_TT_COOKIE_FILE): opts['cookiefile'] = _TT_COOKIE_FILE
    elif is_twitter(url)   and os.path.exists(_TWI_COOKIE_FILE): opts['cookiefile'] = _TWI_COOKIE_FILE
    elif is_pinterest(url) and os.path.exists(_PIN_COOKIE_FILE): opts['cookiefile'] = _PIN_COOKIE_FILE

    loop = asyncio.get_event_loop()
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = await loop.run_in_executor(
                None, lambda: ydl.extract_info(url, download=False)
            )
        return info or {}
    except Exception:
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# CAPTION BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_caption(info: dict, mode: str, quality: str = '', url: str = '') -> str:
    if not info:
        return ''

    title      = info.get('title', '')
    uploader   = info.get('uploader') or info.get('channel') or info.get('creator', '')
    duration   = info.get('duration')
    view_count = info.get('view_count')
    like_count = info.get('like_count')
    webpage    = info.get('webpage_url', '') or url

    dur_str = ''
    if duration:
        m, s = divmod(int(duration), 60)
        h, m = divmod(m, 60)
        dur_str = f'{h:02d}:{m:02d}:{s:02d}' if h else f'{m:02d}:{s:02d}'

    def fmt_num(n):
        if n is None: return 'N/A'
        if n >= 1_000_000: return f'{n/1_000_000:.1f}M'
        if n >= 1_000:     return f'{n/1_000:.1f}K'
        return str(n)

    platform  = get_platform_name(webpage)
    mode_icon = '🎵 MP3' if mode == 'mp3' else ('🖼 Image' if mode == 'image' else '🎬 Video')

    lines = [f'<b>{platform}</b>  |  {mode_icon}', '']
    if title:                       lines.append(f'<b>📝</b> {title}')
    if uploader:                    lines.append(f'<b>👤</b> {uploader}')
    if dur_str:                     lines.append(f'<b>⏱</b> {dur_str}')
    if view_count is not None:      lines.append(f'<b>👁</b> {fmt_num(view_count)}')
    if like_count is not None:      lines.append(f'<b>❤️</b> {fmt_num(like_count)}')
    if quality and quality != 'best' and mode == 'video':
        lines.append(f'<b>🎞</b> {quality}p')
    lines += ['', '<i>⚡ @FullSaveMe_z_Bot</i>']

    return '\n'.join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# COLLECT DOWNLOADED FILES (handles multi-file posts like carousels)
# ─────────────────────────────────────────────────────────────────────────────

def collect_downloaded_files(mode: str, expected_path: str, min_mtime: float) -> list[str]:
    """Returns list of files downloaded after min_mtime."""
    ext_map = {
        'mp3':   ['mp3'],
        'image': ['jpg', 'jpeg', 'png', 'webp', 'gif'],
        'video': ['mp4', 'mkv', 'webm', 'mov'],
    }
    exts = ext_map.get(mode, ['mp4', 'mp3'])

    found = []
    for ext in exts:
        for f in glob.glob(f'downloads/*.{ext}'):
            if os.path.getmtime(f) >= min_mtime:
                found.append(f)

    # Also check expected path
    if os.path.exists(expected_path) and expected_path not in found:
        found.append(expected_path)

    # Sort by modification time
    found.sort(key=os.path.getmtime)
    return found


# ─────────────────────────────────────────────────────────────────────────────
# MAIN DOWNLOAD FUNCTION
# Returns (file_path_or_list, caption)
# For single files: (str, str)
# For multi-file (carousel, slideshow): (list[str], str)
# ─────────────────────────────────────────────────────────────────────────────

async def download_media(url: str, mode: str = 'video', quality: str = 'best') -> tuple:
    os.makedirs('downloads', exist_ok=True)

    # ── Spotify special handler ───────────────────────────────────────────────
    if is_spotify(url):
        return await download_spotify(url)

    # ── Fetch metadata for caption ────────────────────────────────────────────
    info = await get_media_info(url)
    caption = build_caption(info, mode, quality, url)

    ydl_opts = build_ydl_opts(url, mode=mode, quality=quality)

    # Record time before download to find new files
    import time
    min_mtime = time.time() - 2

    loop = asyncio.get_event_loop()

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        dl_info = await loop.run_in_executor(
            None, lambda: ydl.extract_info(url, download=True)
        )

        if not dl_info:
            raise ValueError("yt-dlp returned no info — link may be private or unsupported.")

        expected_path = ydl.prepare_filename(dl_info)

        if mode == 'mp3':
            expected_path = os.path.splitext(expected_path)[0] + '.mp3'
        elif mode != 'image':
            expected_path = os.path.splitext(expected_path)[0] + '.mp4'

    # Collect all files downloaded in this session
    files = collect_downloaded_files(mode, expected_path, min_mtime)

    if not files:
        raise FileNotFoundError(f"No downloaded files found. Expected: {expected_path}")

    # Return list for multi-file, single path for single file
    result = [os.path.abspath(f) for f in files]
    return (result if len(result) > 1 else result[0]), caption
