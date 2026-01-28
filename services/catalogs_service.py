from typing import List, Optional
from utils.decorators import safe_transaction
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from utils.exceptions import AppValidationError
from models.entities import Inmueble, ProveedorServicio, Obligacion, EstadoInmueble, ReglaAjuste, TipoAjuste
from repositories.catalogs_repository import InmuebleRepository, ProveedorRepository, ObligacionRepository
from dtos.catalogs import InmuebleCreateDTO, InmuebleUpdateDTO, ProveedorCreateDTO, ProveedorUpdateDTO
from utils.logger import app_logger

class CatalogService:
    def _get_inmueble_repo(self, session):
        return InmuebleRepository(session, Inmueble)

    def _get_proveedor_repo(self, session):
        return ProveedorRepository(session, ProveedorServicio)

    # --- Inmuebles ---
    @safe_transaction
    def get_inmuebles(self, include_inactive=False, session=None) -> List[Inmueble]:
        repo = self._get_inmueble_repo(session)
        if include_inactive:
            return repo.get_all()
        return repo.get_all_active()

    @safe_transaction
    def create_inmueble(self, dto: InmuebleCreateDTO, session=None) -> Inmueble:
        repo = self._get_inmueble_repo(session)
        if repo.get_by_alias(dto.alias):
            raise AppValidationError(f"El alias '{dto.alias}' ya existe.")
            
        entity = Inmueble(
            alias=dto.alias,
            direccion=dto.direccion,
            tipo_propiedad=dto.tipo_propiedad,
            # Duplicated lines removed
            # estado=EstadoInmueble.ACTIVO # Removed
        )
        return repo.add(entity)

    @safe_transaction
    def update_inmueble(self, id: int, dto: InmuebleUpdateDTO, session=None) -> Inmueble:
        repo = self._get_inmueble_repo(session)
        item = repo.get_by_id(id)
        if not item:
            raise AppValidationError(f"Inmueble {id} no encontrado")

        if dto.alias is not None: 
            # Check unique if changed (Case insensitive check, exclude self)
            if dto.alias.strip().lower() != item.alias.strip().lower():
                existing = repo.get_by_alias(dto.alias)
                if existing and existing.id != item.id:
                    raise AppValidationError(f"El alias '{dto.alias}' ya existe.")
            item.alias = dto.alias
            
        if dto.direccion is not None: item.direccion = dto.direccion
        # if dto.titular is not None: item.titular = dto.titular
        # if dto.estado is not None: pass # Removed
        
        return repo.update(item)

    @safe_transaction
    def delete_inmueble(self, id: int, session=None) -> bool:
        repo = self._get_inmueble_repo(session)
        item = repo.get_by_id(id)
        if item:
            # Hard Delete directly (Cloud DB has no estado/soft delete)
            # Check dependencies? Database FK will handle it or error.
            # Assuming cascade delete is set in models (cascade="all, delete-orphan" on Inmueble.obligaciones)
            session.delete(item)
            return True
        return False

    # --- Proveedores ---
    @safe_transaction
    def get_proveedores(self, include_inactive=False, session=None) -> List[ProveedorServicio]:
        repo = self._get_proveedor_repo(session)
        if include_inactive:
            return repo.get_all()
        return repo.get_all_active()

    @safe_transaction
    def create_proveedor(self, dto: ProveedorCreateDTO, session=None) -> ProveedorServicio:
        repo = self._get_proveedor_repo(session)
        if repo.get_by_name(dto.nombre_entidad):
            raise AppValidationError(f"El proveedor '{dto.nombre_entidad}' ya existe.")

        cat_val = dto.categoria
        if hasattr(cat_val, 'value'):
             cat_val = cat_val.value
        elif isinstance(cat_val, Enum): # Fallback
             cat_val = cat_val.value
        elif hasattr(cat_val, 'name'): # Catch all
             cat_val = cat_val.value if hasattr(cat_val, 'value') else cat_val.name

        entity = ProveedorServicio(
            nombre_entidad=dto.nombre_entidad,
            categoria=str(cat_val) if cat_val else None 
        )
        return repo.add(entity)

    @safe_transaction
    def update_proveedor(self, id: int, dto: ProveedorUpdateDTO, session=None) -> ProveedorServicio:
        repo = self._get_proveedor_repo(session)
        item = repo.get_by_id(id)
        if not item:
            raise AppValidationError(f"Proveedor {id} no encontrado")

        if dto.nombre_entidad is not None:
             # Check unique if changed (Case insensitive, exclude self)
             if dto.nombre_entidad.strip().lower() != item.nombre_entidad.strip().lower():
                existing = repo.get_by_name(dto.nombre_entidad)
                if existing and existing.id != item.id:
                    raise AppValidationError(f"El proveedor '{dto.nombre_entidad}' ya existe.")
             item.nombre_entidad = dto.nombre_entidad
             
        if dto.categoria is not None: 
             cat_val = dto.categoria
             if hasattr(cat_val, 'value'):
                  cat_val = cat_val.value
             item.categoria = str(cat_val)
        # if dto.activo is not None: item.activo = dto.activo

        return repo.update(item)

    @safe_transaction
    def delete_proveedor(self, id: int, session=None) -> bool:
        repo = self._get_proveedor_repo(session)
        item = repo.get_by_id(id)
        if item:
            # Check for dependencies first to avoid IntegrityError/Session Rollback issues
            dep_count = session.query(Obligacion).filter_by(servicio_id=id).count()
            if dep_count > 0:
                raise AppValidationError(f"No se puede eliminar '{item.nombre_entidad}' porque está asignado a {dep_count} obligaciones existentes.\nPrimero elimina esas asignaciones.")
            
            # Hard Delete (No activo column)
            session.delete(item)
            return True
        return False

