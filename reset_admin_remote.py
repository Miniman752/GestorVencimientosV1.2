import sys
import os
import hashlib
import binascii

# --- Mock AuthService Logic ---
def hash_password(password: str) -> str:
    """Hash a password for storing (Same as AuthService)."""
    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), 
                                  salt, 100000)
    pwdhash = binascii.hexlify(pwdhash)
    return (salt + b'$' + pwdhash).decode('ascii')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Hardcoded from config.py
DB_URL = "postgresql://neondb_owner:npg_vhmWRL8ESXI3@ep-green-night-acbu7krn-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require"

def reset_admin():
    print(f"Connecting to DB...")
    try:
        engine = create_engine(DB_URL)
        Session = sessionmaker(bind=engine)
        session = Session()

        # Check if admin exists
        print("Buscando usuario 'admin'...")
        result = session.execute(text("SELECT id FROM usuarios WHERE username = 'admin'"))
        row = result.fetchone()

        new_pass_plain = "admin"
        new_hash = hash_password(new_pass_plain)

        if row:
            user_id = row[0]
            print(f"Usuario 'admin' encontrado (ID: {user_id}). Actualizando password...")
            session.execute(text("UPDATE usuarios SET password_hash = :p, is_active = 1 WHERE id = :id"), {"p": new_hash, "id": user_id})
            session.commit()
            print("✅ Password actualizada a: 'admin'")
        else:
            print("⚠️ Usuario 'admin' NO encontrado. Creándolo...")
            # Create logic setup if needed, but let's try update first.
            # Assuming schema allows direct insert or we need proper Insert
            session.execute(text("""
                INSERT INTO usuarios (username, password_hash, rol, nombre_completo, is_active)
                VALUES ('admin', :p, 'ADMIN', 'Backend Admin', 1)
            """), {"p": new_hash})
            session.commit()
            print("✅ Contraseña set to: 'admin'")

        session.close()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    reset_admin()
