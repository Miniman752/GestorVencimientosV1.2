import sys
import os
import traceback
import pandas as pd

# Add current directory to path
sys.path.append(os.getcwd())

from controllers.reconciliation_controller import ReconciliationController

def run_recon():
    print("--- Starting Reconciliation Analysis ---")
    
    file_path = "Movimientos CA 6548 del 01-12-2025 al 13-01-2026.xlsx"
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return

    ctrl = ReconciliationController()
    
    # Analyze Bank File
    # We rely on auto-detection of columns or we can provide mapping if we know it.
    # Let's try auto-detect first.
    
    print(f"Processing file: {file_path}")
    success, result = ctrl.analyze("Banco", file_path)
    
    if not success:
        print(f"Analysis Failed: {result}")
        return
        
    print(f"Analysis Complete. Processed {len(result)} rows.")
    
    # Check for zero values
    zeros = [r for r in result if r['valor_csv'] == 0.0]
    print(f"Rows with 0.0 amount: {len(zeros)} / {len(result)}")
    if len(zeros) == len(result):
         print("WARNING: ALL AMOUNTS ARE 0.0. MAPPING FAILED?")
    
    # Stats
    matches = [r for r in result if r['status'] == 'MATCH']
    diffs = [r for r in result if r['status'] == 'DIFERENCIA_FECHA']
    remote = [r for r in result if r['status'] == 'MATCH_LEJANO']
    no_sys = [r for r in result if r['status'] == 'NO_EN_SISTEMA']
    
    print(f"MATCH: {len(matches)}")
    print(f"DIF_FECHA: {len(diffs)}")
    print(f"MATCH_LEJANO: {len(remote)}")
    print(f"NO_EN_SISTEMA: {len(no_sys)}")
    
    print("\n--- SAMPLE MATCHES ---")
    for m in matches[:5]:
        print(f"Date: {m['fecha']} | Bank: {m['valor_csv']} | Sys: {m['valor_db']} | Desc: {m['concepto']}")

    print("\n--- SAMPLE MISSED ---")
    for m in no_sys[:5]:
         print(f"Date: {m['fecha']} | Bank: {m['valor_csv']} | Desc: {m['concepto']}")

if __name__ == "__main__":
    try:
        run_recon()
    except Exception:
        traceback.print_exc()
