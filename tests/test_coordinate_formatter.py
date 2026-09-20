"""
Unit tests for coordinate formatter module (DMS ↔ Decimal conversion).

Tests coordinate format conversion, parsing, and validation.

Author: Development Team
Date: 2026-09-20
"""

import unittest
import sys
from pathlib import Path
import math

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.coordinate_formatter import (
    decimal_to_dms,
    dms_to_decimal,
    format_dms,
    format_decimal,
    format_coordinate,
    parse_coordinate,
    DMS_DEGREE_SYMBOL,
    DMS_MINUTE_SYMBOL,
    DMS_SECOND_SYMBOL
)


class TestDecimalToDMS(unittest.TestCase):
    """Test decimal to DMS conversion."""
    
    def test_positive_latitude(self):
        """Convert positive latitude to DMS."""
        deg, min, sec, dir = decimal_to_dms(57.5126, is_longitude=False)
        self.assertEqual(deg, 57)
        self.assertEqual(min, 30)
        self.assertAlmostEqual(sec, 45.36, places=1)
        self.assertEqual(dir, 'N')
        print(f"✅ Positive latitude: 57.5126° → {deg}°{min}'{sec:.1f}\"{dir}")
    
    def test_negative_latitude(self):
        """Convert negative latitude to DMS."""
        deg, min, sec, dir = decimal_to_dms(-57.5126, is_longitude=False)
        self.assertEqual(deg, 57)
        self.assertEqual(min, 30)
        self.assertAlmostEqual(sec, 45.36, places=1)
        self.assertEqual(dir, 'S')
        print(f"✅ Negative latitude: -57.5126° → {deg}°{min}'{sec:.1f}\"{dir}")
    
    def test_positive_longitude(self):
        """Convert positive longitude to DMS."""
        deg, min, sec, dir = decimal_to_dms(12.2584, is_longitude=True)
        self.assertEqual(deg, 12)
        self.assertEqual(min, 15)
        self.assertAlmostEqual(sec, 30.24, places=1)
        self.assertEqual(dir, 'E')
        print(f"✅ Positive longitude: 12.2584° → {deg}°{min}'{sec:.1f}\"{dir}")
    
    def test_negative_longitude(self):
        """Convert negative longitude to DMS."""
        deg, min, sec, dir = decimal_to_dms(-12.2584, is_longitude=True)
        self.assertEqual(deg, 12)
        self.assertEqual(min, 15)
        self.assertAlmostEqual(sec, 30.24, places=1)
        self.assertEqual(dir, 'W')
        print(f"✅ Negative longitude: -12.2584° → {deg}°{min}'{sec:.1f}\"{dir}")
    
    def test_zero(self):
        """Convert zero to DMS."""
        deg, min, sec, dir = decimal_to_dms(0.0, is_longitude=False)
        self.assertEqual(deg, 0)
        self.assertEqual(min, 0)
        self.assertAlmostEqual(sec, 0.0, places=1)
        self.assertEqual(dir, 'N')
        print(f"✅ Zero: 0° → {deg}°{min}'{sec:.1f}\"{dir}")
    
    def test_north_pole(self):
        """Convert north pole to DMS."""
        deg, min, sec, dir = decimal_to_dms(90.0, is_longitude=False)
        self.assertEqual(deg, 90)
        self.assertEqual(min, 0)
        self.assertAlmostEqual(sec, 0.0, places=1)
        self.assertEqual(dir, 'N')
        print(f"✅ North pole: 90° → {deg}°{min}'{sec:.1f}\"{dir}")
    
    def test_south_pole(self):
        """Convert south pole to DMS."""
        deg, min, sec, dir = decimal_to_dms(-90.0, is_longitude=False)
        self.assertEqual(deg, 90)
        self.assertEqual(min, 0)
        self.assertAlmostEqual(sec, 0.0, places=1)
        self.assertEqual(dir, 'S')
        print(f"✅ South pole: -90° → {deg}°{min}'{sec:.1f}\"{dir}")
    
    def test_invalid_latitude_high(self):
        """Invalid latitude > 90 should raise error."""
        with self.assertRaises(ValueError):
            decimal_to_dms(91.0, is_longitude=False)
        print("✅ Invalid latitude (91°) raises ValueError")
    
    def test_invalid_longitude_high(self):
        """Invalid longitude > 180 should raise error."""
        with self.assertRaises(ValueError):
            decimal_to_dms(181.0, is_longitude=True)
        print("✅ Invalid longitude (181°) raises ValueError")


