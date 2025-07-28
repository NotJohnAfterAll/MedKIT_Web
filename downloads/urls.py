from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'requests', views.DownloadRequestViewSet, basename='downloadrequest')
router.register(r'history', views.DownloadHistoryViewSet, basename='downloadhistory')

urlpatterns = [
    path('stats/', views.download_stats, name='download_stats'),
    path('video-info/', views.get_video_info, name='get_video_info'),
    path('video-info-progress/', views.get_video_info_with_progress, name='get_video_info_with_progress'),
    path('progress/<str:task_id>/', views.get_progress, name='get_progress'),
    path('download-progress/<str:download_id>/', views.get_download_progress, name='get_download_progress'),
    path('direct-download/', views.get_direct_download_url, name='get_direct_download_url'),
    path('direct-urls/', views.get_direct_urls, name='get_direct_urls'),  # NEW: True direct URLs
    path('stream/', views.stream_download, name='stream_download'),
    path('test/', views.test_download_page, name='test_download_page'),
    path('', include(router.urls)),
]
