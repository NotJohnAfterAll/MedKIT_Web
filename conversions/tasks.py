from celery import shared_task
from .models import ConversionRequest
from .services import ConversionService
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def process_conversion_task(self, conversion_id: str):
    """Background task to process media conversion"""
    try:
        conversion_request = ConversionRequest.objects.get(id=conversion_id)
        conversion_service = ConversionService()
        
        # Perform the conversion
        output_path = conversion_service.convert_media(conversion_request)
        
        logger.info(f"Conversion completed: {output_path}")
        return f"Conversion completed: {conversion_request.filename}"
        
    except ConversionRequest.DoesNotExist:
        error_msg = f"Conversion request {conversion_id} not found"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Conversion failed: {str(e)}"
        logger.error(error_msg)
        
        # Update the conversion request with error
        try:
            conversion_request = ConversionRequest.objects.get(id=conversion_id)
            conversion_request.status = 'failed'
            conversion_request.error_message = str(e)
            conversion_request.save()
        except:
            pass
        
        return error_msg