class TestDMSToDecimal(unittest.TestCase):
    """Test DMS to decimal conversion."""
    
    def test_north_latitude(self):
        """Convert DMS north latitude to decimal."""
        decimal = dms_to_decimal(57, 30, 45.36, 'N')
        self.assertAlmostEqual(decimal, 57.5126, places=4)
        print(f"✅ North latitude: 57°30'45.36\"N → {decimal:.4f}°")
    
    def test_south_latitude(self):
        """Convert DMS south latitude to decimal."""
        decimal = dms_to_decimal(57, 30, 45.36, 'S')
        self.assertAlmostEqual(decimal, -57.5126, places=4)
        print(f"✅ South latitude: 57°30'45.36\"S → {decimal:.4f}°")
    
    def test_east_longitude(self):
        """Convert DMS east longitude to decimal."""
        decimal = dms_to_decimal(12, 15, 30.24, 'E')
        self.assertAlmostEqual(decimal, 12.2584, places=4)
        print(f"✅ East longitude: 12°15'30.24\"E → {decimal:.4f}°")
    
    def test_west_longitude(self):
        """Convert DMS west longitude to decimal."""
        decimal = dms_to_decimal(12, 15, 30.24, 'W')
        self.assertAlmostEqual(decimal, -12.2584, places=4)
        print(f"✅ West longitude: 12°15'30.24\"W → {decimal:.4f}°")
    
    def test_zero_dms(self):
        """Convert zero DMS to decimal."""
        decimal = dms_to_decimal(0, 0, 0.0, 'N')
        self.assertAlmostEqual(decimal, 0.0, places=4)
        print(f"✅ Zero DMS: 0°0'0\"N → {decimal:.4f}°")
    
    def test_invalid_direction(self):
        """Invalid direction should raise error."""
        with self.assertRaises(ValueError):
            dms_to_decimal(57, 30, 45.36, 'X')
        print("✅ Invalid direction 'X' raises ValueError")
    
    def test_invalid_minutes(self):
        """Invalid minutes > 59 should raise error."""
        with self.assertRaises(ValueError):
            dms_to_decimal(57, 60, 45.36, 'N')
        print("✅ Invalid minutes (60) raises ValueError")
    
    def test_invalid_seconds(self):
        """Invalid seconds >= 60 should raise error."""
        with self.assertRaises(ValueError):
            dms_to_decimal(57, 30, 60.0, 'N')
        print("✅ Invalid seconds (60) raises ValueError")


class TestRoundTrip(unittest.TestCase):
    """Test round-trip conversions (decimal → DMS → decimal)."""
    
    def test_round_trip_latitude(self):
        """Round-trip conversion for latitude."""
        original = 57.5126
        deg, min, sec, dir = decimal_to_dms(original, is_longitude=False)
        result = dms_to_decimal(deg, min, sec, dir)
        self.assertAlmostEqual(result, original, places=4)
        print(f"✅ Round-trip latitude: {original}° → {deg}°{min}'{sec:.1f}\"{dir} → {result:.4f}°")
    
    def test_round_trip_longitude(self):
        """Round-trip conversion for longitude."""
        original = -12.2584
        deg, min, sec, dir = decimal_to_dms(original, is_longitude=True)
        result = dms_to_decimal(deg, min, sec, dir)
        self.assertAlmostEqual(result, original, places=4)
        print(f"✅ Round-trip longitude: {original}° → {deg}°{min}'{sec:.1f}\"{dir} → {result:.4f}°")
    
    def test_round_trip_negative_latitude(self):
        """Round-trip conversion for negative latitude."""
        original = -33.8688
        deg, min, sec, dir = decimal_to_dms(original, is_longitude=False)
        result = dms_to_decimal(deg, min, sec, dir)
        self.assertAlmostEqual(result, original, places=4)
        print(f"✅ Round-trip negative latitude: {original}° → {result:.4f}°")


class TestFormatting(unittest.TestCase):
    """Test coordinate formatting."""
    
    def test_format_dms(self):
        """Format DMS as string."""
        dms_str = format_dms(57, 30, 45.36, 'N', seconds_decimals=1)
        self.assertIn('57', dms_str)
        self.assertIn('30', dms_str)
        self.assertIn('45.4', dms_str)
        self.assertIn('N', dms_str)
        self.assertIn(DMS_DEGREE_SYMBOL, dms_str)
        print(f"✅ Format DMS: {dms_str}")
    
    def test_format_decimal_with_direction(self):
        """Format decimal with direction."""
        dec_str = format_decimal(57.5126, include_direction=True, 
                               is_longitude=False, decimals=4)
        self.assertIn('57.5126', dec_str)
        self.assertIn('N', dec_str)
        self.assertIn(DMS_DEGREE_SYMBOL, dec_str)
        print(f"✅ Format decimal with direction: {dec_str}")
    
    def test_format_decimal_without_direction(self):
        """Format decimal without direction."""
        dec_str = format_decimal(57.5126, include_direction=False, decimals=4)
        self.assertIn('57.5126', dec_str)
        self.assertNotIn('N', dec_str)
        self.assertNotIn('S', dec_str)
        print(f"✅ Format decimal without direction: {dec_str}")
    
    def test_format_negative_decimal(self):
        """Format negative decimal."""
        dec_str = format_decimal(-57.5126, include_direction=True, 
                               is_longitude=False, decimals=4)
        self.assertIn('57.5126', dec_str)  # Absolute value
        self.assertIn('S', dec_str)  # South direction
        print(f"✅ Format negative decimal: {dec_str}")


