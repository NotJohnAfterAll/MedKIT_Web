from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

router = DefaultRouter()
router.register(r'activity-logs', views.ActivityLogViewSet, basename='activitylog')
router.register(r'settings', views.SystemSettingsViewSet, basename='systemsettings')

urlpatterns = [
    path('auth/register/', views.register, name='register'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', views.profile, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('stats/', views.system_stats, name='system_stats'),
    path('', include(router.urls)),
]
