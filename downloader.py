import yt_dlp
import os
import asyncio
import glob


# Platform detection helpers
def is_youtube(url: str) -> bool:
    return any(x in url for x in ['youtube.com', 'youtu.be', 'yt.be'])

def is_instagram(url: str) -> bool:
    return 'instagram.com' in url

def is_tiktok(url: str) -> bool:
    return any(x in url for x in ['tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com'])

def is_facebook(url: str) -> bool:
    return any(x in url for x in ['facebook.com', 'fb.com', 'fb.watch', 'm.facebook.com'])


def get_ydl_base_opts() -> dict:
    """Common yt-dlp options shared across all platforms."""
    return {
        'cookiefile': 'cookies.txt',
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


def build_ydl_opts(url: str, mode: str = 'video', quality: str = 'best') -> dict:
    """
    Build yt-dlp options based on platform and mode.

    :param url:     The media URL
    :param mode:    'video' | 'mp3'
    :param quality: For YouTube — '144' | '240' | '360' | '480' | '720' | '1080' | '1440' | '2160' | 'best'
    """
    opts = get_ydl_base_opts()

    # ── MP3 mode ──────────────────────────────────────────────────────────────
    if mode == 'mp3':
        opts['format'] = 'bestaudio/best'
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
        return opts

    # ── VIDEO mode ────────────────────────────────────────────────────────────

    if is_youtube(url):
        # Quality selection for YouTube
        if quality == 'best':
            opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best'
        else:
            h = quality  # e.g. '720'
            opts['format'] = (
                f'bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/'
                f'bestvideo[height<={h}]+bestaudio/'
                f'best[height<={h}]/best'
            )

    elif is_tiktok(url):
        # TikTok: grab watermark-free version when possible
        opts['format'] = (
            'bestvideo[vcodec!=none]+bestaudio/'
            'bestvideo[format_id*=play]+bestaudio/'
            'best'
        )
        # Some TikTok endpoints need a fresh user-agent
        opts['user_agent'] = (
            'com.zhiliaoapp.musically/2022600030 '
            '(Linux; U; Android 11; en_US; Pixel 4; '
            'Build/RQ3A.210805.001.A1; Cronet/58.0.2991.0)'
        )
        opts['http_headers']['Referer'] = 'https://www.tiktok.com/'

    elif is_instagram(url):
        # Instagram Reels / Posts / Stories
        opts['format'] = 'bestvideo+bestaudio/best'
        opts['http_headers'].update({
            'Referer': 'https://www.instagram.com/',
            'Origin':  'https://www.instagram.com',
        })
        # Stories & highlights may need auth via cookies — cookiefile handles it

    elif is_facebook(url):
        # Facebook Videos / Reels / Watch
        opts['format'] = 'bestvideo+bestaudio/best'
        opts['http_headers']['Referer'] = 'https://www.facebook.com/'

    else:
        # Generic fallback (Twitter/X, Reddit, Dailymotion, etc.)
        opts['format'] = 'bestvideo+bestaudio/best'

    return opts


async def get_media_info(url: str) -> dict:
    """
    Fetch metadata WITHOUT downloading (for captions / quality lists).
    Returns yt-dlp info dict or empty dict on failure.
    """
    opts = get_ydl_base_opts()
    opts['skip_download'] = True

    loop = asyncio.get_event_loop()
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = await loop.run_in_executor(
                None, lambda: ydl.extract_info(url, download=False)
            )
        return info or {}
    except Exception:
        return {}


def build_caption(info: dict, mode: str, quality: str = '') -> str:
    """
    Build a rich caption from yt-dlp info dict.
    Returns empty string if info is missing.
    """
    if not info:
        return ''

    title      = info.get('title', '')
    uploader   = info.get('uploader') or info.get('channel') or info.get('creator', '')
    duration   = info.get('duration')  # seconds
    view_count = info.get('view_count')
    like_count = info.get('like_count')
    webpage    = info.get('webpage_url', '')

    # --- duration formatting ---
    dur_str = ''
    if duration:
        m, s = divmod(int(duration), 60)
        h, m = divmod(m, 60)
        dur_str = f'{h:02d}:{m:02d}:{s:02d}' if h else f'{m:02d}:{s:02d}'

    # --- view/like formatting ---
    def fmt_num(n):
        if n is None:
            return 'N/A'
        if n >= 1_000_000:
            return f'{n/1_000_000:.1f}M'
        if n >= 1_000:
            return f'{n/1_000:.1f}K'
        return str(n)

    platform = '🌐'
    if is_youtube(webpage):   platform = '▶️ YouTube'
    elif is_tiktok(webpage):  platform = '🎵 TikTok'
    elif is_instagram(webpage): platform = '📸 Instagram'
    elif is_facebook(webpage):  platform = '📘 Facebook'

    mode_icon = '🎵 MP3' if mode == 'mp3' else '🎬 Video'
    qual_line = f'\n<b>Quality:</b> {quality}p' if quality and quality != 'best' and mode == 'video' else ''

    lines = [
        f'<b>{platform}</b> | {mode_icon}',
        '',
    ]
    if title:      lines.append(f'<b>📝 Title:</b> {title}')
    if uploader:   lines.append(f'<b>👤 By:</b> {uploader}')
    if dur_str:    lines.append(f'<b>⏱ Duration:</b> {dur_str}')
    if view_count is not None: lines.append(f'<b>👁 Views:</b> {fmt_num(view_count)}')
    if like_count is not None: lines.append(f'<b>❤️ Likes:</b> {fmt_num(like_count)}')
    if qual_line:  lines.append(qual_line.strip())
    lines.append('')
    lines.append('<i>⚡ Downloaded by @YourBotUsername</i>')

    return '\n'.join(lines)


async def download_media(url: str, mode: str = 'video', quality: str = 'best') -> tuple[str, str]:
    """
    Downloads media from TikTok / Instagram / Facebook / YouTube / generic URLs.

    :param url:     The media URL
    :param mode:    'video' | 'mp3'
    :param quality: YouTube quality — '144','240','360','480','720','1080','1440','2160','best'
    :return:        (absolute_file_path, caption_html)  — raises Exception on failure
    """
    os.makedirs('downloads', exist_ok=True)

    # Fetch info first for caption (non-blocking attempt)
    info = await get_media_info(url)
    caption = build_caption(info, mode, quality)

    ydl_opts = build_ydl_opts(url, mode=mode, quality=quality)
    loop = asyncio.get_event_loop()

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        dl_info = await loop.run_in_executor(
            None, lambda: ydl.extract_info(url, download=True)
        )

        if not dl_info:
            raise ValueError("yt-dlp returned no info — the link may be private or unsupported.")

        expected_path = ydl.prepare_filename(dl_info)

        if mode == 'mp3':
            file_path = os.path.splitext(expected_path)[0] + '.mp3'
        else:
            file_path = os.path.splitext(expected_path)[0] + '.mp4'

        # Fallback: pick the newest matching file in downloads/
        if not os.path.exists(file_path):
            ext = 'mp3' if mode == 'mp3' else 'mp4'
            matches = glob.glob(f'downloads/*.{ext}')
            if matches:
                file_path = max(matches, key=os.path.getmtime)
            else:
                raise FileNotFoundError(
                    f"Downloaded file not found. Expected: {file_path}"
                )

    return os.path.abspath(file_path), caption
