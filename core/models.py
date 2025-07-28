from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """Extended User model with additional fields"""
    email = models.EmailField(unique=True)
    is_premium = models.BooleanField(default=False)
    daily_request_limit = models.IntegerField(default=100)
    requests_today = models.IntegerField(default=0)
    last_request_date = models.DateField(default=timezone.now)
    storage_used = models.BigIntegerField(default=0)  # in bytes
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def reset_daily_requests(self):
        """Reset daily request count if it's a new day"""
        today = timezone.now().date()
        if self.last_request_date < today:
            self.requests_today = 0
            self.last_request_date = today
            self.save()

    def can_make_request(self):
        """Check if user can make a request based on daily limit"""
        self.reset_daily_requests()
        return self.is_premium or self.requests_today < self.daily_request_limit

    def increment_request_count(self):
        """Increment the daily request count"""
        self.reset_daily_requests()
        self.requests_today += 1
        self.save()

    def __str__(self):
        return self.email


class SystemSettings(models.Model):
    """Global system settings"""
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "System Settings"

    def __str__(self):
        return f"{self.key}: {self.value}"


class ActivityLog(models.Model):
    """Log all user activities"""
    ACTION_CHOICES = [
        ('download', 'Download'),
        ('convert', 'Convert'),
        ('login', 'Login'),
        ('register', 'Register'),
        ('delete', 'Delete File'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        user_info = self.user.email if self.user else 'Anonymous'
        return f"{user_info} - {self.action} - {self.timestamp}"
