from django.db import models
from django.conf import settings
from django.utils import timezone
import os
import uuid


def upload_to_downloads(instance, filename):
    """Generate upload path for downloaded files"""
    user_id = instance.user.id if instance.user else 'anonymous'
    return f'downloads/{user_id}/{uuid.uuid4()}/{filename}'


class DownloadRequest(models.Model):
    """Model for tracking download requests"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    QUALITY_CHOICES = [
        ('audio', 'Audio Only (Fastest)'),
        ('240p', '240p (Fast)'),
        ('360p', '360p (Fast)'),
        ('480p', '480p (Balanced)'),
        ('720p', '720p (Good Quality)'),
        ('1080p', '1080p (High Quality)'),
        ('1440p', '1440p'),
        ('2160p', '2160p (4K)'),
        ('best', 'Best Available'),
        ('worst', 'Worst Available'),
    ]

    FORMAT_CHOICES = [
        ('mp4', 'MP4 Video'),
        ('webm', 'WebM Video'),
        ('mp3', 'MP3 Audio'),
        ('m4a', 'M4A Audio'),
        ('wav', 'WAV Audio'),
        ('flac', 'FLAC Audio'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    url = models.URLField(max_length=2000)
    title = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    thumbnail_url = models.URLField(max_length=1000, blank=True)
    duration = models.IntegerField(null=True, blank=True)  # in seconds
    
    # Download options
    format_requested = models.CharField(max_length=10, choices=FORMAT_CHOICES, default='mp4')
    quality_requested = models.CharField(max_length=10, choices=QUALITY_CHOICES, default='720p')
    audio_only = models.BooleanField(default=False)
    
    # Status and tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    progress = models.IntegerField(default=0)  # 0-100
    error_message = models.TextField(blank=True)
    
    # File information
    file_path = models.FileField(upload_to=upload_to_downloads, blank=True, null=True)
    file_size = models.BigIntegerField(null=True, blank=True)  # in bytes
    file_format = models.CharField(max_length=10, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    video_codec = models.CharField(max_length=50, blank=True)
    audio_codec = models.CharField(max_length=50, blank=True)
    bitrate = models.IntegerField(null=True, blank=True)
    fps = models.FloatField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title or self.url[:50]} - {self.status}"

    def get_file_size_mb(self):
        """Return file size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0

    def get_duration_formatted(self):
        """Return formatted duration string"""
        if not self.duration:
            return "Unknown"
        
        hours = self.duration // 3600
        minutes = (self.duration % 3600) // 60
        seconds = self.duration % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    def delete_file(self):
        """Delete the associated file from storage"""
        if self.file_path and os.path.exists(self.file_path.path):
            os.remove(self.file_path.path)
            # Update user storage
            if self.user and self.file_size:
                self.user.storage_used -= self.file_size
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


class DownloadHistory(models.Model):
    """Track download history for analytics"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    url = models.URLField(max_length=2000)
    domain = models.CharField(max_length=100)
    success = models.BooleanField(default=False)
    file_size = models.BigIntegerField(null=True, blank=True)
    download_time = models.FloatField(null=True, blank=True)  # in seconds
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "Download Histories"

    def __str__(self):
        user_info = self.user.email if self.user else 'Anonymous'
        return f"{user_info} - {self.domain} - {self.timestamp}"
