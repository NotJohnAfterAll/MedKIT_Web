from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import User, SystemSettings, ActivityLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'username', 'is_premium', 'requests_today', 'storage_used_mb', 'is_active', 'date_joined')
    list_filter = ('is_premium', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('MedKIT Settings', {
            'fields': ('is_premium', 'daily_request_limit', 'requests_today', 'last_request_date', 'storage_used')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('MedKIT Settings', {
            'fields': ('email', 'is_premium', 'daily_request_limit')
        }),
    )
    
    actions = ['grant_premium', 'revoke_premium', 'reset_daily_requests', 'clear_storage']
    
    def storage_used_mb(self, obj):
        return f"{round(obj.storage_used / (1024 * 1024), 2)} MB"
    storage_used_mb.short_description = 'Storage Used'
    
    def grant_premium(self, request, queryset):
        queryset.update(is_premium=True)
        self.message_user(request, f"Granted premium access to {queryset.count()} users.")
    grant_premium.short_description = "Grant premium access"
    
    def revoke_premium(self, request, queryset):
        queryset.update(is_premium=False)
        self.message_user(request, f"Revoked premium access from {queryset.count()} users.")
    revoke_premium.short_description = "Revoke premium access"
    
    def reset_daily_requests(self, request, queryset):
        queryset.update(requests_today=0)
        self.message_user(request, f"Reset daily requests for {queryset.count()} users.")
    reset_daily_requests.short_description = "Reset daily requests"
    
    def clear_storage(self, request, queryset):
        queryset.update(storage_used=0)
        self.message_user(request, f"Cleared storage usage for {queryset.count()} users.")
    clear_storage.short_description = "Clear storage usage"


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ('key', 'value_preview', 'description', 'updated_at')
    search_fields = ('key', 'description')
    list_filter = ('created_at', 'updated_at')
    
    def value_preview(self, obj):
        if len(obj.value) > 50:
            return obj.value[:50] + "..."
        return obj.value
    value_preview.short_description = 'Value'


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'action', 'description_preview', 'ip_address', 'timestamp')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__email', 'description', 'ip_address')
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp',)
    
    def user_email(self, obj):
        return obj.user.email if obj.user else 'Anonymous'
    user_email.short_description = 'User'
    
    def description_preview(self, obj):
        if len(obj.description) > 50:
            return obj.description[:50] + "..."
        return obj.description
    description_preview.short_description = 'Description'
    
    def has_add_permission(self, request):
        return False  # Prevent manual creation of activity logs
    
    def has_change_permission(self, request, obj=None):
        return False  # Prevent editing of activity logs
