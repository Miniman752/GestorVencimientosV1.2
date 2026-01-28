
try:
    import services.auth_service
    print("OK")
except Exception:
    import traceback
    traceback.print_exc()
