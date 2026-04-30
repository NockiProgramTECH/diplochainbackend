from django.contrib import admin
from .models import Diploma


@admin.register(Diploma)
class DiplomaAdmin(admin.ModelAdmin):
    list_display = ["student_full_name", "degree_title", "university", "graduation_year", "status", "is_revoked", "issued_at"]
    list_filter  = ["status", "is_revoked", "degree_level", "graduation_year"]
    search_fields = ["student_first_name", "student_last_name", "file_hash", "university__name"]
    readonly_fields = ["id", "file_hash", "rsa_signature", "eth_signature", "eth_message_hash",
                       "blockchain_tx_hash", "university_fingerprint_at_issue", "issued_at", "updated_at"]
    ordering = ["-issued_at"]
    fieldsets = (
        ("Étudiant", {"fields": ("student_first_name", "student_last_name", "student_dob", "student_national_id")}),
        ("Diplôme",  {"fields": ("university", "degree_title", "degree_level", "field_of_study", "mention", "graduation_year")}),
        ("Fichier",  {"fields": ("pdf_file",)}),
        ("Crypto",   {"fields": ("file_hash", "rsa_signature", "eth_signature", "eth_message_hash", "university_fingerprint_at_issue"), "classes": ("collapse",)}),
        ("Blockchain",{"fields": ("blockchain_tx_hash", "blockchain_block_number"), "classes": ("collapse",)}),
        ("Statut",   {"fields": ("status", "is_revoked", "revocation_reason", "issued_at", "updated_at")}),
    )
