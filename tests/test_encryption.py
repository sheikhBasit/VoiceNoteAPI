import os
import pytest
from app.utils.encryption import EncryptionService

def test_encryption_decryption():
    plaintext = "Sensitive meeting notes about project X"
    ciphertext = EncryptionService.encrypt(plaintext)
    
    assert ciphertext != plaintext
    assert len(ciphertext) > len(plaintext)
    
    decrypted = EncryptionService.decrypt(ciphertext)
    assert decrypted == plaintext

def test_empty_handling():
    assert EncryptionService.encrypt("") == ""
    assert EncryptionService.decrypt("") == ""

def test_invalid_decrypt():
    # Should return original if not valid base64 or too short
    assert EncryptionService.decrypt("not-b64-!") == "not-b64-!"
    assert EncryptionService.decrypt("YQ==") == "YQ==" # "a" in b64, too short for GCM nonce

def test_encryption_salt():
    plaintext = "Same text"
    c1 = EncryptionService.encrypt(plaintext)
    c2 = EncryptionService.encrypt(plaintext)
    
    # GCM uses nonces, so same plaintext should result in different ciphertext
    assert c1 != c2
    assert EncryptionService.decrypt(c1) == plaintext
    assert EncryptionService.decrypt(c2) == plaintext
