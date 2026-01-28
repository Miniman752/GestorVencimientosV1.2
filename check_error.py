
try:
    import models.entities
    print("OK")
except Exception:
    import traceback
    traceback.print_exc()
