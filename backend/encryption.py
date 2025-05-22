
import base64
from cryptography.fernet import Fernet

# Use the provided secret key
SECRET_KEY = base64.urlsafe_b64encode(
    "DhinkiBagaPara@123".encode("utf-8").ljust(32, b"0")
)
fernet = Fernet(SECRET_KEY)

def encrypt(text: str) -> str:
    return fernet.encrypt(text.encode()).decode()

def decrypt(token: str) -> str:
    return fernet.decrypt(token.encode()).decode()
