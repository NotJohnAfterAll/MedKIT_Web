from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.db import models
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import User, ActivityLog, SystemSettings
from .serializers import (
    UserRegistrationSerializer, UserSerializer, LoginSerializer,
    ActivityLogSerializer, SystemSettingsSerializer
)


def log_activity(user, action, description, request=None):
    """Helper function to log user activities"""
    ip_address = None
    user_agent = ""
    
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    ActivityLog.objects.create(
        user=user,
        action=action,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent
    )


@csrf_exempt
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register(request):
    """User registration endpoint"""
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        
        # Log registration activity
        log_activity(user, 'register', f'User registered: {user.email}', request)
        
        return Response({
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_premium': user.is_premium,
                'date_joined': user.date_joined.isoformat(),
            },
            'access': str(access_token),
            'refresh': str(refresh)
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    """User login endpoint"""
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not email or not password:
        return Response({
            'error': 'Email and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user = authenticate(request, username=email, password=password)
    if user:
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        
        # Log login activity
        log_activity(user, 'login', f'User logged in: {user.email}', request)
        
        return Response({
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_premium': user.is_premium,
                'date_joined': user.date_joined.isoformat(),
            },
            'access': str(access_token),
            'refresh': str(refresh)
        })
    
    return Response({
        'error': 'Invalid email or password'
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    """User logout endpoint"""
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        # Log logout activity
        log_activity(request.user, 'logout', f'User logged out: {request.user.email}', request)
        
        return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def profile(request):
    """Get user profile"""
    return Response(UserSerializer(request.user).data)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def update_profile(request):
    """Update user profile"""
    serializer = UserSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def system_stats(request):
    """Get system statistics"""
    from downloads.models import DownloadRequest
    from conversions.models import ConversionRequest
    
    # Get counts
    total_users = User.objects.count()
    total_downloads = DownloadRequest.objects.count()
    total_conversions = ConversionRequest.objects.count()
    
    # Get recent activity counts (last 24 hours)
    yesterday = timezone.now() - timezone.timedelta(days=1)
    recent_downloads = DownloadRequest.objects.filter(created_at__gte=yesterday).count()
    recent_conversions = ConversionRequest.objects.filter(created_at__gte=yesterday).count()
    
    # Get storage usage
    total_storage = User.objects.aggregate(
        total=models.Sum('storage_used')
    )['total'] or 0
    
    return Response({
        'total_users': total_users,
        'total_downloads': total_downloads,
        'total_conversions': total_conversions,
        'recent_downloads': recent_downloads,
        'recent_conversions': recent_conversions,
        'total_storage_gb': round(total_storage / (1024**3), 2),
        'max_storage_gb': round(50, 2)  # 50GB limit
    })


class ActivityLogViewSet(ReadOnlyModelViewSet):
    """ViewSet for activity logs (admin only)"""
    serializer_class = ActivityLogSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        return ActivityLog.objects.all()


class SystemSettingsViewSet(ReadOnlyModelViewSet):
    """ViewSet for system settings (admin only)"""
    serializer_class = SystemSettingsSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = SystemSettings.objects.all()
