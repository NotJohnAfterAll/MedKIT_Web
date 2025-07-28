from rest_framework import serializers
from .models import DownloadRequest, DownloadHistory


class DownloadRequestSerializer(serializers.ModelSerializer):
    file_size_mb = serializers.SerializerMethodField()
    duration_formatted = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()

    class Meta:
        model = DownloadRequest
        fields = (
            'id', 'user_email', 'url', 'title', 'description', 'thumbnail_url',
            'duration', 'duration_formatted', 'format_requested', 'quality_requested',
            'audio_only', 'status', 'progress', 'error_message', 'file_path',
            'file_size', 'file_size_mb', 'file_format', 'created_at', 'started_at',
            'completed_at', 'expires_at', 'video_codec', 'audio_codec', 'bitrate', 'fps'
        )
        read_only_fields = (
            'id', 'title', 'description', 'thumbnail_url', 'duration', 'status',
            'progress', 'error_message', 'file_path', 'file_size', 'file_format',
            'created_at', 'started_at', 'completed_at', 'expires_at', 'video_codec',
            'audio_codec', 'bitrate', 'fps'
        )

    def get_file_size_mb(self, obj):
        return obj.get_file_size_mb()

    def get_duration_formatted(self, obj):
        return obj.get_duration_formatted()

    def get_user_email(self, obj):
        return obj.user.email if obj.user else 'Anonymous'


class DownloadCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DownloadRequest
        fields = ('url', 'format_requested', 'quality_requested', 'audio_only')

    def validate_url(self, value):
        """Validate that the URL is from a supported platform"""
        supported_domains = [
            'youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com',
            'twitch.tv', 'tiktok.com', 'instagram.com', 'facebook.com',
            'twitter.com', 'soundcloud.com'
        ]
        
        from urllib.parse import urlparse
        domain = urlparse(value).netloc.lower()
        
        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Check if domain is supported
        if not any(supported in domain for supported in supported_domains):
            raise serializers.ValidationError(
                f"Unsupported URL. Supported platforms: {', '.join(supported_domains)}"
            )
        
        return value


class DownloadHistorySerializer(serializers.ModelSerializer):
    user_email = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()

    class Meta:
        model = DownloadHistory
        fields = (
            'id', 'user_email', 'url', 'domain', 'success', 'file_size',
            'file_size_mb', 'download_time', 'timestamp'
        )

    def get_user_email(self, obj):
        return obj.user.email if obj.user else 'Anonymous'

    def get_file_size_mb(self, obj):
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return 0
