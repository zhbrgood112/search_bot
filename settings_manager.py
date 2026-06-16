# settings_manager.py
import json
import os

class SettingsManager:
    def __init__(self, filename):
        self.filename = filename
        self.settings = self.load()
    
    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            "active": True,
            "forward_media": True
        }
    
    def save(self):
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=2)
    
    def toggle_active(self):
        self.settings["active"] = not self.settings["active"]
        self.save()
        return self.settings["active"]
    
    def toggle_media(self):
        self.settings["forward_media"] = not self.settings["forward_media"]
        self.save()
        return self.settings["forward_media"]