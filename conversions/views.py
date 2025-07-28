from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, Http404
from django.utils import timezone
from .models import ConversionRequest, ConversionHistory
from .serializers import ConversionRequestSerializer, ConversionCreateSerializer, ConversionHistorySerializer
from .tasks import process_conversion_task  # Import the actual task
from .services import ConversionService  # Import the conversion service
from core.views import log_activity
import logging

logger = logging.getLogger(__name__)


class ConversionRequestViewSet(ModelViewSet):
    """ViewSet for conversion requests"""
    serializer_class = ConversionRequestSerializer
    permission_classes = [permissions.AllowAny]  # Allow anonymous conversions

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return ConversionRequest.objects.filter(user=self.request.user)
        else:
            # For anonymous users, return empty queryset for list view
            if self.action == 'list':
                return ConversionRequest.objects.none()
            # But allow individual conversions to be viewed by ID
            return ConversionRequest.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return ConversionCreateSerializer
        return ConversionRequestSerializer

    def create(self, request, *args, **kwargs):
        """Create a new conversion request"""
        # Check if user can make request
        if request.user.is_authenticated and not request.user.can_make_request():
            return Response(
                {'error': 'Daily request limit exceeded'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            input_file = serializer.validated_data['input_file']
            
            # Extract file information
            input_filename = input_file.name
            input_format = input_filename.split('.')[-1].lower()
            input_size = input_file.size

            # Create conversion request
            conversion_request = serializer.save(
                user=request.user if request.user.is_authenticated else None,
                input_filename=input_filename,
                input_format=input_format,
                input_size=input_size
            )

            # Increment user request count
            if request.user.is_authenticated:
                request.user.increment_request_count()

            # Log activity
            log_activity(
                request.user if request.user.is_authenticated else None,
                'convert',
                f'Conversion requested: {input_filename} to {conversion_request.output_format}',
                request
            )

            # Start conversion task (with fallback to synchronous)
            try:
                from conversions.tasks import process_conversion_task
                process_conversion_task.delay(str(conversion_request.id))
                logger.info(f"Started conversion task for {conversion_request.id}")
            except Exception as e:
                logger.warning(f"Celery unavailable, using synchronous processing: {str(e)}")
                # Fallback to synchronous processing
                try:
                    from core.sync_tasks import SyncTaskProcessor
                    import threading
                    # Run in background thread to avoid blocking the API response
                    thread = threading.Thread(
                        target=SyncTaskProcessor.process_conversion,
                        args=(str(conversion_request.id),)
                    )
                    thread.daemon = True
                    thread.start()
                    logger.info(f"Started synchronous conversion for {conversion_request.id}")
                except Exception as sync_error:
                    logger.error(f"Both async and sync processing failed: {str(sync_error)}")
                    conversion_request.status = 'failed'
                    conversion_request.error_message = f"Processing unavailable: {str(sync_error)}"
                    conversion_request.save()

            return Response(
                ConversionRequestSerializer(conversion_request).data,
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a conversion request"""
        conversion_request = self.get_object()
        
        if conversion_request.status in ['pending', 'processing']:
            conversion_request.status = 'cancelled'
            conversion_request.save()
            
            return Response({'message': 'Conversion cancelled'})
        
        return Response(
            {'error': 'Cannot cancel conversion in current status'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=['get'])
    def download_file(self, request, pk=None):
        """Download the converted file"""
        conversion_request = self.get_object()
        
        if conversion_request.status != 'completed' or not conversion_request.output_file:
            raise Http404("File not available")

        try:
            with open(conversion_request.output_file.path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/octet-stream')
                response['Content-Disposition'] = f'attachment; filename="{conversion_request.output_filename}"'
                return response
        except FileNotFoundError:
            raise Http404("File not found")

    @action(detail=True, methods=['delete'])
    def delete_files(self, request, pk=None):
        """Delete the conversion files"""
        conversion_request = self.get_object()
        
        # Check if user owns this conversion
        if request.user != conversion_request.user and not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        conversion_request.delete_files()
        conversion_request.delete()
        
        log_activity(
            request.user,
            'delete',
            f'Deleted conversion: {conversion_request.input_filename}',
            request
        )
        
        return Response({'message': 'Files deleted successfully'})


class ConversionHistoryViewSet(ReadOnlyModelViewSet):
    """ViewSet for conversion history (admin only)"""
    serializer_class = ConversionHistorySerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = ConversionHistory.objects.all()


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def conversion_stats(request):
    """Get conversion statistics"""
    # Get counts by status
    stats = {
        'pending': ConversionRequest.objects.filter(status='pending').count(),
        'processing': ConversionRequest.objects.filter(status='processing').count(),
        'completed': ConversionRequest.objects.filter(status='completed').count(),
        'failed': ConversionRequest.objects.filter(status='failed').count(),
        'cancelled': ConversionRequest.objects.filter(status='cancelled').count(),
    }
    
    # Get popular conversion types
    from django.db import models
    popular_conversions = ConversionHistory.objects.values('input_format', 'output_format').annotate(
        count=models.Count('id')
    ).order_by('-count')[:5]
    
    return Response({
        'status_counts': stats,
        'popular_conversions': list(popular_conversions)
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def supported_formats(request):
    """Get supported conversion formats"""
    conversion_service = ConversionService()
    
    input_format = request.GET.get('input_format')
    if input_format:
        # Return supported output formats for specific input format
        output_formats = conversion_service.get_supported_output_formats(input_format)
        return Response({
            'input_format': input_format,
            'supported_outputs': output_formats
        })
    else:
        # Return all supported formats
        return Response({
            'supported_formats': conversion_service.SUPPORTED_FORMATS
        })
