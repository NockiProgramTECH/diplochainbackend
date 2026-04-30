from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

urlpatterns = [
    # Auth
    path("auth/register/", views.RegisterUniversityView.as_view(), name="university-register"),
    path("auth/login/", TokenObtainPairView.as_view(), name="university-login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/profile/", views.MyProfileView.as_view(), name="university-profile"),
    path("auth/keys/", views.MyKeysView.as_view(), name="university-keys"),
    # Public
    path("universities/", views.UniversityListView.as_view(), name="university-list"),
    path("universities/<uuid:pk>/", views.UniversityPublicDetailView.as_view(), name="university-detail"),
]
