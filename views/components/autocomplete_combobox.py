import customtkinter as ctk

class AutocompleteCombobox(ctk.CTkComboBox):
    def __init__(self, master=None, completion_list=None, **kwargs):
        # Extract command to avoid double binding issues, though super handles it.
        # We need to ensure we don't pass 'values' in kwargs if we want to use completion_list
        if 'values' in kwargs:
             del kwargs['values']
             
        super().__init__(master, **kwargs)
        
        self._completion_list = sorted(completion_list) if completion_list else []
        self.configure(values=self._completion_list)
        
        # Clear the default "CTkComboBox" text immediately
        self.set("")
        
        self._entry.bind('<KeyRelease>', self._on_key_release)
        # Bind Return/Tab to trigger the command (selection confirmation)
        self._entry.bind('<Return>', self._on_confirm)
        self._entry.bind('<FocusOut>', self._on_confirm)

    def set_completion_list(self, completion_list):
        self._completion_list = sorted(completion_list)
        self.configure(values=self._completion_list)
        
    def _on_key_release(self, event):
        # Filter logic
        if event.keysym in ['Up', 'Down', 'Left', 'Right', 'Return', 'Tab', 'Escape']:
            return

        current_text = self.get().lower()
        filtered_items = [item for item in self._completion_list if current_text in item.lower()]
        
        if filtered_items:
            self.configure(values=filtered_items)

            
    def _on_confirm(self, event=None):
        # Trigger the command manually since typing doesn't trigger it in standard CTkComboBox
        if hasattr(self, "_command") and self._command:
            self._command(self.get())


