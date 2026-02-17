import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.utils.json_logger import JLogger


class EncryptionService:
    """
    AES-GCM Authenticated Encryption for sensitive note content.
    Uses MASTER_ENCRYPTION_KEY from environment.
    """

    @staticmethod
    def _get_key() -> bytes:
        # 32 bytes for AES-256
        key = os.getenv("MASTER_ENCRYPTION_KEY", "voice_note_master_key_32_chars_!")
        return key.encode().ljust(32)[:32]

    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        """Encrypts string to base64 encoded AES-GCM ciphertext."""
        if not plaintext:
            return ""
        try:
            aesgcm = AESGCM(cls._get_key())
            nonce = os.urandom(12)  # GCM recommended nonce size
            ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
            return base64.b64encode(nonce + ciphertext).decode("utf-8")
        except Exception as e:
            JLogger.error("Encryption failed", error=str(e))
            raise ValueError("Failed to encrypt data")

    @classmethod
    def decrypt(cls, ciphertext_b64: str) -> str:
        """Decrypts base64 encoded AES-GCM ciphertext."""
        if not ciphertext_b64:
            return ""
        try:
            data = base64.b64decode(ciphertext_b64)
            if len(data) < 13: # Nonce (12) + at least 1 byte tag/data
                return ciphertext_b64
                
            nonce = data[:12]
            ciphertext = data[12:]
            aesgcm = AESGCM(cls._get_key())
            decrypted = aesgcm.decrypt(nonce, ciphertext, None)
            return decrypted.decode("utf-8")
        except Exception as e:
            # If decryption fails, it might be plaintext or wrong key
            JLogger.debug("Decryption failed, returning as-is", error=str(e))
            return ciphertext_b64
