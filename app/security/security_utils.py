import hashlib
import os
from base64 import urlsafe_b64encode
from typing import Tuple

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_SALT_SIZE = 16


def encrypt(data: bytes, password: bytes) -> Tuple[bytes, bytes]:
    """
    Encrypt data using a password-derived key.

    Args:
        data (bytes): The plaintext data to encrypt.
        password (bytes): The password to derive the encryption key.

    Returns:
        Tuple[bytes, bytes]: A tuple containing the encrypted data and the salt used for key derivation.
    """
    salt = os.urandom(_SALT_SIZE)
    cipher = _get_cipher(password, salt)
    encrypted = cipher.encrypt(data)
    return encrypted, salt


def decrypt(encrypted: bytes, password: bytes, data_salt: bytes) -> bytes:
    """
    Decrypt data using a password and salt.

    Args:
        encrypted (bytes): The encrypted data.
        password (bytes): The password to derive the decryption key.
        data_salt (bytes): The salt used during encryption for key derivation.

    Returns:
        bytes: The decrypted plaintext data.

    Raises:
        ValueError: If the password is incorrect or data is corrupted.
    """
    cipher = _get_cipher(password, data_salt)
    try:
        return cipher.decrypt(encrypted)
    except InvalidToken:
        raise ValueError("Invalid password or corrupted data")


def get_hash(key: bytes, salt: bytes = os.urandom(_SALT_SIZE)) -> Tuple[bytes, bytes]:
    """
    Generate a secure hash and salt from a password using PBKDF2.

    Args:
        key (bytes): The password to hash.
        salt (bytes): The password's salt if exist

    Returns:
        Tuple[str, str]: A tuple containing the hex-encoded hash and hex-encoded salt.

    """
    password_salted = salt + key
    return hashlib.sha256(password_salted).digest(), salt


def _get_cipher(password: bytes, salt: bytes) -> Fernet:
    """
    Create a Fernet cipher instance from a password and salt.

    Args:
        password (bytes): The password to derive the key.
        salt (bytes): The salt used for key derivation.

    Returns:
        Fernet: A Fernet cipher object initialized with the derived key.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    password = urlsafe_b64encode(kdf.derive(password))
    return Fernet(password)
