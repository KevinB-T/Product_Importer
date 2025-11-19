from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),

    # Product management
    path("", include("products.urls")),              # Root → product list
    path("products/", include("products.urls")),     # Explicit products prefix

    # Webhooks
    path("webhooks/", include("webhooks.urls")),
]
