"""
DiploChain — URL principal
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView


@api_view(["GET"])
@permission_classes([AllowAny])
def api_root(request):
    return Response({
        "project": "DiploChain API",
        "version": "1.0.0",
        "description": "Système de certification de diplômes — Burkina Faso",
        "documentation": {
            "swagger":        "/api/schema/swagger-ui/",
            "redoc":          "/api/schema/redoc/",
            "schema_json":    "/api/schema/",
        },
        "endpoints": {
            "auth": {
                "register":       "/api/auth/register/",
                "login":          "/api/auth/login/",
                "token_refresh":  "/api/auth/token/refresh/",
                "profile":        "/api/auth/profile/",
                "my_keys":        "/api/auth/keys/",
            },
            "universities": {
                "list":           "/api/universities/",
                "detail":         "/api/universities/<id>/",
            },
            "diplomas": {
                "issue":          "/api/diplomas/issue/",
                "list":           "/api/diplomas/",
                "detail":         "/api/diplomas/<id>/",
                "revoke":         "/api/diplomas/<id>/revoke/",
                "verify_file":    "/api/diplomas/verify/file/",
                "verify_hash":    "/api/diplomas/verify/hash/",
            },
        },
    })


urlpatterns = [
    path("admin/", admin.site.urls),
    # Schema and Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    
    path("api/", api_root),
    path("api/", include("universities.urls")),
    path("api/", include("diplomas.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
