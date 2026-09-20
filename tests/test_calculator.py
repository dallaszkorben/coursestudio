"""
Unit tests for calculator module (distance and coordinate calculations).

Tests Haversine formula, track distance calculation, and coordinate validation.

Author: Development Team
Date: 2026-09-20
"""

import unittest
import math
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.calculator import (
    haversine_distance,
    calculate_track_distance,
    calculate_bearing,
    validate_coordinate,
    EARTH_RADIUS_KM
)


class TestHaversineDistance(unittest.TestCase):
    """Test Haversine great-circle distance calculation."""
    
    def test_same_point(self):
        """Distance between same point should be 0."""
        dist = haversine_distance(57.5126, 12.2584, 57.5126, 12.2584)
        self.assertAlmostEqual(dist, 0.0, places=5)
        print("✅ Same point distance: 0 km")
    
    def test_known_distance(self):
        """Test with known distance (Stockholm to Gothenburg ~400 km)."""
        # Stockholm: 59.3293, 18.0686
        # Gothenburg: 57.7089, 11.9746
        dist = haversine_distance(59.3293, 18.0686, 57.7089, 11.9746)
        
        # Should be approximately 400 km
        self.assertGreater(dist, 390)
        self.assertLess(dist, 420)
        print(f"✅ Known distance test: {dist:.2f} km (expected ~400 km)")
    
    def test_short_distance(self):
        """Test very short distance (nearby points)."""
        # Two points ~0.1 km apart
        lat1, lon1 = 57.5126, 12.2584
        lat2, lon2 = 57.5135, 12.2595
        dist = haversine_distance(lat1, lon1, lat2, lon2)
        
        self.assertGreater(dist, 0)
        self.assertLess(dist, 0.2)
        print(f"✅ Short distance: {dist:.4f} km")
    
    def test_equator(self):
        """Test distance along equator."""
        # 1 degree of longitude at equator ≈ 111.32 km
        dist = haversine_distance(0.0, 0.0, 0.0, 1.0)
        self.assertGreater(dist, 110)
        self.assertLess(dist, 112)
        print(f"✅ Equator distance (1° longitude): {dist:.2f} km (expected ~111.32)")
    
    def test_pole(self):
        """Test distance along meridian."""
        # 1 degree of latitude ≈ 111.32 km
        dist = haversine_distance(0.0, 0.0, 1.0, 0.0)
        self.assertGreater(dist, 110)
        self.assertLess(dist, 112)
        print(f"✅ Meridian distance (1° latitude): {dist:.2f} km (expected ~111.32)")
    
    def test_invalid_latitude(self):
        """Invalid latitude should raise ValueError."""
        with self.assertRaises(ValueError):
            haversine_distance(91.0, 0.0, 0.0, 0.0)
        print("✅ Invalid latitude raises ValueError")
    
    def test_invalid_longitude(self):
        """Invalid longitude should raise ValueError."""
        with self.assertRaises(ValueError):
            haversine_distance(0.0, 181.0, 0.0, 0.0)
        print("✅ Invalid longitude raises ValueError")
    
    def test_antipodal_points(self):
        """Test distance between antipodal points (opposite sides of Earth)."""
        # North Pole to South Pole through equator
        dist = haversine_distance(90.0, 0.0, -90.0, 0.0)
        
        # Should be approximately half Earth's circumference
        expected = math.pi * EARTH_RADIUS_KM
        self.assertAlmostEqual(dist, expected, delta=0.1)
        print(f"✅ Antipodal points: {dist:.2f} km (expected {expected:.2f})")


class TestTrackDistance(unittest.TestCase):
    """Test track distance calculation."""
    
    def test_empty_track(self):
        """Empty track should have 0 distance."""
        dist = calculate_track_distance([])
        self.assertEqual(dist, 0.0)
        print("✅ Empty track: 0 km")
    
    def test_single_point(self):
        """Single point track should have 0 distance."""
        dist = calculate_track_distance([(57.5126, 12.2584)])
        self.assertEqual(dist, 0.0)
        print("✅ Single point: 0 km")
    
    def test_two_point_track(self):
        """Two point track should equal distance between points."""
        points = [(57.5126, 12.2584), (57.5135, 12.2595)]
        dist = calculate_track_distance(points)
        
        # Should be small but positive
        self.assertGreater(dist, 0)
        self.assertLess(dist, 0.2)
        print(f"✅ Two point track: {dist:.4f} km")
    
    def test_multi_point_track(self):
        """Multi-point track distance should be sum of segments."""
        # Three points forming a simple path
        points = [
            (57.5126, 12.2584),
            (57.5135, 12.2595),
            (57.5145, 12.2605)
        ]
        dist = calculate_track_distance(points)
        
        # Should be positive and reasonable
        self.assertGreater(dist, 0)
        self.assertLess(dist, 1.0)
        print(f"✅ Three point track: {dist:.4f} km")
    
    def test_large_track(self):
        """Test with larger distance."""
        # Stockholm to Gothenburg
        points = [
            (59.3293, 18.0686),
            (58.0, 15.0),
            (57.7089, 11.9746)
        ]
        dist = calculate_track_distance(points)
        
        # Should be roughly 450+ km
        self.assertGreater(dist, 400)
        print(f"✅ Large track: {dist:.2f} km")


