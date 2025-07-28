"""
Synchronous task processor for when Celery is not available
"""
import logging
from django.utils import timezone
from downloads.models import DownloadRequest
from downloads.services import DownloadService
from conversions.models import ConversionRequest
from conversions.services import ConversionService

logger = logging.getLogger(__name__)

class SyncTaskProcessor:
    """Processes tasks synchronously when Celery is not available"""
    
    @staticmethod
    def process_download(download_id: str):
        """Process download synchronously with proper progress updates"""
        try:
            download_request = DownloadRequest.objects.get(id=download_id)
            download_service = DownloadService()
            
            # Update status to processing immediately
            download_request.status = 'processing'
            download_request.progress = 1
            download_request.started_at = timezone.now()
            download_request.save()
            
            # SPEED: Extract title AFTER API response, during processing
            if download_request.title == 'Video Download':
                try:
                    video_info = download_service.get_video_info(download_request.url)
                    download_request.title = video_info.get('title', 'Video Download')
                    download_request.save()
                except Exception as e:
                    logger.warning(f"Could not extract video info: {str(e)}")
            
            # Perform download with progress tracking
            result = download_service.download_video(download_request)
            
            # Final update
            download_request.refresh_from_db()  # Get latest progress from download_video
            if download_request.status != 'completed':
                download_request.status = 'completed'
                download_request.progress = 100
                download_request.completed_at = timezone.now()
                download_request.save()
            
            logger.info(f"Download {download_id} completed synchronously")
            
        except Exception as e:
            logger.error(f"Sync download failed for {download_id}: {str(e)}")
            try:
                download_request = DownloadRequest.objects.get(id=download_id)
                download_request.status = 'failed'
                download_request.error_message = str(e)
                download_request.save()
            except:
                pass
    
    @staticmethod
    def process_conversion(conversion_id: str):
        """Process conversion synchronously"""
        try:
            conversion_request = ConversionRequest.objects.get(id=conversion_id)
            conversion_service = ConversionService()
            
            # Update status to processing
            conversion_request.status = 'processing'
            conversion_request.save()
            
            # Perform conversion
            result = conversion_service.convert_media(conversion_request)
            
            # Update status based on result
            if result:
                conversion_request.status = 'completed'
                conversion_request.progress = 100
                conversion_request.output_file = result
            else:
                conversion_request.status = 'failed'
                conversion_request.error_message = "Conversion failed"
            
            conversion_request.save()
            logger.info(f"Conversion {conversion_id} completed synchronously")
            
        except Exception as e:
            logger.error(f"Sync conversion failed for {conversion_id}: {str(e)}")
            try:
                conversion_request = ConversionRequest.objects.get(id=conversion_id)
                conversion_request.status = 'failed'
                conversion_request.error_message = str(e)
                conversion_request.save()
            except:
                pass
