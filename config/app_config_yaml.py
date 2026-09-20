"""
Application configuration manager using YAML format.

Handles loading, accessing, and saving configuration settings
from YAML config files with support for nested values.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Optional


class AppConfig:
    """
    YAML-based configuration manager for mangpx.
    
    Supports nested configuration hierarchy with dot-notation access.
    Example: config.get('Map.track.path.color') returns 'FF0000'
    """
    
    DEFAULT_CONFIG_FILE = 'config/settings.yaml'
    
    def __init__(self, config_file: str = DEFAULT_CONFIG_FILE):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to YAML configuration file
        """
        self.config_file = Path(config_file)
        self.config_data = {}
        self.load_from_file()
    
    def load_from_file(self) -> bool:
        """
        Load configuration from YAML file.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.config_file.exists():
            print(f"⚠️  Config file not found: {self.config_file}")
            return False
        
        try:
            with open(self.config_file, 'r') as f:
                self.config_data = yaml.safe_load(f) or {}
            print(f"✅ Configuration loaded from: {self.config_file}")
            return True
        except yaml.YAMLError as e:
            print(f"❌ Error parsing YAML: {e}")
            return False
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            return False
    
    def save_to_file(self) -> bool:
        """
        Save configuration to YAML file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(self.config_data, f, default_flow_style=False, sort_keys=False)
            print(f"✅ Configuration saved to: {self.config_file}")
            return True
        except Exception as e:
            print(f"❌ Error saving config: {e}")
            return False
    
    def get(self, path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            path: Dot-separated path (e.g., 'Map.track.path.color')
            default: Value to return if path not found
        
        Returns:
            Configuration value or default
        """
        keys = path.split('.')
        value = self.config_data
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_int(self, path: str, default: int = 0) -> int:
        """Get integer configuration value."""
        value = self.get(path, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def get_float(self, path: str, default: float = 0.0) -> float:
        """Get float configuration value."""
        value = self.get(path, default)
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def get_bool(self, path: str, default: bool = False) -> bool:
        """Get boolean configuration value."""
        value = self.get(path, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', '1', 'on')
        return bool(value)
    
    def get_str(self, path: str, default: str = "") -> str:
        """Get string configuration value."""
        value = self.get(path, default)
        return str(value) if value is not None else default
    
    def get_list(self, path: str, default: list = None) -> list:
        """Get list configuration value."""
        if default is None:
            default = []
        value = self.get(path, default)
        return value if isinstance(value, list) else default
    
    def set(self, path: str, value: Any) -> None:
        """
        Set configuration value using dot notation.
        
        Args:
            path: Dot-separated path (e.g., 'Map.track.path.color')
            value: Value to set
        """
        keys = path.split('.')
        config = self.config_data
        
        # Navigate/create nested structure
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # Set final value
        config[keys[-1]] = value
    
    def get_all(self) -> dict:
        """Get entire configuration dictionary."""
        return self.config_data
    
    def __repr__(self):
        return f"AppConfig(file={self.config_file})"


def get_config(config_file: str = 'config/settings.yaml') -> AppConfig:
    """
    Factory function to get or create AppConfig instance.
    
    Args:
        config_file: Path to YAML configuration file
    
    Returns:
        AppConfig instance
    """
    return AppConfig(config_file)