class TestCoordinateValidation(unittest.TestCase):
    """Test coordinate validation."""
    
    def test_valid_coordinate(self):
        """Valid coordinates should pass."""
        valid, msg = validate_coordinate(57.5126, 12.2584)
        self.assertTrue(valid)
        self.assertEqual(msg, "")
        print("✅ Valid coordinate: accepted")
    
    def test_latitude_too_high(self):
        """Latitude > 90 should fail."""
        valid, msg = validate_coordinate(91.0, 12.2584)
        self.assertFalse(valid)
        self.assertIn("Latitude", msg)
        print(f"✅ Latitude > 90: rejected ({msg})")
    
    def test_latitude_too_low(self):
        """Latitude < -90 should fail."""
        valid, msg = validate_coordinate(-91.0, 12.2584)
        self.assertFalse(valid)
        self.assertIn("Latitude", msg)
        print(f"✅ Latitude < -90: rejected ({msg})")
    
    def test_longitude_too_high(self):
        """Longitude > 180 should fail."""
        valid, msg = validate_coordinate(57.5126, 181.0)
        self.assertFalse(valid)
        self.assertIn("Longitude", msg)
        print(f"✅ Longitude > 180: rejected ({msg})")
    
    def test_longitude_too_low(self):
        """Longitude < -180 should fail."""
        valid, msg = validate_coordinate(57.5126, -181.0)
        self.assertFalse(valid)
        self.assertIn("Longitude", msg)
        print(f"✅ Longitude < -180: rejected ({msg})")
    
    def test_nan_latitude(self):
        """NaN latitude should fail."""
        valid, msg = validate_coordinate(float('nan'), 12.2584)
        self.assertFalse(valid)
        self.assertIn("NaN", msg)
        print(f"✅ NaN latitude: rejected ({msg})")
    
    def test_inf_longitude(self):
        """Infinite longitude should fail."""
        valid, msg = validate_coordinate(57.5126, float('inf'))
        self.assertFalse(valid)
        self.assertIn("infinite", msg)
        print(f"✅ Inf longitude: rejected ({msg})")
    
    def test_non_numeric_latitude(self):
        """Non-numeric latitude should fail."""
        valid, msg = validate_coordinate("57.5", 12.2584)
        self.assertFalse(valid)
        self.assertIn("number", msg)
        print(f"✅ String latitude: rejected ({msg})")
    
    def test_boundary_latitude_north(self):
        """North pole coordinate should be valid."""
        valid, msg = validate_coordinate(90.0, 0.0)
        self.assertTrue(valid)
        print("✅ North pole (90°): accepted")
    
    def test_boundary_latitude_south(self):
        """South pole coordinate should be valid."""
        valid, msg = validate_coordinate(-90.0, 0.0)
        self.assertTrue(valid)
        print("✅ South pole (-90°): accepted")
    
    def test_boundary_longitude_east(self):
        """East dateline coordinate should be valid."""
        valid, msg = validate_coordinate(0.0, 180.0)
        self.assertTrue(valid)
        print("✅ East dateline (180°): accepted")
    
    def test_boundary_longitude_west(self):
        """West dateline coordinate should be valid."""
        valid, msg = validate_coordinate(0.0, -180.0)
        self.assertTrue(valid)
        print("✅ West dateline (-180°): accepted")


class TestBearing(unittest.TestCase):
    """Test bearing calculation."""
    
    def test_north_bearing(self):
        """Bearing north should be ~0°."""
        bearing = calculate_bearing(0.0, 0.0, 1.0, 0.0)
        self.assertLess(bearing, 45)  # Close to 0°
        print(f"✅ North bearing: {bearing:.2f}° (expected ~0°)")
    
    def test_east_bearing(self):
        """Bearing east should be ~90°."""
        bearing = calculate_bearing(0.0, 0.0, 0.0, 1.0)
        self.assertGreater(bearing, 45)
        self.assertLess(bearing, 135)
        print(f"✅ East bearing: {bearing:.2f}° (expected ~90°)")
    
    def test_bearing_range(self):
        """Bearing should always be 0-360."""
        bearing = calculate_bearing(57.5, 12.5, 58.5, 13.5)
        self.assertGreaterEqual(bearing, 0)
        self.assertLess(bearing, 360)
        print(f"✅ Bearing in valid range: {bearing:.2f}°")


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
    print("Testing Calculator Module")
    print("="*70 + "\n")
    
    exit_code = run_tests_with_timeout()
    
    print("\n" + "="*70)
    if exit_code == 0:
        print("✅ All Calculator tests PASSED")
    else:
        print("❌ Some Calculator tests FAILED")
    print("="*70 + "\n")
    
    sys.exit(exit_code)
