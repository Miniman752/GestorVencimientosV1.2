from database import SessionLocal
from models.entities import Credencial, Inmueble, ProveedorServicio
from services.security_service import SecurityService
from utils.decorators import safe_transaction
from datetime import datetime
from sqlalchemy.orm import joinedload

class CredentialsController:
    
    def get_credentials(self, inmueble_id=None):
        session = SessionLocal()
        try:
            query = session.query(Credencial) # Removed .filter(Credencial.is_deleted == 0)
            # Eager load relationships to avoid DetachedInstanceError
            query = query.options(
                joinedload(Credencial.inmueble),
                joinedload(Credencial.proveedor)
            )
            
            if inmueble_id:
                query = query.filter(Credencial.inmueble_id == inmueble_id)
            return query.all()
        finally:
            session.close()

    @safe_transaction
    def create_credential(self, session, inmueble_id, usuario, password_plain, sitio_web=None, proveedor_id=None, notas=None):
        enc_pass = SecurityService.encrypt(password_plain) if password_plain else None
        
        new_cred = Credencial(
            inmueble_id=inmueble_id,
            proveedor_id=proveedor_id,
            sitio_web=sitio_web,
            usuario=usuario,
            password_enc=enc_pass,
            notas=notas
            # is_deleted=0 # Removed
        )
        session.add(new_cred)
        return new_cred

    @safe_transaction
    def update_credential(self, session, cred_id, **kwargs):
        cred = session.query(Credencial).get(cred_id)
        if not cred: raise ValueError("Credencial no encontrada")
        
        if 'password_plain' in kwargs:
            plain = kwargs.pop('password_plain')
            cred.password_enc = SecurityService.encrypt(plain) if plain else None
            
        for key, value in kwargs.items():
            if hasattr(cred, key):
                setattr(cred, key, value)
        return cred

    @safe_transaction
    def delete_credential(self, session, cred_id):
        cred = session.query(Credencial).get(cred_id)
        if cred:
            # cred.is_deleted = 1
            session.delete(cred)
            
    def decrypt_password(self, cred_id):
        session = SessionLocal()
        try:
            cred = session.query(Credencial).get(cred_id)
            if cred and cred.password_enc:
                return SecurityService.decrypt(cred.password_enc)
            return ""
        finally:
            session.close()
