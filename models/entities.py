
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Boolean, ForeignKey, Enum, Text, DateTime, event, LargeBinary, CheckConstraint
from sqlalchemy.orm import relationship, declarative_base
from enum import Enum as PyEnum
from datetime import date, datetime

Base = declarative_base()


class EstadoInmueble(PyEnum):
    ACTIVO = "Activo"
    INACTIVO = "Inactivo"

class Inmueble(Base):
    __tablename__ = 'inmuebles'
    id = Column(Integer, primary_key=True, autoincrement=True)
    alias = Column(String(100), nullable=False)
    direccion = Column(String(200))
    # propietario removed as not in DB
    tipo_propiedad = Column(String(50)) # "Casa", "Departamento", "Oficina"
    
    # estado removed as not in DB
    
    # Relación uno a muchos con Obligaciones
    obligaciones = relationship("Obligacion", back_populates="inmueble", cascade="all, delete-orphan")

class CategoriaServicio(PyEnum):
    SERVICIOS = "SERVICIO"
    IMPUESTOS = "IMPUESTO"
    EXPENSAS = "EXPENSA"
    MANTENIMIENTO = "OTRO" # Fallback to OTRO until DB update
    TARJETAS = "OTRO" # Fallback to OTRO
    OTROS = "OTRO"

class ProveedorServicio(Base):
    __tablename__ = 'proveedores'
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre_entidad = Column(String(100), nullable=False, unique=True)
    categoria = Column(String(50)) # e.g. "Servicios", "Impuestos", "Mantenimiento"
    # cuit and contacto removed as not in DB
    
    obligaciones = relationship("Obligacion", back_populates="proveedor")

class Obligacion(Base):
    __tablename__ = 'obligaciones'
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    inmueble_id = Column(Integer, ForeignKey('inmuebles.id'), nullable=False)
    servicio_id = Column(Integer, ForeignKey('proveedores.id'), nullable=False)
    
    inmueble = relationship("Inmueble", back_populates="obligaciones")
    proveedor = relationship("ProveedorServicio", back_populates="obligaciones")

    numero_cliente_referencia = Column(String(100))

    @property
    def identificador_pago(self):
        return self.numero_cliente_referencia
    
    @identificador_pago.setter
    def identificador_pago(self, value):
        self.numero_cliente_referencia = value
    
    # Configuración de recurrencia (Simplificado)
    # es_recurrente removed as it is not in DB

    vencimientos = relationship("Vencimiento", back_populates="obligacion", cascade="all, delete-orphan")
    reglas_ajuste = relationship("ReglaAjuste", back_populates="obligacion", uselist=False, cascade="all, delete-orphan")

class EstadoVencimiento(PyEnum):
    PENDIENTE = "PENDIENTE"
    PAGADO = "PAGADO"
    PROXIMO = "PROXIMO"
    VENCIDO = "VENCIDO"
    ANULADO = "ANULADO"
    REVISION = "REVISION"

class EstadoPeriodo(PyEnum):
    ABIERTO = "ABIERTO"
    CERRADO = "CERRADO"
    BLOQUEADO = "BLOQUEADO"

class Moneda(PyEnum):
    ARS = "ARS"
    USD = "USD"
    # Otras si aplica

