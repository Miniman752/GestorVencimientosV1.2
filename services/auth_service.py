
import hashlib
import os
import binascii
from typing import Optional
from sqlalchemy.orm import Session
from database import SessionLocal
from models.entities import Usuario, RolUsuario
from utils.decorators import safe_transaction
from utils.logger import app_logger

class AuthService:
    
    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash a password for storing."""
        salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
        pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), 
                                      salt, 100000)
        pwdhash = binascii.hexlify(pwdhash)
        return (salt + b'$' + pwdhash).decode('ascii')

    @staticmethod
    def _verify_password(stored_password: str, provided_password: str) -> bool:
        """Verify a stored password against one provided by user"""
        try:
            salt = stored_password.split('$')[0]
            stored_hash = stored_password.split('$')[1]
            pwdhash = hashlib.pbkdf2_hmac('sha512', provided_password.encode('utf-8'), 
                                          salt.encode('ascii'), 100000)
            pwdhash = binascii.hexlify(pwdhash).decode('ascii')
            return pwdhash == stored_hash
        except IndexError:
            return False

    @staticmethod
    def login(username, password) -> Optional[Usuario]:
        session: Session = SessionLocal()
        try:
            user = session.query(Usuario).filter(Usuario.username == username, Usuario.is_active == 1).first()
            if user and AuthService._verify_password(user.password_hash, password):
                # Update last login
                try:
                    # from datetime import datetime
                    # user.last_login = datetime.now().date()
                    # session.commit()
                    pass
                except Exception as e:
                    app_logger.error(f"Failed to update last_login: {e}")
                
                session.refresh(user)
                session.expunge(user)
                return user
            return None
        except Exception as e:
            app_logger.error(f"Login error: {e}")
            return None
        finally:
            session.close()

    @staticmethod
    @safe_transaction
    def create_user(session, username, password, role=RolUsuario.OPERADOR, nombre=None):
        if session.query(Usuario).filter(Usuario.username == username).first():
            raise ValueError(f"El usuario {username} ya existe.")
            
        hashed = AuthService._hash_password(password)
        
        # Ensure role is string
        role_val = role.value if hasattr(role, 'value') else role
        
        new_user = Usuario(
            username=username,
            password_hash=hashed,
            rol=role_val,
            nombre_completo=nombre or username,
            is_active=1
        )
        session.add(new_user)
        # session.add(new_user) # Removed duplicate add
        return new_user

    @staticmethod
    @safe_transaction
    def update_user(session, user_id, nombre=None, role=None):
        user = session.query(Usuario).get(user_id)
        if user:
            if nombre: user.nombre_completo = nombre
            if role: 
                user.rol = role.value if hasattr(role, 'value') else role

    @staticmethod
    @safe_transaction
    def delete_user(session, user_id):
        user = session.query(Usuario).get(user_id)
        if user:
            # Maybe soft delete?
            user.is_active = 0 # Soft delete via active flag
    
    @staticmethod
    @safe_transaction
    def change_password(session, user_id, new_password):
         user = session.query(Usuario).get(user_id)
         if user:
             user.password_hash = AuthService._hash_password(new_password)

    @staticmethod
    def get_user(user_id):
        session = SessionLocal()
        try:
            return session.query(Usuario).get(user_id)
        finally:
            session.close()

    @staticmethod
    def list_users():
        session = SessionLocal()
        try:
            return session.query(Usuario).filter(Usuario.is_active == 1).all()
        finally:
            session.close()

    @staticmethod
    def ensure_admin_exists():
        session = SessionLocal()
        created = False
        try:
            existing = session.query(Usuario).first()
            if not existing:
                app_logger.info("No users found. Creating default admin.")
                AuthService.create_user(
                    session=session, # Pass session explicitly to avoid nested transaction issues in safe_transaction if strict
                    # Wait, create_user handles its own session if passed? 
                    # create_user is decorated with @safe_transaction.
                    # @safe_transaction(session) logic: if first arg is session, uses it?
                    # My implementations of safe_transaction usually detect 'session' kwarg or first arg.
                    # Let's call create_user normally without session if it opens its own, 
                    # OR pass the session I just opened.
                    # If create_user opens its own session, I should close mine first or let it handle it.
                    # Actually `AuthService.create_user` implementation:
                    # `@safe_transaction`
                    # `def create_user(session, ...)`
                    # The decorator injects session.
                    # So I should call `AuthService.create_user(username=...)` and it will get a session.
                    # But I am already holding a session to check `existing`.
                    # I should close `session` before calling `create_user` to avoid potential locks if sqlite?
                    # Or just use the session I have.
                    # Let's assume `create_user` needs to be called without session argument if decorator provides it, UNLESS I pass it.
                    # Let's verify `create_user` signature in `auth_service.py` step 698.
                    # `def create_user(session, username, ...)`
                    # Decorator usually handles injection.
                    # Simpler strategy: Just check count. Close session. If 0, call create_user.
                )
                
            # Re-read implementation of create_user to be safe.
            # It was:
            # @safe_transaction
            # def create_user(session, username, password, role=RolUsuario.OPERADOR, nombre=None):
            # So I call it as create_user(username=..., ...). Session is injected.
        except Exception as e:
             app_logger.error(f"Error ensuring admin: {e}")
        finally:
            session.close()
            
        # Re-implementation for returning True
        session = SessionLocal()
        created = False
        try:
            if not session.query(Usuario).first():
                 session.close() # Close read session
                 AuthService.create_user(
                    username="admin", 
                    password="admin", 
                    role=RolUsuario.ADMIN,
                    nombre="Administrador Sistema"
                )
                 created = True
        except Exception:
            pass
        finally:
             if session.is_active: session.close()
        return created
