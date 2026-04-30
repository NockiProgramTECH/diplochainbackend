"""
diplomas/views.py
Vues principales : émission, signature, vérification, révocation.
"""
import os
import tempfile

from django.core.files.base import ContentFile
from django.conf import settings

from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Diploma
from .serializers import (
    DiplomaCreateSerializer,
    DiplomaDetailSerializer,
    DiplomaListSerializer,
    VerifyByFileSerializer,
    VerifyByHashSerializer,
    VerifyByScanSerializer,
    RevokeSerializer,
)
from .pdf_service import generate_diploma_pdf
from universities.crypto_service import (
    hash_bytes,
    hash_file,
    sign_diploma_hash,
    verify_diploma_signature,
    sign_hash_ethereum,
    verify_ethereum_signature,
)


# ══════════════════════════════════════════════════════════════
# ÉMISSION
# ══════════════════════════════════════════════════════════════

class DiplomaIssueView(APIView):
    """
    POST /api/diplomas/issue/

    Flux complet :
    1. Crée le diplôme en base
    2. Génère le PDF
    3. Calcule le hash SHA-256 du PDF
    4. Signe le hash avec la clé privée RSA de l'université
    5. Signe le hash avec la clé privée Ethereum (pour ancrage blockchain)
    6. Sauvegarde tout
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        university = request.user

        if not university.is_verified:
            return Response(
                {"error": "Votre université n'est pas encore vérifiée par un administrateur."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = DiplomaCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        diploma = serializer.save()

        # ── Étape 1 : Générer le PDF ──────────────────────────────
        try:
            pdf_bytes = generate_diploma_pdf({
                "student_first_name": diploma.student_first_name,
                "student_last_name":  diploma.student_last_name,
                "degree_title":       diploma.degree_title,
                "degree_level":       diploma.degree_level,
                "field_of_study":     diploma.field_of_study,
                "mention":            diploma.mention,
                "graduation_year":    diploma.graduation_year,
                "university_name":    university.name,
                "university_acronym": university.acronym,
                "university_city":    university.city,
                "university_country": university.country,
                "diploma_id":         str(diploma.id),
                "issued_at":          diploma.issued_at.strftime("%Y-%m-%d") if diploma.issued_at else "",
            })

            pdf_filename = f"diploma_{diploma.id}.pdf"
            diploma.pdf_file.save(pdf_filename, ContentFile(pdf_bytes), save=False)

        except Exception as e:
            diploma.delete()
            return Response(
                {"error": f"Erreur génération PDF: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ── Étape 2 : Hash SHA-256 du PDF ─────────────────────────
        file_hash = hash_bytes(pdf_bytes)
        diploma.file_hash = file_hash

        # ── Étape 3 : Signature RSA ───────────────────────────────
        try:
            rsa_sig = sign_diploma_hash(file_hash, university.private_key_pem)
            diploma.rsa_signature = rsa_sig
        except Exception as e:
            diploma.delete()
            return Response(
                {"error": f"Erreur signature RSA: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ── Étape 4 : Signature Ethereum ──────────────────────────
        try:
            eth_result = sign_hash_ethereum(file_hash, university.blockchain_private_key)
            diploma.eth_signature   = eth_result["eth_signature"]
            diploma.eth_message_hash = eth_result["message_hash"]
        except Exception as e:
            # Non bloquant — la signature Eth est un bonus
            diploma.eth_signature = ""

        # ── Étape 5 : Sauvegarde ──────────────────────────────────
        diploma.university_fingerprint_at_issue = university.crypto_fingerprint
        diploma.status = Diploma.STATUS_SIGNED
        diploma.save()

        return Response(
            {
                "message": "Diplôme émis et signé avec succès.",
                "diploma_id": str(diploma.id),
                "student": diploma.student_full_name,
                "degree": diploma.degree_title,
                "file_hash": file_hash,
                "rsa_signature": rsa_sig,
                "eth_signature": diploma.eth_signature,
                "university_address": university.blockchain_address,
                "university_fingerprint": university.crypto_fingerprint,
                "status": diploma.status,
                "pdf_url": request.build_absolute_uri(diploma.pdf_file.url) if diploma.pdf_file else None,
            },
            status=status.HTTP_201_CREATED,
        )


# ══════════════════════════════════════════════════════════════
# VÉRIFICATION
# ══════════════════════════════════════════════════════════════

class VerifyByFileView(APIView):
    """
    POST /api/diplomas/verify/file/
    Soumettre un fichier PDF pour vérification.
    Accessible publiquement (pas de token requis).
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyByFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["pdf_file"]
        diploma_id = serializer.validated_data.get("diploma_id")

        # Calculer le hash du fichier soumis
        file_bytes = uploaded_file.read()
        computed_hash = hash_bytes(file_bytes)

        # Chercher le diplôme en base
        try:
            if diploma_id:
                diploma = Diploma.objects.get(id=diploma_id, is_revoked=False)
            else:
                diploma = Diploma.objects.get(file_hash=computed_hash, is_revoked=False)
        except Diploma.DoesNotExist:
            return Response(
                {
                    "valid": False,
                    "reason": "not_found",
                    "computed_hash": computed_hash,
                    "message": "Aucun diplôme trouvé pour ce fichier. Diplôme inexistant ou révoqué.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Vérification 1 : Hash identique ?
        if computed_hash != diploma.file_hash:
            return Response(
                {
                    "valid": False,
                    "reason": "hash_mismatch",
                    "computed_hash": computed_hash,
                    "stored_hash": diploma.file_hash,
                    "message": "Le fichier a été modifié. Le hash ne correspond pas.",
                }
            )

        # Vérification 2 : Signature RSA valide ?
        valid, reason = verify_diploma_signature(
            diploma.file_hash,
            diploma.rsa_signature,
            diploma.university.public_key_pem,
        )

        if not valid:
            return Response(
                {
                    "valid": False,
                    "reason": reason,
                    "message": "Signature invalide. Ce diplôme est potentiellement frauduleux.",
                }
            )

        # Vérification 3 (bonus) : Empreinte université cohérente ?
        fingerprint_match = (
            diploma.university_fingerprint_at_issue == diploma.university.crypto_fingerprint
        )

        # Tout est OK ✅
        return Response(
            {
                "valid": True,
                "reason": "authentic",
                "message": "Diplôme AUTHENTIQUE. Toutes les vérifications sont passées.",
                "diploma": {
                    "id": str(diploma.id),
                    "student": diploma.student_full_name,
                    "degree": diploma.degree_title,
                    "field": diploma.field_of_study,
                    "mention": diploma.mention,
                    "year": diploma.graduation_year,
                    "issued_at": diploma.issued_at.isoformat(),
                },
                "university": {
                    "name": diploma.university.name,
                    "acronym": diploma.university.acronym,
                    "country": diploma.university.country,
                    "blockchain_address": diploma.university.blockchain_address,
                    "is_verified": diploma.university.is_verified,
                },
                "crypto": {
                    "hash_match": True,
                    "rsa_signature_valid": True,
                    "fingerprint_match": fingerprint_match,
                    "blockchain_anchored": diploma.is_blockchain_anchored,
                    "blockchain_tx": diploma.blockchain_tx_hash or None,
                },
            }
        )


class VerifyByHashView(APIView):
    """
    POST /api/diplomas/verify/hash/
    Vérification rapide par hash SHA-256.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyByHashSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file_hash = serializer.validated_data["file_hash"]

        try:
            diploma = Diploma.objects.get(file_hash=file_hash, is_revoked=False)
        except Diploma.DoesNotExist:
            return Response(
                {"valid": False, "reason": "not_found", "hash": file_hash},
                status=status.HTTP_404_NOT_FOUND,
            )

        valid, reason = verify_diploma_signature(
            diploma.file_hash,
            diploma.rsa_signature,
            diploma.university.public_key_pem,
        )

        return Response(
            {
                "valid": valid,
                "reason": reason,
                "diploma_id": str(diploma.id),
                "student": diploma.student_full_name,
                "university": diploma.university.name,
                "degree": diploma.degree_title,
                "issued_at": diploma.issued_at.isoformat(),
                "blockchain_anchored": diploma.is_blockchain_anchored,
            }
        )


class VerifyByScanView(APIView):
    """
    POST /api/diplomas/verify/scan/
    Vérification via scan de l'ID (depuis un QR code par exemple).
    Accessible publiquement pour les recruteurs.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyByScanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        diploma_id = serializer.validated_data["diploma_id"]
        student_last_name = serializer.validated_data.get("student_last_name")

        try:
            diploma = Diploma.objects.get(id=diploma_id)
        except Diploma.DoesNotExist:
            return Response(
                {"valid": False, "reason": "not_found", "message": "Diplôme introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Vérification si révoqué
        if diploma.is_revoked:
            return Response(
                {
                    "valid": False,
                    "reason": "revoked",
                    "message": "Ce diplôme a été révoqué par l'université.",
                    "revocation_reason": diploma.revocation_reason,
                }
            )

        # Vérification optionnelle du nom pour éviter les erreurs de scan
        if student_last_name and student_last_name.lower() != diploma.student_last_name.lower():
            return Response(
                {
                    "valid": False,
                    "reason": "name_mismatch",
                    "message": "Le nom ne correspond pas à l'ID scanné.",
                }
            )

        # Tout est OK ✅
        return Response(
            {
                "valid": True,
                "reason": "authentic",
                "message": "Diplôme AUTHENTIQUE.",
                "diploma": {
                    "id": str(diploma.id),
                    "student": diploma.student_full_name,
                    "degree": diploma.degree_title,
                    "field": diploma.field_of_study,
                    "mention": diploma.mention,
                    "year": diploma.graduation_year,
                    "issued_at": diploma.issued_at.isoformat(),
                },
                "university": {
                    "name": diploma.university.name,
                    "acronym": diploma.university.acronym,
                    "is_verified": diploma.university.is_verified,
                },
                "blockchain": {
                    "anchored": diploma.is_blockchain_anchored,
                    "tx_hash": diploma.blockchain_tx_hash or None,
                }
            }
        )


# ══════════════════════════════════════════════════════════════
# LISTE & DÉTAIL
# ══════════════════════════════════════════════════════════════

class MyDiplomasView(generics.ListAPIView):
    """GET /api/diplomas/ — Diplômes émis par l'université connectée."""
    serializer_class = DiplomaListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Diploma.objects.filter(university=self.request.user)


class DiplomaDetailView(generics.RetrieveAPIView):
    """GET /api/diplomas/<id>/ — Détail d'un diplôme (public)."""
    queryset = Diploma.objects.all()
    serializer_class = DiplomaDetailSerializer
    permission_classes = [permissions.AllowAny]


# ══════════════════════════════════════════════════════════════
# RÉVOCATION
# ══════════════════════════════════════════════════════════════

class RevokeDiplomaView(APIView):
    """
    POST /api/diplomas/<id>/revoke/
    Révoque un diplôme. Seule l'université émettrice peut révoquer.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            diploma = Diploma.objects.get(id=pk, university=request.user)
        except Diploma.DoesNotExist:
            return Response(
                {"error": "Diplôme introuvable ou non autorisé."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if diploma.is_revoked:
            return Response({"error": "Ce diplôme est déjà révoqué."})

        serializer = RevokeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        diploma.is_revoked = True
        diploma.status = Diploma.STATUS_REVOKED
        diploma.revocation_reason = serializer.validated_data["reason"]
        diploma.save()

        return Response(
            {
                "message": "Diplôme révoqué avec succès.",
                "diploma_id": str(diploma.id),
                "reason": diploma.revocation_reason,
            }
        )
