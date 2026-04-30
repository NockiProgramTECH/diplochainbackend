"""
universities/models.py
Modele University — remplace le User Django standard.
Chaque universite possede une paire de cles cryptographiques
dont la cle publique est derivee des donnees blockchain (adresse Ethereum).
"""
import uuid
import hashlib
import base64

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend

try:
    from eth_account import Account
    ETH_AVAILABLE = True
except ImportError:
    ETH_AVAILABLE = False


class UniversityManager(BaseUserManager):
    def create_user(self, email, name, country, password=None, **extra_fields):
        if not email:
            raise ValueError("L'email est obligatoire")
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, country=country, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, country="BF", password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, name, country, password, **extra_fields)


class University(AbstractBaseUser, PermissionsMixin):
    """
    Utilisateur = Universite / Ecole
    La cle publique est derivee de l'adresse Ethereum (secp256k1).
    La cle privee est stockee chiffree (PEM) — en prod: utiliser un KMS.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Informations de l'institution
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, verbose_name="Nom de l'universite")
    acronym = models.CharField(max_length=20, verbose_name="Sigle (ex: UO, 2iE)")
    country = models.CharField(max_length=100, default="Burkina Faso")
    city = models.CharField(max_length=100, default="Ouagadougou")
    website = models.URLField(blank=True, null=True)
    logo = models.ImageField(upload_to="university_logos/", blank=True, null=True)

    # --- Cryptographie RSA (pour signer les diplomes) ---
    # Cle privee RSA chiffree en PEM (PKCS8 + AES256)
    private_key_pem = models.TextField(
        verbose_name="Cle privee RSA (PEM chiffre)",
        blank=True
    )
    # Cle publique RSA en PEM — calculee a partir de la privee
    public_key_pem = models.TextField(
        verbose_name="Cle publique RSA (PEM)",
        blank=True
    )

    # --- Donnees blockchain (Ethereum/Polygon) ---
    # Adresse Ethereum derivee depuis la cle privee secp256k1
    blockchain_address = models.CharField(
        max_length=42,
        unique=True,
        blank=True,
        verbose_name="Adresse Ethereum (blockchain)"
    )
    # Cle publique Ethereum (secp256k1 non compressee, hex)
    blockchain_public_key = models.TextField(
        blank=True,
        verbose_name="Cle publique Ethereum (secp256k1)"
    )
    # Cle privee Ethereum en hex — ATTENTION: a proteger avec KMS en prod
    blockchain_private_key = models.TextField(
        blank=True,
        verbose_name="Cle privee Ethereum (hex)"
    )

    # Empreinte combinee: hash(blockchain_address + rsa_public_key)
    # Sert d'identifiant cryptographique unique de l'universite
    crypto_fingerprint = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="Empreinte cryptographique (SHA256)"
    )

    # Django auth
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Universite verifiee par l'admin"
    )
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UniversityManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name", "country"]

    class Meta:
        verbose_name = "Universite"
        verbose_name_plural = "Universites"

    def __str__(self):
        return f"{self.name} ({self.acronym})"

    def compute_crypto_fingerprint(self):
        """
        Calcule l'empreinte cryptographique de l'universite:
        SHA256(blockchain_address + blockchain_public_key + rsa_public_key)
        
        Cette empreinte unique lie:
        - L'identite blockchain (adresse Ethereum)
        - La cle publique secp256k1 
        - La cle publique RSA de signature
        """
        raw = (
            self.blockchain_address.lower()
            + self.blockchain_public_key
            + self.public_key_pem
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def save(self, *args, **kwargs):
        # Recalcule l'empreinte a chaque sauvegarde si les cles existent
        if self.blockchain_address and self.public_key_pem:
            self.crypto_fingerprint = self.compute_crypto_fingerprint()
        super().save(*args, **kwargs)
