import os
from sqlalchemy import create_engine, text
from config import DATABASE_URL
from collections import defaultdict

def check_duplicates():
    print(f"--- BÚSQUEDA DE DUPLICADOS EN NEON.TECH ---")
    print(f"URL: {DATABASE_URL.split('@')[1]}")
    
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        
        # 1. Check Proveedores (Duplicate nombre_entidad)
        print("\n[1] Analizando Proveedores...")
        # Note: cuit column removed from DB model, so we only check nombre_entidad
        q_prov = text("SELECT id, nombre_entidad FROM proveedores")
        provs = conn.execute(q_prov).fetchall()
        
        seen_names = defaultdict(list)
        
        for p in provs:
            # Normalize name
            name_norm = p.nombre_entidad.strip().lower()
            seen_names[name_norm].append(p.id)
                
        dupe_names = {k: v for k, v in seen_names.items() if len(v) > 1}
        
        if dupe_names:
            print(f"   ⚠️ SE ENCONTRARON POSIBLES DUPLICADOS:")
            print(f"      Por Nombre: {dupe_names}")
        else:
            print("   ✅ No se encontraron proveedores duplicados.")

        # 2. Check Inmuebles (Duplicate Direction or Alias)
        print("\n[2] Analizando Inmuebles...")
        q_inm = text("SELECT id, direccion, alias FROM inmuebles")
        inms = conn.execute(q_inm).fetchall()
        
        seen_dir = defaultdict(list)
        for i in inms:
            if i.direccion:
                d_norm = i.direccion.strip().lower()
                seen_dir[d_norm].append(i.id)
        
        dupe_dir = {k: v for k, v in seen_dir.items() if len(v) > 1}
        
        if dupe_dir:
            print(f"   ⚠️ SE ENCONTRARON INMUEBLES DUPLICADOS (Por Dirección):")
            print(f"      {dupe_dir}")
        else:
            print("   ✅ No se encontraron inmuebles duplicados.")

        # 3. Check Vencimientos (Same Obligacion in Same Period)
        print("\n[3] Analizando Vencimientos Activos (No eliminados)...")
        # Logic: A single obligation should typically happen once per period (month)
        # Filter is_deleted = 0
        q_venc = text("SELECT id, obligacion_id, periodo FROM vencimientos WHERE is_deleted = 0")
        vencs = conn.execute(q_venc).fetchall()
        
        seen_venc = defaultdict(list)
        for v in vencs:
            key = (v.obligacion_id, v.periodo)
            seen_venc[key].append(v.id)
            
        dupe_venc = {k: v for k, v in seen_venc.items() if len(v) > 1}
        
        if dupe_venc:
             print(f"   ⚠️ SE ENCONTRARON VENCIMIENTOS DUPLICADOS:")
             for (obl_id, per), ids in dupe_venc.items():
                 print(f"      Obligación {obl_id} en Periodo {per}: IDs {ids}")
        else:
             print("   ✅ No se encontraron vencimientos duplicados (misma obligación/periodo).")

if __name__ == "__main__":
    import sys
    # Redirect stdout to file
    with open("duplicates_report.txt", "w", encoding="utf-8") as f:
        sys.stdout = f
        check_duplicates()
        sys.stdout = sys.__stdout__
    
    # Print to console
    with open("duplicates_report.txt", "r", encoding="utf-8") as f:
        print(f.read())
