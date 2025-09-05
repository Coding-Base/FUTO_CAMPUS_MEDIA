# futo_media/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import routers
from blog.views import PostViewSet

router = routers.DefaultRouter()
router.register(r"posts", PostViewSet, basename="post")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
]

# Serve media files in DEBUG for local dev
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
