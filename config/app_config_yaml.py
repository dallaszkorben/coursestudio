"""
Application configuration manager using YAML format.

Handles loading, accessing, and saving configuration settings
from YAML config files with support for nested values.

Includes PyQt5 signals for real-time config change notifications,
enabling widgets to stay synchronized when config values change.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Optional

from PyQt5.QtCore import QObject, pyqtSignal


class AppConfig(QObject):
    """
    YAML-based configuration manager for CourseStudio with signal support.
    
    Supports nested configuration hierarchy with dot-notation access.
    Example: config.get('Map.track.path.color') returns 'FF0000'
    
    Signals:
        config_changed: Emitted when any config value changes
            Args: (key: str, value: Any) - The config key and new value
        
        map_position_changed: Emitted when map position/zoom changes
            Args: (center_lat: float, center_lon: float, zoom: int)
            Convenience signal for tracking map state changes
    """
    
    # Signals
    config_changed = pyqtSignal(str, object)  # key, value
    map_position_changed = pyqtSignal(float, float, int)  # lat, lon, zoom
    
    DEFAULT_CONFIG_FILE = 'config/settings.yaml'
    
    def __init__(self, config_file: str = DEFAULT_CONFIG_FILE):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to YAML configuration file
        """
        super().__init__()
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
    
    def get_dict(self, path: str, default: dict = None) -> dict:
        """
        Get dictionary configuration value.
        
        Args:
            path: Dot-separated path (e.g., 'Appearance.MapDisplay.TrackPath.colors')
            default: Value to return if path not found
        
        Returns:
            Dictionary or default
        """
        if default is None:
            default = {}
        value = self.get(path, default)
        return value if isinstance(value, dict) else default
    
    def set(self, path: str, value: Any) -> None:
        """
        Set configuration value using dot notation.
        
        Emits config_changed signal when value is updated.
        Emits map_position_changed signal for map-related changes.
        
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
        
        # ✅ NEW: Emit config_changed signal
        self.config_changed.emit(path, value)
        
        # ✅ NEW: Emit map_position_changed signal for map-related keys
        if path == 'appearance.tiles.recent_center.lat' or \
           path == 'appearance.tiles.recent_center.lon' or \
           path == 'appearance.tiles.recent_zoom':
            # Emit map position changed signal with all three values
            lat = self.get_float('appearance.tiles.recent_center.lat', 0)
            lon = self.get_float('appearance.tiles.recent_center.lon', 0)
            zoom = self.get_int('appearance.tiles.recent_zoom', 10)
            self.map_position_changed.emit(lat, lon, zoom)
    
    def set_silent(self, path: str, value: Any) -> None:
        """
        Set configuration value WITHOUT emitting signals.
        
        Used internally to set multiple related values without triggering
        intermediate signal emissions. Call emit_map_position_changed() 
        manually after setting all values.
        
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
        
        # Set final value (NO signals emitted)
        config[keys[-1]] = value
    
    def emit_map_position_changed(self) -> None:
        """
        Manually emit map_position_changed signal.
        
        Used after setting multiple map-related values via set_silent()
        to emit a single signal with all values set correctly.
        
        This prevents the feedback loop caused by emitting signals
        after each individual set() call.
        """
        lat = self.get_float('appearance.tiles.recent_center.lat', 0)
        lon = self.get_float('appearance.tiles.recent_center.lon', 0)
        zoom = self.get_int('appearance.tiles.recent_zoom', 10)
        self.map_position_changed.emit(lat, lon, zoom)
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
