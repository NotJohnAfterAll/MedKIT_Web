from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'requests', views.ConversionRequestViewSet, basename='conversionrequest')
router.register(r'history', views.ConversionHistoryViewSet, basename='conversionhistory')

urlpatterns = [
    path('stats/', views.conversion_stats, name='conversion_stats'),
    path('supported-formats/', views.supported_formats, name='supported_formats'),
    path('', include(router.urls)),
]
