"""
Distance and coordinate calculations for CourseStudio.

Provides utility functions for:
- Haversine distance calculation (great-circle distance)
- Track distance summation
- Coordinate validation
- Geographic utilities

Author: Development Team
Date: 2026-09-20
"""

import math
from typing import Tuple, List


# Earth radius in kilometers (used for Haversine formula)
EARTH_RADIUS_KM = 6371.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two points using Haversine formula.
    
    The Haversine formula calculates the shortest distance between two points
    on a sphere given their longitudes and latitudes in decimal degrees.
    
    Args:
        lat1 (float): Latitude of first point in decimal degrees (-90 to 90)
        lon1 (float): Longitude of first point in decimal degrees (-180 to 180)
        lat2 (float): Latitude of second point in decimal degrees (-90 to 90)
        lon2 (float): Longitude of second point in decimal degrees (-180 to 180)
    
    Returns:
        float: Distance in kilometers
    
    Raises:
        ValueError: If coordinates are outside valid ranges
    
    Example:
        distance = haversine_distance(57.5126, 12.2584, 57.5130, 12.2590)
        # distance ≈ 0.066 km
    
    References:
        - https://en.wikipedia.org/wiki/Haversine_formula
        - https://www.movable-type.co.uk/scripts/latlong.html
    """
    
    # Validate coordinate ranges
    if not (-90 <= lat1 <= 90 and -90 <= lat2 <= 90):
        raise ValueError(f"Latitude must be between -90 and 90, got: lat1={lat1}, lat2={lat2}")
    
    if not (-180 <= lon1 <= 180 and -180 <= lon2 <= 180):
        raise ValueError(f"Longitude must be between -180 and 180, got: lon1={lon1}, lon2={lon2}")
    
    # ===== HAVERSINE FORMULA ALGORITHM =====
    # Purpose: Calculate shortest distance on Earth between two points (great-circle distance)
    # Why: More accurate than simple Euclidean math, accounts for Earth's spherical shape
    # Accuracy: ±0.5% error typical, less accurate at poles, very accurate for normal distances
    # Reference: https://en.wikipedia.org/wiki/Haversine_formula
    #
    # Formula structure:
    #   a = sin²(Δlat/2) + cos(lat1) × cos(lat2) × sin²(Δlon/2)
    #   c = 2 × atan2(√a, √(1-a))
    #   d = R × c
    # Where:
    #   d = distance
    #   R = Earth's mean radius (6371 km for WGS84)
    #   Δlat = latitude difference
    #   Δlon = longitude difference
    
    # Step 1: Convert degrees to radians (trigonometric functions require radians)
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)  # Latitude difference
    delta_lon = math.radians(lon2 - lon1)  # Longitude difference
    
    # Step 2: Calculate intermediate value 'a'
    # This represents the square of half the chord length between points
    # Breaking it down:
    #   - sin²(Δlat/2): latitude component of chord
    #   - cos(lat1) × cos(lat2) × sin²(Δlon/2): longitude component, adjusted for latitude
    #     (cos(lat) adjustment: longitude lines converge at poles)
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    
    # Step 3: Calculate central angle 'c' in radians
    # atan2(√a, √(1-a)) is more numerically stable than asin(√a)
    # Central angle is the angle at Earth's center between the two points
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    # Step 4: Multiply by Earth radius to get distance
    # Arc length = radius × angle (in radians)
    distance = EARTH_RADIUS_KM * c
    
    return distance


def calculate_track_distance(trackpoints: List[Tuple[float, float]]) -> float:
    """
    Calculate total distance of a track by summing distances between consecutive points.
    
    Sums the great-circle distances between each pair of consecutive trackpoints.
    
    Args:
        trackpoints (List[Tuple[float, float]]): List of (latitude, longitude) tuples
                                                 Each coordinate in decimal degrees
    
    Returns:
        float: Total track distance in kilometers
    
    Example:
        points = [(57.5126, 12.2584), (57.5130, 12.2590), (57.5135, 12.2595)]
        distance = calculate_track_distance(points)
        # distance ≈ 0.13 km
    
    Notes:
        - Returns 0.0 for tracks with 0 or 1 points
        - Each point should be (latitude, longitude) tuple
        - Coordinates must be in decimal degrees
    """
    
    # Empty or single point tracks have no distance
    if len(trackpoints) < 2:
        return 0.0
    
    total_distance = 0.0
    
    # Sum distances between consecutive points
    for i in range(len(trackpoints) - 1):
        lat1, lon1 = trackpoints[i]
        lat2, lon2 = trackpoints[i + 1]
        
        try:
            distance = haversine_distance(lat1, lon1, lat2, lon2)
            total_distance += distance
        except ValueError as e:
            # Log error but continue with calculation
            print(f"⚠️  Warning: Invalid coordinate at index {i}: {e}")
            continue
    
    return total_distance


def point_to_line_distance(point_lat: float, point_lon: float, 
                          line_start_lat: float, line_start_lon: float,
                          line_end_lat: float, line_end_lon: float) -> float:
    """
    Calculate perpendicular distance from a point to a line segment.
    
    Useful for determining how close a point is to a track path.
    Uses the cross-track distance formula for great-circle calculations.
    
    Args:
        point_lat (float): Latitude of point in decimal degrees
        point_lon (float): Longitude of point in decimal degrees
        line_start_lat (float): Latitude of line start in decimal degrees
        line_start_lon (float): Longitude of line start in decimal degrees
        line_end_lat (float): Latitude of line end in decimal degrees
        line_end_lon (float): Longitude of line end in decimal degrees
    
    Returns:
        float: Perpendicular distance from point to line in kilometers (absolute value)
    
    Example:
        distance = point_to_line_distance(
                57.515, 12.260,  # point
                57.5126, 12.2584,  # line start
                57.5130, 12.2590   # line end
            )
        print(f"{distance:.4f} km")
    
    Notes:
        - Returns absolute value (always positive)
        - Line is treated as infinite (not limited to segment endpoints)
        - Useful for click-hit detection on track paths
    
    References:
        - https://en.wikipedia.org/wiki/Cross_track_distance
        - https://www.movable-type.co.uk/scripts/latlong.html
    """
    
    # ===== CROSS-TRACK DISTANCE ALGORITHM =====
    # Purpose: Find perpendicular distance from point to great-circle path
    # Use case: Hit detection when user clicks near track on map
    # Formula: dxt = asin(sin(d13/R) × sin(bearing_13 - bearing_12)) × R
    # Where:
    #   d13 = distance from line_start to point
    #   R = Earth radius
    #   bearing_12 = direction from line_start to line_end
    #   bearing_13 = direction from line_start to point
    
    # Step 1: Calculate distance from line start to the point
    # This is one side of the triangle formed by (line_start, line_end, point)
    d13 = haversine_distance(line_start_lat, line_start_lon, point_lat, point_lon)
    
    # Step 2: Calculate bearing (direction) from line start to line end
    # This is the bearing along which we measure perpendicular distance
    bearing_12 = calculate_bearing(line_start_lat, line_start_lon, line_end_lat, line_end_lon)
    
    # Step 3: Calculate bearing from line start to the point
    # Difference between this and bearing_12 tells us which side of line the point is on
    bearing_13 = calculate_bearing(line_start_lat, line_start_lon, point_lat, point_lon)
    
    # Step 4: Calculate cross-track distance using sine of angle between bearings
    # The angle (bearing_13 - bearing_12) tells us how far from the line
    # sin(angle) × distance = perpendicular distance
    # Divide d13 by Earth radius to convert to radians (for trigonometry)
    # Multiply result by Earth radius to convert back to km
    dxt = math.asin(math.sin(d13 / EARTH_RADIUS_KM) * math.sin(math.radians(bearing_13 - bearing_12))) * EARTH_RADIUS_KM
    
    # Return absolute value (distance is always positive)
    return abs(dxt)


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate initial bearing from point 1 to point 2.
    
    Bearing is the compass direction (0°=North, 90°=East, 180°=South, 270°=West)
    from point 1 toward point 2 at the start of travel.
    
    Args:
        lat1 (float): Latitude of first point in decimal degrees
        lon1 (float): Longitude of first point in decimal degrees
        lat2 (float): Latitude of second point in decimal degrees
        lon2 (float): Longitude of second point in decimal degrees
    
    Returns:
        float: Initial bearing in degrees (0-360)
    
    Example:
        bearing = calculate_bearing(57.5126, 12.2584, 57.5130, 12.2590)
        print(f"{bearing:.1f}°")  # Should be roughly East/Northeast
    
    References:
        - https://www.movable-type.co.uk/scripts/latlong.html
    """
    
    # ===== BEARING CALCULATION (Forward Azimuth) =====
    # Purpose: Find compass direction from point 1 to point 2
    # Uses: atan2 to determine angle between two vectors
    # Reference: Based on great-circle navigation formulas
    #
    # Formula:
    #   x = sin(Δlon) × cos(lat2)
    #   y = cos(lat1) × sin(lat2) - sin(lat1) × cos(lat2) × cos(Δlon)
    #   bearing = atan2(x, y)
    # Then normalize to 0-360° range
    
    # Convert to radians for trigonometric functions
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)
    
    # Calculate Cartesian components
    # x: East-West component (positive = East)
    # y: North-South component (positive = North)
    # These components represent direction vector from point 1 to point 2
    x = math.sin(delta_lon) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon)
    
    # Use atan2 to get angle from East (0°) and North (+Y axis)
    # atan2(y, x) gives angle in range [-180°, +180°]
    bearing = math.degrees(math.atan2(x, y))
    
    # Normalize to compass bearing [0°, 360°)
    # atan2 result: -180° to +180° (where 0° = North, 90° = East, -90° = West)
    # Compass bearing: 0° to 360° (where 0° = North, 90° = East, 180° = South, 270° = West)
    bearing = (bearing + 360) % 360  # This adds 360 if negative, then mod 360 ensures 0-359 range
    
    return bearing


