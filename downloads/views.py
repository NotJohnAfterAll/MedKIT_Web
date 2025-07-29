from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.decorators import action
from django.http import HttpResponse, Http404, StreamingHttpResponse
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from urllib.parse import urlparse
import os
import logging
import requests
from .models import DownloadRequest, DownloadHistory
from .serializers import DownloadRequestSerializer, DownloadCreateSerializer, DownloadHistorySerializer
from .tasks import process_download_task  # Import the actual task
from .services import DownloadService  # Import the download service
from core.views import log_activity

logger = logging.getLogger(__name__)


class DownloadRequestViewSet(ModelViewSet):
    """ViewSet for download requests"""
    serializer_class = DownloadRequestSerializer
    permission_classes = [permissions.AllowAny]  # Allow anonymous downloads

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return DownloadRequest.objects.filter(user=self.request.user)
        else:
            # For anonymous users, return empty queryset for list view
            if self.action == 'list':
                return DownloadRequest.objects.none()
            # But allow individual downloads to be viewed by ID
            return DownloadRequest.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return DownloadCreateSerializer
        return DownloadRequestSerializer

    def create(self, request, *args, **kwargs):
        """Create a new download request"""
        # Check if user can make request
        if request.user.is_authenticated and not request.user.can_make_request():
            return Response(
                {'error': 'Daily request limit exceeded'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Extract domain for analytics
            domain = urlparse(serializer.validated_data['url']).netloc
            if domain.startswith('www.'):
                domain = domain[4:]

            # ULTRA SPEED OPTIMIZATION: Defer ALL slow operations
            # Don't call DownloadService at all during creation
            title = 'Video Download'  # Always use generic title for speed

            # Create download request
            download_request = serializer.save(
                user=request.user if request.user.is_authenticated else None,
                title=title
            )

            # Increment user request count
            if request.user.is_authenticated:
                request.user.increment_request_count()

            # Log activity
            log_activity(
                request.user if request.user.is_authenticated else None,
                'download',
                f'Download requested: {download_request.url}',
                request
            )

            # PREFERRED: Use Celery for production-grade task processing
            try:
                # Try Celery first (production recommended)
                from downloads.tasks import process_download_task
                process_download_task.delay(str(download_request.id))
                logger.info(f"Started Celery task for {download_request.id}")
            except Exception as e:
                logger.warning(f"Celery unavailable ({str(e)}), using fast synchronous fallback")
                # Fast fallback when Celery not available (development)
                try:
                    from core.sync_tasks import SyncTaskProcessor
                    import threading
                    # Run in background thread to avoid blocking the API response
                    thread = threading.Thread(
                        target=SyncTaskProcessor.process_download,
                        args=(str(download_request.id),)
                    )
                    thread.daemon = True
                    thread.start()
                    logger.info(f"Started synchronous download for {download_request.id}")
                except Exception as sync_error:
                    logger.error(f"Both Celery and sync processing failed: {str(sync_error)}")
                    download_request.status = 'failed'
                    download_request.error_message = f"Processing unavailable: {str(sync_error)}"
                    download_request.save()

            return Response(
                DownloadRequestSerializer(download_request).data,
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a download request"""
        download_request = self.get_object()
        
        if download_request.status in ['pending', 'processing']:
            download_request.status = 'cancelled'
            download_request.save()
            
            return Response({'message': 'Download cancelled'})
        
        return Response(
            {'error': 'Cannot cancel download in current status'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=['get'])
    def download_file(self, request, pk=None):
        """Download the completed file"""
        download_request = self.get_object()
        
        if download_request.status != 'completed' or not download_request.file_path:
            raise Http404("File not available")

        try:
            # Construct full file path
            if hasattr(download_request.file_path, 'path'):
                # If it's a FileField
                file_path = download_request.file_path.path
                filename = os.path.basename(download_request.file_path.name)
            else:
                # If it's stored as a string path
                file_path = os.path.join(settings.MEDIA_ROOT, str(download_request.file_path))
                filename = os.path.basename(str(download_request.file_path))
            
            with open(file_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/octet-stream')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
        except FileNotFoundError:
            raise Http404("File not found")

    @action(detail=True, methods=['delete'])
    def delete_file(self, request, pk=None):
        """Delete the downloaded file"""
        download_request = self.get_object()
        
        # Check if user owns this download
        if request.user != download_request.user and not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        download_request.delete_file()
        download_request.delete()
        
        log_activity(
            request.user,
            'delete',
            f'Deleted download: {download_request.title or download_request.url}',
            request
        )
        
        return Response({'message': 'File deleted successfully'})


class DownloadHistoryViewSet(ReadOnlyModelViewSet):
    """ViewSet for download history (admin only)"""
    serializer_class = DownloadHistorySerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = DownloadHistory.objects.all()


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def download_stats(request):
    """Get download statistics"""
    # Get counts by status
    stats = {
        'pending': DownloadRequest.objects.filter(status='pending').count(),
        'processing': DownloadRequest.objects.filter(status='processing').count(),
        'completed': DownloadRequest.objects.filter(status='completed').count(),
        'failed': DownloadRequest.objects.filter(status='failed').count(),
        'cancelled': DownloadRequest.objects.filter(status='cancelled').count(),
    }
    
    # Get popular domains
    from django.db import models
    popular_domains = DownloadHistory.objects.values('domain').annotate(
        count=models.Count('domain')
    ).order_by('-count')[:5]
    
    return Response({
        'status_counts': stats,
        'popular_domains': list(popular_domains)
    })


@api_view(['GET', 'POST'])
@permission_classes([permissions.AllowAny])
def get_direct_urls(request):
    """Get direct download URLs for client-side downloading - bypasses server bandwidth entirely"""
    if request.method == 'GET':
        url = request.GET.get('url')
        format_id = request.GET.get('format_id')
    elif request.method == 'POST':
        url = request.data.get('url')
        format_id = request.data.get('format_id')
        
    if not url:
        return Response(
            {'error': 'URL is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Use TV client to get direct URLs for downloadable files
        # TV client has excellent format availability including audio-only formats like 140
        tv_opts = {
            'quiet': True,
            'skip_download': True,
            'format': format_id or 'bestaudio[ext=m4a]/bestaudio[ext=aac]/bestaudio[acodec!=none]/bestaudio',  # Prioritize M4A audio for direct downloads
            'extractor_args': {
                'youtube': {
                    'player_client': ['tv'],  # TV client for best format availability including M4A
                }
            },
            # Prefer downloadable formats over streaming
            'prefer_free_formats': False,  # We want quality, not just free formats
            'format_sort': ['ext:m4a', 'ext:aac', 'ext:mp3', 'acodec', '+size', '+br', '+res', '+fps', 'proto:https', 'proto:http'],
        }
        
        import yt_dlp
        with yt_dlp.YoutubeDL(tv_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        
        title = info.get('title', 'Unknown Title')
        
        # Check for direct URLs
        direct_url = info.get('url')
        requested_formats = info.get('requested_formats', [])
        
        if direct_url:
            # Single direct URL - but we need to proxy it due to CORS
            # Create a proxy download URL through our backend
            import urllib.parse
            
            # Encode the direct URL and other parameters for our proxy endpoint
            proxy_params = {
                'direct_url': direct_url,
                'filename': f"{title}.{info.get('ext', 'mp4')}",
                'ext': info.get('ext', 'mp4'),
                'filesize': info.get('filesize') or info.get('filesize_approx', 0)
            }
            
            # Create proxy URL that will download via our backend
            proxy_url = f"/api/downloads/proxy-download/?{urllib.parse.urlencode(proxy_params)}"
            
            return Response({
                'type': 'single_url',
                'direct_urls': [
                    {
                        'type': 'single',
                        'url': proxy_url,  # Use our proxy URL instead of direct googlevideo URL
                        'filename': f"{title}.{info.get('ext', 'mp4')}",
                        'resolution': f"{info.get('width', 'unknown')}x{info.get('height', 'unknown')}",
                        'ext': info.get('ext', 'mp4'),
                        'filesize': info.get('filesize') or info.get('filesize_approx'),
                        'original_url': direct_url  # Keep the original for debugging
                    }
                ],
                'title': title,
                'message': 'Proxied download URL - bypasses CORS via backend streaming'
            })
            
        elif requested_formats:
            # Multiple URLs (video + audio that need merging)
            direct_urls = []
            total_filesize = 0
            
            for fmt in requested_formats:
                fmt_url = fmt.get('url')
                if fmt_url:
                    filesize = fmt.get('filesize') or fmt.get('filesize_approx') or 0
                    total_filesize += filesize
                    
                    direct_urls.append({
                        'type': 'video' if fmt.get('vcodec', 'none') != 'none' else 'audio',
                        'url': fmt_url,
                        'format_id': fmt.get('format_id'),
                        'ext': fmt.get('ext', 'mp4'),
                        'resolution': f"{fmt.get('width', 'N/A')}x{fmt.get('height', 'N/A')}" if fmt.get('width') else 'audio',
                        'codec': f"{fmt.get('vcodec', 'none')}/{fmt.get('acodec', 'none')}",
                        'filesize': filesize
                    })
            
            if direct_urls:
                return Response({
                    'type': 'multiple_urls',
                    'direct_urls': direct_urls,
                    'title': title,
                    'message': f'Found {len(direct_urls)} direct URLs - client can download directly and merge',
                    'needs_merging': True,
                    'total_filesize': total_filesize,
                    'instructions': {
                        'step1': 'Download video and audio streams in parallel',
                        'step2': 'Use ffmpeg to merge: ffmpeg -i video.mp4 -i audio.m4a -c copy output.mp4',
                        'benefit': 'Bypasses server bandwidth - direct download from YouTube servers'
                    }
                })
        
        # Fallback if no direct URLs
        return Response({
            'error': 'No direct URLs available for this format',
            'message': 'This format requires server-side processing. Use /stream/ endpoint instead.',
            'fallback_suggestion': 'Try with format_id parameter or use server streaming mode'
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Direct URL extraction failed: {str(e)}")
        return Response({
            'error': f'Direct URL extraction failed: {str(e)}',
            'fallback_suggestion': 'Use server streaming mode via /stream/ endpoint'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST'])
@permission_classes([permissions.AllowAny])
def stream_download(request):
    """Stream download directly to user using yt-dlp with enhanced progress tracking"""
    # Handle both GET and POST requests
    if request.method == 'GET':
        url = request.GET.get('url')
        quality = request.GET.get('quality', '720p')
        format_id = request.GET.get('format_id')
        test_mode = request.GET.get('test', 'false').lower() == 'true'
        download_id = request.GET.get('download_id')
        
        # Fix URL encoding issue where + becomes space
        if format_id and ' ' in format_id:
            format_id = format_id.replace(' ', '+')
            logger.info(f"Fixed format_id from URL encoding: {format_id}")
            
    else:  # POST
        url = request.data.get('url')
        quality = request.data.get('quality', '720p')
        format_id = request.data.get('format_id')
        test_mode = request.data.get('test', False)
        download_id = request.data.get('download_id')
        
        # DEBUG: Print what we received - CLEAN
        logger.info(f"Stream download request - URL: {url}, Format: {format_id}")
    
    if not url:
        return Response({'error': 'URL is required'}, status=400)
    
    try:
        import tempfile
        import os
        from .youtube_bypass import YouTubeBypassHelper
        from django.http import FileResponse
        from django.core.cache import cache
        
        # Use our bypass helper
        bypass_helper = YouTubeBypassHelper()
        
        # Create a temporary directory for this download
        temp_dir = tempfile.mkdtemp()
        
        # Progress tracking setup - use dedicated download progress key
        progress_key = f"download_progress_{download_id}" if download_id else None
        
        # Set initial progress and clear any existing progress data
        if progress_key:
            cache.delete(progress_key)
            progress_data = {
                'progress': 0,
                'message': "Starting download...",
                'status': 'downloading'
            }
            cache.set(progress_key, progress_data, 300)  # Cache for 5 minutes
        
        def update_download_progress(percentage, message=""):
            """Update download progress in cache"""
            if progress_key:
                progress_data = {
                    'progress': percentage,
                    'message': message,
                    'status': 'downloading'
                }
                cache.set(progress_key, progress_data, 300)  # Cache for 5 minutes
        
        # Define progress hook for yt-dlp
        def progress_hook(d):
            # Check for cancellation first
            if progress_key:
                cancel_key = f"download_cancel_{download_id}"
                is_cancelled = cache.get(cancel_key)
                if is_cancelled:
                    logger.info(f"Download {download_id} cancelled during progress hook")
                    # This will cause yt-dlp to stop - we raise an exception to interrupt
                    raise Exception("Download cancelled by user")
            
            if d['status'] == 'downloading' and progress_key:
                downloaded = d.get('downloaded_bytes', 0)
                total_bytes = d.get('total_bytes', 0)
                total_estimate = d.get('total_bytes_estimate', 0)
                
                if total_estimate > 0 and total_estimate < 50000:  # Less than 50KB is likely metadata
                    return
                
                if total_bytes > 0:
                    progress = int((downloaded / total_bytes) * 100)
                    speed = d.get('speed', 0)
                    if speed:
                        speed_mb = speed / 1024 / 1024
                        update_download_progress(progress, f"Downloading... {speed_mb:.1f} MB/s")
                    else:
                        update_download_progress(progress, "Downloading...")
                elif total_estimate > 0:
                    progress = int((downloaded / total_estimate) * 100)
                    update_download_progress(progress, "Downloading...")
                else:
                    # If no size info, report unknown progress
                    update_download_progress(0, "Downloading... (size unknown)")
            elif d['status'] == 'finished' and progress_key:
                update_download_progress(95, "Processing...")
        
        try:
            # Get enhanced yt-dlp options with anti-detection
            ydl_opts = bypass_helper.get_base_ydl_opts(for_download=True)
            
            # Check if this is a combined format (video+audio) 
            # Detect format type correctly
            # Smart selectors contain special characters like [, ], <, >, =
            # Combined formats are simple like 137+251 (only digits and +)
            is_smart_selector = format_id and any(char in format_id for char in ['[', ']', '<', '>', '='])
            is_combined_format = ('+' in (format_id or '')) and not is_smart_selector
            
            # Don't set format here - we'll set it after validation with proper quoting
            
            # Add download-specific options with proper filename template and iOS client force
            ydl_opts.update({
                'outtmpl': os.path.join(temp_dir, '%(title).100s.%(ext)s'),  # Use actual title
                'retries': 3,
                'fragment_retries': 3,
                'skip_unavailable_fragments': True,
                'writeinfojson': False,
                'writethumbnail': False,
                'writesubtitles': False,
                'progress_hooks': [progress_hook],  # Add progress tracking
                # FORCE iOS client for downloads - this is critical for our smart selectors to work
                'extractor_args': {
                    'youtube': {
                        'player_client': ['ios'],  # iOS client ONLY for downloads since our smart selectors depend on it
                    }
                },
            })
            
            # If test mode, just return info without downloading
            if test_mode:
                ydl_opts['skip_download'] = True
                
            # Import yt_dlp here to use updated options
            import yt_dlp
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info first with our enhanced bypass
                logger.info(f"Extracting info for URL: {url}")
                info = bypass_helper.extract_video_info_with_retry(url)
                
                if not info:
                    raise Exception("Could not extract video information - YouTube may be blocking requests")
                
                title = info.get('title', 'Unknown Title')
                duration = info.get('duration', 0)
                
                # Validate format availability before downloading
                available_formats = info.get('formats', [])
                format_available = False
                actual_format_to_use = format_id
                
                if is_smart_selector:
                    # Smart selector formats - these always work, let yt-dlp handle them
                    format_available = True
                    actual_format_to_use = format_id
                    logger.info(f"Using smart selector format: {format_id}")
                    
                elif is_combined_format:
                    # For combined formats like 137+251, check if both parts exist in RAW formats
                    video_id, audio_id = format_id.split('+')
                    video_exists = any(f.get('format_id') == video_id for f in available_formats)
                    audio_exists = any(f.get('format_id') == audio_id for f in available_formats)
                    
                    if video_exists and audio_exists:
                        format_available = True
                        logger.info(f"Combined format validated: {video_id}+{audio_id}")
                    else:
                        logger.warning(f"Combined format {format_id} not available: video_exists={video_exists}, audio_exists={audio_exists}")
                        # Fall back to smart selector that works with any available formats
                        actual_format_to_use = 'bestvideo[height<=1080]+bestaudio/best'
                        format_available = True
                        logger.info(f"Falling back to smart selector: {actual_format_to_use}")
                        
                elif format_id and format_id not in ['best', 'worst']:
                    # Simple format ID - check if it exists in RAW formats
                    format_available = any(f.get('format_id') == format_id for f in available_formats)
                    if not format_available:
                        logger.warning(f"Format {format_id} not available in raw formats, using smart fallback")
                        actual_format_to_use = 'best[height<=720]/best'
                        format_available = True
                else:
                    # Default formats like 'best' or 'worst' - these always work
                    format_available = True
                    actual_format_to_use = format_id
                
                # Update ydl_opts with the validated format (with proper quoting)
                if is_smart_selector or (actual_format_to_use and any(char in actual_format_to_use for char in ['[', ']', '<', '>', '='])):
                    # Smart selectors - these work without quotes and may need merging
                    ydl_opts.update({
                        'format': actual_format_to_use,  # Smart selectors work without quotes
                        'merge_output_format': 'mp4',    # Smart selectors may need merging
                        'prefer_ffmpeg': True,
                    })
                    logger.info(f"Using smart selector: {actual_format_to_use}")
                elif is_combined_format and '+' in actual_format_to_use:
                    # For combined formats like 137+251, try without quotes first
                    ydl_opts.update({
                        'format': actual_format_to_use,  # Try without quotes first
                        'merge_output_format': 'mp4',
                        'prefer_ffmpeg': True,
                    })
                    logger.info(f"Using combined format: {actual_format_to_use}")
                else:
                    # Simple formats don't need quotes or special handling
                    ydl_opts['format'] = actual_format_to_use
                    logger.info(f"Using simple format: {actual_format_to_use}")
                
                logger.info(f"Final ydl format setting: {ydl_opts['format']}")
                
                # Create proper filename using actual video title
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_title = safe_title[:100]  # Limit length
                
                # Determine file extension based on format
                if is_combined_format or actual_format_to_use == 'best':
                    ext = 'mp4'  # Combined/merged formats are always mp4
                else:
                    # Get extension from the specific format
                    selected_format = None
                    for fmt in available_formats:
                        if fmt.get('format_id') == actual_format_to_use:
                            selected_format = fmt
                            break
                    ext = selected_format.get('ext', 'mp4') if selected_format else 'mp4'
                
                filename = f"{safe_title}.{ext}"
                
                # Update ydl_opts with the proper filename template using actual title
                ydl_opts['outtmpl'] = os.path.join(temp_dir, f"{safe_title}.%(ext)s")
                
                if test_mode:
                    return Response({
                        'status': 'ready',
                        'filename': filename,
                        'title': title,
                        'duration': duration,
                        'format': ext,
                        'validated_format': actual_format_to_use,
                        'original_format': format_id
                    })
                
                # Download the file with iOS client directly - no retry logic that might override our client
                logger.info(f"Starting iOS client download for: {title}")
                logger.info(f"Using format: {actual_format_to_use}")
                
                # Initialize progress
                if progress_key:
                    update_download_progress(5, "Initializing download...")
                
                # Check for cancellation before starting download
                if progress_key:
                    cancel_key = f"download_cancel_{download_id}"
                    is_cancelled = cache.get(cancel_key)
                    if is_cancelled:
                        logger.info(f"Download {download_id} cancelled before starting")
                        raise Exception("Download cancelled by user")
                
                try:
                    # Use yt-dlp directly with iOS client
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        download_result = ydl.download([url])
                        logger.info(f"iOS client download successful: {download_result}")
                        
                except Exception as download_error:
                    logger.error(f"iOS client download failed: {download_error}")
                    
                    # Try one more time with simpler format
                    logger.info("Attempting fallback with iOS client and simpler format")
                    try:
                        fallback_opts = ydl_opts.copy()
                        fallback_opts['format'] = 'best[height<=1080]/best'  # Simpler but still iOS
                        with yt_dlp.YoutubeDL(fallback_opts) as ydl_fallback:
                            download_result = ydl_fallback.download([url])
                            logger.info("iOS client fallback succeeded")
                    except Exception as final_error:
                        logger.error(f"iOS client fallback also failed: {final_error}")
                        
                        # List available formats for debugging
                        logger.info("Available formats for debugging:")
                        for fmt in available_formats:
                            logger.info(f"  - {fmt.get('format_id')}: {fmt.get('ext')} {fmt.get('height', 'audio')}p")
                        
                        raise Exception(f"All iOS download attempts failed. Original error: {download_error}")
                
                # Update progress after download completes
                if progress_key:
                    update_download_progress(97, "Finalizing...")
                
                # Find the downloaded file
                try:
                    temp_files = os.listdir(temp_dir)
                    downloaded_files = [f for f in temp_files if os.path.isfile(os.path.join(temp_dir, f))]
                    logger.info(f"Files in temp directory: {temp_files}")
                    logger.info(f"Downloaded files found: {downloaded_files}")
                except Exception as list_error:
                    logger.error(f"Error listing temp directory: {list_error}")
                    raise Exception(f"Cannot access temporary directory: {list_error}")
                
                if not downloaded_files:
                    logger.error(f"No files found in {temp_dir}")
                    raise Exception("Download failed - no file was created")
                
                downloaded_file_path = os.path.join(temp_dir, downloaded_files[0])
                logger.info(f"Download completed: {downloaded_file_path}")
                
                # Final progress update - file is ready for download
                if progress_key:
                    update_download_progress(100, f"Downloaded: {filename}")
                
                # Note: Don't set progress to 100% here as it conflicts with real yt-dlp progress
                # The yt-dlp 'finished' hook will handle the final progress update
                
                # Create a file response that streams the file and cleans up after
                def file_iterator(file_path, chunk_size=8192):
                    try:
                        with open(file_path, 'rb') as f:
                            while True:
                                chunk = f.read(chunk_size)
                                if not chunk:
                                    break
                                yield chunk
                    finally:
                        # Clean up the temporary file and directory
                        try:
                            if os.path.exists(file_path):
                                os.remove(file_path)
                            if os.path.exists(temp_dir):
                                os.rmdir(temp_dir)
                        except Exception as cleanup_error:
                            logger.warning(f"Cleanup error: {cleanup_error}")
                
                from django.http import StreamingHttpResponse
                
                response = StreamingHttpResponse(
                    file_iterator(downloaded_file_path),
                    content_type='application/octet-stream'
                )
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                
                # Add file size if available
                try:
                    file_size = os.path.getsize(downloaded_file_path)
                    response['Content-Length'] = str(file_size)
                except:
                    pass
                
                # Add CORS headers
                response['Access-Control-Allow-Origin'] = '*'
                response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
                response['Access-Control-Allow-Headers'] = 'Content-Type'
                
                return response
                
        except Exception as e:
            # Clean up temp directory on error
            try:
                import shutil
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except:
                pass
            raise e
        
        # Log the download
        if request.user.is_authenticated:
            log_activity(
                request.user,
                'stream_download',
                f'Streamed download: {url}',
                request
            )
        
        return streaming_response
        
    except Exception as e:
        logger.error(f"Error streaming download: {str(e)}")
        return Response({'error': str(e)}, status=400)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_download_progress(request, download_id):
    """Get real-time download progress"""
    from django.core.cache import cache
    
    progress_key = f"download_progress_{download_id}"  # Use dedicated download progress key
    progress_data = cache.get(progress_key)
    
    if progress_data:
        return Response(progress_data)
    else:
        # Return a more informative default response
        default_response = {
            'progress': 0,
            'message': 'No progress data available',
            'status': 'unknown'
        }
        return Response(default_response)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def cancel_download(request):
    """Cancel an active download"""
    download_id = request.data.get('download_id')
    
    if not download_id:
        return Response(
            {'error': 'download_id is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        from django.core.cache import cache
        import os
        
        # 1. Mark the download as cancelled in cache
        progress_key = f"download_progress_{download_id}"
        cancel_key = f"download_cancel_{download_id}"
        
        # Set cancellation flag
        cache.set(cancel_key, True, 300)  # Cache for 5 minutes
        
        # Update progress to show cancellation
        cancel_progress = {
            'progress': 0,
            'message': 'Download cancelled by user',
            'status': 'cancelled'
        }
        cache.set(progress_key, cancel_progress, 300)
        
        logger.info(f"Download {download_id} marked for cancellation")
        
        # 2. Try to clean up any temporary files for this download
        # Note: The actual yt-dlp process cancellation will be handled by the AbortController
        # on the frontend, which will close the HTTP connection
        try:
            import tempfile
            import glob
            
            # Look for temp directories that might be related to this download
            temp_base = tempfile.gettempdir()
            possible_temp_dirs = glob.glob(os.path.join(temp_base, f"*{download_id}*"))
            
            for temp_dir in possible_temp_dirs:
                if os.path.isdir(temp_dir):
                    import shutil
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up temp directory: {temp_dir}")
                    
        except Exception as cleanup_error:
            logger.warning(f"Could not clean up temp files for {download_id}: {cleanup_error}")
        
        return Response({
            'message': f'Download {download_id} cancellation requested',
            'status': 'cancelled'
        })
        
    except Exception as e:
        logger.error(f"Error cancelling download {download_id}: {str(e)}")
        return Response({
            'error': f'Failed to cancel download: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_download_progress(request, download_id):
    """Get real-time download progress"""
    from django.core.cache import cache
    
    progress_key = f"download_progress_{download_id}"  # Use dedicated download progress key
    progress_data = cache.get(progress_key)
    
    if progress_data:
        return Response(progress_data)
    else:
        # Return a more informative default response
        default_response = {
            'progress': 0,
            'message': 'No progress data available',
            'status': 'unknown'
        }
        return Response(default_response)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def proxy_download(request):
    """Proxy download from direct URLs to bypass CORS restrictions"""
    direct_url = request.GET.get('direct_url')
    filename = request.GET.get('filename', 'download.mp4')
    ext = request.GET.get('ext', 'mp4')
    filesize = request.GET.get('filesize', 0)
    
    if not direct_url:
        return Response(
            {'error': 'direct_url parameter is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        import requests
        from django.http import StreamingHttpResponse
        
        # Set up headers to mimic a browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'audio/mp4,audio/*,*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'identity',  # Don't use gzip to avoid decompression issues
            'Range': 'bytes=0-',  # Request full file
            'Connection': 'keep-alive'
        }
        
        # Make the request to the direct URL
        logger.info(f"Proxying download: {filename}")
        
        response = requests.get(direct_url, headers=headers, stream=True, timeout=30)
        
        if not response.ok:
            logger.error(f"Failed to fetch from direct URL: {response.status_code}")
            return Response(
                {'error': f'Failed to fetch file: {response.status_code} {response.reason}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create streaming response
        def file_iterator():
            try:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
            except Exception as e:
                logger.error(f"Error streaming file: {str(e)}")
                # If streaming fails, we can't recover gracefully
                pass
            finally:
                response.close()
        
        # Create the streaming response with proper download headers
        streaming_response = StreamingHttpResponse(
            file_iterator(),
            content_type='application/octet-stream'
        )
        
        # Set download headers
        streaming_response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Set content length if we have it
        content_length = response.headers.get('Content-Length')
        if content_length:
            streaming_response['Content-Length'] = content_length
        elif filesize and int(filesize) > 0:
            streaming_response['Content-Length'] = str(filesize)
        
        # Add CORS headers for frontend
        streaming_response['Access-Control-Allow-Origin'] = '*'
        streaming_response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        streaming_response['Access-Control-Allow-Headers'] = 'Content-Type'
        
        logger.info(f"Started proxy download for: {filename}")
        return streaming_response
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error in proxy download: {str(e)}")
        return Response(
            {'error': f'Network error: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        logger.error(f"Error in proxy download: {str(e)}")
        return Response(
            {'error': f'Proxy download failed: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def get_direct_download_url(request):
    """Get direct download URL for client-side downloading"""
    url = request.data.get('url')
    quality = request.data.get('quality', '720p')
    use_proxy = request.data.get('use_proxy', False)
    
    if not url:
        return Response(
            {'error': 'URL is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        download_service = DownloadService()
        direct_info = download_service.get_direct_download_url(url, quality)
        
        # If use_proxy is True, provide our stream endpoint instead of direct URL
        if use_proxy:
            # Create a proxy URL through our server
            proxy_url = f"/api/downloads/stream/?url={url}&quality={quality}"
            direct_info['direct_url'] = proxy_url
            direct_info['proxy_mode'] = True
        
        # Log the request for analytics
        if request.user.is_authenticated:
            log_activity(
                request.user,
                'direct_download',
                f'Direct download requested: {url}',
                request
            )
        
        return Response(direct_info)
    except Exception as e:
        logger.error(f"Error getting direct download URL: {str(e)}")
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def test_download_page(request):
    """Serve test page for debugging downloads"""
    import os
    from django.http import HttpResponse
    
    # Look for test_download.html in the project root
    project_root = os.path.dirname(os.path.dirname(__file__))
    test_file_path = os.path.join(project_root, 'test_download.html')
    
    if os.path.exists(test_file_path):
        try:
            with open(test_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return HttpResponse(content, content_type='text/html')
        except Exception as e:
            return HttpResponse(f"Error reading test file: {str(e)}", status=500)
    else:
        return HttpResponse(f"Test file not found at {test_file_path}", status=404)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def get_video_info(request):
    """Get video information and available formats without downloading"""
    url = request.data.get('url')
    if not url:
        return Response(
            {'error': 'URL is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        download_service = DownloadService()
        video_info = download_service.get_video_info(url)
        
        # Get available formats with audio
        available_formats = download_service.get_available_formats(url)
        
        return Response({
            'title': video_info.get('title', 'Unknown'),
            'duration': video_info.get('duration', 0),
            'thumbnail': video_info.get('thumbnail', ''),
            'available_formats': available_formats
        })
    except Exception as e:
        logger.error(f"Error getting video info: {str(e)}")
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_progress(request, task_id):
    """Get progress for a specific task"""
    try:
        from django.core.cache import cache
        
        progress_data = cache.get(f'video_info_progress_{task_id}')
        
        if not progress_data:
            return Response({
                'error': 'Task not found or expired'
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response(progress_data)
        
    except Exception as e:
        logger.error(f"Error getting progress: {str(e)}")
        return Response({
            'error': f'Failed to get progress: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST'])
@permission_classes([permissions.AllowAny])
def get_video_info_with_progress(request):
    """Get video information with progress tracking for better UX"""
    if request.method == 'POST':
        url = request.data.get('url')
    else:
        url = request.GET.get('url')
        
    if not url:
        return Response(
            {'error': 'URL is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Return immediate response with progress indication
        import uuid
        import threading
        from django.core.cache import cache
        
        # Generate unique task ID for this request
        task_id = str(uuid.uuid4())
        
        # Initialize progress
        cache.set(f'video_info_progress_{task_id}', {
            'status': 'fetching',
            'progress': 0,
            'message': 'Initializing...',
            'stage': 'starting'
        }, timeout=300)  # 5 minutes
        
        def fetch_video_info():
            """Background task to fetch video info"""
            try:
                # Update progress - extraction started
                cache.set(f'video_info_progress_{task_id}', {
                    'status': 'fetching',
                    'progress': 25,
                    'message': 'Extracting video metadata...',
                    'stage': 'extracting'
                }, timeout=300)
                
                download_service = DownloadService()
                
                # Update progress - getting formats
                cache.set(f'video_info_progress_{task_id}', {
                    'status': 'fetching',
                    'progress': 75,
                    'message': 'Analyzing available formats...',
                    'stage': 'analyzing'
                }, timeout=300)
                
                video_info = download_service.get_video_info(url)
                
                # Filter video_info to only include essential data - not the massive subtitle/format data
                filtered_info = {
                    'title': video_info.get('title', 'Unknown Title'),
                    'duration': video_info.get('duration', 0),
                    'thumbnail': video_info.get('thumbnail', ''),
                    'uploader': video_info.get('uploader', ''),
                    'view_count': video_info.get('view_count', 0),
                    'upload_date': video_info.get('upload_date', ''),
                    'available_formats': video_info.get('available_formats', [])  # This should be our clean format list
                }
                
                # Update progress - complete
                cache.set(f'video_info_progress_{task_id}', {
                    'status': 'completed',
                    'progress': 100,
                    'message': 'Video information ready',
                    'stage': 'completed',
                    'result': filtered_info  # Use filtered info instead of raw video_info
                }, timeout=300)
                
            except Exception as e:
                logger.error(f"Background video info error: {str(e)}")
                # Update progress - error
                cache.set(f'video_info_progress_{task_id}', {
                    'status': 'error',
                    'progress': 100,
                    'message': f'Error: {str(e)}',
                    'stage': 'error',
                    'error': str(e)
                }, timeout=300)
        
        # Start background task
        thread = threading.Thread(target=fetch_video_info)
        thread.daemon = True
        thread.start()
        
        # Return task ID for progress tracking
        return Response({
            'task_id': task_id,
            'status': 'fetching',
            'message': 'Video information extraction started',
            'progress_url': f'/api/downloads/progress/{task_id}/'
        })
        
    except Exception as e:
        logger.error(f"Error starting video info extraction: {str(e)}")
        return Response({
            'error': f'Failed to start extraction: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
