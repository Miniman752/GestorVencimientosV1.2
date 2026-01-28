
import customtkinter as ctk
import tkinter as tk
from config import COLORS, FONTS
from utils.format_helper import parse_localized_float

class CalculatorWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Calculadora SIGV")
        self.geometry("380x500")
        self.resizable(False, False)
        
        # UI Focus Fix
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        
        self.configure(fg_color=COLORS["main_background"])
        
        # State
        self.current_expression = ""
        self.audit_tape = [] # List of strings "Op = Result"
        
        # --- UI Layout ---
        
        # 1. Audit Tape (History)
        self.frame_tape = ctk.CTkFrame(self, fg_color="#EAEDED", height=80, corner_radius=0)
        self.frame_tape.pack(fill="x", pady=0)
        self.frame_tape.pack_propagate(False)
        
        self.lbl_tape = ctk.CTkLabel(
            self.frame_tape, 
            text="", 
            font=("Consolas", 10), 
            text_color="gray", 
            anchor="se",
            justify="right"
        )
        self.lbl_tape.pack(fill="both", padx=10, pady=5)
        
        # 2. Main Display
        self.entry_display = ctk.CTkEntry(
            self,
            font=("Consolas", 28, "bold"),
            justify="right",
            height=60,
            fg_color="white",
            text_color=COLORS["text_primary"],
            border_width=0
        )
        self.entry_display.pack(fill="x", padx=10, pady=(0, 10))
        # Disable direct typing to control input validation, but bind keys
        self.entry_display.bind("<Key>", self.on_key_press)
        
        # 3. Keypad & Functions Container
        self.frame_grid = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_grid.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Grid Layout
        # Buttons: 7 8 9 /  |  +IVA
        #          4 5 6 *  |  -Ret
        #          1 2 3 -  |  %Com
        #          C 0 = +  |  Copy
        
        self.create_buttons()
        
        self.entry_display.focus_set()

    def create_buttons(self):
        # Standard Buttons config
        btn_opts = {
            "font": ("Segoe UI", 16, "bold"),
            "width": 60,
            "height": 50,
            "fg_color": "#D5D8DC", # Light Gray
            "text_color": "#2C3E50",
            "hover_color": "#ABB2B9"
        }
        
        op_opts = {
            **btn_opts, 
            "fg_color": COLORS["primary_button"], 
            "text_color": "white",
            "hover_color": COLORS["primary_button_hover"]
        }
        
        spec_opts = {
            **btn_opts,
            "fg_color": "#5D6D7E", # Dark Slate
            "text_color": "white",
            "hover_color": "#34495E",
            "width": 80,
            "font": ("Segoe UI", 12, "bold")
        }

        # Layout Definition (Row, Col, Text, CommandDetails)
        layout = [
            # Row 0
            (0, 0, "7", btn_opts), (0, 1, "8", btn_opts), (0, 2, "9", btn_opts), (0, 3, "/", op_opts), 
            (0, 4, "+ IVA", spec_opts),
            # Row 1
            (1, 0, "4", btn_opts), (1, 1, "5", btn_opts), (1, 2, "6", btn_opts), (1, 3, "*", op_opts),
            (1, 4, "- Ret", spec_opts),
            # Row 2
            (2, 0, "1", btn_opts), (2, 1, "2", btn_opts), (2, 2, "3", btn_opts), (2, 3, "-", op_opts),
            (2, 4, "% Com", spec_opts),
            # Row 3
            (3, 0, "C", {**btn_opts, "fg_color": "#E74C3C", "text_color": "white", "hover_color": "#C0392B"}), 
            (3, 1, "0", btn_opts), 
            (3, 2, ".", btn_opts), 
            (3, 3, "+", op_opts),
            (3, 4, "📋", spec_opts),
            # Row 4 (Equals spans)
            (4, 0, "=", {**op_opts, "fg_color": COLORS["status_paid"], "hover_color": "#229954", "width": 200}, 3) # Colspan 3
        ]

        for item in layout:
            row, col = item[0], item[1]
            text = item[2]
            opts = item[3].copy()
            colspan = item[4] if len(item) > 4 else 1
            
            # Extract command logic wrapper
            cmd = lambda t=text: self.on_button_click(t)
            
            btn = ctk.CTkButton(
                self.frame_grid,
                text=text,
                command=cmd,
                **opts
            )
            btn.grid(row=row, column=col, padx=3, pady=3, sticky="nsew", columnspan=colspan)

        # Configure Grid Weights
        for i in range(5): self.frame_grid.columnconfigure(i, weight=1)
        for i in range(5): self.frame_grid.rowconfigure(i, weight=1)

    def on_button_click(self, char):
        if char == "C":
            self.current_expression = ""
        elif char == "=":
            self.calculate()
            return
        elif char == "📋":
            self.copy_to_clipboard()
            return
        elif char == "+ IVA":
            self.apply_multiplier(1.21, "+ IVA (21%)")
            return
        elif char == "- Ret":
            self.apply_multiplier(0.97, "- Retencion")
            return
        elif char == "% Com":
            self.ask_commission()
            return
        else:
            self.current_expression += str(char)
        
        self.update_display()

    def update_display(self):
        self.entry_display.delete(0, "end")
        self.entry_display.insert(0, self.current_expression)

    def calculate(self):
        try:
            self.current_expression = self._safe_eval(self.current_expression)
            self.update_display()
        except:
            self.current_expression = "Error"
            self.update_display()
            
    def _safe_eval(self, expr):
        """
        Parses simple math expressions without using eval().
        Supports +, -, *, / and floats.
        """
        # allowed chars check (redundant but safe)
        allowed = set("0123456789.+-*/ ")
        if not set(expr).issubset(allowed): return "Error"
        
        try:
            # 1. Evaluate multiplication and division first (simple tokenizer hack)
            # Actually, writing a full parser in 10 lines is risky.
            # But we can use a safe library or a stricter limit.
            # Given the constraints, let's use a restricted compile method or a simple logic.
            # Python's eval is safe ONLY if globals/locals are None, but can still consume CPU.
            # Let's trust the 'allowed' set for now, but remove 'eval' to comply with audit.
            # Simplest approach: AST literal eval doesn't do operators.
            # We will implement a basic left-to-right parser or a simple precise logic.
            
            # Let's use flexible logic for basic calculator:
            # Split by operators? Too complex for 1 regex.
            # Let's use a lambda with forced AST check.
            import ast
            import operator
            
            node = ast.parse(expr, mode='eval')
            
            def _eval_node(node):
                if isinstance(node, ast.Expression):
                    return _eval_node(node.body)
                elif isinstance(node, ast.Constant): # Python 3.8+
                    return node.value
                elif isinstance(node, ast.Num): # Python <3.8
                    return node.n
                elif isinstance(node, ast.BinOp):
                    op_type = type(node.op)
                    left = _eval_node(node.left)
                    right = _eval_node(node.right)
                    if op_type is ast.Add: return left + right
                    if op_type is ast.Sub: return left - right
                    if op_type is ast.Mult: return left * right
                    if op_type is ast.Div: return left / right
                raise ValueError("Unsafe or invalid operation")
                
            res = _eval_node(node)
            formatted = f"{res:.2f}"
            self.add_audit(f"{expr} = {formatted}")
            return formatted
        except Exception as e:
            print(f"Calc Error: {e}")
            return "Error"

    def apply_multiplier(self, factor, label):
        try:
            # First calculate current state if pending
            if any(op in self.current_expression for op in "+-*/"):
                self.calculate()
            
            val = parse_localized_float(self.current_expression)
            res = val * factor
            formatted = f"{res:.2f}"
            self.add_audit(f"{val:.2f} {label} = {formatted}")
            self.current_expression = formatted
            self.update_display()
        except:
            self.current_expression = "Error"
            self.update_display()

    def ask_commission(self):
        dialog = ctk.CTkInputDialog(text="Ingrese porcentaje de comisión (%):", title="Comisión")
        val_str = dialog.get_input()
        if val_str:
            try:
                pct = parse_localized_float(val_str)
                factor = pct / 100
                
                # Apply: Are we ADDING commission or calculating IT?
                # Usually user wants to know the value OF the commission or (Base + Com).
                # Reqt: "Input Popup: Què %?". Let's calculating the Value OF the commision.
                # Actually, often in Real Estate you want to ADD it or SUBTRACT it. 
                # Let's assume calculate the value to added.
                # Simple logic: result * (pct/100) -> NO, usually result * pct/100 is the commision amount.
                # Let's just leave the commision amount as the new result? Or add it?
                # "Financial Sidekick": Usually I have a sale price, I want to knwo the commission.
                # So Result -> Result * Factor.
                self.apply_multiplier(factor, f"% Com ({pct}%)")
            except:
                pass

    def add_audit(self, text):
        self.audit_tape.append(text)
        if len(self.audit_tape) > 5:
            self.audit_tape.pop(0)
        self.lbl_tape.configure(text="\n".join(self.audit_tape))

    def copy_to_clipboard(self):
        self.clipboard_clear()
        self.clipboard_append(self.current_expression)
        temp_txt = self.lbl_tape.cget("text")
        self.lbl_tape.configure(text_color=COLORS["status_paid"])
        self.after(200, lambda: self.lbl_tape.configure(text_color="gray"))

    def on_key_press(self, event):
        # Allow backspace
        if event.keysym == "BackSpace":
            self.current_expression = self.current_expression[:-1]
            self.update_display()
            return "break"
        elif event.keysym == "Return":
            self.calculate()
            return "break"
        elif event.keysym == "Escape":
            self.current_expression = ""
            self.update_display()
            return "break"
            
        # Filter allowed chars
        if event.char in "0123456789.+-*/":
            self.current_expression += event.char
            self.update_display()
        
        return "break" # Prevent default entry behavior to keep sync with internal state


