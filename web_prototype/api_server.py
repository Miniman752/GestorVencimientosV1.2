from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import sys
import os
from datetime import date

# --- Fix Path to find parent modules ---
# We add the parent directory to sys.path so we can import 'services', 'models', etc.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.vencimiento_service import VencimientoService
from services.auth_service import AuthService
from models.entities import Vencimiento, EstadoVencimiento
from database import init_db
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

app = FastAPI(title="Gestor Vencimientos API (Mobile Prototype)")

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initializes DB and ensures admin user on startup."""
    print("API STARTUP: Initializing Database...")
    print("API STARTUP: Initializing Database...")
    from config import DATABASE_URL
    print(f"API STARTUP: Using Database URL -> {DATABASE_URL}")
    init_db()
    
    print("API STARTUP: Ensuring Admin User...")
    AuthService.ensure_admin_exists()
    
    # Mount Static Files
    static_dir = os.path.dirname(os.path.abspath(__file__))
    app.mount("/icons", StaticFiles(directory=os.path.join(static_dir, "icons")), name="icons")
    
    @app.get("/manifest.json")
    def get_manifest():
        return FileResponse(os.path.join(static_dir, "manifest.json"))
        
    print("API STARTUP: Ready.")

# --- Data Models (Pydantic) ---
class LoginRequest(BaseModel):
    username: str
    password: str

class VencimientoSimple(BaseModel):
    id: int
    fecha: date
    monto: float
    estado: str
    proveedor: str
    servicio: str

    inmueble: str
    has_pdf: bool
    
    class Config:
        orm_mode = True

class DashboardStats(BaseModel):
    total_deuda: float
    total_pagado: float
    vencimientos_pendientes: int
    proximos_vencimientos: int
    distribucion_propiedades: List[dict]
    stats_mensuales: List[dict]

class ProveedorSimple(BaseModel):
    id: int
    nombre: str
    categoria: str 
    
    class Config:
        orm_mode = True

    class Config:
        orm_mode = True

class PagoSimple(BaseModel):
    id: int
    fecha: date
    monto: float
    medio_pago: str
    vencimiento_id: int
    detalle: str # e.g. "Edenor - Diciembre"
    
    class Config:
        orm_mode = True

class InmuebleSimple(BaseModel):
    id: int
    alias: str
    direccion: str
    
    class Config:
        orm_mode = True



# --- Services (Lazy Init) ---
# service = VencimientoService() # MOVED INSIDE ENDPOINTS

from fastapi.responses import HTMLResponse
import os

@app.get("/", response_class=HTMLResponse)
def read_root():
    # Read the index.html content
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()

@app.post("/login")
def login(request: LoginRequest):
    # Lazy Init
    from services.auth_service import AuthService
    user = AuthService.login(request.username, request.password)
    # ... rest of function ...
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    return {"status": "ok", "user": user.username, "role": user.rol}

@app.get("/vencimientos", response_model=List[VencimientoSimple])
def get_vencimientos(periodo: Optional[str] = None, search: Optional[str] = None):
    """Get vencimientos, optionally filtered by period and/or search term"""
    print(f"DEBUG: Fetching vencimientos (Period: {periodo}, Search: {search})...")
    
    try:
        from sqlalchemy.orm import joinedload
        from models.entities import Obligacion, Documento
        from database import SessionLocal
        
        session = SessionLocal()
        try:
            from sqlalchemy import or_
            from models.entities import Obligacion, Documento, ProveedorServicio, Inmueble

            query = session.query(Vencimiento).options(
                joinedload(Vencimiento.obligacion).joinedload(Obligacion.proveedor),
                joinedload(Vencimiento.obligacion).joinedload(Obligacion.inmueble)
            ).filter(
                Vencimiento.is_deleted == 0
            )

            if periodo:
                query = query.filter(Vencimiento.periodo == periodo)
            
            if search:
                from models.entities import Obligacion, ProveedorServicio, Inmueble
                # Use word boundaries (\m) to match start of words (e.g., 'abl' matches 'ABL' but not 'Contable')
                # This makes the search much more intuitive for small terms.
                search_regex = f"\\m{search}"
                query = query.join(Obligacion, Vencimiento.obligacion_id == Obligacion.id)\
                             .join(ProveedorServicio, Obligacion.servicio_id == ProveedorServicio.id)\
                             .join(Inmueble, Obligacion.inmueble_id == Inmueble.id)\
                             .filter(
                                or_(
                                    ProveedorServicio.nombre_entidad.op('~*')(search_regex),
                                    Inmueble.alias.op('~*')(search_regex),
                                    Inmueble.direccion.op('~*')(search_regex)
                                )
                             )
            
            results = query.order_by(
                Vencimiento.fecha_vencimiento.desc()
            ).limit(100).all()
            
            print(f"DEBUG: Found {len(results)} records")
            
            data = []
            for v in results:
                try:
                    prov_name = "N/A"
                    serv_name = "N/A"
                    inm_alias = "N/A"
                    
                    if v.obligacion:
                        if v.obligacion.proveedor: 
                            prov_name = v.obligacion.proveedor.nombre_entidad
                            serv_name = str(v.obligacion.proveedor.categoria) if v.obligacion.proveedor.categoria else "General"
                        
                        if v.obligacion.inmueble: inm_alias = v.obligacion.inmueble.alias
                
                    has_pdf_file = False
                    if v.documento_id: has_pdf_file = True
                    elif v.ruta_archivo_pdf and os.path.exists(v.ruta_archivo_pdf): has_pdf_file = True
                    
                    data.append({
                        "id": v.id,
                        "fecha": v.fecha_vencimiento,
                        "monto": float(v.monto_original) if v.monto_original else 0.0,
                        "estado": str(v.estado.value) if hasattr(v.estado, 'value') else str(v.estado),
                        "proveedor": prov_name,
                        "servicio": serv_name,
                        "inmueble": inm_alias,
                        "has_pdf": has_pdf_file
                    })
                except Exception as inner_e:
                    print(f"Error mapping item {v.id}: {inner_e}")
                    
            return data
        finally:
            session.close()
    except Exception as e:
        import traceback
        with open("api_error.log", "w") as f:
            f.write(traceback.format_exc())
        print(f"API CRASH: {e}")
        raise HTTPException(status_code=500, detail=str(e))

        session.close()

@app.get("/periodos-disponibles")
def get_available_periods():
    """Returns a unique list of periods stored in DB for filtering"""
    from database import SessionLocal
    session = SessionLocal()
    try:
        from sqlalchemy import distinct
        periods = session.query(distinct(Vencimiento.periodo)).filter(Vencimiento.is_deleted == 0).order_by(Vencimiento.periodo.desc()).all()
        return [p[0] for p in periods if p[0]]
    finally:
        session.close()

from fastapi.responses import Response, FileResponse

@app.get("/vencimientos/{id}/pdf")
def get_vencimiento_pdf(id: int):
    print(f"DEBUG: Fetching PDF for Vencimiento {id}")
    from database import SessionLocal
    from models.entities import Documento
    
    session = SessionLocal()
    try:
        v = session.query(Vencimiento).filter(Vencimiento.id == id).first()
        if not v:
            raise HTTPException(status_code=404, detail="Vencimiento no encontrado")
            
        # 1. Try Blob Storage
        if v.documento_id:
            doc = session.query(Documento).filter(Documento.id == v.documento_id).first()
            if doc and doc.file_data:
                # Determine mime type
                mime = doc.mime_type or "application/pdf"
                fname = doc.filename or f"vencimiento_{id}.pdf"
                return Response(content=doc.file_data, media_type=mime, headers={"Content-Disposition": f"inline; filename={fname}"})
        
        # 2. Try File System
        if v.ruta_archivo_pdf:
            if os.path.exists(v.ruta_archivo_pdf):
                return FileResponse(v.ruta_archivo_pdf)
            else:
                print(f"DEBUG: File not found at {v.ruta_archivo_pdf}")
        
        raise HTTPException(status_code=404, detail="PDF no encontrado para este vencimiento")
    except HTTPException:
        raise
    except Exception as e:
        print(f"PDF ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error retrieving PDF")
    finally:
        session.close()


# --- Payment Logic ---
class PaymentRequest(BaseModel):
    monto: float
    fecha: date
    medio_pago: str = "Efectivo"
    nota: Optional[str] = None

@app.post("/vencimientos/{id}/pagar")
def pagar_vencimiento(id: int, payment: PaymentRequest):
    print(f"DEBUG: Processing Payment for {id}: {payment}")
    from database import SessionLocal
    from models.entities import Pago, EstadoVencimiento
    
    session = SessionLocal()
    try:
        v = session.query(Vencimiento).filter(Vencimiento.id == id).first()
        if not v:
            raise HTTPException(status_code=404, detail="Vencimiento no encontrado")
            
        # Create Payment Record
        nuevo_pago = Pago(
            vencimiento_id=v.id,
            fecha_pago=payment.fecha,
            monto=payment.monto,
            medio_pago=payment.medio_pago
        )
        session.add(nuevo_pago)
        
        # Update Vencimiento Status
        # Simple logic: If paid amount >= original, mark as PAGADO
        # For now, just mark PAGADO if user says so
        v.estado = EstadoVencimiento.PAGADO
        
        session.commit()
        return {"status": "ok", "message": "Pago registrado correctamente"}
        
    except Exception as e:
        session.rollback()
        print(f"PAYMENT ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error al procesar el pago")
    finally:
        session.close()



# --- Module Endpoints ---

@app.get("/dashboard-stats", response_model=DashboardStats)
def get_dashboard_stats():
    print("DEBUG: Fetching Dashboard Stats")
    from database import SessionLocal
    from models.entities import Vencimiento, EstadoVencimiento, Pago
    from sqlalchemy import func
    
    session = SessionLocal()
    try:
        # 1. Total Deuda (Pending/Vencido/Proximo)
        deuda_q = text("SELECT SUM(monto_original) FROM vencimientos WHERE is_deleted = 0 AND estado != 'PAGADO'")
        total_deuda = session.execute(deuda_q).scalar() or 0.0
        
        # 2. Total Pagado (All time)
        pagado_q = text("SELECT SUM(monto) FROM pagos")
        raw_pagado = session.execute(pagado_q).scalar()
        print(f"DEBUG: Calculated Total Pagado: {raw_pagado} (Type: {type(raw_pagado)})")
        total_pagado = raw_pagado or 0.0
        
        # 3. Counts
        pend_q = text("SELECT COUNT(id) FROM vencimientos WHERE is_deleted = 0 AND estado IN ('PENDIENTE', 'VENCIDO')")
        pendientes = session.execute(pend_q).scalar() or 0
        
        from datetime import date, timedelta
        next_week = (date.today() + timedelta(days=7)).strftime('%Y-%m-%d')
        today_str = date.today().strftime('%Y-%m-%d')
        prox_q = text(f"SELECT COUNT(id) FROM vencimientos WHERE is_deleted = 0 AND estado != 'PAGADO' AND fecha_vencimiento <= '{next_week}' AND fecha_vencimiento >= '{today_str}'")
        proximos = session.execute(prox_q).scalar() or 0

        # 4. Distribution by Property (By Amount)
        prop_query = text("""
            SELECT i.alias, SUM(v.monto_original)
            FROM vencimientos v
            JOIN obligaciones o ON v.obligacion_id = o.id
            JOIN inmuebles i ON o.inmueble_id = i.id
            WHERE v.is_deleted = 0 AND v.estado != 'PAGADO'
            GROUP BY i.alias
            ORDER BY SUM(v.monto_original) DESC
        """)
        prop_stats = session.execute(prop_query).fetchall()
        dist_prop = [{"name": p[0], "amount": float(p[1])} for p in prop_stats]

        # 5. Monthly Trend
        trend_query = text("""
            SELECT periodo, SUM(monto_original)
            FROM vencimientos
            WHERE is_deleted = 0
            GROUP BY periodo
            ORDER BY periodo DESC
            LIMIT 6
        """)
        trend_data = session.execute(trend_query).fetchall()
        stats_mensuales = [{"periodo": t[0], "monto": float(t[1])} for t in reversed(trend_data)]

        # 6. Debt by Category (Amount)
        cat_query = text("""
            SELECT COALESCE(p.categoria, 'OTRO'), SUM(v.monto_original)
            FROM vencimientos v
            JOIN obligaciones o ON v.obligacion_id = o.id
            LEFT JOIN proveedores p ON o.servicio_id = p.id
            WHERE v.is_deleted = 0 AND v.estado != 'PAGADO'
            GROUP BY COALESCE(p.categoria, 'OTRO')
            ORDER BY SUM(v.monto_original) DESC
        """)
        cat_stats = session.execute(cat_query).fetchall()
        print(f"DEBUG: Found {len(cat_stats)} category stats")
        dist_cat = [{"name": p[0], "amount": float(p[1])} for p in cat_stats]
        
        return {
            "total_deuda": float(total_deuda),
            "total_pagado": float(total_pagado),
            "vencimientos_pendientes": pendientes,
            "proximos_vencimientos": proximos,
            "distribucion_propiedades": dist_prop[:8], # Top 8 only
            "stats_mensuales": stats_mensuales,
            "distribucion_categorias": dist_cat
        }
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"DASHBOARD ERROR: {e}")
        with open("api_dashboard_error.log", "w", encoding="utf-8") as f:
            f.write(f"Error en dashboard-stats:\n{error_msg}")
        raise HTTPException(status_code=500, detail=f"Error interno en dashboard: {str(e)}")
    finally:
        session.close()

@app.get("/proveedores", response_model=List[ProveedorSimple])
def get_proveedores():
    print("DEBUG: Fetching Proveedores")
    from database import SessionLocal
    from models.entities import ProveedorServicio
    
    session = SessionLocal()
    try:
        # Fetch active providers (simple list)
        provs = session.query(ProveedorServicio).order_by(ProveedorServicio.nombre_entidad).all()
        
        data = []
        for p in provs:
            cat = str(p.categoria) if p.categoria else "General"
            data.append({
                "id": p.id,
                "nombre": p.nombre_entidad,
                "categoria": cat
            })
        return data
    finally:
        session.close()



@app.get("/inmuebles", response_model=List[InmuebleSimple])
def get_inmuebles():
    from database import SessionLocal
    from models.entities import Inmueble
    
    session = SessionLocal()
    try:
        data = session.query(Inmueble).order_by(Inmueble.alias).all()
        return [{"id": i.id, "alias": i.alias, "direccion": i.direccion} for i in data]
    finally:
        session.close()

@app.get("/pagos", response_model=List[PagoSimple])
def get_pagos():
    from database import SessionLocal
    from models.entities import Pago, Vencimiento, Obligacion, ProveedorServicio
    from sqlalchemy.orm import joinedload
    
    session = SessionLocal()
    try:
        # Query Last 50 payments
        pagos = session.query(Pago).join(Pago.vencimiento).options(
            joinedload(Pago.vencimiento).joinedload(Vencimiento.obligacion).joinedload(Obligacion.proveedor)
        ).order_by(Pago.fecha_pago.desc()).limit(50).all()
        
        data = []
        for p in pagos:
            detalle = "Desconocido"
            if p.vencimiento and p.vencimiento.obligacion and p.vencimiento.obligacion.proveedor:
                prov = p.vencimiento.obligacion.proveedor.nombre_entidad
                periodo = p.vencimiento.periodo or "?"
                detalle = f"{prov} ({periodo})"
            
            data.append({
                "id": p.id,
                "fecha": p.fecha_pago,
                "monto": p.monto,
                "medio_pago": p.medio_pago or "Otro",
                "vencimiento_id": p.vencimiento_id,
                "detalle": detalle
            })
        return data
    finally:
        session.close()



if __name__ == "__main__":
    import uvicorn
    # Get port from environment (Render/Railway) or default to 8000
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
