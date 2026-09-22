"""
Unit tests for AppConfig class (configuration management).

Tests basic configuration loading, type conversion, and default handling.

Author: Development Team
Date: 2026-09-20
"""

import unittest
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.app_config import AppConfig
from config import constants


class TestAppConfig(unittest.TestCase):
    """Test suite for AppConfig configuration loader."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures before running tests."""
        cls.config_file = 'config/settings.ini'
        
        # Verify config file exists
        if not os.path.exists(cls.config_file):
            raise FileNotFoundError(
                f"Configuration file required for tests: {cls.config_file}"
            )
    
    def setUp(self):
        """Create fresh AppConfig instance for each test."""
        self.config = AppConfig(self.config_file)
    
    # ====================================================================
    # Basic Loading Tests
    # ====================================================================
    
    def test_config_file_loads(self):
        """Test that configuration file loads successfully."""
        self.assertIsNotNone(self.config.config)
        print("✅ Config file loads successfully")
    
    def test_application_section_exists(self):
        """Test that [Application] section exists."""
        self.assertTrue(
            self.config.has_section('Application'),
            "Missing [Application] section in settings.ini"
        )
        print("✅ [Application] section exists")
    
    def test_map_section_exists(self):
        """Test that [Map] section exists."""
        self.assertTrue(
            self.config.has_section('Map'),
            "Missing [Map] section in settings.ini"
        )
        print("✅ [Map] section exists")
    
    def test_coordinates_section_exists(self):
        """Test that [Coordinates] section exists."""
        self.assertTrue(
            self.config.has_section('Coordinates'),
            "Missing [Coordinates] section in settings.ini"
        )
        print("✅ [Coordinates] section exists")
    
    # ====================================================================
    # Type Conversion Tests
    # ====================================================================
    
    def test_get_string_value(self):
        """Test retrieving string configuration values."""
        app_name = self.config.get_str('Application', 'app_name')
        self.assertEqual(app_name, 'CourseStudio')
        print(f"✅ String retrieval: app_name = '{app_name}'")
    
    def test_get_int_value(self):
        """Test retrieving and converting integer values."""
        window_width = self.config.get_int('UI', 'window_width')
        self.assertIsInstance(window_width, int)
        self.assertGreater(window_width, 0)
        print(f"✅ Integer retrieval: window_width = {window_width}")
    
    def test_get_bool_value(self):
        """Test retrieving and converting boolean values."""
        create_backup = self.config.get_bool('File', 'create_backup')
        self.assertIsInstance(create_backup, bool)
        print(f"✅ Boolean retrieval: create_backup = {create_backup}")
    
    def test_get_float_value(self):
        """Test retrieving and converting float values."""
        center_lat = self.config.get_float('Map', 'default_map_center_lat')
        self.assertIsInstance(center_lat, float)
        self.assertGreater(center_lat, -90)
        self.assertLess(center_lat, 90)
        print(f"✅ Float retrieval: default_map_center_lat = {center_lat}")
    
    # ====================================================================
    # Default Value Tests
    # ====================================================================
    
    def test_missing_key_returns_default(self):
        """Test that missing keys return default values."""
        result = self.config.get('Application', 'nonexistent_key', 'default_value')
        self.assertEqual(result, 'default_value')
        print("✅ Missing key returns default value")
    
    def test_missing_section_returns_default(self):
        """Test that missing sections return default values."""
        result = self.config.get('NonexistentSection', 'key', 'default_value')
        self.assertEqual(result, 'default_value')
        print("✅ Missing section returns default value")
    
    def test_get_int_with_default(self):
        """Test get_int with default value."""
        result = self.config.get_int('NonexistentSection', 'key', 999)
        self.assertEqual(result, 999)
        print("✅ get_int returns default: 999")
    
    def test_get_bool_with_default(self):
        """Test get_bool with default value."""
        result = self.config.get_bool('NonexistentSection', 'key', True)
        self.assertEqual(result, True)
        print("✅ get_bool returns default: True")
    
    # ====================================================================
    # Configuration Key Tests
    # ====================================================================
    
    def test_has_option(self):
        """Test checking for configuration key existence."""
        self.assertTrue(
            self.config.has_option('Application', 'app_name'),
            "Key 'app_name' should exist in [Application]"
        )
        self.assertFalse(
            self.config.has_option('Application', 'nonexistent_key'),
            "Key 'nonexistent_key' should not exist"
        )
        print("✅ has_option works correctly")
    
    def test_list_sections(self):
        """Test retrieving list of configuration sections."""
        sections = self.config.list_sections()
        self.assertIsInstance(sections, list)
        self.assertGreater(len(sections), 0)
        self.assertIn('Application', sections)
        self.assertIn('Map', sections)
        print(f"✅ Found {len(sections)} configuration sections")
    
    def test_list_keys(self):
        """Test retrieving list of keys in a section."""
        keys = self.config.list_keys('Application')
        self.assertIsInstance(keys, list)
        self.assertGreater(len(keys), 0)
        self.assertIn('app_name', keys)
        print(f"✅ Found {len(keys)} keys in [Application] section")
    
    # ====================================================================
    # Critical Configuration Tests
    # ====================================================================
    
    def test_app_name_configured(self):
        """Test that app name is configured correctly."""
        app_name = self.config.get_str('Application', 'app_name')
        self.assertEqual(app_name, 'CourseStudio')
        print(f"✅ App name configured: {app_name}")
    
    def test_default_mbtiles_configured(self):
        """Test that default mbtiles is configured."""
        mbtiles = self.config.get_str('Map', 'default_mbtiles')
        self.assertIsNotNone(mbtiles)
        self.assertIn('.mbtiles', mbtiles)
        print(f"✅ Default mbtiles: {mbtiles}")
    
    def test_coordinate_format_configured(self):
        """Test that coordinate format is configured correctly."""
        coord_format = self.config.get_str('Coordinates', 'coordinate_format')
        self.assertIn(coord_format, ['dms', 'decimal'])
        print(f"✅ Coordinate format: {coord_format}")
    
    def test_map_defaults_reasonable(self):
        """Test that map configuration has reasonable defaults."""
        zoom = self.config.get_int('Map', 'initial_zoom_level')
        self.assertGreaterEqual(zoom, constants.MIN_ZOOM_LEVEL)
        self.assertLessEqual(zoom, constants.MAX_ZOOM_LEVEL)
        
        lat = self.config.get_float('Map', 'default_map_center_lat')
        self.assertGreaterEqual(lat, constants.LATITUDE_MIN)
        self.assertLessEqual(lat, constants.LATITUDE_MAX)
        
        lon = self.config.get_float('Map', 'default_map_center_lon')
        self.assertGreaterEqual(lon, constants.LONGITUDE_MIN)
        self.assertLessEqual(lon, constants.LONGITUDE_MAX)
        
        print(f"✅ Map defaults are reasonable (Z{zoom}, {lat}°, {lon}°)")
    
    # ====================================================================
    # Edge Case Tests
    # ====================================================================
    
    def test_empty_string_value(self):
        """Test handling of empty string values."""
        # This should not raise an exception
        result = self.config.get_str('Application', 'nonexistent', '')
        self.assertEqual(result, '')
        print("✅ Empty string default handled correctly")
    
    def test_zero_value(self):
        """Test handling of zero values."""
        result = self.config.get_int('SomeSection', 'SomeKey', 0)
        self.assertEqual(result, 0)
        print("✅ Zero default handled correctly")
    
    def test_negative_value(self):
        """Test handling of negative values."""
        result = self.config.get_int('SomeSection', 'SomeKey', -1)
        self.assertEqual(result, -1)
        print("✅ Negative default handled correctly")


