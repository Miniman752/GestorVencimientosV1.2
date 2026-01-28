
try:
    from models.entities import YearConfig
    print("OK: YearConfig imported successfully")
except ImportError as e:
    print(f"IMPORT ERROR: {e}")
except Exception as e:
    import traceback
    traceback.print_exc()
