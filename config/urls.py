"""
Root URL configuration for Tramper API.

Routing structure:
- /admin/                  - Django admin
- /api/v1/auth/           - Authentication endpoints
- /api/docs/              - Swagger UI documentation
- /api/redoc/             - ReDoc documentation
- /api/schema/            - OpenAPI schema
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),
    # API v1 - Authentication endpoints
    path("api/v1/auth/", include("apps.users.urls")),
    # API v1 - Trips endpoints
    path("api/v1/trips/", include("apps.trips.urls")),
    # API v1 - Shipments endpoints
    path("api/v1/shipments/", include("apps.shipments.urls")),
    # API v1 - Requests endpoints
    path("api/v1/requests/", include("apps.requests.urls")),
    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

# Serve media files in development
if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Enable debug toolbar in development
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns

# Configure admin site
admin.site.site_header = "Tramper Administration"
admin.site.site_title = "Tramper Admin"
admin.site.index_title = "Welcome to Tramper"
