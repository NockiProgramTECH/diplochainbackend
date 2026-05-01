"""
diplomas/pdf_service.py
Génère le PDF du diplôme avec ReportLab.
"""
import os
import tempfile
from datetime import datetime

try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False


def generate_diploma_pdf(diploma_data: dict) -> bytes:
    """
    Génère un PDF de diplôme et retourne les bytes.
    """
    if not REPORTLAB_AVAILABLE:
        # Génère un PDF minimaliste sans ReportLab
        return _generate_simple_pdf(diploma_data)

    buffer = tempfile.SpooledTemporaryFile(max_size=10 * 1024 * 1024)

    p = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)

    # ... (code précédent de fond et en-tête) ...
    # ─── Fond ────────────────────────────────────────────────────
    p.setFillColor(colors.HexColor("#0D1521"))
    p.rect(0, 0, width, height, fill=True, stroke=False)

    # Bordure décorative
    p.setStrokeColor(colors.HexColor("#00E5FF"))
    p.setLineWidth(3)
    p.rect(1.5*cm, 1.5*cm, width - 3*cm, height - 3*cm, fill=False, stroke=True)
    p.setLineWidth(1)
    p.setStrokeColor(colors.HexColor("#7B2FFF"))
    p.rect(1.8*cm, 1.8*cm, width - 3.6*cm, height - 3.6*cm, fill=False, stroke=True)

    # ─── En-tête université ──────────────────────────────────────
    p.setFillColor(colors.HexColor("#00E5FF"))
    p.setFont("Helvetica-Bold", 22)
    p.drawCentredString(width/2, height - 3.5*cm,
                        diploma_data.get("university_name", "Université").upper())

    p.setFillColor(colors.HexColor("#4A6080"))
    p.setFont("Helvetica", 11)
    p.drawCentredString(width/2, height - 4.3*cm,
                        f"{diploma_data.get('university_city', '')} — {diploma_data.get('university_country', '')}")

    # Ligne séparatrice
    p.setStrokeColor(colors.HexColor("#1A2940"))
    p.setLineWidth(1)
    p.line(3*cm, height - 4.8*cm, width - 3*cm, height - 4.8*cm)

    # ─── Titre ───────────────────────────────────────────────────
    p.setFillColor(colors.HexColor("#C8D8E8"))
    p.setFont("Helvetica", 14)
    p.drawCentredString(width/2, height - 6*cm, "CERTIFIE AVOIR CONFERE LE TITRE DE")

    p.setFillColor(colors.HexColor("#00FF88"))
    p.setFont("Helvetica-Bold", 32)
    p.drawCentredString(width/2, height - 7.8*cm,
                        diploma_data.get("degree_title", "Diplôme").upper())

    p.setFillColor(colors.HexColor("#C8D8E8"))
    p.setFont("Helvetica", 13)
    p.drawCentredString(width/2, height - 8.8*cm,
                        f"Spécialité : {diploma_data.get('field_of_study', '')}")

    # ─── Étudiant ────────────────────────────────────────────────
    p.setFillColor(colors.HexColor("#4A6080"))
    p.setFont("Helvetica", 13)
    p.drawCentredString(width/2, height - 10*cm, "décerné à")

    p.setFillColor(colors.HexColor("#FFFFFF"))
    p.setFont("Helvetica-Bold", 26)
    full_name = f"{diploma_data.get('student_first_name', '')} {diploma_data.get('student_last_name', '')}".upper()
    p.drawCentredString(width/2, height - 11.4*cm, full_name)

    mention = diploma_data.get("mention", "")
    if mention:
        p.setFillColor(colors.HexColor("#FFD700"))
        p.setFont("Helvetica-Bold", 14)
        p.drawCentredString(width/2, height - 12.4*cm,
                            f"Mention : {mention.replace('_', ' ').title()}")

    year = diploma_data.get("graduation_year", "")
    p.setFillColor(colors.HexColor("#C8D8E8"))
    p.setFont("Helvetica", 12)
    p.drawCentredString(width/2, height - 13.4*cm, f"Promotion {year}")

    # ─── QR Code ─────────────────────────────────────────────────
    if QRCODE_AVAILABLE:
        diploma_id = str(diploma_data.get("diploma_id", ""))
        # On peut mettre l'URL de vérification ou juste l'ID
        qr_content = f"{diploma_id}"
        
        qr = qrcode.QRCode(version=1, box_size=10, border=1)
        qr.add_data(qr_content)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white")
        
        # Sauvegarder temporairement l'image
        temp_qr_path = os.path.join(tempfile.gettempdir(), f"qr_{diploma_id}.png")
        img_qr.save(temp_qr_path)
        
        # Dessiner le QR code en haut à droite (aligné avec la bordure intérieure)
        p.drawImage(temp_qr_path, width - 4.3*cm, height - 4.3*cm, width=2.5*cm, height=2.5*cm)
        
        # Nettoyage
        try: os.remove(temp_qr_path)
        except: pass

    # ─── Pied de page (données crypto) ──────────────────────────
    p.setFillColor(colors.HexColor("#1A2940"))
    p.rect(0, 0, width, 3.5*cm, fill=True, stroke=False)

    p.setFillColor(colors.HexColor("#4A6080"))
    p.setFont("Helvetica", 7)
    diploma_id = str(diploma_data.get("diploma_id", ""))
    issued_at = diploma_data.get("issued_at", datetime.now().strftime("%Y-%m-%d"))
    p.drawString(2*cm, 2.6*cm, f"ID : {diploma_id}")
    p.drawString(2*cm, 2.0*cm, f"Émis le : {issued_at}")
    p.drawRightString(width - 2*cm, 2.0*cm,
                      "Vérifiable sur : DiploChain — diplochainbf.com/verify")
    p.setFillColor(colors.HexColor("#00E5FF"))
    p.setFont("Helvetica-Bold", 7)
    p.drawCentredString(width/2, 1.0*cm,
                        "Ce document est protégé cryptographiquement — Toute falsification est détectable")

    p.showPage()
    p.save()

    buffer.seek(0)
    return buffer.read()


def _generate_simple_pdf(diploma_data: dict) -> bytes:
    """PDF minimal sans ReportLab (fallback)."""
    content = f"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 200>>stream
BT /F1 16 Tf 100 700 Td ({diploma_data.get('degree_title','Diplome')}) Tj ET
BT /F1 14 Tf 100 650 Td ({diploma_data.get('student_first_name','')} {diploma_data.get('student_last_name','')}) Tj ET
endstream endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
xref 0 6
trailer<</Size 6/Root 1 0 R>>
startxref 0 %%EOF"""
    return content.encode("latin-1")
