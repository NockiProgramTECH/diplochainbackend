# DiploChain — Backend Django

Système de certification de diplômes par cryptographie et blockchain.  
Développé pour le contexte burkinabè (MIABE Hackathon 2026 — Equipe-BF-10).

---

## Stack technique

| Couche | Technologie |
|---|---|
| Backend API | Django 4.2 + Django REST Framework |
| Authentification | JWT (simplejwt) |
| Crypto diplômes | RSA-2048 (bibliothèque `cryptography`) |
| Crypto blockchain | secp256k1 via `eth-account` / `eth-keys` |
| Génération PDF | ReportLab |
| Base de données | SQLite (dev) / PostgreSQL (prod) |
| Blockchain | Polygon Amoy Testnet (chain_id 80002) |

---

## Architecture des clés cryptographiques

Chaque université possède **deux paires de clés** liées cryptographiquement :

```
┌─────────────────────────────────────────────────────────────┐
│  UNIVERSITÉ                                                  │
│                                                             │
│  1. Clé Ethereum (secp256k1)                                │
│     private_key  ──derive──►  public_key  ──derive──► adresse│
│                                                             │
│  2. Clé RSA-2048 (signature diplômes)                       │
│     private_key  ──derive──►  public_key_PEM                │
│                                                             │
│  3. Empreinte cryptographique (fingerprint)                 │
│     SHA256(adresse_eth + pubkey_eth_hex + pubkey_rsa_pem)   │
│     → Lien immuable entre identité blockchain + capacité    │
│       de signature des diplômes                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Installation

```bash
# 1. Cloner et créer l'environnement
git clone <repo>
cd diplochainbackend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Variables d'environnement
cp .env.example .env
# Éditer .env avec vos valeurs

# 4. Migrations
python manage.py migrate

# 5. Créer un superadmin
python manage.py createsuperuser

# 6. Lancer le serveur
python manage.py runserver
```

---

## Routes API

### Authentification (Universités)

| Méthode | Route | Description | Auth |
|---|---|---|---|
| POST | `/api/auth/register/` | Enregistrement + génération auto des clés | Public |
| POST | `/api/auth/login/` | Connexion → retourne access + refresh token | Public |
| POST | `/api/auth/token/refresh/` | Renouveler le token | Public |
| GET | `/api/auth/profile/` | Profil de l'université connectée | 🔒 JWT |
| GET | `/api/auth/keys/` | Voir toutes les clés (publiques + privées) | 🔒 JWT |

### Universités

| Méthode | Route | Description | Auth |
|---|---|---|---|
| GET | `/api/universities/` | Liste des universités vérifiées | Public |
| GET | `/api/universities/<id>/` | Profil public d'une université | Public |

### Diplômes

| Méthode | Route | Description | Auth |
|---|---|---|---|
| POST | `/api/diplomas/issue/` | Émettre + signer un diplôme | 🔒 JWT |
| GET | `/api/diplomas/` | Diplômes émis par l'université connectée | 🔒 JWT |
| GET | `/api/diplomas/<id>/` | Détail d'un diplôme | Public |
| POST | `/api/diplomas/<id>/revoke/` | Révoquer un diplôme | 🔒 JWT |
| POST | `/api/diplomas/verify/file/` | Vérifier par fichier PDF soumis | Public |
| POST | `/api/diplomas/verify/hash/` | Vérification rapide par hash SHA-256 | Public |

---

# Documentation API pour les Recruteurs - DiploChain

Cette documentation détaille comment utiliser l'API DiploChain pour vérifier l'authenticité d'un diplôme via une application mobile.

## 1. Flux de Vérification Mobile

1.  **Scan du Diplôme** : Le recruteur utilise l'application mobile pour scanner le **QR Code** présent sur le diplôme PDF (en bas à droite).
2.  **Extraction** : Le QR Code contient une URL ou directement l'**ID du diplôme** (UUID).
    *   Exemple d'ID scanné : `e94ac5d8-474a-487e-87e7-bf9206e41e14`
3.  **Appel API** : L'application mobile envoie cet ID à l'API de vérification.
4.  **Résultat** : L'API répond si le diplôme est authentique, révoqué ou inexistant.

---

## 2. Point de terminaison (Endpoint)

### Vérifier par Scan
Permet de vérifier un diplôme en envoyant son identifiant unique.

*   **URL** : `/api/diplomas/verify/scan/`
*   **Méthode** : `POST`
*   **Authentification** : Aucune (Public)
*   **Format de données** : `JSON`

#### Requête (Body)
| Champ | Type | Obligatoire | Description |
| :--- | :--- | :--- | :--- |
| `diploma_id` | UUID | Oui | L'identifiant extrait du QR Code. |
| `student_last_name` | String | Non | Nom de famille de l'étudiant (pour double vérification). |

**Exemple de requête :**
```json
{
    "diploma_id": "e94ac5d8-474a-487e-87e7-bf9206e41e14",
    "student_last_name": "DOE"
}
```

---

## 3. Réponses de l'API

### Cas 1 : Diplôme Authentique ✅
**Code HTTP : 200 OK**
```json
{
    "valid": true,
    "reason": "authentic",
    "message": "Diplôme AUTHENTIQUE.",
    "diploma": {
        "id": "e94ac5d8-474a-487e-87e7-bf9206e41e14",
        "student": "John DOE",
        "degree": "Master en Informatique",
        "field": "Intelligence Artificielle",
        "mention": "bien",
        "year": 2024,
        "issued_at": "2024-04-29T10:00:00Z"
    },
    "university": {
        "name": "Université Polytechnique",
        "acronym": "UPB",
        "is_verified": true
    },
    "blockchain": {
        "anchored": true,
        "tx_hash": "0xabc123..."
    }
}
```

### Cas 2 : Diplôme Révoqué ❌
**Code HTTP : 200 OK** (Le diplôme existe mais n'est plus valide)
```json
{
    "valid": false,
    "reason": "revoked",
    "message": "Ce diplôme a été révoqué par l'université.",
    "revocation_reason": "Erreur administrative lors de la saisie des notes."
}
```

### Cas 3 : Incohérence de Nom ⚠️
**Code HTTP : 200 OK** (Si `student_last_name` a été fourni et ne correspond pas)
```json
{
    "valid": false,
    "reason": "name_mismatch",
    "message": "Le nom ne correspond pas à l'ID scanné."
}
```

### Cas 4 : Diplôme Introuvable / Faux 🚫
**Code HTTP : 404 Not Found**
```json
{
    "valid": false,
    "reason": "not_found",
    "message": "Diplôme introuvable."
}
```

---

## 4. Recommandations pour l'application mobile

*   **Gestion du QR Code** : Utilisez une bibliothèque comme `zxing` (Android) ou `AVFoundation` (iOS) pour scanner le code.
*   **Affichage** : Si `valid` est `true`, affichez un badge vert "Vérifié" avec les informations de l'étudiant pour que le recruteur puisse comparer avec le document physique/PDF.
*   **Sécurité** : Ne stockez pas les données des étudiants localement après la vérification pour respecter la confidentialité des données (RGPD).

---

### Documentation API (sWAGGER)
| Méthode | Route | Description | Auth |
|---|---|---|---|
| GET | `/api/schema/swagger-ui/` | Documentation interactive (Swagger UI) | Public |
Générée automatiquement par `drf-yasg` à partir des vues et serializers.
|GET | `/api/schema/redoc/` | Documentation alternative (ReDoc) | Public |
|GET | `/api/schema/` | Schéma OpenAPI brut (JSON) | Public





## Flux d'émission d'un diplôme

```
POST /api/diplomas/issue/
         │
         ▼
  1. Crée le diplôme en base (status: draft)
         │
         ▼
  2. Génère le PDF (ReportLab)
         │
         ▼
  3. hash = SHA256(pdf_bytes)
         │
         ▼
  4. rsa_signature = RSA_sign(hash, university.private_key_pem)
         │
         ▼
  5. eth_signature = ETH_sign(hash, university.blockchain_private_key)
         │
         ▼
  6. Sauvegarde: hash + rsa_sig + eth_sig → DB  (status: signed)
         │
         ▼
  7. Retourne: diploma_id, hash, signatures, pdf_url