class Vencimiento(Base):
    __tablename__ = 'vencimientos'
    __table_args__ = (
        CheckConstraint(r"periodo ~ '^\d{4}-\d{2}$'", name='chk_vencimiento_periodo_fmt'),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    obligacion_id = Column(Integer, ForeignKey('obligaciones.id'), nullable=False)
    obligacion = relationship("Obligacion", back_populates="vencimientos")
    
    periodo = Column(String(7)) # MM-YYYY (Para filtrado y agrupar)
    fecha_vencimiento = Column(Date, nullable=False)
    
    monto_original = Column(Float, default=0.0)
    moneda = Column(Enum(Moneda), default=Moneda.ARS)
    
    monto_actualizado = Column(Float, default=0.0) # Con intereses o ajustes
    # fecha_actualizacion = Column(Date) # Removed not in DB
    
    estado = Column(Enum(EstadoVencimiento), default=EstadoVencimiento.PENDIENTE)
    
    # Metadata
    # nota = Column(Text) # Removed not in DB
    # observaciones = Column(String(255)) # Removed as column does not exist in DB
    prioridad = Column(Integer, default=1) # 1: Normal, 2: Alta
    
    # --- CLOUD DOCUMENTS SUPPORT ---
    # Legacy: File path string
    ruta_archivo_pdf = Column(String(255)) 
    
    # New: Database Storage
    documento_id = Column(Integer, ForeignKey('documentos.id'), nullable=True)
    documento = relationship("Documento", foreign_keys=[documento_id])

    ruta_comprobante_pago = Column(String(255))
    comprobante_pago_id = Column(Integer, ForeignKey('documentos.id'), nullable=True)

    comprobante_pago = relationship("Documento", foreign_keys=[comprobante_pago_id])

    # RELATIONSHIPS
    pagos = relationship("Pago", back_populates="vencimiento", cascade="all, delete-orphan")

    is_deleted = Column(Integer, default=0)

class Pago(Base):
    __tablename__ = 'pagos'
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    vencimiento_id = Column(Integer, ForeignKey('vencimientos.id'), nullable=False)
    vencimiento = relationship("Vencimiento", back_populates="pagos")
    
    fecha_pago = Column(Date, default=date.today)
    monto = Column(Float, nullable=False) # Renamed to match DB
    # moneda_pago = Column(Enum(Moneda), default=Moneda.ARS) # Removed not in DB
    
    medio_pago = Column(String(50)) # Renamed from metodo_pago to match DB
    # referencia = Column(String(100)) # Removed not in DB
    
    comprobante_path = Column(String(255)) # Legacy

    documento_id = Column(Integer, ForeignKey('documentos.id'), nullable=True)

# --- OTHER MODELS ---
class RolUsuario(PyEnum):
    ADMIN = "ADMIN"
    OPERADOR = "OPERADOR"
    INVITADO = "LECTURA"

class Usuario(Base):
    __tablename__ = 'usuarios'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    nombre_completo = Column(String(100))
    rol = Column(String(20), default="user") 
    
    @property
    def role(self):
        return self.rol
        
    @role.setter
    def role(self, value):
        self.rol = value

    is_active = Column(Integer, default=1)

class Credencial(Base):
    __tablename__ = 'credenciales'
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    inmueble_id = Column(Integer, ForeignKey('inmuebles.id'))
    inmueble = relationship("Inmueble")
    
    proveedor_id = Column(Integer, ForeignKey('proveedores.id'))
    proveedor = relationship("ProveedorServicio")
    
    sitio_web = Column(String(200))
    usuario = Column(String(100))
    password_enc = Column(String(200)) # Encriptada
    notas = Column(Text)

class IndiceEconomico(Base):
    __tablename__ = 'indices_economicos'
    __table_args__ = (
        CheckConstraint(r"periodo ~ '^\d{4}-\d{2}$'", name='chk_indice_periodo_fmt'),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    # tipo = Column(String(50)) # "IPC", "UVA" # Removed not in DB
    periodo = Column(String(7)) # MM-YYYY
    valor = Column(Float)
    # fecha_carga = Column(Date, default=date.today) # Removed not in DB

class Cotizacion(Base):
    __tablename__ = 'cotizaciones'
    fecha = Column(Date, primary_key=True)
    moneda = Column(Enum(Moneda), primary_key=True)
    compra = Column(Float)
    venta = Column(Float)


class PeriodoContable(Base):
    __tablename__ = 'periodos_contables'
    __table_args__ = (
        CheckConstraint(r"periodo_id ~ '^\d{4}-\d{2}$'", name='chk_periodo_contable_fmt'),
    )
    # Use simple integer ID for better FK referencing if needed, or composite.
    # But string "MM-YYYY" is currently the main identifier across app.
    # To govern locking, we can just use the string ID.
    periodo_id = Column(String(7), primary_key=True) # "MM-YYYY"
    estado = Column(String(20), default="ABIERTO") # ABIERTO, CERRADO
    fecha_cierre = Column(Date, nullable=True)
    notas = Column(Text)
    
    # Store snapshot of totals?
    # total_deuda = Column(Float, default=0.0) # Removed not in DB
    # total_pagado = Column(Float, default=0.0) # Removed not in DB

class YearConfig(Base):
    __tablename__ = 'config_years'
    year = Column(Integer, primary_key=True)
    is_active = Column(Integer, default=1)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now)
    user_id = Column(String(50)) # Renamed from user to match DB
    action = Column(String(50)) # UPLOAD, DELETE, EDIT
    entity_id = Column(String(100)) # Added to match DB
    details = Column(String(255))

class TipoAjuste(PyEnum):
    FIJO = "FIJO"
    PROMEDIO_MOVIL_3M = "PROMEDIO_MOVIL_3M"
    ESTACIONAL_IPC = "ESTACIONAL_IPC"
    INDICE_CONTRATO = "INDICE_CONTRATO"
    # IPC = "IPC" # Not in DB
    # MANUAL = "Manual" # Not in DB
    # DOLAR = "Dólar" # Not in DB

class ReglaAjuste(Base):
    __tablename__ = 'reglas_ajuste'
    id = Column(Integer, primary_key=True, autoincrement=True)
    obligacion_id = Column(Integer, ForeignKey('obligaciones.id'))
    obligacion = relationship("Obligacion", back_populates="reglas_ajuste")
    
    tipo_ajuste = Column(String(50)) # "IPC", "MANUAL", "DOLAR"
    frecuencia_meses = Column(Integer, default=1) # Cada cuantos meses
    
    # ultimo_ajuste removed as not in DB or date type issue

# Defines Documento Model last to resolve relationships?
# No, we use 'documento.py' or inject it.
# To keep single file structure clean:
class Documento(Base):
    __tablename__ = 'documentos'

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    file_data = Column(LargeBinary, nullable=False) # Stores the actual bytes
    upload_date = Column(DateTime, default=datetime.now)
    mime_type = Column(String(100), nullable=True) # e.g., 'application/pdf', 'image/jpeg'
    file_size = Column(Integer, nullable=True) # Size in bytes
