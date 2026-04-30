"""
universities/serializers.py
Sérialiseurs pour l'enregistrement, l'authentification et le profil université.
"""
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

from .models import University
from .crypto_service import generate_university_keypairs


class UniversityRegisterSerializer(serializers.ModelSerializer):
    """
    Enregistrement d'une nouvelle université.
    Génère automatiquement les paires de clés cryptographiques.
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )

    class Meta:
        model = University
        fields = [
            "id", "email", "name", "acronym",
            "country", "city", "website",
            "password", "password_confirm",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password": "Les mots de passe ne correspondent pas."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        # Génération automatique des clés cryptographiques
        try:
            keys = generate_university_keypairs(chain_id=80002)
        except Exception as e:
            raise serializers.ValidationError(
                {"crypto": f"Erreur de génération des clés: {str(e)}"}
            )

        university = University(
            **validated_data,
            # Blockchain
            blockchain_private_key=keys["blockchain_private_key"],
            blockchain_public_key=keys["blockchain_public_key"],
            blockchain_address=keys["blockchain_address"],
            # RSA
            private_key_pem=keys["private_key_pem"],
            public_key_pem=keys["public_key_pem"],
            # Empreinte
            crypto_fingerprint=keys["crypto_fingerprint"],
        )
        university.set_password(password)
        university.save()
        return university


class UniversityPublicSerializer(serializers.ModelSerializer):
    """
    Profil public d'une université — exposé pour la vérification des diplômes.
    Jamais la clé privée.
    """
    diplomas_count = serializers.SerializerMethodField()

    class Meta:
        model = University
        fields = [
            "id", "name", "acronym", "country", "city", "website",
            "blockchain_address", "blockchain_public_key",
            "public_key_pem", "crypto_fingerprint",
            "is_verified", "date_joined", "diplomas_count",
        ]

    def get_diplomas_count(self, obj):
        return obj.diploma_set.filter(is_revoked=False).count()


class UniversityProfileSerializer(serializers.ModelSerializer):
    """
    Profil complet — réservé à l'université elle-même (authentifiée).
    Inclut les infos blockchain mais PAS la clé privée RSA.
    """
    class Meta:
        model = University
        fields = [
            "id", "email", "name", "acronym", "country", "city",
            "website", "logo",
            "blockchain_address", "blockchain_public_key",
            "public_key_pem", "crypto_fingerprint",
            "is_verified", "date_joined",
        ]
        read_only_fields = [
            "id", "blockchain_address", "blockchain_public_key",
            "public_key_pem", "crypto_fingerprint", "date_joined",
        ]


class UniversityKeysSerializer(serializers.ModelSerializer):
    """
    Export des clés — retourne TOUTES les clés y compris privées.
    Réservé à l'université authentifiée, à utiliser avec précaution.
    """
    class Meta:
        model = University
        fields = [
            "id", "name",
            "blockchain_address",
            "blockchain_public_key",
            "blockchain_private_key",
            "public_key_pem",
            "private_key_pem",
            "crypto_fingerprint",
        ]
