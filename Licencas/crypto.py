from django.conf import settings
from base64 import urlsafe_b64encode, urlsafe_b64decode
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet

def _derive_key() -> bytes:
    secret = settings.SECRET_KEY.encode()
    salt = b"licencas-certificado-a1"
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=390000)
    key = urlsafe_b64encode(kdf.derive(secret))
    return key

def get_fernet() -> Fernet:
    return Fernet(_derive_key())

def encrypt_bytes(data: bytes) -> bytes:
    f = get_fernet()
    return f.encrypt(data)

def decrypt_bytes(token) -> bytes:
    if isinstance(token, memoryview):
        token = token.tobytes()
    if isinstance(token, str):
        token = token.encode("utf-8")
    f = get_fernet()
    return f.decrypt(token)

def encrypt_str(text: str) -> str:
    token = encrypt_bytes(text.encode("utf-8"))
    return token.decode("utf-8")

def decrypt_str(token: str) -> str:
    data = decrypt_bytes(token)
    return data.decode("utf-8")
