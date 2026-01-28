
import os
import platform
from pathlib import Path

class CloudService:
    @staticmethod
    def detect_cloud_providers():
        """
        Scans standard user directories for known Cloud Storage Providers.
        Returns a list of dicts: [{'name': 'OneDrive', 'path': '/path/to/OneDrive'}, ...]
        """
        user_home = Path.home()
        providers = []
        
        # Standard Paths (Windows oriented, but safe)
        # 1. Check Environment Variables (Reliable for moved folders)
        env_vars = {
            "OneDrive": ["OneDrive", "OneDriveConsumer", "OneDriveCommercial"],
            "Dropbox": ["Dropbox"],
            "Google Drive": ["GoogleDrive"] # Less common env var, but sometimes
        }
        
        for name, env_keys in env_vars.items():
            for key in env_keys:
                path = os.environ.get(key)
                if path and os.path.exists(path):
                    providers.append({
                        "name": name,
                        "path": path,
                        "icon": name.lower().replace(" ", "")
                    })
                    break # Found one for this provider
        
        # 2. Check Standard Paths (Fallback)
        # Scan both C: and actual home (in case they differ or mapped drives)
        scan_roots = [user_home]
        # 2. Check standard paths dynamically
        user_home = os.path.expanduser("~")
        
        # OneDrive
        onedrive = os.path.join(user_home, "OneDrive")
        if os.path.exists(onedrive):
             scan_roots.append(Path(onedrive))
             
        potential_paths = {
            "Google Drive": ["Google Drive", "GoogleDrive"],
            "Dropbox": ["Dropbox"],
            "iCloud": ["iCloudDrive"]
        }
        
        for root in set(scan_roots): # Use set to avoid duplicates
            for name, subpaths in potential_paths.items():
                # Don't add if already found via Env Var
                if any(p['name'] == name for p in providers):
                    continue
                    
                for sub in subpaths:
                    p = root / sub
                    if p.exists() and p.is_dir():
                        providers.append({
                            "name": name,
                            "path": str(p),
                            "icon": name.lower().replace(" ", "")
                        })
                        break
        
        return providers

