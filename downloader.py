import yt_dlp
import os
import asyncio
import glob

# ─────────────────────────────────────────────────────────────────────────────
# COOKIES SETUP
# Reads YOUTUBE_COOKIES and INSTAGRAM_COOKIES from environment variables.
# Set these in Koyeb → Environment Variables as the raw Netscape cookie string.
# ─────────────────────────────────────────────────────────────────────────────

def _write_cookie_file(env_var: str, filename: str) -> str | None:
    """
    If env_var is set, writes its content to filename and returns the path.
    Returns None if env_var is not set or file already exists on disk.
    """
    content = os.environ.get(env_var, '').strip()
    if not content:
        return None
    os.makedirs('cookies', exist_ok=True)
    path = f'cookies/{filename}'
    if not os.path.exists(path):
        with open(path, 'w') as f:
            # Ensure Netscape header is present
            if not content.startswith('# Netscape'):
                f.write('# Netscape HTTP Cookie File\n')
            f.write(content)
    return path


# Write cookies on module load (once per container start)
_YT_COOKIE_FILE = _write_cookie_file('YOUTUBE_COOKIES', 'youtube.txt') or 'cookies/youtube.txt'
_IG_COOKIE_FILE = _write_cookie_file('INSTAGRAM_COOKIES', 'instagram.txt') or 'cookies/instagram.txt'
_FB_COOKIE_FILE = _write_cookie_file('FACEBOOK_COOKIES', 'facebook.txt') or 'cookies/facebook.txt'


# ─────────────────────────────────────────────────────────────────────────────
# PLATFORM DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def is_youtube(url: str) -> bool:
    return any(x in url for x in ['youtube.com', 'youtu.be', 'yt.be'])

def is_instagram(url: str) -> bool:
    return 'instagram.com' in url

def is_tiktok(url: str) -> bool:
    return any(x in url for x in ['tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com'])

def is_facebook(url: str) -> bool:
    return any(x in url for x in ['facebook.com', 'fb.com', 'fb.watch', 'm.facebook.com'])


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

    # ── MP3 mode ──────────────────────────────────────────────────────────────
    if mode == 'mp3':
        opts['format'] = 'bestaudio/best'
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
        # Still apply cookies for platforms that need auth for audio too
        if is_youtube(url) and os.path.exists(_YT_COOKIE_FILE):
            opts['cookiefile'] = _YT_COOKIE_FILE
        elif is_instagram(url) and os.path.exists(_IG_COOKIE_FILE):
            opts['cookiefile'] = _IG_COOKIE_FILE
        elif is_facebook(url) and os.path.exists(_FB_COOKIE_FILE):
            opts['cookiefile'] = _FB_COOKIE_FILE
        return opts

    # ── VIDEO mode ────────────────────────────────────────────────────────────

    if is_youtube(url):
        if os.path.exists(_YT_COOKIE_FILE):
            opts['cookiefile'] = _YT_COOKIE_FILE
        # Quality selection
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
        # TikTok — watermark-free, no cookies needed usually
        opts['format'] = 'bestvideo[vcodec!=none]+bestaudio/best'
        opts['user_agent'] = (
            'com.zhiliaoapp.musically/2022600030 '
            '(Linux; U; Android 11; en_US; Pixel 4; '
            'Build/RQ3A.210805.001.A1; Cronet/58.0.2991.0)'
        )
        opts['http_headers']['Referer'] = 'https://www.tiktok.com/'

    elif is_instagram(url):
        if os.path.exists(_IG_COOKIE_FILE):
            opts['cookiefile'] = _IG_COOKIE_FILE
        opts['format'] = 'bestvideo+bestaudio/best'
        opts['http_headers'].update({
            'Referer': 'https://www.instagram.com/',
            'Origin':  'https://www.instagram.com',
        })

    elif is_facebook(url):
        if os.path.exists(_FB_COOKIE_FILE):
            opts['cookiefile'] = _FB_COOKIE_FILE
        opts['format'] = 'bestvideo+bestaudio/best'
        opts['http_headers']['Referer'] = 'https://www.facebook.com/'

    else:
        opts['format'] = 'bestvideo+bestaudio/best'

    return opts


# ─────────────────────────────────────────────────────────────────────────────
# METADATA FETCH (for caption, no download)
# ─────────────────────────────────────────────────────────────────────────────

async def get_media_info(url: str) -> dict:
    opts = get_ydl_base_opts()
    opts['skip_download'] = True
    # Apply cookies for info fetch too
    if is_youtube(url) and os.path.exists(_YT_COOKIE_FILE):
        opts['cookiefile'] = _YT_COOKIE_FILE
    elif is_instagram(url) and os.path.exists(_IG_COOKIE_FILE):
        opts['cookiefile'] = _IG_COOKIE_FILE
    elif is_facebook(url) and os.path.exists(_FB_COOKIE_FILE):
        opts['cookiefile'] = _FB_COOKIE_FILE

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

def build_caption(info: dict, mode: str, quality: str = '') -> str:
    if not info:
        return ''

    title      = info.get('title', '')
    uploader   = info.get('uploader') or info.get('channel') or info.get('creator', '')
    duration   = info.get('duration')
    view_count = info.get('view_count')
    like_count = info.get('like_count')
    webpage    = info.get('webpage_url', '')

    dur_str = ''
    if duration:
        m, s = divmod(int(duration), 60)
        h, m = divmod(m, 60)
        dur_str = f'{h:02d}:{m:02d}:{s:02d}' if h else f'{m:02d}:{s:02d}'

    def fmt_num(n):
        if n is None: return 'N/A'
        if n >= 1_000_000: return f'{n/1_000_000:.1f}M'
        if n >= 1_000: return f'{n/1_000:.1f}K'
        return str(n)

    if is_youtube(webpage):      platform = '▶️ YouTube'
    elif is_tiktok(webpage):     platform = '🎵 TikTok'
    elif is_instagram(webpage):  platform = '📸 Instagram'
    elif is_facebook(webpage):   platform = '📘 Facebook'
    else:                        platform = '🌐 Web'

    mode_icon = '🎵 MP3' if mode == 'mp3' else '🎬 Video'

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
# MAIN DOWNLOAD FUNCTION
# Returns (file_path, caption) — raises on failure
# ─────────────────────────────────────────────────────────────────────────────

async def download_media(url: str, mode: str = 'video', quality: str = 'best') -> tuple:
    os.makedirs('downloads', exist_ok=True)

    # Fetch metadata for caption (best-effort, won't block download on failure)
    info = await get_media_info(url)
    caption = build_caption(info, mode, quality)

    ydl_opts = build_ydl_opts(url, mode=mode, quality=quality)
    loop = asyncio.get_event_loop()

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        dl_info = await loop.run_in_executor(
            None, lambda: ydl.extract_info(url, download=True)
        )

        if not dl_info:
            raise ValueError("yt-dlp returned no info — link may be private or unsupported.")

        expected_path = ydl.prepare_filename(dl_info)

        if mode == 'mp3':
            file_path = os.path.splitext(expected_path)[0] + '.mp3'
        else:
            file_path = os.path.splitext(expected_path)[0] + '.mp4'

        # Fallback: newest matching file in downloads/
        if not os.path.exists(file_path):
            ext = 'mp3' if mode == 'mp3' else 'mp4'
            matches = glob.glob(f'downloads/*.{ext}')
            if matches:
                file_path = max(matches, key=os.path.getmtime)
            else:
                raise FileNotFoundError(f"Downloaded file not found. Expected: {file_path}")

    return os.path.abspath(file_path), caption
