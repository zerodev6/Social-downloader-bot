import yt_dlp
import asyncio

async def download_media(url, download_type='video'):
    """
    download_type can be 'video' or 'mp3'
    """
    ydl_opts = {
        # 1. AUTHENTICATION: Use cookies from your browser to bypass bot detection
        # Change 'chrome' to 'firefox', 'edge', or 'safari' if needed
        'cookiesfrombrowser': ('chrome',), 
        
        'quiet': False,
        'no_warnings': False,
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        
        # 2. FORMATTING: Logic for Video vs Audio
        'format': 'bestvideo+bestaudio/best' if download_type == 'video' else 'bestaudio/best',
        
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }] if download_type == 'mp3' else [],

        # 3. SPOOFING & BYPASS
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0 Safari/537.36',
        'referer': 'https://www.google.com/',
        'geo_bypass': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Extract info first to return to user
        info = ydl.extract_info(url, download=True)
        
        # Gather useful information
        metadata = {
            "title": info.get('title'),
            "author": info.get('uploader'),
            "views": info.get('view_count'),
            "duration": info.get('duration'),
            "description": info.get('description'),
            "filename": ydl.prepare_filename(info)
        }
        
        return metadata

# Example Usage
# asyncio.run(download_media("URL_HERE", download_type='video'))
