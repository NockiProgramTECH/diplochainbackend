"""
diplomas/serializers.py
"""
from rest_framework import serializers
from .models import Diploma
from universities.serializers import UniversityPublicSerializer


class DiplomaCreateSerializer(serializers.ModelSerializer):
    """Création d'un diplôme — l'université est déduite du token JWT."""
    class Meta:
        model = Diploma
        fields = [
            "student_first_name", "student_last_name", "student_dob",
            "student_national_id",
            "degree_title", "degree_level", "field_of_study",
            "mention", "graduation_year",
        ]

    def create(self, validated_data):
        # L'université est automatiquement celle qui est connectée
        university = self.context["request"].user
        diploma = Diploma.objects.create(university=university, **validated_data)
        return diploma


class DiplomaDetailSerializer(serializers.ModelSerializer):
    """Détail complet d'un diplôme."""
    university = UniversityPublicSerializer(read_only=True)
    student_full_name = serializers.CharField(read_only=True)
    is_blockchain_anchored = serializers.BooleanField(read_only=True)

    class Meta:
        model = Diploma
        fields = [
            "id", "university",
            "student_full_name", "student_first_name", "student_last_name",
            "student_dob", "student_national_id",
            "degree_title", "degree_level", "field_of_study", "mention",
            "graduation_year",
            "file_hash", "rsa_signature", "university_fingerprint_at_issue",
            "eth_signature", "eth_message_hash",
            "blockchain_tx_hash", "blockchain_block_number",
            "status", "is_revoked", "revocation_reason",
            "is_blockchain_anchored",
            "issued_at", "updated_at",
        ]
        read_only_fields = fields


class DiplomaListSerializer(serializers.ModelSerializer):
    """Diplôme dans une liste."""
    university_name = serializers.CharField(source="university.name", read_only=True)
    student_full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Diploma
        fields = [
            "id", "university_name", "student_full_name",
            "degree_title", "degree_level", "field_of_study",
            "graduation_year", "status", "is_revoked",
            "file_hash", "issued_at",
        ]


class VerifyByFileSerializer(serializers.Serializer):
    """Vérification d'un diplôme en soumettant le fichier PDF."""
    pdf_file   = serializers.FileField(required=True)
    diploma_id = serializers.UUIDField(required=False)


class VerifyByHashSerializer(serializers.Serializer):
    """Vérification d'un diplôme par hash SHA-256."""
    file_hash = serializers.CharField(min_length=64, max_length=64)


class VerifyByScanSerializer(serializers.Serializer):
    """Vérification d'un diplôme via scan QR code (ID uniquement)."""
    diploma_id = serializers.UUIDField(required=True)
    # Optionnel : pour renforcer la vérification mobile
    student_last_name = serializers.CharField(required=False, allow_blank=True)


class RevokeSerializer(serializers.Serializer):
    """Révocation d'un diplôme."""
    reason = serializers.CharField(max_length=500, required=True)
