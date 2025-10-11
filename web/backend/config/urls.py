"""URL configuration for the Quant web backend."""
from __future__ import annotations

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("web.backend.api.urls")),
]
