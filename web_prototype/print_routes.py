from web_prototype.api_server import app
for route in app.routes:
    print(f"{route.path} -> {route.name}")
