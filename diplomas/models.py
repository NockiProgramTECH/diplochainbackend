"""
diplomas/models.py
Modèle principal du diplôme avec hash, signature RSA et ancrage blockchain.
"""
import uuid
from django.db import models
from django.conf import settings


class Diploma(models.Model):
    """
    Diplôme certifié par une université.

    Cycle de vie:
    1. DRAFT      → créé mais pas encore signé
    2. SIGNED     → hash calculé + signature RSA générée
    3. ANCHORED   → hash ancré sur la blockchain Polygon
    4. REVOKED    → révoqué (fraude, erreur admin)
    """

    STATUS_DRAFT    = "draft"
    STATUS_SIGNED   = "signed"
    STATUS_ANCHORED = "anchored"
    STATUS_REVOKED  = "revoked"

    STATUS_CHOICES = [
        (STATUS_DRAFT,    "Brouillon"),
        (STATUS_SIGNED,   "Signé"),
        (STATUS_ANCHORED, "Ancré sur blockchain"),
        (STATUS_REVOKED,  "Révoqué"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # ─── Relation avec l'université émettrice ───────────────────
    university = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="diploma_set",
        verbose_name="Université émettrice",
    )

    # ─── Informations de l'étudiant ─────────────────────────────
    student_first_name = models.CharField(max_length=100)
    student_last_name  = models.CharField(max_length=100)
    student_dob        = models.DateField(verbose_name="Date de naissance", null=True, blank=True)
    student_national_id = models.CharField(
        max_length=50, blank=True,
        verbose_name="Numéro national d'identité"
    )

    # ─── Informations du diplôme ─────────────────────────────────
    degree_title   = models.CharField(max_length=255, verbose_name="Intitulé du diplôme")
    degree_level   = models.CharField(
        max_length=50,
        choices=[
            ("licence", "Licence (Bac+3)"),
            ("master",  "Master (Bac+5)"),
            ("doctorat","Doctorat (Bac+8)"),
            ("bts",     "BTS"),
            ("dut",     "DUT"),
            ("ingenieur","Diplôme d'Ingénieur"),
            ("autre",   "Autre"),
        ],
        default="licence",
    )
    field_of_study = models.CharField(max_length=255, verbose_name="Filière / Spécialité")
    mention        = models.CharField(
        max_length=50,
        choices=[
            ("passable", "Passable"),
            ("assez_bien", "Assez Bien"),
            ("bien", "Bien"),
            ("tres_bien", "Très Bien"),
            ("excellent", "Excellent"),
        ],
        blank=True,
    )
    graduation_year = models.PositiveIntegerField(verbose_name="Année d'obtention")

    # ─── Fichier PDF ─────────────────────────────────────────────
    pdf_file = models.FileField(
        upload_to="diplomas/pdf/",
        blank=True,
        null=True,
        verbose_name="Fichier PDF du diplôme",
    )

    # ─── Cryptographie ───────────────────────────────────────────
    # Hash SHA-256 du fichier PDF
    file_hash = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="Hash SHA-256 du PDF",
        db_index=True,
    )
    # Signature RSA du hash avec la clé privée de l'université
    rsa_signature = models.TextField(
        blank=True,
        verbose_name="Signature RSA (base64)",
    )
    # Empreinte cryptographique de l'université au moment de l'émission
    university_fingerprint_at_issue = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="Empreinte crypto université (au moment d'émission)",
    )

    # ─── Données blockchain ──────────────────────────────────────
    # Signature Ethereum du hash (secp256k1)
    eth_signature = models.TextField(
        blank=True,
        verbose_name="Signature Ethereum (secp256k1)",
    )
    eth_message_hash = models.CharField(
        max_length=66,
        blank=True,
        verbose_name="Hash du message Ethereum signé",
    )
    # Transaction hash si le diplôme est ancré on-chain
    blockchain_tx_hash = models.CharField(
        max_length=66,
        blank=True,
        verbose_name="Transaction hash blockchain",
    )
    blockchain_block_number = models.PositiveBigIntegerField(
        null=True, blank=True,
        verbose_name="Numéro de bloc",
    )

    # ─── Statut ──────────────────────────────────────────────────
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    is_revoked = models.BooleanField(default=False)
    revocation_reason = models.TextField(blank=True)

    issued_at  = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Diplôme"
        verbose_name_plural = "Diplômes"
        ordering = ["-issued_at"]

    def __str__(self):
        return f"{self.student_last_name} {self.student_first_name} — {self.degree_title} ({self.university.acronym})"

    @property
    def student_full_name(self):
        return f"{self.student_first_name} {self.student_last_name}"

    @property
    def is_blockchain_anchored(self):
        return bool(self.blockchain_tx_hash)
