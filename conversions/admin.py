from django.contrib import admin
from django.utils.html import format_html
from .models import ConversionRequest, ConversionHistory


@admin.register(ConversionRequest)
class ConversionRequestAdmin(admin.ModelAdmin):
    list_display = ('input_filename', 'user_email', 'status', 'input_format', 'output_format', 'input_size_mb', 'output_size_mb', 'progress', 'created_at')
    list_filter = ('status', 'input_format', 'output_format', 'output_quality', 'created_at')
    search_fields = ('input_filename', 'output_filename', 'user__email')
    date_hierarchy = 'created_at'
    readonly_fields = ('id', 'created_at', 'started_at', 'completed_at', 'input_size_mb', 'output_size_mb', 'duration_formatted', 'compression_percentage')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'input_filename', 'input_format', 'input_size_mb')
        }),
        ('Conversion Settings', {
            'fields': ('output_format', 'output_quality', 'custom_settings')
        }),
        ('Status & Progress', {
            'fields': ('status', 'progress', 'error_message')
        }),
        ('Output Information', {
            'fields': ('output_file', 'output_filename', 'output_size_mb', 'compression_percentage')
        }),
        ('Processing Details', {
            'fields': ('duration_formatted', 'conversion_time'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'started_at', 'completed_at', 'expires_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['cancel_conversions', 'retry_failed_conversions', 'cleanup_expired']
    
    def user_email(self, obj):
        return obj.user.email if obj.user else 'Anonymous'
    user_email.short_description = 'User'
    
    def input_size_mb(self, obj):
        return f"{obj.get_input_size_mb()} MB"
    input_size_mb.short_description = 'Input Size'
    
    def output_size_mb(self, obj):
        return f"{obj.get_output_size_mb()} MB" if obj.output_size else "N/A"
    output_size_mb.short_description = 'Output Size'
    
    def duration_formatted(self, obj):
        return obj.get_duration_formatted()
    duration_formatted.short_description = 'Duration'
    
    def compression_percentage(self, obj):
        percentage = obj.get_compression_percentage()
        if percentage > 0:
            return format_html(
                '<span style="color: green;">-{}%</span>',
                percentage
            )
        elif percentage < 0:
            return format_html(
                '<span style="color: red;">+{}%</span>',
                abs(percentage)
            )
        return "0%"
    compression_percentage.short_description = 'Compression'
    
    def cancel_conversions(self, request, queryset):
        count = queryset.filter(status__in=['pending', 'processing']).update(status='cancelled')
        self.message_user(request, f"Cancelled {count} conversions.")
    cancel_conversions.short_description = "Cancel selected conversions"
    
    def retry_failed_conversions(self, request, queryset):
        count = queryset.filter(status='failed').update(status='pending', progress=0, error_message='')
        self.message_user(request, f"Retrying {count} failed conversions.")
    retry_failed_conversions.short_description = "Retry failed conversions"
    
    def cleanup_expired(self, request, queryset):
        from django.utils import timezone
        expired = queryset.filter(expires_at__lt=timezone.now())
        for conversion in expired:
            conversion.delete_files()
        count = expired.delete()[0]
        self.message_user(request, f"Cleaned up {count} expired conversions.")
    cleanup_expired.short_description = "Clean up expired conversions"


@admin.register(ConversionHistory)
class ConversionHistoryAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'conversion_type', 'input_size_mb', 'output_size_mb', 'conversion_time', 'success', 'timestamp')
    list_filter = ('success', 'input_format', 'output_format', 'timestamp')
    search_fields = ('user__email', 'ip_address')
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp',)
    
    def user_email(self, obj):
        return obj.user.email if obj.user else 'Anonymous'
    user_email.short_description = 'User'
    
    def conversion_type(self, obj):
        return f"{obj.input_format} → {obj.output_format}"
    conversion_type.short_description = 'Conversion'
    
    def input_size_mb(self, obj):
        return f"{round(obj.input_size / (1024 * 1024), 2)} MB"
    input_size_mb.short_description = 'Input Size'
    
    def output_size_mb(self, obj):
        if obj.output_size:
            return f"{round(obj.output_size / (1024 * 1024), 2)} MB"
        return "N/A"
    output_size_mb.short_description = 'Output Size'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
