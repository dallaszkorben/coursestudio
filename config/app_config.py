"""
Configuration management for mangpx application.

Loads and provides thread-safe access to configuration values from settings.ini.
Supports automatic type conversion with sensible defaults.

Author: Development Team
Date: 2026-09-20
"""

import configparser
import os
from pathlib import Path
from typing import Any, Optional


class AppConfig:
    """
    Thread-safe configuration loader for mangpx.
    
    Loads configuration from settings.ini file and provides methods
    to access values with automatic type conversion and defaults.
    
    Example:
        config = AppConfig('config/settings.ini')
        app_name = config.get('Application', 'app_name')
        window_width = config.get_int('UI', 'window_width', default=1400)
        is_backup_enabled = config.get_bool('File', 'create_backup', default=True)
    """
    
    def __init__(self, config_file: str = 'config/settings.ini'):
        """
        Initialize AppConfig and load configuration from file.
        
        Args:
            config_file (str): Path to settings.ini file.
                               Defaults to 'config/settings.ini'
        
        Raises:
            FileNotFoundError: If config file doesn't exist
            configparser.Error: If config file is malformed
        """
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        
        # Verify file exists
        if not os.path.exists(config_file):
            raise FileNotFoundError(
                f"Configuration file not found: {config_file}\n"
                f"Please create {config_file} or use default settings."
            )
        
        # Load configuration file
        try:
            self.config.read(config_file, encoding='utf-8')
        except configparser.Error as e:
            raise configparser.Error(
                f"Error parsing configuration file: {config_file}\n"
                f"Error details: {str(e)}"
            ) from e
        
        # Log successful load
        print(f"✅ Configuration loaded from: {config_file}")
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get configuration value with automatic type inference.
        
        Attempts to parse the value as int, float, or bool before
        returning as string. Returns default if not found.
        
        Args:
            section (str): Configuration section name
            key (str): Configuration key name
            default (Any): Default value if key not found
        
        Returns:
            Any: Configuration value (int, float, bool, or str)
        
        Example:
            value = config.get('Map', 'default_mbtiles')  # Returns string
            zoom = config.get('Map', 'initial_zoom_level')  # Auto-converts to int
        """
        try:
            value = self.config.get(section, key)
            
            # Try to convert to int
            try:
                return int(value)
            except ValueError:
                pass
            
            # Try to convert to float
            try:
                return float(value)
            except ValueError:
                pass
            
            # Try to convert to bool
            if value.lower() in ('true', 'yes', '1', 'on'):
                return True
            elif value.lower() in ('false', 'no', '0', 'off'):
                return False
            
            # Return as string
            return value
            
        except (configparser.NoSectionError, configparser.NoOptionError):
            if default is not None:
                print(f"⚠️  Config key not found: [{section}] {key}, using default: {default}")
            return default
    
    def get_int(self, section: str, key: str, default: int = 0) -> int:
        """
        Get configuration value as integer.
        
        Args:
            section (str): Configuration section name
            key (str): Configuration key name
            default (int): Default value if key not found or conversion fails
        
        Returns:
            int: Configuration value as integer
        
        Raises:
            ValueError: If value cannot be converted to int (caught and returns default)
        
        Example:
            window_width = config.get_int('UI', 'window_width', default=1400)
        """
        try:
            value = self.config.get(section, key)
            return int(value)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default
    
    def get_float(self, section: str, key: str, default: float = 0.0) -> float:
        """
        Get configuration value as float.
        
        Args:
            section (str): Configuration section name
            key (str): Configuration key name
            default (float): Default value if key not found or conversion fails
        
        Returns:
            float: Configuration value as float
        
        Example:
            latitude = config.get_float('Map', 'center_latitude', default=57.5)
        """
        try:
            value = self.config.get(section, key)
            return float(value)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default
    
    def get_bool(self, section: str, key: str, default: bool = False) -> bool:
        """
        Get configuration value as boolean.
        
        Accepts: true, yes, 1, on (case-insensitive) as True
        Accepts: false, no, 0, off (case-insensitive) as False
        
        Args:
            section (str): Configuration section name
            key (str): Configuration key name
            default (bool): Default value if key not found
        
        Returns:
            bool: Configuration value as boolean
        
        Example:
            create_backup = config.get_bool('File', 'create_backup', default=True)
        """
        try:
            value = self.config.get(section, key).lower()
            
            if value in ('true', 'yes', '1', 'on'):
                return True
            elif value in ('false', 'no', '0', 'off'):
                return False
            else:
                print(f"⚠️  Invalid boolean value for [{section}] {key}: {value}, using default: {default}")
                return default
                
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default
    
    def get_str(self, section: str, key: str, default: str = "") -> str:
        """
        Get configuration value as string (no type conversion).
        
        Args:
            section (str): Configuration section name
            key (str): Configuration key name
            default (str): Default value if key not found
        
        Returns:
            str: Configuration value as string
        
        Example:
            app_name = config.get_str('Application', 'app_name', default='mangpx')
        """
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default
    
    def set(self, section: str, key: str, value: Any) -> None:
        """
        Set a configuration value in memory.
        
        Note: Does NOT write to file. Use save_to_file() to persist changes.
        
        Args:
            section (str): Configuration section name (created if not exists)
            key (str): Configuration key name
            value (Any): Value to set (converted to string)
        
        Example:
            config.set('Map', 'initial_zoom_level', 14)
            config.save_to_file()  # Persist changes
        """
        if not self.config.has_section(section):
            self.config.add_section(section)
        
        self.config.set(section, key, str(value))
    
    def save_to_file(self) -> None:
        """
        Save current configuration to file.
        
        Writes all configuration changes back to settings.ini file.
        
        Example:
            config.set('Application', 'version', '1.0.1')
            config.save_to_file()  # Persist to file
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
            print(f"✅ Configuration saved to: {self.config_file}")
        except IOError as e:
            print(f"❌ Error saving configuration file: {e}")
    
    def has_section(self, section: str) -> bool:
        """
        Check if configuration section exists.
        
        Args:
            section (str): Section name to check
        
        Returns:
            bool: True if section exists, False otherwise
        """
        return self.config.has_section(section)
    
    def has_option(self, section: str, key: str) -> bool:
        """
        Check if configuration key exists in section.
        
        Args:
            section (str): Section name
            key (str): Key name to check
        
        Returns:
            bool: True if key exists in section, False otherwise
        """
        return self.config.has_option(section, key)
    
    def list_sections(self) -> list:
        """
        Get list of all configuration sections.
        
        Returns:
            list: All section names
        
        Example:
            sections = config.list_sections()  # ['Application', 'Map', 'File', ...]
        """
        return self.config.sections()
    
    def list_keys(self, section: str) -> list:
        """
        Get list of all keys in a configuration section.
        
        Args:
            section (str): Section name
        
        Returns:
            list: All keys in section, empty list if section not found
        
        Example:
            keys = config.list_keys('Map')  # ['default_mbtiles', 'initial_zoom_level', ...]
        """
        try:
            return self.config.options(section)
        except configparser.NoSectionError:
            return []
    
    def print_all(self) -> None:
        """
        Print entire configuration (useful for debugging).
        
        Example:
            config.print_all()  # Shows all sections and keys
        """
        print("\n" + "="*70)
        print(f"Configuration: {self.config_file}")
        print("="*70)
        
        for section in self.config.sections():
            print(f"\n[{section}]")
            for key, value in self.config.items(section):
                print(f"  {key} = {value}")
        
        print("\n" + "="*70 + "\n")


# ============================================================================
# Convenience functions for global configuration access
# ============================================================================

# Global config instance (lazy-loaded on first use)
_global_config: Optional[AppConfig] = None


def get_config(config_file: str = 'config/settings.ini') -> AppConfig:
    """
    Get or create global configuration instance.
    
    Thread-safe singleton pattern for global config access.
    
    Args:
        config_file (str): Path to settings.ini file
    
    Returns:
        AppConfig: Global configuration instance
    
    Example:
        config = get_config()
        app_name = config.get('Application', 'app_name')
    """
    global _global_config
    
    if _global_config is None:
        _global_config = AppConfig(config_file)
    
    return _global_config


if __name__ == "__main__":
    # Test configuration loading
    try:
        test_config = AppConfig('config/settings.ini')
        print("✅ AppConfig successfully loaded")
        print(f"Sections: {test_config.list_sections()}")
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
