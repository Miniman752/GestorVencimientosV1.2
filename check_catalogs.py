
try:
    import services.catalogs_service
    print("OK")
except Exception:
    import traceback
    traceback.print_exc()
