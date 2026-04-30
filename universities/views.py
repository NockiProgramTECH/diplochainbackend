"""
universities/views.py
"""
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import University
from .serializers import (
    UniversityRegisterSerializer,
    UniversityPublicSerializer,
    UniversityProfileSerializer,
    UniversityKeysSerializer,
)


class RegisterUniversityView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    Enregistre une nouvelle université et génère ses clés cryptographiques.
    """
    queryset = University.objects.all()
    serializer_class = UniversityRegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        university = serializer.save()

        return Response(
            {
                "message": "Université enregistrée avec succès.",
                "university_id": str(university.id),
                "name": university.name,
                "blockchain_address": university.blockchain_address,
                "crypto_fingerprint": university.crypto_fingerprint,
                "public_key_pem": university.public_key_pem,
                "warning": (
                    "Conservez vos clés privées en lieu sûr. "
                    "Récupérez-les via GET /api/auth/keys/ (authentification requise)."
                ),
            },
            status=status.HTTP_201_CREATED,
        )


class MyProfileView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/auth/profile/  — Profil de l'université connectée
    PUT  /api/auth/profile/  — Mise à jour du profil
    """
    serializer_class = UniversityProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class MyKeysView(APIView):
    """
    GET /api/auth/keys/
    Retourne toutes les clés (publiques ET privées) de l'université authentifiée.
    ATTENTION: endpoint sensible — à sécuriser davantage en production.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UniversityKeysSerializer(request.user)
        return Response(
            {
                "warning": (
                    "CES DONNÉES SONT CONFIDENTIELLES. "
                    "Ne partagez JAMAIS vos clés privées."
                ),
                "keys": serializer.data,
            }
        )


class UniversityPublicDetailView(generics.RetrieveAPIView):
    """
    GET /api/universities/<id>/
    Profil public d'une université (pour vérification externe).
    """
    queryset = University.objects.filter(is_active=True)
    serializer_class = UniversityPublicSerializer
    permission_classes = [permissions.AllowAny]


class UniversityListView(generics.ListAPIView):
    """
    GET /api/universities/
    Liste des universités vérifiées.
    """
    queryset = University.objects.filter(is_active=True, is_verified=True)
    serializer_class = UniversityPublicSerializer
    permission_classes = [permissions.AllowAny]
