
from datetime import timedelta

class ReconciliationService:
    """
    Pure Business Logic for reconciling Bank Transactions against System Records.
    """

    def match_transactions(self, bank_transactions, system_transactions):
        """
        bank_transactions: List of dicts {date, description, amount, ...}
        system_transactions: List of dicts {id, date, amount, obj, matched}
        
        Returns: List of enriched bank_transaction dicts (with 'status', 'match_data')
        """
        
        results = []
        
        # Prepare System Pool (ensure 'matched' flag is tracked via ID or object reference)
        # We'll use a local ID map to track consumed system payments in this session
        matched_ids = set()
        
        for bank_row in bank_transactions:
            
            bank_date = bank_row['date']
            target_amt = abs(bank_row['amount'])
            
            # Defaults
            status = "NO_EN_SISTEMA"
            match_data = None
            display_desc = bank_row['description']
            
            # --- MATCHING LOGIC ---
            
            # 1. Find Candidates by Amount (Unmatched only)
            candidates = []
            for sys_row in system_transactions:
                if sys_row['id'] in matched_ids: continue
                
                # Check Amount Match (Tolerance 0.05)
                if abs(sys_row['amount'] - target_amt) < 0.05:
                    candidates.append(sys_row)
            
            if candidates:
                # 2. Find Closest Date
                best_match = min(candidates, key=lambda x: abs((x['date'] - bank_date).days))
                
                # Determine quality of match
                days_diff = abs((best_match['date'] - bank_date).days)
                
                # Thresholds:
                # 0 days = Perfect
                # < 5 days = Date Slip
                # > 5 days = Remote Match (but amount is exact, so likely valid)
                
                matched_ids.add(best_match['id']) # Mark as used
                match_data = best_match
                
                if days_diff == 0: status = "MATCH"
                elif days_diff <= 5: status = "DIFERENCIA_FECHA"
                else: status = "MATCH_LEJANO"
                
                # Enrich Description with System Data
                if best_match['obj'].vencimiento:
                    sys_desc = best_match['obj'].vencimiento.descripcion
                    sys_date_str = best_match['date'].strftime('%d/%m')
                    display_desc = f"✅ {sys_desc} ({sys_date_str})"
            
            # Build Result Row
            results.append({
                "fecha": bank_date,
                "concepto": display_desc,
                "valor_csv": bank_row['amount'],
                "valor_db": match_data['amount'] if match_data else 0.0,
                "valor_db_display": (-abs(match_data['amount']) if bank_row['amount'] < 0 else abs(match_data['amount'])) if match_data else 0.0,
                "status": status,
                "moneda": "ARS", # Simplification
                "original_row": bank_row,
                "id": match_data['id'] if match_data else None,
                "sys_obj": match_data['obj'] if match_data else None
            })
            
        return results
