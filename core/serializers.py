from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, ActivityLog, SystemSettings


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password')

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email already exists.")
        return value

    def create(self, validated_data):
        # Use email as username since our User model uses email for authentication
        validated_data['username'] = validated_data['email']
        user = User.objects.create_user(**validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    storage_used_mb = serializers.SerializerMethodField()
    requests_remaining = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'is_premium', 
                 'daily_request_limit', 'requests_today', 'requests_remaining', 
                 'storage_used', 'storage_used_mb', 'date_joined')
        read_only_fields = ('id', 'requests_today', 'storage_used', 'date_joined')

    def get_storage_used_mb(self, obj):
        return round(obj.storage_used / (1024 * 1024), 2)

    def get_requests_remaining(self, obj):
        obj.reset_daily_requests()
        if obj.is_premium:
            return "Unlimited"
        return max(0, obj.daily_request_limit - obj.requests_today)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include email and password')


class ActivityLogSerializer(serializers.ModelSerializer):
    user_email = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = ('id', 'user_email', 'action', 'description', 'timestamp')

    def get_user_email(self, obj):
        return obj.user.email if obj.user else 'Anonymous'


class SystemSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSettings
        fields = ('key', 'value', 'description')
