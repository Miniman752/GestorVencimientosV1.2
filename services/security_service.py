import os
from cryptography.fernet import Fernet
from config import BASE_DIR, APP_DATA_DIR # Assuming these exist or we derive path
from utils.logger import app_logger

# Path to the secret key
# Should be in a secure location, preferably not in git (but this is local desktop app)
KEY_FILE = os.path.join(APP_DATA_DIR if 'APP_DATA_DIR' in locals() else os.path.dirname(BASE_DIR), "security.key")

class SecurityService:
    _key = None
    _cipher = None

    @classmethod
    def _load_key(cls):
        if cls._key: return cls._key
        
        if os.path.exists(KEY_FILE):
            with open(KEY_FILE, "rb") as key_file:
                cls._key = key_file.read()
        else:
            # Generate new key
            app_logger.warning("Generating NEW Security Key. Previous encrypted data will be unrecoverable if key was lost.")
            cls._key = Fernet.generate_key()
            try:
                with open(KEY_FILE, "wb") as key_file:
                    key_file.write(cls._key)
            except Exception as e:
                app_logger.error(f"Failed to save security key: {e}")
        
        return cls._key

    @classmethod
    def _get_cipher(cls):
        if cls._cipher: return cls._cipher
        key = cls._load_key()
        cls._cipher = Fernet(key)
        return cls._cipher

    @staticmethod
    def encrypt(data: str) -> str:
        if not data: return ""
        try:
            cipher = SecurityService._get_cipher()
            # Encrypt bytes, return string
            encrypted_bytes = cipher.encrypt(data.encode('utf-8'))
            return encrypted_bytes.decode('utf-8')
        except Exception as e:
            app_logger.error(f"Encryption failed: {e}")
            raise e

    @staticmethod
    def decrypt(token: str) -> str:
        if not token: return ""
        try:
            cipher = SecurityService._get_cipher()
            decrypted_bytes = cipher.decrypt(token.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            app_logger.error(f"Decryption failed: {e}")
            return "[Error: Clave Inválida o Datos Corruptos]"
