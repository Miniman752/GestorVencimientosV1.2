
try:
    from models.entities import Usuario, Obligacion, RolUsuario
    
    # Test Usuario
    u = Usuario(username="test", password_hash="hash", rol="admin")
    print(f"Usuario created. Rol: {u.rol}, Role (Prop): {u.role}")
    
    u.role = "user"
    print(f"Updated via prop. Rol: {u.rol}, Role (Prop): {u.role}")

    # Test Obligacion
    o = Obligacion(inmueble_id=1, servicio_id=2)
    print(f"Obligacion created. ServicioID: {o.servicio_id}")
    
    print("OK")
except Exception:
    import traceback
    traceback.print_exc()
