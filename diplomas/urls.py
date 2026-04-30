from django.urls import path
from . import views

urlpatterns = [
    # Émission
    path("diplomas/issue/", views.DiplomaIssueView.as_view(), name="diploma-issue"),
    # Liste (université connectée)
    path("diplomas/", views.MyDiplomasView.as_view(), name="diploma-list"),
    # Détail public
    path("diplomas/<uuid:pk>/", views.DiplomaDetailView.as_view(), name="diploma-detail"),
    # Révocation
    path("diplomas/<uuid:pk>/revoke/", views.RevokeDiplomaView.as_view(), name="diploma-revoke"),
    # Vérification — publique
    path("diplomas/verify/file/", views.VerifyByFileView.as_view(), name="diploma-verify-file"),
    path("diplomas/verify/hash/", views.VerifyByHashView.as_view(), name="diploma-verify-hash"),
    path("diplomas/verify/scan/", views.VerifyByScanView.as_view(), name="diploma-verify-scan"),
]
