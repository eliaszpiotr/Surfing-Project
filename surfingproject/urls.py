"""
URL configuration for surfingproject project.

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
from django.views.static import serve
from django.urls import re_path
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path("accounts/", include("accounts.urls", namespace="accounts")),
    path("chat/", include("chat.urls", namespace="chat")),
    path("notifications/", include("notifications.urls", namespace="notifications")),
    path('spots/', include('spots.urls', namespace='spots')),
    path('surf_sessions/', include('surf_sessions.urls', namespace='surf_sessions')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif getattr(settings, "SERVE_MEDIA_LOCALLY", False):
    urlpatterns += [
        re_path(
            r"^%s(?P<path>.*)$" % settings.MEDIA_URL.lstrip("/"),
            serve,
            {"document_root": settings.MEDIA_ROOT},
        )
    ]