```

## Flux de vérification

```
POST /api/diplomas/verify/file/  { pdf_file }
         │
         ▼
  1. computed_hash = SHA256(uploaded_pdf)
         │
         ▼
  2. Cherche diplôme par hash en base
         │
         ▼
  3. computed_hash == stored_hash ?  ──NON──► hash_mismatch ❌
         │ OUI
         ▼
  4. RSA_verify(stored_hash, stored_signature, university.public_key) ?
         │                    ──NON──► invalid_signature ❌
         │ OUI
         ▼
  5. Fingerprint université cohérent ? (vérification bonus)
         │
         ▼
  6. → DIPLÔME AUTHENTIQUE ✅
```

---

## Variables d'environnement (.env)

```env
SECRET_KEY=votre-cle-secrete-django
DEBUG=True
BLOCKCHAIN_RPC_URL=https://rpc-amoy.polygon.technology
BLOCKCHAIN_CHAIN_ID=80002
CONTRACT_ADDRESS=0x... (adresse du smart contract après déploiement)
```

---

## Structure du projet

```
diplochainbackend/
├── config/
│   ├── settings.py       # Configuration Django
│   └── urls.py           # Routes principales
├── universities/
│   ├── models.py         # Modèle University (custom User)
│   ├── crypto_service.py # ⭐ Toute la cryptographie
│   ├── serializers.py    # Sérialiseurs DRF
│   ├── views.py          # Vues API
│   └── urls.py           # Routes /auth/ et /universities/
├── diplomas/
│   ├── models.py         # Modèle Diploma
│   ├── pdf_service.py    # Génération PDF (ReportLab)
│   ├── serializers.py    # Sérialiseurs DRF
│   ├── views.py          # Vues API (issue, verify, revoke)
│   └── urls.py           # Routes /diplomas/
├── requirements.txt
├── .env.example
└── manage.py
```



