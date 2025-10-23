from passlib.hash import bcrypt
from cryptography.fernet import Fernet

_f = None

def init_crypto(fernet_key_str):
    global _f
    _f = Fernet(fernet_key_str)

def hash_password(raw_password: str) -> str:
    return bcrypt.using(rounds=12).hash(raw_password)

def verify_password(raw_password: str, password_hash: str) -> bool:
    return bcrypt.verify(raw_password, password_hash)

def enc(s: str) -> bytes:
    return _f.encrypt(s.encode())

def dec(b: bytes) -> str:
    if isinstance(b, str):
        b = b.encode()
    return _f.decrypt(b).decode()
