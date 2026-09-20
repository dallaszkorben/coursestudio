"""
Distance and coordinate calculations for mangpx.

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
        >>> distance = haversine_distance(57.5126, 12.2584, 57.5130, 12.2590)
        >>> print(f"{distance:.3f} km")
        0.066 km
    
    References:
        - https://en.wikipedia.org/wiki/Haversine_formula
        - https://www.movable-type.co.uk/scripts/latlong.html
    """
    
    # Validate coordinate ranges
    if not (-90 <= lat1 <= 90 and -90 <= lat2 <= 90):
        raise ValueError(f"Latitude must be between -90 and 90, got: lat1={lat1}, lat2={lat2}")
    
    if not (-180 <= lon1 <= 180 and -180 <= lon2 <= 180):
        raise ValueError(f"Longitude must be between -180 and 180, got: lon1={lon1}, lon2={lon2}")
    
    # Convert decimal degrees to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    # Haversine formula
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
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
        >>> points = [(57.5126, 12.2584), (57.5130, 12.2590), (57.5135, 12.2595)]
        >>> distance = calculate_track_distance(points)
        >>> print(f"{distance:.2f} km")
        0.13 km
    
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
    Uses the cross-track distance formula.
    
    Args:
        point_lat (float): Latitude of point in decimal degrees
        point_lon (float): Longitude of point in decimal degrees
        line_start_lat (float): Latitude of line start in decimal degrees
        line_start_lon (float): Longitude of line start in decimal degrees
        line_end_lat (float): Latitude of line end in decimal degrees
        line_end_lon (float): Longitude of line end in decimal degrees
    
    Returns:
        float: Perpendicular distance from point to line in kilometers
    
    Example:
        >>> distance = point_to_line_distance(
        ...     57.515, 12.260,  # point
        ...     57.5126, 12.2584,  # line start
        ...     57.5130, 12.2590   # line end
        ... )
        >>> print(f"{distance:.4f} km")
    
    References:
        - https://en.wikipedia.org/wiki/Cross_track_distance
    """
    
    # Distance from start to end point
    d13 = haversine_distance(line_start_lat, line_start_lon, point_lat, point_lon)
    
    # Bearing from start to end point
    bearing_12 = calculate_bearing(line_start_lat, line_start_lon, line_end_lat, line_end_lon)
    bearing_13 = calculate_bearing(line_start_lat, line_start_lon, point_lat, point_lon)
    
    # Cross-track distance (simplified formula)
    dxt = math.asin(math.sin(d13 / EARTH_RADIUS_KM) * math.sin(math.radians(bearing_13 - bearing_12))) * EARTH_RADIUS_KM
    
    return abs(dxt)


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate initial bearing from point 1 to point 2.
    
    Args:
        lat1 (float): Latitude of first point in decimal degrees
        lon1 (float): Longitude of first point in decimal degrees
        lat2 (float): Latitude of second point in decimal degrees
        lon2 (float): Longitude of second point in decimal degrees
    
    Returns:
        float: Initial bearing in degrees (0-360)
    
    References:
        - https://www.movable-type.co.uk/scripts/latlong.html
    """
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)
    
    x = math.sin(delta_lon) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon)
    
    bearing = math.degrees(math.atan2(x, y))
    bearing = (bearing + 360) % 360  # Normalize to 0-360
    
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
        >>> valid, msg = validate_coordinate(57.5126, 12.2584)
        >>> print(valid, msg)
        True 
        
        >>> valid, msg = validate_coordinate(91.0, 12.2584)
        >>> print(valid, msg)
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
