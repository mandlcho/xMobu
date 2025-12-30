"""
Configuration management for xMobu
"""

import json
import os
from pathlib import Path


class ConfigManager:
    """Manages configuration for xMobu"""

    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._config is None:
            self._load_config()

    def _get_config_path(self):
        """Get the path to the config file"""
        # Get the root directory of xMobu
        root_dir = Path(__file__).parent.parent
        config_dir = root_dir / "config"

        # Check for local config first (for user overrides)
        local_config = config_dir / "local_config.json"
        if local_config.exists():
            return local_config

        # Otherwise use default config
        return config_dir / "config.json"

    def _load_config(self):
        """Load configuration from JSON file"""
        config_path = self._get_config_path()

        if config_path.exists():
            with open(config_path, 'r') as f:
                self._config = json.load(f)
        else:
            # Default configuration
            self._config = self._get_default_config()

    def _get_default_config(self):
        """Return default configuration"""
        return {
            "version": "1.0.0",
            "mobu": {
                "menu_name": "xMobu",
                "tool_categories": [
                    {"name": "Animation", "enabled": True},
                    {"name": "Rigging", "enabled": True},
                    {"name": "Unreal Engine", "enabled": True},
                    {"name": "Debug", "enabled": True}
                ]
            },
            "perforce": {
                "server": "",
                "user": "",
                "workspace": ""
            },
            "export": {
                "fbx_path": ""
            },
            "unreal": {
                "default_project_path": "",
                "content_browser_path": "/Game/",
                "import_animations": True
            },
            "logging": {
                "level": "INFO",
                "log_to_file": False
            }
        }

    def get(self, key, default=None):
        """Get configuration value by key (supports dot notation)"""
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key, value):
        """Set configuration value by key (supports dot notation)"""
        keys = key.split('.')
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def save(self):
        """Save current configuration to file"""
        config_path = self._get_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, 'w') as f:
            json.dump(self._config, f, indent=4)

    @property
    def config(self):
        """Get the entire configuration dictionary"""
        return self._config


# Singleton instance
config = ConfigManager()
