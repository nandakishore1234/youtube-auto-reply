import json

from cryptography.fernet import Fernet

from app.config import get_settings


def _fernet() -> Fernet:
    settings = get_settings()
    return Fernet(settings.token_encryption_key.encode())


def encrypt_tokens(token_data: dict) -> str:
    serialized = json.dumps(token_data).encode("utf-8")
    return _fernet().encrypt(serialized).decode("utf-8")


def decrypt_tokens(encrypted_data: str) -> dict:
    decrypted = _fernet().decrypt(
        encrypted_data.encode("utf-8")
    )
    return json.loads(decrypted.decode("utf-8"))