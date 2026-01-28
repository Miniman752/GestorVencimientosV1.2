
import json
import os
import re
from datetime import datetime

class ReconciliationHistoryService:
    def __init__(self, storage_dir="data/reconciliations"):
        self.storage_dir = storage_dir
        self._ensure_storage()
        
    def _ensure_storage(self):
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir, exist_ok=True)
            
    def _sanitize_filename(self, name):
        return re.sub(r'[^a-zA-Z0-9_\-]', '_', name)

    def save_snapshot(self, period, source_name, report_data, summary_stats):
        """
        Saves the current reconciliation state.
        period: str (e.g. "11-2025")
        source_name: str
        report_data: list of dicts
        summary_stats: dict (match, new, conflict counts)
        """
        clean_source = self._sanitize_filename(source_name)
        clean_period = self._sanitize_filename(period)
        filename = f"{clean_source}_{clean_period}.json"
        filepath = os.path.join(self.storage_dir, filename)
        
        data = {
            "meta": {
                "period": period,
                "source": source_name,
                "saved_at": datetime.now().isoformat(),
                "stats": summary_stats
            },
            "items": report_data
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False, default=str)
            return True, filepath
        except Exception as e:
            return False, str(e)

    def list_snapshots(self):
        """Returns list of available snapshots metadata."""
        snapshots = []
        if not os.path.exists(self.storage_dir): return []
        
        for f in os.listdir(self.storage_dir):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(self.storage_dir, f), 'r', encoding='utf-8') as file:
                        d = json.load(file)
                        meta = d.get('meta', {})
                        snapshots.append(meta)
                except: pass
        
        # Sort by saved_at desc
        snapshots.sort(key=lambda x: x.get('saved_at', ''), reverse=True)
        return snapshots

    def load_snapshot(self, period, source_name):
        clean_source = self._sanitize_filename(source_name)
        clean_period = self._sanitize_filename(period)
        filename = f"{clean_source}_{clean_period}.json"
        filepath = os.path.join(self.storage_dir, filename)
        
        if not os.path.exists(filepath): return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    def delete_snapshot(self, period, source_name):
        clean_source = self._sanitize_filename(source_name)
        clean_period = self._sanitize_filename(period)
        filename = f"{clean_source}_{clean_period}.json"
        filepath = os.path.join(self.storage_dir, filename)
        
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                return True, "Eliminado correctamente"
            except Exception as e:
                return False, str(e)
        return False, "Archivo no encontrado"

    def get_storage_path(self):
        return os.path.abspath(self.storage_dir)


