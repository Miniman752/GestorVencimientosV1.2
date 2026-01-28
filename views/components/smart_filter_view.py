
import customtkinter as ctk
from datetime import date, datetime
from config import COLORS, FONTS, FILTER_ALL_OPTION

class SmartFilterView(ctk.CTkFrame):
    """
    A reusable component that inspects data and creates filters automatically.
    """
    def __init__(self, master, on_filter_change_callback, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.callback = on_filter_change_callback
        self.original_data = [] # List of objects or dicts
        self.filters = {} # key: field_name, value: widget
        self.active_filters = {} # key: field_name, value: current_value
        
        # Layout
        self.grid_rowconfigure(0, weight=1)
        
        # Container for widgets
        self.widgets_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.widgets_frame.pack(side="left", fill="x", expand=True)
        
        # Reset Button to the right
        self.btn_reset = ctk.CTkButton(
            self, 
            text="🧹", 
            width=30, 
            fg_color="gray", 
            hover_color="red",
            command=self.reset_filters
        )
        self.btn_reset.pack(side="right", padx=10)

    def set_data(self, data, filterable_columns):
        """
        data: List of objects (e.g. VencimientoDTO)
        filterable_columns: List of dicts
        """
        self.original_data = data
        
        # Check if schema changed
        current_fields = sorted(list(self.filters.keys()))
        new_fields = sorted([col['field'] for col in filterable_columns])
        
        schema_changed = (current_fields != new_fields)
        
        if schema_changed:
            self.active_filters = {}
            # Clear existing widgets
            for widget in self.widgets_frame.winfo_children():
                widget.destroy()
            self.filters = {}

            # Build Widgets
            for idx, col_cfg in enumerate(filterable_columns):
                field = col_cfg['field']
                label = col_cfg.get('label', field)
                ftype = col_cfg.get('type', 'text')
                
                # Container for specific filter
                f_container = ctk.CTkFrame(self.widgets_frame, fg_color="transparent")
                f_container.pack(side="left", padx=5)
                
                # Label
                ctk.CTkLabel(f_container, text=label, font=("Segoe UI", 10)).pack(anchor="w")
                
                widget = None
                
                # Check if explicit options provided
                if 'options' in col_cfg:
                     values = col_cfg['options']
                else:
                     values = self._extract_unique_values(data, field)
                     
                unique_vals = [FILTER_ALL_OPTION] + sorted(list(values))

                if ftype == 'category' or ftype == 'status':
                    # Use Segmented if few options for status
                    if ftype == 'status' and len(values) <= 4:
                         widget = ctk.CTkSegmentedButton(
                            f_container, 
                            values=unique_vals,
                            command=lambda val, f=field: self._on_filter_update(f, val)
                        )
                    else:
                        widget = ctk.CTkComboBox(
                            f_container, 
                            values=unique_vals, 
                            width=120,
                            command=lambda val, f=field: self._on_filter_update(f, val)
                        )
                    widget.set(FILTER_ALL_OPTION)
                
                if widget:
                    self.filters[field] = widget
                    widget.pack()
        else:
            # Schema same, just create non-existing logic if any (unlikely if checks passed)
            # OR just Update Values
            for col_cfg in filterable_columns:
                field = col_cfg['field']
                widget = self.filters.get(field)
                if widget:
                    values = self._extract_unique_values(data, field)
                    unique_vals = [FILTER_ALL_OPTION] + sorted(list(values))
                    
                    if isinstance(widget, ctk.CTkComboBox):
                        widget.configure(values=unique_vals)
                        # Keep selection if valid? 
                        # If current selection not in new values, reset to Todos
                        curr = widget.get()
                        if curr not in unique_vals:
                            widget.set(FILTER_ALL_OPTION)
                    elif isinstance(widget, ctk.CTkSegmentedButton):
                        widget.configure(values=unique_vals)
                        curr = widget.get()
                        if curr not in unique_vals:
                            widget.set(FILTER_ALL_OPTION)

    def _extract_unique_values(self, data, field):
        values = set()
        for item in data:
            val = self._get_field_value(item, field)
            if val: values.add(str(val))
        return values

    def _get_field_value(self, item, field_path):
        """Helper to get value from object using 'prop.subprop' syntax or dict key."""
        try:
            val = item
            for part in field_path.split('.'):
                if hasattr(val, part):
                    val = getattr(val, part)
                elif isinstance(val, dict) and part in val:
                    val = val[part]
                else:
                    return None
            
            # Handle Enums
            if hasattr(val, 'value'):
                return val.value
            return val
        except:
            return None

    def _on_filter_update(self, field, value):
        if value == FILTER_ALL_OPTION:
            if field in self.active_filters:
                del self.active_filters[field]
        else:
            self.active_filters[field] = value
            
        self._apply_filters()

    def _apply_filters(self):
        filtered = []
        for item in self.original_data:
            match = True
            for field, target_val in self.active_filters.items():
                item_val = str(self._get_field_value(item, field))
                if item_val != str(target_val):
                    match = False
                    break
            if match:
                filtered.append(item)
        
        self.callback(filtered)

    def reset_filters(self):
        self.active_filters = {}
        # Reset UI
        for field, widget in self.filters.items():
            if isinstance(widget, ctk.CTkComboBox) or isinstance(widget, ctk.CTkSegmentedButton):
                widget.set(FILTER_ALL_OPTION)
            # Clear text entries if implemented
            
        self.callback(self.original_data)