class TestParseCoordinate(unittest.TestCase):
    """Test coordinate parsing."""
    
    def test_parse_dms_unicode(self):
        """Parse DMS with Unicode symbols."""
        parsed = parse_coordinate(f"57{DMS_DEGREE_SYMBOL}30{DMS_MINUTE_SYMBOL}45.5{DMS_SECOND_SYMBOL}N", 
                                is_longitude=False)
        self.assertAlmostEqual(parsed, 57.5126, places=3)
        print(f"✅ Parse DMS (Unicode): 57°30'45.5\"N → {parsed:.4f}°")
    
    def test_parse_dms_letters(self):
        """Parse DMS with letter delimiters."""
        parsed = parse_coordinate("57d30m45.5sN", is_longitude=False)
        self.assertAlmostEqual(parsed, 57.5126, places=3)
        print(f"✅ Parse DMS (letters): 57d30m45.5sN → {parsed:.4f}°")
    
    def test_parse_dms_dashes(self):
        """Parse DMS with dashes."""
        parsed = parse_coordinate("57-30-45.5N", is_longitude=False)
        self.assertAlmostEqual(parsed, 57.5126, places=3)
        print(f"✅ Parse DMS (dashes): 57-30-45.5N → {parsed:.4f}°")
    
    def test_parse_dms_spaces(self):
        """Parse DMS with spaces."""
        parsed = parse_coordinate("57 30 45.5 N", is_longitude=False)
        self.assertAlmostEqual(parsed, 57.5126, places=3)
        print(f"✅ Parse DMS (spaces): 57 30 45.5 N → {parsed:.4f}°")
    
    def test_parse_decimal_with_direction(self):
        """Parse decimal with direction."""
        parsed = parse_coordinate("57.5126N", is_longitude=False)
        self.assertAlmostEqual(parsed, 57.5126, places=4)
        print(f"✅ Parse decimal with direction: 57.5126N → {parsed:.4f}°")
    
    def test_parse_decimal_with_symbol_and_direction(self):
        """Parse decimal with symbol and direction."""
        parsed = parse_coordinate(f"57.5126{DMS_DEGREE_SYMBOL}N", is_longitude=False)
        self.assertAlmostEqual(parsed, 57.5126, places=4)
        print(f"✅ Parse decimal with symbol: 57.5126°N → {parsed:.4f}°")
    
    def test_parse_decimal_negative(self):
        """Parse negative decimal."""
        parsed = parse_coordinate("-57.5126", is_longitude=False)
        self.assertAlmostEqual(parsed, -57.5126, places=4)
        print(f"✅ Parse negative decimal: -57.5126 → {parsed:.4f}°")
    
    def test_parse_decimal_south(self):
        """Parse decimal with south direction."""
        parsed = parse_coordinate("57.5126S", is_longitude=False)
        self.assertAlmostEqual(parsed, -57.5126, places=4)
        print(f"✅ Parse decimal south: 57.5126S → {parsed:.4f}°")
    
    def test_parse_invalid(self):
        """Parse invalid string should raise error."""
        with self.assertRaises(ValueError):
            parse_coordinate("invalid", is_longitude=False)
        print("✅ Parse invalid string raises ValueError")


class TestFormatCoordinate(unittest.TestCase):
    """Test main format_coordinate function."""
    
    def test_format_as_dms(self):
        """Format as DMS."""
        result = format_coordinate(57.5126, is_longitude=False, format_type='dms')
        self.assertIn(DMS_DEGREE_SYMBOL, result)
        self.assertIn('N', result)
        print(f"✅ Format as DMS: {result}")
    
    def test_format_as_decimal(self):
        """Format as decimal."""
        result = format_coordinate(57.5126, is_longitude=False, format_type='decimal')
        self.assertIn('57.5126', result)
        self.assertIn('N', result)
        print(f"✅ Format as decimal: {result}")
    
    def test_format_invalid_type(self):
        """Invalid format_type should raise error."""
        with self.assertRaises(ValueError):
            format_coordinate(57.5126, format_type='invalid')
        print("✅ Invalid format_type raises ValueError")


def run_tests_with_timeout():
    """Run all tests with timeout protection."""
    import signal
    
    timeout_seconds = 60
    
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Tests exceeded {timeout_seconds} second timeout")
    
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    
    try:
        suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        signal.alarm(0)
        return 0 if result.wasSuccessful() else 1
    
    except TimeoutError as e:
        print(f"❌ TIMEOUT: {e}")
        signal.alarm(0)
        return 1


if __name__ == "__main__":
    print("\n" + "="*70)
    print("Testing Coordinate Formatter Module")
    print("="*70 + "\n")
    
    exit_code = run_tests_with_timeout()
    
    print("\n" + "="*70)
    if exit_code == 0:
        print("✅ All Coordinate Formatter tests PASSED")
    else:
        print("❌ Some Coordinate Formatter tests FAILED")
    print("="*70 + "\n")
    
    sys.exit(exit_code)
