
import requests
import time
import sys
import os

API_URL = "http://localhost:8000"

def log(msg):
    print(f"[TEST] {msg}")

def check_endpoint(endpoint):
    url = f"{API_URL}{endpoint}"
    log(f"Consultando {url}...")
    try:
        res = requests.get(url, timeout=5)
        log(f"Status: {res.status_code}")
        if res.status_code != 200:
            log(f"ERROR BODY: {res.text[:500]}")
        else:
            log("OK")
            import json
            print(json.dumps(res.json(), indent=2))
    except Exception as e:
        log(f"FALLO CONEXION: {e}")

if __name__ == "__main__":
    # Asegurarse de que estamos en el directorio correcto para importaciones si fuera necesario,
    # pero este script actúa como cliente HTTP externo.
    
    log("Iniciando diagnostico de Web API...")
    
    # 1. Probar Root
    check_endpoint("/")
    
    # 2. Probar Dashboard Stats (El que suele fallar)
    check_endpoint("/dashboard-stats")
    
    # 3. Probar Vencimientos
    check_endpoint("/vencimientos")
    
    log("Diagnostico finalizado.")
