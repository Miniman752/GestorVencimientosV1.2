import flet as ft
import requests
import traceback

# --- DEBUG LOGGER ---
log_file = open("web_app_debug.log", "w", buffering=1)
def log(msg):
    try:
        log_file.write(str(msg) + "\n")
        log_file.flush()
        print(msg) 
    except: pass

API_URL = "http://localhost:8000"

def main(page: ft.Page):
    log("Web App Started.")
    page.title = "Gestor Vencimientos Web"
    page.bgcolor = "white"
    
    # --- Responsive State ---
    # We store data to redraw when resizing
    current_items = []
    
    def get_items():
        try:
            res = requests.get(f"{API_URL}/vencimientos", timeout=10)
            if res.status_code == 200:
                return res.json()
            else:
                log(f"API Error: {res.status_code}")
                return []
        except Exception as e:
            log(f"API Exception: {e}")
            return []

    def build_mobile_view(items):
        lv = ft.Column(spacing=10, scroll="auto")
        for item in items:
            icon_name = "warning"
            color = "red"
            status = str(item.get('estado', '')).lower()
            if "pagado" in status:
                icon_name = "check_circle"
                color = "green"
            elif "pendiente" in status:
                icon_name = "schedule"
                color = "orange"

            card = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(icon_name, color=color),
                        ft.Text(f"{item.get('proveedor')} - ${item.get('monto')}", weight="bold", color="black"),
                    ]),
                    ft.Text(f"Vence: {item.get('fecha')}", color="black"),
                    ft.Row([ft.TextButton("Ver PDF"), ft.TextButton("Pagar")], alignment="end")
                ]),
                padding=10, bgcolor="#f5f5f5", border_radius=5, margin=5
            )
            lv.controls.append(card)
        return lv

    def build_desktop_view(items):
        # Create a DataTable for Desktop
        rows = []
        for item in items:
            status = str(item.get('estado', ''))
            color = "red"
            if "Pagado" in status: color = "green"
            elif "Pendiente" in status: color = "orange"

            rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(item.get('fecha')), color="black")),
                    ft.DataCell(ft.Text(str(item.get('proveedor')), weight="bold", color="black")),
                    ft.DataCell(ft.Text(str(item.get('servicio')), color="black")),
                    ft.DataCell(ft.Text(f"${item.get('monto')}", color="black")),
                    ft.DataCell(ft.Container(
                        content=ft.Text(status, color="white", size=10),
                        bgcolor=color, padding=5, border_radius=5
                    )),
                    ft.DataCell(ft.Row([
                        ft.IconButton("picture_as_pdf", tooltip="Ver PDF"),
                        ft.IconButton("attach_money", tooltip="Pagar")
                    ]))
                ])
            )
        
        dt = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Fecha", color="black")),
                ft.DataColumn(ft.Text("Proveedor", color="black")),
                ft.DataColumn(ft.Text("Servicio", color="black")),
                ft.DataColumn(ft.Text("Monto", color="black")),
                ft.DataColumn(ft.Text("Estado", color="black")),
                ft.DataColumn(ft.Text("Acciones", color="black")),
            ],
            rows=rows,
            border=ft.border.all(1, "grey"),
            vertical_lines=ft.border.all(1, "#eeeeee"),
            heading_row_color="#e0e0e0",
        )
        return ft.Column([dt], scroll="auto")

    def render_content():
        page.clean()
        
        # Header
        page.add(ft.Container(
            content=ft.Row([
                ft.Icon("language", color="white"),
                ft.Text("Gestor Vencimientos Web", size=20, weight="bold", color="white")
            ]),
            bgcolor="#1976d2", padding=15
        ))

        # Content based on width
        if not current_items:
             page.add(ft.Text("Cargando o Sin Datos...", color="black"))
        else:
            if page.width < 600:
                log("Rendering Mobile View")
                page.add(ft.Text("Vista Movil", color="grey", italic=True))
                page.add(build_mobile_view(current_items))
            else:
                log("Rendering Desktop View")
                page.add(ft.Text("Vista Escritorio", color="grey", italic=True))
                page.add(build_desktop_view(current_items))
        
        page.update()

    def on_resize(e):
        render_content()

    page.on_resized = on_resize

    # Initial Load
    items = get_items()
    if items:
        current_items = items
        render_content()
    else:
        # Retry login if needed? For WEB, we assume auto-login or public view for prototype
        # Or simplistic login
        pass # Keep simple for now

    # Just force a render
    render_content()

if __name__ == "__main__":
    # Launch in Browser
    ft.app(target=main, view="web_browser", port=8555)
