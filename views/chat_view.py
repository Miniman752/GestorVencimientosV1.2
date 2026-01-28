import customtkinter as ctk
from config import COLORS, FONTS
from services.chat_service import ChatService

class ChatView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color=COLORS["main_background"])
        
        self.service = ChatService()
        
        # Header
        self.header = ctk.CTkFrame(self, height=60, fg_color=COLORS["content_surface"])
        self.header.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(self.header, text="🧠 Asistente CFO Virtual", font=FONTS["heading"], text_color=COLORS["primary_button"]).pack(side="left", padx=20, pady=15)
        
        # Chat History (Scrollable)
        self.history_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.history_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        # Initial Greeting
        self.add_bubble("¡Hola! Soy tu Asistente Financiero. Pregúntame sobre tu deuda total, gastos por proveedor o historial.\nEj: '¿Cuánto debo?'", is_user=False)
        
        # Input Area
        self.input_frame = ctk.CTkFrame(self, height=50, fg_color=COLORS["content_surface"])
        self.input_frame.pack(fill="x", padx=20, pady=20)
        
        self.entry_msg = ctk.CTkEntry(self.input_frame, placeholder_text="Escribe tu consulta aquí...", height=40, font=("Segoe UI", 12))
        self.entry_msg.pack(side="left", fill="x", expand=True, padx=10, pady=5)
        self.entry_msg.bind("<Return>", self.send_message)
        
        self.btn_send = ctk.CTkButton(self.input_frame, text="Enviar ✈️", width=100, height=40, command=self.send_message, fg_color=COLORS["primary_button"])
        self.btn_send.pack(side="right", padx=10, pady=5)
        
    def send_message(self, event=None):
        msg = self.entry_msg.get()
        if not msg.strip(): return
        
        self.add_bubble(msg, is_user=True)
        self.entry_msg.delete(0, 'end')
        
        # Process in BG (Mocking async for UI responsiveness)
        self.after(100, lambda: self._process_response(msg))
        
    def _process_response(self, msg):
        # Call Service
        response = self.service.process_query(msg)
        self.add_bubble(response, is_user=False)
        
    def add_bubble(self, text, is_user):
        # Container
        frame = ctk.CTkFrame(self.history_frame, fg_color="transparent")
        frame.pack(fill="x", pady=5)
        
        # Bubble Style
        color = COLORS["secondary_button"] if is_user else COLORS["content_surface"]
        anchor = "e" if is_user else "w"
        justify = "right" if is_user else "left"
        
        bubble = ctk.CTkLabel(
            frame, 
            text=text, 
            fg_color=color, 
            text_color="white" if is_user else COLORS["text_primary"],
            corner_radius=15, 
            pady=10, 
            padx=15,
            wraplength=600,
            justify=justify,
            font=("Segoe UI", 12)
        )
        bubble.pack(side="right" if is_user else "left", padx=10)
        
        # Auto scroll down
        self.history_frame._parent_canvas.yview_moveto(1.0)


