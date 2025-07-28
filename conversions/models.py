from django.db import models
from django.conf import settings
from django.utils import timezone
import os
import uuid


def upload_to_conversions(instance, filename):
    """Generate upload path for converted files"""
    user_id = instance.user.id if instance.user else 'anonymous'
    return f'conversions/{user_id}/{uuid.uuid4()}/{filename}'


class ConversionRequest(models.Model):
    """Model for tracking file conversion requests"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    OUTPUT_FORMAT_CHOICES = [
        ('mp4', 'MP4 Video'),
        ('avi', 'AVI Video'),
        ('mkv', 'MKV Video'),
        ('mov', 'MOV Video'),
        ('webm', 'WebM Video'),
        ('mp3', 'MP3 Audio'),
        ('wav', 'WAV Audio'),
        ('flac', 'FLAC Audio'),
        ('aac', 'AAC Audio'),
        ('ogg', 'OGG Audio'),
        ('m4a', 'M4A Audio'),
    ]

    QUALITY_CHOICES = [
        ('144p', '144p'),
        ('240p', '240p'),
        ('360p', '360p'),
        ('480p', '480p'),
        ('720p', '720p'),
        ('1080p', '1080p'),
        ('1440p', '1440p'),
        ('2160p', '2160p (4K)'),
        ('original', 'Original Quality'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    
    # Input file
    input_file = models.FileField(upload_to='temp_uploads/')
    input_filename = models.CharField(max_length=255)
    input_format = models.CharField(max_length=10)
    input_size = models.BigIntegerField()  # in bytes
    
    # Output settings
    output_format = models.CharField(max_length=10, choices=OUTPUT_FORMAT_CHOICES)
    output_quality = models.CharField(max_length=10, choices=QUALITY_CHOICES, default='original')
    custom_settings = models.JSONField(default=dict, blank=True)
    
    # Output file
    output_file = models.FileField(upload_to=upload_to_conversions, blank=True, null=True)
    output_filename = models.CharField(max_length=255, blank=True)
    output_size = models.BigIntegerField(null=True, blank=True)  # in bytes
    
    # Status and tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    progress = models.IntegerField(default=0)  # 0-100
    error_message = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Processing metadata
    duration = models.FloatField(null=True, blank=True)  # in seconds
    conversion_time = models.FloatField(null=True, blank=True)  # in seconds
    compression_ratio = models.FloatField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.input_filename} -> {self.output_format} - {self.status}"

    def get_input_size_mb(self):
        """Return input file size in MB"""
        return round(self.input_size / (1024 * 1024), 2)

    def get_output_size_mb(self):
        """Return output file size in MB"""
        if self.output_size:
            return round(self.output_size / (1024 * 1024), 2)
        return 0

    def get_compression_percentage(self):
        """Return compression percentage"""
        if self.compression_ratio:
            return round((1 - self.compression_ratio) * 100, 1)
        return 0

    def get_duration_formatted(self):
        """Return formatted duration string"""
        if not self.duration:
            return "Unknown"
        
        hours = int(self.duration // 3600)
        minutes = int((self.duration % 3600) // 60)
        seconds = int(self.duration % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    def delete_files(self):
        """Delete both input and output files from storage"""
        if self.input_file and os.path.exists(self.input_file.path):
            os.remove(self.input_file.path)
        
        if self.output_file and os.path.exists(self.output_file.path):
            os.remove(self.output_file.path)
            # Update user storage
            if self.user and self.output_size:
                self.user.storage_used -= self.output_size
                self.user.save()

    def save(self, *args, **kwargs):
        # Set expiration date (7 days from creation)
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=7)
        
        # Update started_at when status changes to processing
        if self.status == 'processing' and not self.started_at:
            self.started_at = timezone.now()
        
        # Update completed_at when status changes to completed or failed
        if self.status in ['completed', 'failed'] and not self.completed_at:
            self.completed_at = timezone.now()
        
        super().save(*args, **kwargs)


class ConversionHistory(models.Model):
    """Track conversion history for analytics"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    input_format = models.CharField(max_length=10)
    output_format = models.CharField(max_length=10)
    input_size = models.BigIntegerField()
    output_size = models.BigIntegerField(null=True, blank=True)
    conversion_time = models.FloatField(null=True, blank=True)
    success = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "Conversion Histories"

    def __str__(self):
        user_info = self.user.email if self.user else 'Anonymous'
        return f"{user_info} - {self.input_format} to {self.output_format} - {self.timestamp}"