class TestConfigurationIntegration(unittest.TestCase):
    """Integration tests for AppConfig with application startup."""
    
    def test_config_loads_before_pyqt(self):
        """Test that config loads before PyQt5 is needed."""
        try:
            config = AppConfig('config/settings.ini')
            self.assertIsNotNone(config)
            print("✅ Configuration loads independently of PyQt5")
        except Exception as e:
            self.fail(f"Configuration loading failed: {e}")
    
    def test_all_required_sections_present(self):
        """Test that all required configuration sections exist."""
        config = AppConfig('config/settings.ini')
        
        required_sections = [
            'Application',
            'Map',
            'Coordinates',
            'File',
            'UI',
            'Logging'
        ]
        
        for section in required_sections:
            self.assertTrue(
                config.has_section(section),
                f"Missing required section: [{section}]"
            )
        
        print(f"✅ All {len(required_sections)} required sections present")
    
    def test_all_critical_keys_present(self):
        """Test that all critical configuration keys exist."""
        config = AppConfig('config/settings.ini')
        
        critical_keys = {
            'Application': ['app_name', 'version'],
            'Map': ['default_mbtiles', 'initial_zoom_level'],
            'Coordinates': ['coordinate_format'],
            'File': ['create_backup'],
            'UI': ['window_width', 'window_height'],
            'Logging': ['log_level', 'log_file']
        }
        
        for section, keys in critical_keys.items():
            for key in keys:
                self.assertTrue(
                    config.has_option(section, key),
                    f"Missing critical key: [{section}] {key}"
                )
        
        print(f"✅ All critical configuration keys present")


def run_tests_with_timeout():
    """Run all tests with timeout protection."""
    import signal
    
    # Set 60-second timeout for all tests
    timeout_seconds = 60
    
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Tests exceeded {timeout_seconds} second timeout")
    
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    
    try:
        # Run tests
        suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        # Cancel timeout
        signal.alarm(0)
        
        return 0 if result.wasSuccessful() else 1
        
    except TimeoutError as e:
        print(f"❌ TIMEOUT: {e}")
        signal.alarm(0)
        return 1


if __name__ == "__main__":
    print("\n" + "="*70)
    print("Testing AppConfig - Configuration Management")
    print("="*70 + "\n")
    
    exit_code = run_tests_with_timeout()
    
    print("\n" + "="*70)
    if exit_code == 0:
        print("✅ All AppConfig tests PASSED")
    else:
        print("❌ Some AppConfig tests FAILED")
    print("="*70 + "\n")
    
    sys.exit(exit_code)
