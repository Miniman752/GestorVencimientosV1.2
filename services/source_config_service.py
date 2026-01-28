
import json
import os

class SourceConfigService:
    def __init__(self, storage_path="data/sources.json"):
        self.storage_path = storage_path
        self._ensure_storage()
    
    def _ensure_storage(self):
        if not os.path.exists("data"):
            os.makedirs("data", exist_ok=True)
            
        if not os.path.exists(self.storage_path):
            # Create default sources
            defaults = [
                {
                    "name": "Banco Galicia - Pesos",
                    "type": "Banco",
                    "format": "CSV",
                    "currency": "ARS",
                    "delimiter": ";", 
                    "header_row": 0,
                    "mapping": {
                        "fecha": "Fecha",
                        "descripcion": "Descripción",
                        "importe_entrada": "Crédito",
                        "importe_salida": "Débito",
                        "identificador_unico": "Referencia"
                    }
                },
                {
                    "name": "Santander - Dólares",
                    "type": "Banco",
                    "format": "CSV",
                    "currency": "USD",
                    "delimiter": ",",
                    "header_row": 0,
                    "mapping": {
                        "fecha": "Date",
                        "descripcion": "Concept",
                        "importe_entrada": "Amount Credit",
                        "importe_salida": "Amount Debit",
                        "identificador_unico": "Ref"
                    }
                }
            ]
            self.save_sources(defaults)

    def get_sources(self):
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("Error loading sources:", e)
            return []

    def save_sources(self, sources):
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(sources, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print("Error saving sources:", e)
            return False

    def add_source(self, new_source):
        sources = self.get_sources()
        sources.append(new_source)
        return self.save_sources(sources)

    def update_source(self, old_name, updated_source):
        sources = self.get_sources()
        for i, s in enumerate(sources):
            if s['name'] == old_name:
                sources[i] = updated_source
                return self.save_sources(sources)
        return False

    def delete_source(self, name):
        sources = self.get_sources()
        sources = [s for s in sources if s['name'] != name]
        return self.save_sources(sources)


