from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import DownloadRequest, DownloadHistory


@admin.register(DownloadRequest)
class DownloadRequestAdmin(admin.ModelAdmin):
    list_display = ('title_preview', 'user_email', 'status', 'format_requested', 'quality_requested', 'file_size_mb', 'progress', 'created_at')
    list_filter = ('status', 'format_requested', 'quality_requested', 'audio_only', 'created_at')
    search_fields = ('title', 'url', 'user__email')
    date_hierarchy = 'created_at'
    readonly_fields = ('id', 'created_at', 'started_at', 'completed_at', 'file_size_mb', 'duration_formatted')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'url', 'title', 'description')
        }),
        ('Download Options', {
            'fields': ('format_requested', 'quality_requested', 'audio_only')
        }),
        ('Status & Progress', {
            'fields': ('status', 'progress', 'error_message')
        }),
        ('File Information', {
            'fields': ('file_path', 'file_size_mb', 'file_format', 'duration_formatted')
        }),
        ('Technical Details', {
            'fields': ('video_codec', 'audio_codec', 'bitrate', 'fps'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'started_at', 'completed_at', 'expires_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['cancel_downloads', 'retry_failed_downloads', 'cleanup_expired']
    
    def title_preview(self, obj):
        if obj.title:
            return obj.title[:50] + "..." if len(obj.title) > 50 else obj.title
        return obj.url[:50] + "..."
    title_preview.short_description = 'Title/URL'
    
    def user_email(self, obj):
        return obj.user.email if obj.user else 'Anonymous'
    user_email.short_description = 'User'
    
    def file_size_mb(self, obj):
        return f"{obj.get_file_size_mb()} MB" if obj.file_size else "N/A"
    file_size_mb.short_description = 'File Size'
    
    def duration_formatted(self, obj):
        return obj.get_duration_formatted()
    duration_formatted.short_description = 'Duration'
    
    def cancel_downloads(self, request, queryset):
        count = queryset.filter(status__in=['pending', 'processing']).update(status='cancelled')
        self.message_user(request, f"Cancelled {count} downloads.")
    cancel_downloads.short_description = "Cancel selected downloads"
    
    def retry_failed_downloads(self, request, queryset):
        count = queryset.filter(status='failed').update(status='pending', progress=0, error_message='')
        self.message_user(request, f"Retrying {count} failed downloads.")
    retry_failed_downloads.short_description = "Retry failed downloads"
    
    def cleanup_expired(self, request, queryset):
        from django.utils import timezone
        expired = queryset.filter(expires_at__lt=timezone.now())
        for download in expired:
            download.delete_file()
        count = expired.delete()[0]
        self.message_user(request, f"Cleaned up {count} expired downloads.")
    cleanup_expired.short_description = "Clean up expired downloads"


@admin.register(DownloadHistory)
class DownloadHistoryAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'domain', 'success', 'file_size_mb', 'download_time', 'timestamp')
    list_filter = ('success', 'domain', 'timestamp')
    search_fields = ('user__email', 'url', 'domain', 'ip_address')
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp',)
    
    def user_email(self, obj):
        return obj.user.email if obj.user else 'Anonymous'
    user_email.short_description = 'User'
    
    def file_size_mb(self, obj):
        if obj.file_size:
            return f"{round(obj.file_size / (1024 * 1024), 2)} MB"
        return "N/A"
    file_size_mb.short_description = 'File Size'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
