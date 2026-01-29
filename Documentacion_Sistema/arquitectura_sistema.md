# Documentación Técnica de la Arquitectura del Sistema

**Rol:** Arquitecto de Software  
**Fecha:** 29 de Enero, 2026  
**Objetivo:** Radiografía técnica del código actual.

---

## 1. Estructura de Directorios (File Tree)

Árbol visual de los componentes principales del sistema (se han omitido archivos temporales, caché y entornos virtuales).

```ascii
📦 Raíz del Proyecto
 ┣ 📂 models                 # Definición de Entidades de Base de Datos
 ┃ ┗ 📜 entities.py          # Clases ORM (Vencimiento, Pago, Inmueble, etc.)
 ┣ 📂 services               # Lógica de Negocio y Controladores
 ┃ ┣ 📜 auth_service.py      # Gestión de usuarios y autenticación
 ┃ ┗ 📜 vencimiento_service.py # Lógica CRUD para vencimientos
 ┣ 📂 web_prototype          # Módulo Web / Mobile (FastAPI + Frontend)
 ┃ ┣ 📜 api_server.py        # Backend API (Endpoints REST)
 ┃ ┗ 📜 index.html           # Frontend Single Page Application (Dashboard)
 ┣ 📂 controllers            # Controladores de la App de Escritorio
 ┣ 📂 views                  # Vistas de la App de Escritorio (UI)
 ┣ 📜 config.py              # Configuración global (Rutas, Secretos, Flags)
 ┣ 📜 database.py            # Motor de Base de Datos (Conexión, Session Factory)
 ┣ 📜 main.py                # Punto de entrada para App de Escritorio
 ┗ 📜 requirements.txt       # Dependencias del proyecto
```

---

## 2. Mapa de Dependencias y Servicios

### Stack Tecnológico
*   **Lenguaje Core:** Python 3.10+
*   **Web Framework:** FastAPI (Backend), Uvicorn (Servidor AGI)
*   **Frontend:** HTML5, Vanilla JavaScript, CSS3 (Diseño responsivo y moderno)
*   **ORM (Object-Relational Mapping):** SQLAlchemy (Gestión de base de datos)
*   **GUI Escritorio:** CustomTkinter (Interfaz nativa de Windows)

### Servicios Externos
*   **Base de Datos Principal:** PostgreSQL (Alojada en **Neon Tech** - Cloud)
    *   *Uso:* Almacenamiento persistente de todas las transacciones, usuarios y configuraciones.
*   **Plataforma de Despliegue (Web):** Railway / Render (Para el `api_server.py`)
*   **Control de Versiones:** GitHub (Repositorio remoto)

### Interconexiones
Diseño modular donde múltiples interfaces consumen los mismos datos.

1.  **Frontend Web (`index.html`)** ↔ **API Backend (`api_server.py`)**  
    *Comunicación vía HTTP/REST (JSON)*
2.  **API Backend** ↔ **Capa de Datos (`database.py`)**  
    *Consultas SQL a través de SQLAlchemy*
3.  **App Escritorio (`main.py`)** ↔ **Capa de Datos (`database.py`)**  
    *Conexión directa a DB (misma fuente de verdad)*

---

## 3. Flujo de Datos (Data Flow)

### Ejemplo: Registro de un Pago

1.  **Entrada (Usuario):** 
    *   El usuario hace clic en "Pagar" desde el Dashboard Web (`index.html`).
    *   JS captura el monto y fecha, y envía un `POST` a `/vencimientos/{id}/pagar`.

2.  **Procesamiento (API Server):**
    *   `api_server.py` recibe la solicitud y valida el token.
    *   Instancia una sesión de base de datos (`SessionLocal()`).
    *   Localiza el registro `Vencimiento` correspondiente.

3.  **Persistencia (Base de Datos):**
    *   Se crea un nuevo objeto `Pago` vinculado al vencimiento.
    *   Se actualiza el estado del `Vencimiento` a `PAGADO` (si corresponde).
    *   `session.commit()` confirma la transacción en PostgreSQL (Neon).

4.  **Confirmación (Salida):**
    *   La API responde con un JSON `{"status": "ok"}`.
    *   El Frontend actualiza la UI dinámicamente sin recargar la página.
