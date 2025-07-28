from celery import shared_task
from django.core.files.base import ContentFile
from .models import DownloadRequest
from .services import DownloadService
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def process_download_task(self, download_id: str):
    """Background task to process video download"""
    try:
        download_request = DownloadRequest.objects.get(id=download_id)
        download_service = DownloadService()
        
        # Extract video info first
        try:
            video_info = download_service.get_video_info(download_request.url)
            download_request.title = video_info.get('title', download_request.title)
            download_request.save()
        except Exception as e:
            logger.warning(f"Could not extract video info: {str(e)}")
        
        # Download the video/audio
        if download_request.format in ['mp3', 'm4a', 'wav', 'flac']:
            file_path = download_service.download_audio(download_request)
        else:
            file_path = download_service.download_video(download_request)
        
        logger.info(f"Download completed: {file_path}")
        return f"Download completed: {download_request.title}"
        
    except DownloadRequest.DoesNotExist:
        error_msg = f"Download request {download_id} not found"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Download failed: {str(e)}"
        logger.error(error_msg)
        
        # Update the download request with error
        try:
            download_request = DownloadRequest.objects.get(id=download_id)
            download_request.status = 'failed'
            download_request.error_message = str(e)
            download_request.save()
        except:
            pass
        
        return error_msg