def validate_coordinate(latitude: float, longitude: float) -> Tuple[bool, str]:
    """
    Validate that a coordinate pair is within valid ranges.
    
    Args:
        latitude (float): Latitude value in decimal degrees
        longitude (float): Longitude value in decimal degrees
    
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
                         is_valid: True if valid, False otherwise
                         error_message: Empty string if valid, error description if invalid
    
    Example:
        valid, msg = validate_coordinate(57.5126, 12.2584)
        print(valid, msg)
        True 
        valid, msg = validate_coordinate(91.0, 12.2584)
        print(valid, msg)
        False Latitude must be between -90 and 90
    """
    
    if not isinstance(latitude, (int, float)):
        return False, f"Latitude must be a number, got {type(latitude).__name__}"
    
    if not isinstance(longitude, (int, float)):
        return False, f"Longitude must be a number, got {type(longitude).__name__}"
    
    if math.isnan(latitude) or math.isnan(longitude):
        return False, "Coordinate values cannot be NaN"
    
    if math.isinf(latitude) or math.isinf(longitude):
        return False, "Coordinate values cannot be infinite"
    
    if not (-90 <= latitude <= 90):
        return False, f"Latitude must be between -90 and 90, got {latitude}"
    
    if not (-180 <= longitude <= 180):
        return False, f"Longitude must be between -180 and 180, got {longitude}"
    
    return True, ""


if __name__ == "__main__":
    # Simple test
    print("\n" + "="*70)
    print("Testing Calculator Module")
    print("="*70 + "\n")
    
    # Test Haversine distance
    dist = haversine_distance(57.5126, 12.2584, 57.5130, 12.2590)
    print(f"✅ Haversine distance: {dist:.4f} km")
    
    # Test track distance
    points = [(57.5126, 12.2584), (57.5130, 12.2590), (57.5135, 12.2595)]
    total = calculate_track_distance(points)
    print(f"✅ Track distance (3 points): {total:.4f} km")
    
    # Test coordinate validation
    valid, msg = validate_coordinate(57.5126, 12.2584)
    print(f"✅ Valid coordinate: {valid} ({msg if msg else 'OK'})")
    
    valid, msg = validate_coordinate(91.0, 12.2584)
    print(f"✅ Invalid coordinate: {not valid} ({msg})")
    
    print("\n" + "="*70 + "\n")
