
try:
    print("Importing models.entities...")
    import models.entities
    print(f"File: {models.entities.__file__}")
    print(f"EstadoPeriodo in dir: {'EstadoPeriodo' in dir(models.entities)}")
    print("Success models.entities")
    
    print("Importing services.proactive_service...")
    import services.proactive_service
    print("Success services.proactive_service")

    print("Importing services.catalogs_service...")
    import services.catalogs_service
    print("Success services.catalogs_service")

except Exception as e:
    import traceback
    traceback.print_exc()

