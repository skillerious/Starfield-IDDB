import json
import os

DEFAULT_SETTINGS = {
    "theme": "dark",
    "highlight_color": "#3a7ae0",
    "font_color": "white",
    "background_color": "#1e1e1e",
    "alternate_background_color": "#2e2e2e",
    "border_color": "#3a7ae0",
    "button_hover_color": "#3a7ae0",
    "button_press_color": "#2a69bf",
    "toolbar_bg_start": "#3a3a3a",
    "toolbar_bg_end": "#1e1e1e",
    "dialog_bg_color": "#1e1e1e",
    "label_color": "white",
    "font_size": 12,
    "row_height": 50,
    "show_grid": True,
    "alternate_row_colors": True,
    "shortcut_new_file": "Ctrl+N",
    "shortcut_add": "Ctrl+A",
    "shortcut_edit": "Ctrl+E",
    "shortcut_open": "Ctrl+O",
    "shortcut_save": "Ctrl+S",
    "shortcut_save_as": "Ctrl+Shift+S",
    "shortcut_undo": "Ctrl+Shift+Z",
    "shortcut_redo": "Ctrl+Y",
    "shortcut_delete": "Delete",
    "default_csv_path": "",
    "default_json_path": "",
    "startup_json": "Favourites",
    "custom_json_path": "",
    "auto_save": False,
    "auto_save_interval": 5,
    "backup_on_exit": False,
    "backup_path": "",
    "backup_interval": 60,
    "check_for_updates": True,
    "show_notifications": True,
    "enable_error_logging": True,
    "debug_mode": False,
    "cache_timeout": 60,
    "enable_scheduled_updates": False,
    "update_interval_days": 7
}

SETTINGS_FILE = "settings.json"

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return DEFAULT_SETTINGS
    with open(SETTINGS_FILE, "r") as f:
        try:
            settings = json.load(f)
        except json.JSONDecodeError:
            settings = DEFAULT_SETTINGS
    return settings

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)
