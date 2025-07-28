"""
URL configuration for medkit_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.views.static import serve
from django.shortcuts import render
from django.views.generic import TemplateView
import os

def api_status(request):
    return JsonResponse({
        'status': 'MedKIT API is running',
        'version': '1.0.0',
        'endpoints': {
            'admin': '/admin/',
            'auth': '/api/auth/',
            'downloads': '/api/downloads/',
            'conversions': '/api/conversions/'
        }
    })

class FrontendAppView(TemplateView):
    """Serve the Next.js frontend application"""
    
    def get(self, request, *args, **kwargs):
        try:
            # For the root path, serve index.html
            if request.path == '/' or request.path == '':
                frontend_path = os.path.join(settings.FRONTEND_BUILD_DIR, 'index.html')
            else:
                # For other paths, try to serve the corresponding HTML file
                path_parts = request.path.strip('/').split('/')
                if path_parts and path_parts[0]:
                    html_file = f"{path_parts[0]}/index.html"
                    frontend_path = os.path.join(settings.FRONTEND_BUILD_DIR, html_file)
                    
                    # If specific page doesn't exist, serve the main index.html (SPA fallback)
                    if not os.path.exists(frontend_path):
                        frontend_path = os.path.join(settings.FRONTEND_BUILD_DIR, 'index.html')
                else:
                    frontend_path = os.path.join(settings.FRONTEND_BUILD_DIR, 'index.html')
            
            # Read and serve the HTML file
            if os.path.exists(frontend_path):
                with open(frontend_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                from django.http import HttpResponse
                return HttpResponse(content, content_type='text/html')
            else:
                # Fallback to a basic response if file doesn't exist
                return HttpResponse('Frontend not found', status=404)
                
        except Exception as e:
            return HttpResponse(f'Error serving frontend: {str(e)}', status=500)

urlpatterns = [
    path('api-status/', api_status, name='api_status'),
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
    path('api/downloads/', include('downloads.urls')),
    path('api/conversions/', include('conversions.urls')),
    
    # Serve frontend static files
    re_path(r'^_next/(?P<path>.*)$', serve, {
        'document_root': os.path.join(settings.FRONTEND_BUILD_DIR, '_next'),
    }),
    re_path(r'^(?P<path>.*\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot))$', serve, {
        'document_root': settings.FRONTEND_BUILD_DIR,
    }),
    
    # Catch-all pattern for frontend routes (exclude specific patterns)
    re_path(r'^(?!api/|admin/|_next/).*$', FrontendAppView.as_view(), name='frontend'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
