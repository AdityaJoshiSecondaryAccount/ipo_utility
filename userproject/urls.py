"""userproject URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
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
from django.urls import path, include
from django.http import HttpResponse

def unregister_service_worker(request):
    # Unregisters any stale service workers left in client browsers
    return HttpResponse("self.addEventListener('install', () => self.skipWaiting()); self.addEventListener('activate', () => self.registration.unregister());", content_type="application/javascript")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('serviceworker.js', unregister_service_worker),
    path('whatsapp/', include('whatsapp.urls')),
    path('', include('home.urls')),
    path('', include('pwa.urls')),
]
