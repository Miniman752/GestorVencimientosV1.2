import platform
import logging
from utils.logger import app_logger
from utils.exceptions import PlatformError

class AudioService:
    _instance = None
    _os_name = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AudioService, cls).__new__(cls)
            cls._os_name = platform.system()
            app_logger.info(f"AudioService initialized on {cls._os_name}")
        return cls._instance

    def play_success(self):
        """Plays a 'Crystal Clean' success chime (Ascending major third)."""
        try:
            if self._os_name == 'Windows':
                import winsound
                # C6 (1047Hz) -> E6 (1318Hz) : Happy/Success
                # Duration small for crispness
                winsound.Beep(1047, 100)
                winsound.Beep(1318, 150)
            else:
                pass
        except Exception as e:
            app_logger.warning(f"Audio playback failed: {e}")

    def play_error(self):
        """Plays a 'Soft Warning' thud (Descending minor third)."""
        try:
            if self._os_name == 'Windows':
                import winsound
                # G4 (392Hz) -> E4 (329Hz) : Warning/Error
                winsound.Beep(392, 100)
                winsound.Beep(329, 200)
            else:
                pass
        except Exception:
            pass
            
    def play_alert(self):
        self.play_error()


