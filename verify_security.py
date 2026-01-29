import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_security():
    print("--- INICIANDO TEST DE SEGURIDAD (JWT) ---")
    
    # 1. Intentar acceder a Dashboard sin token (Debe fallar)
    print("\n1. Probando acceso no autorizado a /dashboard-stats...")
    try:
        r = requests.get(f"{BASE_URL}/dashboard-stats")
        if r.status_code == 401:
            print("✅ ÉXITO: Acceso denegado correctamente (401 Unauthorized).")
        else:
            print(f"❌ FALLO: Se esperaba 401, se obtuvo {r.status_code}.")
            print(r.text)
            return False
    except Exception as e:
        print(f"❌ ERROR DE CONEXIÓN: {e}")
        return False

    # 2. Intentar Login (Debe devolver token)
    print("\n2. Probando Login (admin/admin)...")
    try:
        # Nota: El username/password debe coincidir con alguno de la DB.
        # Asumimos que existe admin/admin o similar.
        # Si falla, puede ser porque la DB está vacía o credentials incorrectas.
        payload = {"username": "admin", "password": "admin"}
        r = requests.post(f"{BASE_URL}/login", data=payload)
        
        if r.status_code == 200:
            token_data = r.json()
            if "access_token" in token_data:
                token = token_data["access_token"]
                print(f"✅ ÉXITO: Token obtenido: {token[:20]}...")
            else:
                print("❌ FALLO: Respuesta 200 pero sin access_token.")
                print(r.json())
                return False
        else:
            print(f"❌ FALLO: Login rechazado ({r.status_code}).")
            print(r.text)
            # No podemos seguir si no hay login
            return False
            
    except Exception as e:
        print(f"❌ ERROR DE LOGIN: {e}")
        return False

    # 3. Acceder con Token (Debe funcionar)
    print("\n3. Probando acceso AUTORIZADO a /dashboard-stats...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get(f"{BASE_URL}/dashboard-stats", headers=headers)
        
        if r.status_code == 200:
            data = r.json()
            print("✅ ÉXITO: Datos de dashboard obtenidos correctamente.")
            print(f"   Total Deuda: ${data.get('total_deuda', 0)}")
        else:
            print(f"❌ FALLO: Acceso denegado con token válido ({r.status_code}).")
            print(r.text)
            return False
            
    except Exception as e:
        print(f"❌ ERROR CON TOKEN: {e}")
        return False

    print("\n✅ TODAS LAS PRUEBAS DE SEGURIDAD PASARON.")
    return True

if __name__ == "__main__":
    if not test_security():
        sys.exit(1)