class ObligacionService:
    def _get_repo(self, session):
        return ObligacionRepository(session, Obligacion)

    @safe_transaction
    def get_all_detailed(self, session=None) -> List[Obligacion]:
        repo = self._get_repo(session)
        return repo.get_all_with_relations()

    @safe_transaction
    def create(self, dto, session=None) -> bool:
        repo = self._get_repo(session)
        
        # Check duplicate
        exists = session.query(Obligacion).filter_by(
            inmueble_id=dto['inmueble_id'], 
            servicio_id=dto['servicio_id']
        ).first()
        if exists:
            raise ValueError("Este servicio ya está asignado al inmueble.")

        # Create Obligacion
        new_obl = Obligacion(
            inmueble_id=dto['inmueble_id'],
            servicio_id=dto['servicio_id'],
            numero_cliente_referencia=dto.get('referencia')
        )
        session.add(new_obl)
        session.flush()

        # Create ReglaAjuste
        tipo_enum = TipoAjuste.ESTACIONAL_IPC 
        if 'tipo_ajuste' in dto:
            for t in TipoAjuste:
                if t.value == dto['tipo_ajuste']:
                    tipo_enum = t
                    break
        
        new_rule = ReglaAjuste(
            obligacion_id=new_obl.id,
            tipo_ajuste=tipo_enum.value,
            frecuencia_meses=1
        )
        session.add(new_rule)
        return True

    @safe_transaction
    def delete(self, id: int, session=None) -> bool:
        repo = self._get_repo(session)
        obl = session.query(Obligacion).get(id)
        if obl:
            session.delete(obl)
            return True
        return False

    @safe_transaction
    def create_default_for_inmueble(self, inmueble_id: int, session=None) -> Obligacion:
        """Finds or Creates 'Varios' provider and links to Inmueble."""
        # 1. Find or Create 'Varios' Provider
        # Try finding generic name
        prov_repo = ProveedorRepository(session, ProveedorServicio)
        
        # Possible variations
        candidates = ["Varios", "Generico", "General", "Otro"]
        provider = None
        
        for name in candidates:
            provider = prov_repo.get_by_name(name)
            if provider: break
            
        if not provider:
            # Create 'Varios'
            provider = ProveedorServicio(nombre_entidad="Varios", categoria="OTRO")
            session.add(provider)
            session.flush() # Get ID
            
        # 2. Check if already linked
        repo = self._get_repo(session)
        existing = session.query(Obligacion).filter_by(inmueble_id=inmueble_id, servicio_id=provider.id).first()
        
        if existing:
            return existing
            
        # 3. Create Obligacion
        new_obl = Obligacion(
            inmueble_id=inmueble_id,
            servicio_id=provider.id
        )
        session.add(new_obl)
        session.flush()
        
        # 4. Create Default Adjustment Rule (Manual or Fijo)
        # Using MANUAL to follow inflation as per recent Oracle fix, or FIJO?
        # Let's say FIJO/MANUAL. "MANUAL" is safer for "Varios".
        
        try:
            # "MANUAL" is not in DB enum yet, use "FIJO" for safety.
            # Must pass .value because Column is String.
            adj_type = TipoAjuste.FIJO.value
        except:
             adj_type = "FIJO"
             
        new_rule = ReglaAjuste(
            obligacion_id=new_obl.id,
            tipo_ajuste=adj_type,
            frecuencia_meses=1
        )
        session.add(new_rule)
        
        return new_obl

    @safe_transaction
    def update_rule(self, id: int, tipo_ajuste_str: str, session=None) -> bool:
        rule = session.query(ReglaAjuste).filter_by(obligacion_id=id).first()
        if not rule:
            rule = ReglaAjuste(obligacion_id=id)
            session.add(rule)
        
        for t in TipoAjuste:
            if t.value == tipo_ajuste_str:
                rule.tipo_ajuste = t.value
                break
        return True


