"""
universities/crypto_service.py

Service centralise pour toute la cryptographie de DiploChain.

Architecture des cles :
1. Cle Ethereum (secp256k1) → adresse blockchain (identite on-chain)
   La cle publique secp256k1 est derivee mathematiquement de la cle privee.

2. Cle RSA-2048 (pour signer les diplomes PDF)
   La cle PUBLIQUE RSA est calculee depuis la cle privee RSA.
   Elle est liee aux donnees blockchain via l'empreinte cryptographique.

3. Empreinte (Fingerprint)
   SHA256(blockchain_address + secp256k1_pubkey_hex + rsa_pubkey_pem)
   Lien cryptographique entre identite blockchain et capacite de signature.
"""

import os
import base64
import hashlib
from typing import Tuple, Dict

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

try:
    from eth_account import Account
    from eth_account.messages import encode_defunct
    from eth_keys import keys as eth_keys_lib
    ETH_AVAILABLE = True
except ImportError:
    ETH_AVAILABLE = False


# ══════════════════════════════════════════════════════════════
# 1. GENERATION DE CLES ETHEREUM (secp256k1)
# ══════════════════════════════════════════════════════════════

def generate_ethereum_keypair() -> Dict[str, str]:
    """
    Genere une paire de cles Ethereum (secp256k1).
    Returns:
        private_key_hex, public_key_hex, address
    """
    if not ETH_AVAILABLE:
        raise RuntimeError("eth_account non installe. pip install eth-account eth-keys")

    account = Account.create()
    priv_hex = account.key.hex()  # "0xabcdef..."

    # Padder a 32 bytes — certaines cles commencent par 0x00
    priv_bytes = bytes.fromhex(priv_hex[2:])
    priv_bytes = priv_bytes.rjust(32, b'\x00')

    priv_key_obj = eth_keys_lib.PrivateKey(priv_bytes)
    pub_key_obj  = priv_key_obj.public_key

    return {
        "private_key_hex": "0x" + priv_bytes.hex(),
        "public_key_hex": pub_key_obj.to_hex(),
        "address": account.address,
    }


# ══════════════════════════════════════════════════════════════
# 2. GENERATION DE CLES RSA-2048
#    La cle publique est derivee mathematiquement de la privee
#    ET son empreinte est liee aux donnees blockchain
# ══════════════════════════════════════════════════════════════

def generate_rsa_keypair(
    blockchain_address: str,
    blockchain_pubkey_hex: str,
    chain_id: int = 80002,
) -> Dict[str, str]:
    """
    Genere une paire RSA-2048 pour la signature de diplomes.

    La cle publique RSA est calculee depuis la cle privee RSA,
    puis son empreinte est liee a l'adresse blockchain.
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    # Derivation mathematique: cle publique depuis cle privee RSA
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    # Empreinte liant RSA + Blockchain
    raw_fp = (
        blockchain_address.lower()
        + blockchain_pubkey_hex
        + public_pem.strip()
    ).encode("utf-8")
    key_fingerprint = "sha256:" + hashlib.sha256(raw_fp).hexdigest()

    return {
        "private_key_pem": private_pem,
        "public_key_pem": public_pem,
        "key_fingerprint": key_fingerprint,
        "linked_address": blockchain_address,
        "linked_chain_id": chain_id,
    }


# ══════════════════════════════════════════════════════════════
# 3. GENERATION COMPLETE (Ethereum + RSA liees)
# ══════════════════════════════════════════════════════════════

def generate_university_keypairs(chain_id: int = 80002) -> Dict:
    """
    Genere l'ensemble complet des cles cryptographiques d'une universite.
    - Paire Ethereum (secp256k1)   → adresse blockchain
    - Paire RSA-2048                → signature diplomes
    - Empreinte cryptographique     → lien entre les deux
    """
    eth = generate_ethereum_keypair()

    rsa_data = generate_rsa_keypair(
        blockchain_address=eth["address"],
        blockchain_pubkey_hex=eth["public_key_hex"],
        chain_id=chain_id,
    )

    # Empreinte finale: SHA256(adresse_eth + pubkey_eth + pubkey_rsa)
    crypto_fingerprint = hashlib.sha256(
        (
            eth["address"].lower()
            + eth["public_key_hex"]
            + rsa_data["public_key_pem"].strip()
        ).encode()
    ).hexdigest()

    return {
        "blockchain_private_key": eth["private_key_hex"],
        "blockchain_public_key":  eth["public_key_hex"],
        "blockchain_address":     eth["address"],
        "private_key_pem":        rsa_data["private_key_pem"],
        "public_key_pem":         rsa_data["public_key_pem"],
        "crypto_fingerprint":     crypto_fingerprint,
        "rsa_key_fingerprint":    rsa_data["key_fingerprint"],
        "chain_id":               chain_id,
    }


# ══════════════════════════════════════════════════════════════
# 4. HASH SHA-256
# ══════════════════════════════════════════════════════════════

def hash_file(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ══════════════════════════════════════════════════════════════
# 5. SIGNATURE RSA
# ══════════════════════════════════════════════════════════════

def sign_diploma_hash(file_hash: str, private_key_pem: str) -> str:
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"),
        password=None,
        backend=default_backend(),
    )
    signature = private_key.sign(
        file_hash.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("utf-8")


# ══════════════════════════════════════════════════════════════
# 6. VERIFICATION SIGNATURE RSA
# ══════════════════════════════════════════════════════════════

def verify_diploma_signature(
    file_hash: str,
    signature_b64: str,
    public_key_pem: str,
) -> Tuple[bool, str]:
    try:
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode("utf-8"),
            backend=default_backend(),
        )
        signature = base64.b64decode(signature_b64)
        public_key.verify(
            signature,
            file_hash.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True, "valid"
    except InvalidSignature:
        return False, "invalid_signature"
    except Exception as e:
        return False, f"error:{str(e)}"


# ══════════════════════════════════════════════════════════════
# 7. SIGNATURE ETHEREUM
# ══════════════════════════════════════════════════════════════

def sign_hash_ethereum(file_hash: str, eth_private_key_hex: str) -> Dict[str, str]:
    if not ETH_AVAILABLE:
        raise RuntimeError("eth_account non installe")
    account = Account.from_key(eth_private_key_hex)
    message = encode_defunct(text=file_hash)
    signed = account.sign_message(message)
    return {
        "eth_signature":  signed.signature.hex(),
        "signer_address": account.address,
        "message_hash":   signed.messageHash.hex(),
    }


def verify_ethereum_signature(
    file_hash: str,
    eth_signature_hex: str,
    expected_address: str,
) -> bool:
    if not ETH_AVAILABLE:
        raise RuntimeError("eth_account non installe")
    message = encode_defunct(text=file_hash)
    recovered = Account.recover_message(
        message, signature=bytes.fromhex(eth_signature_hex)
    )
    return recovered.lower() == expected_address.lower()
