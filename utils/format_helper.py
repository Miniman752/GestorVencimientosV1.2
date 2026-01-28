
import re

def parse_localized_float(value):
    """
    Parses a string number into a float, handling localized formats safely.
    
    Supports:
    - 1200.50 (Standard) -> 1200.5
    - 1.200,50 (Euro/Latam) -> 1200.5
    - 1,200.50 (US/UK) -> 1200.5
    - $ 1.500,00 -> 1500.0
    - "  " -> 0.0
    - None -> 0.0
    
    Returns 0.0 on failure instead of crashing.
    """
    if value is None:
        return 0.0
        
    if isinstance(value, (int, float)):
        return float(value)
        
    s = str(value).strip()
    if not s:
        return 0.0
        
    try:
        # Remove currency symbols and spaces
        s = re.sub(r'[^\d.,-]', '', s)
        
        # Check for empty after cleanup
        if not s:
            return 0.0
            
        # Ambiguity check: 1.234 could be 1234 or 1.234
        # Heuristic: If contains both . and ,
        if '.' in s and ',' in s:
            last_dot = s.rfind('.')
            last_comma = s.rfind(',')
            
            if last_comma > last_dot:
                # Format: 1.200,50 (Comma is decimal)
                s = s.replace('.', '').replace(',', '.')
            else:
                # Format: 1,200.50 (Dot is decimal)
                s = s.replace(',', '') 
                
        elif ',' in s:
            # If only comma, assume it's decimal separator if it looks like decimal limit (2 chars)
            # OR assume it is thousand separator if 3 chars follows?
            # Safe bet for Argentina/Latam: Comma is usually Decimal.
            # But "1,000" could be thousand.
            # Let's count commas.
            if s.count(',') > 1:
                # 1,000,000 -> Thousand separator
                s = s.replace(',', '')
            else:
                # Single comma. 
                # Check decimals. 
                # 100,50 -> Decimal
                # 1,000 -> Ambiguous. 
                # System Policy: We prefer Comma as Decimal for user input here.
                s = s.replace(',', '.')
                
        return round(float(s), 2)
    except Exception:
        return 0.00

def parse_fuzzy_date(value, dayfirst=True):
    """
    Robust date parser supporting:
    - Excel Serial Numbers (Int/Float)
    - ISO Strings (YYYY-MM-DD)
    - Localized Strings (DD/MM/YYYY)
    - Pandas Timestamp / Python Date / Datetime
    
    Returns: datetime.date or None
    """
    from datetime import datetime, date
    import pandas as pd
    
    if value is None or str(value).strip() == "":
        return None
        
    # 1. Already correct type
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if hasattr(value, 'date'): # Pandas Timestamp
        return value.date()
        
    # 2. Excel Serial (Int/Float)
    if isinstance(value, (int, float)):
        try:
            # Excel base date is usually 1899-12-30
            return pd.to_datetime(value, unit='D', origin='1899-12-30').date()
        except: pass
        
    # 3. String Parsing
    s = str(value).strip()
    
    # Try ISO first (YYYY-MM-DD)
    if "-" in s and len(s) >= 10:
        try:
             # Fast path for YYYY-MM-DD
             if s[4] == "-" and s[7] == "-":
                 return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except: pass
        
    # Try Pandas Flexible
    try:
        dt = pd.to_datetime(s, dayfirst=dayfirst)
        if hasattr(dt, 'date'): return dt.date()
        if hasattr(dt, 'to_pydatetime'): return dt.to_pydatetime().date()
    except: pass
    
    # Fallback Manual (DD/MM/YYYY)
    try:
        return datetime.strptime(s[:10], "%d/%m/%Y").date()
    except: pass
    
    return None
