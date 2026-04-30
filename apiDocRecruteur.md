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
