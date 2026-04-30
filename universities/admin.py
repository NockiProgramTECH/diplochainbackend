from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import University


@admin.register(University)
class UniversityAdmin(UserAdmin):
    list_display = ["name", "acronym", "email", "country", "is_verified", "is_active", "date_joined"]
    list_filter = ["is_verified", "is_active", "country"]
    search_fields = ["name", "email", "acronym", "blockchain_address"]
    ordering = ["-date_joined"]

    fieldsets = (
        ("Informations", {"fields": ("email", "name", "acronym", "country", "city", "website", "logo")}),
        ("Cryptographie RSA", {"fields": ("public_key_pem", "private_key_pem"), "classes": ("collapse",)}),
        ("Blockchain", {"fields": ("blockchain_address", "blockchain_public_key", "crypto_fingerprint"), "classes": ("collapse",)}),
        ("Statut", {"fields": ("is_active", "is_verified", "is_staff", "is_superuser")}),
        ("Permissions", {"fields": ("groups", "user_permissions"), "classes": ("collapse",)}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "name", "acronym", "country", "password1", "password2"),
        }),
    )

    readonly_fields = ["crypto_fingerprint", "blockchain_address", "blockchain_public_key", "public_key_pem"]
