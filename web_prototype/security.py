from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
import os

# Configuration
# En un entorno real, esto debe venir de variables de entorno.
# Para Railway, asegúrate de configurar SECRET_KEY en las variables del proyecto.
SECRET_KEY = os.environ.get("SECRET_KEY", "CLAVE_ULTRA_SECRETA_POR_DEFECTO_CAMBIAR_EN_PRODUCCION_URGENTE")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 horas para facilidad de uso en prototipo

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    """Verifica si la contraseña plana coincide con el hash"""
    try:
        # Nota: AuthService usa un hash custom con salt + sha512.
        # Este validador es para bcrypt estándar si decidiéramos migrar,
        # pero por compatibilidad con el AuthService existente, usaremos su método.
        # Aquí dejaremos la función placeholder por si migramos a passlib full.
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # Fallback para el sistema legacy si fuera necesario, pero
        # la validación real la haremos en el endpoint de login usando AuthService.
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    """
    Decodifica el token y devuelve el payload si es válido.
    Lanza JWTError si es inválido o ha expirado.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
