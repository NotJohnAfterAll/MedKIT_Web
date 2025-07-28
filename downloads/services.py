import os
import uuid
from typing import Dict, Any, Optional
import yt_dlp
from django.conf import settings
from django.core.files.storage import default_storage
from .models import DownloadRequest
from .youtube_bypass import YouTubeBypassHelper
import logging

logger = logging.getLogger(__name__)

class DownloadService:
    """Service for handling video downloads using yt-dlp, inspired by the original downloader.py"""
    
    def __init__(self):
        self.download_dir = os.path.join(settings.MEDIA_ROOT, 'downloads')
        os.makedirs(self.download_dir, exist_ok=True)
        self.bypass_helper = YouTubeBypassHelper()
    
    def get_direct_download_url(self, url: str, quality: str = '720p') -> Dict[str, Any]:
        """Extract direct download URL without downloading to server"""
        try:
            # Get video info with download URLs
            info = self.bypass_helper.extract_video_info_with_retry(url)
            
            if not info:
                raise Exception("No video information could be extracted")
            
            # Get the best format based on quality preference
            formats = info.get('formats', [])
            if not formats:
                raise Exception("No downloadable formats found")
            
            # Select format based on quality
            selected_format = self._select_format_for_direct_download(formats, quality)
            
            if not selected_format:
                raise Exception("No suitable format found for direct download")
            
            return {
                'title': info.get('title', 'Unknown Title'),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', 'Unknown'),
                'thumbnail': info.get('thumbnail', ''),
                'direct_url': selected_format.get('url'),
                'format_id': selected_format.get('format_id'),
                'ext': selected_format.get('ext', 'mp4'),
                'filesize': selected_format.get('filesize'),
                'filesize_approx': selected_format.get('filesize_approx'),
                'quality': selected_format.get('height', 'unknown'),
                'format_note': selected_format.get('format_note', ''),
            }
            
        except Exception as e:
            logger.error(f"Error getting direct download URL: {str(e)}")
            raise e
    
    def _select_format_for_direct_download(self, formats: list, quality: str) -> Optional[Dict]:
        """Select the best format for direct download based on quality preference"""
        if quality == 'audio':
            # Audio only - find best audio format
            audio_formats = [f for f in formats if f.get('vcodec') == 'none' and f.get('acodec') != 'none']
            if audio_formats:
                return max(audio_formats, key=lambda x: x.get('abr', 0) or 0)
        
        # Video formats
        video_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('url')]
        
        if not video_formats:
            # Fallback to any format with URL
            return next((f for f in formats if f.get('url')), None)
        
        # Quality preferences
        quality_preferences = {
            '240p': 240,
            '360p': 360,
            '480p': 480,
            '720p': 720,
            '1080p': 1080,
            'best': 9999,
            'worst': 1
        }
        
        target_height = quality_preferences.get(quality, 720)
        
        # Find format closest to target quality
        if target_height == 1:  # worst
            return min(video_formats, key=lambda x: x.get('height', 9999))
        elif target_height == 9999:  # best
            return max(video_formats, key=lambda x: x.get('height', 0))
        else:
            # Find closest to target
            return min(video_formats, key=lambda x: abs((x.get('height', 720)) - target_height))

    def get_available_formats(self, url: str) -> list:
        """Get all available video formats using iOS client with working smart selectors"""
        try:
            # Use iOS client for maximum format availability
            ios_opts = {
                'quiet': True,
                'skip_download': True,
                'format': 'all',
                'extractor_args': {
                    'youtube': {
                        'player_client': ['ios'],
                    }
                },
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ios_opts) as ydl:
                ios_info = ydl.extract_info(url, download=False)
            
            ios_formats = ios_info.get('formats', [])
            logger.info(f"iOS extraction: {len(ios_formats)} formats")
            
            # Categorize formats
            video_only = [f for f in ios_formats if f.get('vcodec', 'none') != 'none' and f.get('acodec', 'none') == 'none']
            audio_only = [f for f in ios_formats if f.get('vcodec', 'none') == 'none' and f.get('acodec', 'none') != 'none']
            video_with_audio = [f for f in ios_formats if f.get('vcodec', 'none') != 'none' and f.get('acodec', 'none') != 'none']
            
            logger.info(f"Video-only: {len(video_only)}, Audio-only: {len(audio_only)}, Combined: {len(video_with_audio)}")
            
            available_formats = []
            
            # Add existing video+audio formats if any (these work directly)
            for f in video_with_audio:
                height = f.get('height', 0)
                if height > 0:
                    quality_label = self._get_quality_label(height)
                    available_formats.append({
                        'quality': quality_label,
                        'format_id': f.get('format_id'),
                        'ext': f.get('ext', 'mp4'),
                        'filesize': f.get('filesize') or f.get('filesize_approx'),
                        'has_audio': True,
                        'video_codec': f.get('vcodec', 'unknown'),
                        'audio_codec': f.get('acodec', 'unknown'),
                        'fps': f.get('fps'),
                        'width': f.get('width'),
                        'height': f.get('height'),
                        'type': 'combined',
                        'source': 'ios',
                        'resolution': f'{f.get("width", "unknown")}x{f.get("height", "unknown")}'
                    })
            
            # Since iOS has video-only but no audio-only, we need to use working smart selectors
            # These are the selectors that ACTUALLY WORK as proven by our testing
            smart_selectors = [
                {
                    'quality': '2160p',
                    'format_id': 'bestvideo[height>=2160]+bestaudio/best[height>=2160]',
                    'height': 2160,
                    'width': 3840,
                    'min_height': 2160
                },
                {
                    'quality': '1440p', 
                    'format_id': 'bestvideo[height>=1440][height<2160]+bestaudio/best[height>=1440][height<2160]',
                    'height': 1440,
                    'width': 2560,
                    'min_height': 1440
                },
                {
                    'quality': '1080p',
                    'format_id': 'bestvideo[height>=1080][height<1440]+bestaudio/best[height>=1080][height<1440]',
                    'height': 1080,
                    'width': 1920,
                    'min_height': 1080
                },
                {
                    'quality': '720p',
                    'format_id': 'bestvideo[height>=720][height<1080]+bestaudio/best[height>=720][height<1080]',
                    'height': 720,
                    'width': 1280,
                    'min_height': 720
                },
                {
                    'quality': '480p',
                    'format_id': 'bestvideo[height>=480][height<720]+bestaudio/best[height>=480][height<720]',
                    'height': 480,
                    'width': 854,
                    'min_height': 480
                },
                {
                    'quality': '360p',
                    'format_id': 'bestvideo[height>=360][height<480]+bestaudio/best[height>=360][height<480]',
                    'height': 360,
                    'width': 640,
                    'min_height': 360
                }
            ]
            
            # Only add smart selectors for qualities we actually have video for
            video_heights = set(f.get('height', 0) for f in video_only)
            max_available_height = max(video_heights) if video_heights else 0
            
            logger.info(f"Max available video height: {max_available_height}")
            
            for selector in smart_selectors:
                # Check if we have video at this quality level and don't already have combined format
                has_video_at_height = any(f.get('height', 0) >= selector['min_height'] for f in video_only)
                existing_quality = any(fmt['quality'] == selector['quality'] for fmt in available_formats)
                
                if has_video_at_height and not existing_quality:
                    available_formats.append({
                        'quality': selector['quality'],
                        'label': f"{selector['quality']} - {selector['width']}x{selector['height']}",
                        'format_id': selector['format_id'],
                        'ext': 'mp4',
                        'filesize': None,  # Will be determined at download time
                        'has_audio': True,
                        'video_codec': 'auto',
                        'audio_codec': 'auto',
                        'fps': None,
                        'width': selector['width'],
                        'height': selector['height'],
                        'type': 'ios_smart_selector',
                        'source': 'ios',
                        'resolution': f"{selector['width']}x{selector['height']}"
                    })
                    logger.info(f"Added working iOS smart selector: {selector['quality']} - {selector['format_id']}")
            
            # Add general fallback if no high quality formats were added
            if not any(fmt.get('height', 0) >= 720 for fmt in available_formats):
                available_formats.append({
                    'quality': 'best', 
                    'label': 'Best Available Quality',
                    'format_id': 'best[height<=1080]',
                    'ext': 'mp4',
                    'has_audio': True,
                    'video_codec': 'auto',
                    'audio_codec': 'auto',
                    'height': 1080,
                    'width': 1920,
                    'type': 'smart_selector',
                    'source': 'fallback',
                    'resolution': '1920x1080',
                    'description': 'Best available quality'
                })
                logger.info("Added general fallback selector")
            
            # Add audio-only option with preference for m4a over webm
            if audio_only:
                best_audio = max(audio_only, key=lambda x: x.get('abr', 0))
                available_formats.append({
                    'quality': 'audio',
                    'label': f"Audio Only - {best_audio.get('ext', 'm4a').upper()}",
                    'format_id': best_audio.get('format_id'),
                    'ext': best_audio.get('ext', 'm4a'),
                    'filesize': best_audio.get('filesize') or best_audio.get('filesize_approx'),
                    'has_audio': True,
                    'video_codec': 'none',
                    'audio_codec': best_audio.get('acodec', 'unknown'),
                    'abr': best_audio.get('abr'),
                    'type': 'audio_only',
                    'source': 'ios'
                })
            else:
                # Add smart audio selector as fallback (prefer m4a format)
                available_formats.append({
                    'quality': 'audio',
                    'label': 'Audio Only - M4A',
                    'format_id': 'bestaudio[ext=m4a]/bestaudio',  # Prefer m4a over webm
                    'ext': 'm4a',
                    'filesize': None,  # Will be determined at download time
                    'has_audio': True,
                    'video_codec': 'none',
                    'audio_codec': 'auto',
                    'type': 'audio_smart_selector',
                    'source': 'ios',
                    'description': 'Best audio quality (m4a preferred)'
                })
            
            # Sort by quality (highest first)
            quality_priority = {'2160p': 8, '1440p': 7, '1080p': 6, '720p': 5, '480p': 4, '360p': 3, '240p': 2, '144p': 1, 'audio': 0}
            available_formats.sort(key=lambda x: quality_priority.get(x['quality'], 0), reverse=True)
            
            logger.info(f"Final available formats: {len(available_formats)}")
            return available_formats
            
        except Exception as e:
            logger.error(f"Error getting available formats: {str(e)}")
            raise
    
    def get_video_info(self, url: str) -> Dict[str, Any]:
        """Get video information and available formats for frontend display"""
        try:
            info = self.bypass_helper.extract_video_info_with_retry(url)
            
            if not info:
                raise Exception("No video information could be extracted")
            
            # Get available formats
            available_formats = self.get_available_formats(url)
            
            return {
                'title': info.get('title', 'Unknown Title'),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', 'Unknown'),
                'thumbnail': info.get('thumbnail', ''),
                'view_count': info.get('view_count', 0),
                'upload_date': info.get('upload_date', ''),
                'description': info.get('description', '')[:500] if info.get('description') else '',
                'available_formats': available_formats,
                # Add quick select options
                'quick_select': {
                    'best_quality': available_formats[0]['format_id'] if available_formats else None,
                    'audio_only': next((fmt['format_id'] for fmt in available_formats if fmt['quality'] == 'audio'), None),
                    'recommended': next((fmt['format_id'] for fmt in available_formats if fmt['quality'] in ['1080p', '720p']), available_formats[0]['format_id'] if available_formats else None)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting video info: {str(e)}")
            raise
    
    def get_direct_download_url_by_format(self, url: str, format_id: str) -> Dict[str, Any]:
        """Extract direct download URL for a specific format ID using iOS client approach"""
        try:
            # For REAL combined formats (video_id+audio_id) - these should work!
            if '+' in format_id and not 'bestvideo' in format_id:
                # This is a real combined format like "270+234"
                ydl_opts = {
                    'quiet': True,
                    'skip_download': True,
                    'format': format_id,
                    'merge_output_format': 'mp4',
                    'prefer_ffmpeg': True,
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['ios'],  # iOS client for high quality
                        }
                    },
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                return {
                    'title': info.get('title', 'Unknown Title'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'thumbnail': info.get('thumbnail', ''),
                    'direct_url': None,  # Combined formats need merging
                    'format_id': format_id,
                    'ext': 'mp4',
                    'filesize': info.get('filesize'),
                    'filesize_approx': info.get('filesize_approx'),
                    'resolution': f"{info.get('width', 0)}x{info.get('height', 0)}",
                    'width': info.get('width'),
                    'height': info.get('height'),
                    'fps': info.get('fps'),
                    'vcodec': info.get('vcodec'),
                    'acodec': info.get('acodec'),
                    'is_real_combined': True
                }
            else:
                # Regular format, use iOS client for better compatibility
                ydl_opts = {
                    'quiet': True,
                    'skip_download': True,
                    'format': format_id,
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['ios'],
                        }
                    },
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                
                return {
                    'title': info.get('title', 'Unknown Title'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'thumbnail': info.get('thumbnail', ''),
                    'direct_url': info.get('url'),  # Single format might have direct URL
                    'format_id': format_id,
                    'ext': info.get('ext', 'mp4'),
                    'filesize': info.get('filesize'),
                    'filesize_approx': info.get('filesize_approx'),
                    'resolution': f"{info.get('width', 0)}x{info.get('height', 0)}",
                    'width': info.get('width'),
                    'height': info.get('height'),
                    'fps': info.get('fps'),
                    'vcodec': info.get('vcodec'),
                    'acodec': info.get('acodec'),
                    'is_real_combined': False
                }
            
        except Exception as e:
            logger.error(f"Error getting direct download URL by format: {str(e)}")
            raise
    
    def _find_best_format_for_quality(self, formats: list, quality: str) -> Optional[Dict]:
        """Find the best format for a specific quality"""
        height_map = {
            '144p': 144, '240p': 240, '360p': 360, '480p': 480,
            '720p': 720, '1080p': 1080, '1440p': 1440, '2160p': 2160
        }
        
        target_height = height_map.get(quality)
        if not target_height:
            return None
        
        # First try to find formats with both video and audio
        video_audio_formats = [
            f for f in formats 
            if f.get('height') == target_height 
            and f.get('vcodec', 'none') != 'none' 
            and f.get('acodec', 'none') != 'none'
        ]
        
        if video_audio_formats:
            # Return the one with best overall quality
            return max(video_audio_formats, key=lambda x: x.get('tbr', 0))
        
        # If no combined format, find video-only format
        video_only_formats = [
            f for f in formats 
            if f.get('height') == target_height 
            and f.get('vcodec', 'none') != 'none'
        ]
        
        if video_only_formats:
            return max(video_only_formats, key=lambda x: x.get('vbr', 0))
        
        return None
    
    def _get_quality_label(self, height: int) -> str:
        """Convert height to quality label"""
        if height >= 2160:
            return '2160p'
        elif height >= 1440:
            return '1440p'
        elif height >= 1080:
            return '1080p'
        elif height >= 720:
            return '720p'
        elif height >= 480:
            return '480p'
        elif height >= 360:
            return '360p'
        elif height >= 240:
            return '240p'
        else:
            return '144p'
    
    def _select_best_format(self, formats: list) -> Optional[Dict]:
        """Select the best format from a list of formats with same resolution"""
        if not formats:
            return None
        
        # Prefer formats with audio
        audio_formats = [f for f in formats if f.get('acodec', 'none') != 'none']
        if audio_formats:
            # Return the one with best total bitrate
            return max(audio_formats, key=lambda x: x.get('tbr', 0))
        
        # If no audio formats, return best video-only format
        return max(formats, key=lambda x: x.get('vbr', 0))
    
    def _get_available_formats(self, info: Dict) -> list:
        """Get available video formats, inspired by videoResSelector"""
        formats = info.get('formats', [])
        available_formats = []
        
        for f in formats:
            if (f.get('resolution') != 'audio only' and 
                ('vp' in str(f.get('vcodec', '')) or 'avc1' in str(f.get('vcodec', ''))) and
                f.get('fps', 0) > 23 and 
                f.get('ext') == "mp4"):
                
                available_formats.append({
                    'format_id': f.get('format_id'),
                    'resolution': f.get('resolution'),
                    'fps': f.get('fps'),
                    'bitrate': f.get('tbr', 0),
                    'filesize': f.get('filesize', 0)
                })
        
        return sorted(available_formats, key=lambda x: x.get('bitrate', 0), reverse=True)
    
    def get_best_format(self, url: str) -> str:
        """Get best quality format ID, inspired by videoBestQualitySelector"""
        try:
            ydl_opts = {
                'quiet': True,
                'skip_download': True,
                'noplaylist': True,
                # Anti-bot detection measures
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'referer': 'https://www.youtube.com/',
                'headers': {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                },
                'nocheckcertificate': True,
                'ignoreerrors': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
            formats = info.get('formats', [])
            
            # Find best video format
            best_video = None
            for f in formats:
                if (f.get('resolution') != 'audio only' and
                    ('vp' in str(f.get('vcodec', '')) or 'avc1' in str(f.get('vcodec', ''))) and
                    f.get('fps', 0) > 23 and
                    f.get('ext') == "mp4" and
                    len(str(f.get('format_id', ''))) == 3):
                    best_video = f.get('format_id')
                    break
            
            # Find best audio format
            best_audio = self._get_best_audio_format(formats)
            
            if best_video and best_audio:
                return f"{best_video}+{best_audio}"
            elif best_video:
                return best_video
            else:
                return "best"
                
        except Exception as e:
            logger.error(f"Error getting best format: {str(e)}")
            return "best"
    
    def _get_best_audio_format(self, formats: list) -> Optional[str]:
        """Get best audio format, inspired by audioQtySelector"""
        multipletracks = ""
        
        # Check for multiple tracks
        for f in formats:
            if len(str(f.get('format_id', ''))) == 5:
                multipletracks = "original"
                break
        
        # Find best audio format
        for f in formats:
            if (f.get('resolution') == 'audio only' and
                f.get('ext') == "m4a" and
                multipletracks in str(f.get('format_note', '')) and
                len(str(f.get('format_id', ''))) <= 5):
                return f.get('format_id')
        
        return None
    
    def download_video(self, download_request: DownloadRequest) -> str:
        """Download video with progress tracking - ULTRA FAST mode"""
        try:
            # Generate unique filename using the download request ID
            safe_title = "".join(c for c in download_request.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = f"{download_request.id}_{safe_title}.%(ext)s"
            filepath = os.path.join(self.download_dir, filename)
            
            # Progress hook for real-time updates
            def progress_hook(d):
                if d['status'] == 'downloading':
                    if 'total_bytes' in d:
                        progress = int((d['downloaded_bytes'] / d['total_bytes']) * 100)
                    elif 'total_bytes_estimate' in d:
                        progress = int((d['downloaded_bytes'] / d['total_bytes_estimate']) * 100)
                    else:
                        progress = 0
                    
                    # Update progress in database
                    DownloadRequest.objects.filter(id=download_request.id).update(
                        progress=min(progress, 99),  # Keep at 99% until complete
                        status='processing'
                    )
                elif d['status'] == 'finished':
                    DownloadRequest.objects.filter(id=download_request.id).update(
                        progress=100,
                        status='completed'
                    )
            
            # ULTRA SPEED OPTIMIZATION: Direct format selection without info extraction
            quality = download_request.quality_requested
            
            if quality == 'audio':
                # Audio only - fastest
                format_selector = "bestaudio/best[acodec!*=none]"
            elif quality in ['240p']:
                # Very fast - prefer small files but be flexible
                format_selector = "worst[height<=360]/worst[ext=mp4]/worst[ext=webm]/worst"
            elif quality in ['360p']:
                # Fast - small files but flexible
                format_selector = "worst[height<=480]/worst[ext=mp4]/worst[ext=webm]/worst"
            else:
                # Default to fastest available
                format_selector = "worst"
            
            # ULTRA FAST yt-dlp options - minimal processing
            ydl_opts = {
                'outtmpl': filepath,
                'noplaylist': True,
                'format': format_selector,
                'progress_hooks': [progress_hook],
                'quiet': True,
                'no_warnings': True,
                # EXTREME SPEED OPTIMIZATIONS
                'skip_download': False,
                'extract_flat': False,
                'writeinfojson': False,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'writedescription': False,
                'writethumbnail': False,
                'concurrent_fragment_downloads': 8,  # More parallel downloads
                'fragment_retries': 0,  # No retries for speed
                'retries': 0,  # No retries for speed
                'file_access_retries': 0,
                'skip_unavailable_fragments': True,
                'abort_on_unavailable_fragment': False,
                'ignore_no_formats_error': True,
                # Minimal headers for speed
                'user_agent': 'Mozilla/5.0',
                'nocheckcertificate': True,
                'ignoreerrors': True,
            }
            
            # Update status to processing immediately
            download_request.status = 'processing'
            download_request.progress = 1
            download_request.save()
            
            # Use YouTube bypass helper with anti-detection measures
            custom_opts = {
                'outtmpl': filepath,
                'noplaylist': True,
                'format': format_selector,
                'progress_hooks': [progress_hook],
                'concurrent_fragment_downloads': 8,
                'fragment_retries': 0,
                'retries': 0,
                'ignoreerrors': True,
            }
            
            # Use bypass helper for all downloads to avoid bot detection
            success = self.bypass_helper.download_with_fallback(download_request.url, custom_opts)
            
            if not success:
                raise Exception("All download strategies failed")
            
            # Find the actual downloaded file with broader extension search
            base_path = filepath.replace('.%(ext)s', '')
            possible_extensions = ['.mp4', '.webm', '.mkv', '.m4a', '.mp3', '.wav', '.ogg', '.flac']
            
            final_path = None
            for ext in possible_extensions:
                if os.path.exists(base_path + ext):
                    final_path = base_path + ext
                    break
            
            if not final_path:
                # Try finding any file with the base name
                import glob
                pattern = base_path + '*'
                files = glob.glob(pattern)
                if files:
                    final_path = files[0]
                else:
                    raise Exception("Downloaded file not found")
            
            # Update file path and mark as completed
            download_request.file_path = os.path.relpath(final_path, settings.MEDIA_ROOT)
            download_request.file_size = os.path.getsize(final_path)
            download_request.status = 'completed'
            download_request.progress = 100
            download_request.save()
            
            return final_path
            
        except Exception as e:
            logger.error(f"Download failed: {str(e)}")
            download_request.status = 'failed'
            download_request.error_message = str(e)
            download_request.save()
            raise e
    
    def download_audio(self, download_request: DownloadRequest) -> str:
        """Download audio only, inspired by audioDownload"""
        try:
            # Generate unique filename using the download request ID
            safe_title = "".join(c for c in download_request.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = f"{download_request.id}_{safe_title}.%(ext)s"
            filepath = os.path.join(self.download_dir, filename)
            
            # Progress hook
            def progress_hook(d):
                if d['status'] == 'downloading':
                    if 'total_bytes' in d:
                        progress = int((d['downloaded_bytes'] / d['total_bytes']) * 100)
                    elif 'total_bytes_estimate' in d:
                        progress = int((d['downloaded_bytes'] / d['total_bytes_estimate']) * 100)
                    else:
                        progress = 0
                    
                    DownloadRequest.objects.filter(id=download_request.id).update(
                        progress=min(progress, 99),
                        status='processing'
                    )
                elif d['status'] == 'finished':
                    DownloadRequest.objects.filter(id=download_request.id).update(
                        progress=100,
                        status='completed'
                    )
            
            # Get best audio format
            info_opts = {
                'quiet': True, 
                'skip_download': True,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'nocheckcertificate': True,
                'ignoreerrors': True,
            }
            info = yt_dlp.YoutubeDL(info_opts).extract_info(
                download_request.url, download=False
            )
            audio_format = self._get_best_audio_format(info.get('formats', []))
            
            ydl_opts = {
                'outtmpl': filepath,
                'format': audio_format or 'bestaudio',
                'progress_hooks': [progress_hook],
                'quiet': True,
                'no_warnings': True,
                # Anti-bot detection measures
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'referer': 'https://www.youtube.com/',
                'headers': {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                },
                'nocheckcertificate': True,
                'ignoreerrors': True,
            }
            
            download_request.status = 'processing'
            download_request.save()
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([download_request.url])
            
            # Find the actual downloaded file
            base_path = filepath.replace('.%(ext)s', '')
            for ext in ['.m4a', '.mp3', '.webm', '.ogg']:
                if os.path.exists(base_path + ext):
                    final_path = base_path + ext
                    break
            else:
                raise Exception("Downloaded file not found")
            
            download_request.file_path = os.path.relpath(final_path, settings.MEDIA_ROOT)
            download_request.file_size = os.path.getsize(final_path)
            download_request.status = 'completed'
            download_request.progress = 100
            download_request.save()
            
            return final_path
            
        except Exception as e:
            logger.error(f"Audio download failed: {str(e)}")
            download_request.status = 'failed'
            download_request.error_message = str(e)
            download_request.save()
            raise e
