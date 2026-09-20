"""
Coordinate format conversion utilities for mangpx.

Converts between DMS (Degrees-Minutes-Seconds) and Decimal Degrees formats.
Supports parsing, validation, and formatting of geographic coordinates.

Supported Formats:
- DMS: 57°30'45.5"N (with Unicode symbols or ASCII delimiters)
- Decimal: 57.5126°N or 57.5126

Author: Development Team
Date: 2026-09-20
"""

import re
import math
from typing import Tuple, Optional


# Unicode symbols for coordinate formatting
DMS_DEGREE_SYMBOL = "°"
DMS_MINUTE_SYMBOL = "'"
DMS_SECOND_SYMBOL = '"'

# Cardinal directions
CARDINAL_NORTH = "N"
CARDINAL_SOUTH = "S"
CARDINAL_EAST = "E"
CARDINAL_WEST = "W"

# Valid cardinal directions
VALID_LAT_DIRECTIONS = {CARDINAL_NORTH, CARDINAL_SOUTH}
VALID_LON_DIRECTIONS = {CARDINAL_EAST, CARDINAL_WEST}


def decimal_to_dms(decimal: float, is_longitude: bool = False) -> Tuple[int, int, float, str]:
    """
    Convert decimal degrees to DMS components.
    
    Converts a decimal degree value to Degrees, Minutes, Seconds components
    and determines the cardinal direction (N/S for latitude, E/W for longitude).
    
    Args:
        decimal (float): Decimal degree value
        is_longitude (bool): Whether this is longitude (determines direction)
                            False = latitude (N/S), True = longitude (E/W)
    
    Returns:
        Tuple[int, int, float, str]: (degrees, minutes, seconds, direction)
            - degrees (int): Degree component (0-360)
            - minutes (int): Minute component (0-59)
            - seconds (float): Second component (0-59.999)
            - direction (str): Cardinal direction ('N', 'S', 'E', 'W')
    
    Raises:
        ValueError: If decimal value is outside valid range
    
    Example:
        >>> dms = decimal_to_dms(57.5126, is_longitude=False)
        >>> print(dms)
        (57, 30, 45.36, 'N')
        
        >>> dms = decimal_to_dms(-12.2584, is_longitude=True)
        >>> print(dms)
        (12, 15, 30.24, 'W')
    """
    
    # Validate range
    if is_longitude:
        if not (-180 <= decimal <= 180):
            raise ValueError(f"Longitude must be between -180 and 180, got {decimal}")
        direction = CARDINAL_EAST if decimal >= 0 else CARDINAL_WEST
    else:
        if not (-90 <= decimal <= 90):
            raise ValueError(f"Latitude must be between -90 and 90, got {decimal}")
        direction = CARDINAL_NORTH if decimal >= 0 else CARDINAL_SOUTH
    
    # Work with absolute value
    abs_decimal = abs(decimal)
    
    # Extract degrees
    degrees = int(abs_decimal)
    
    # Extract minutes
    minutes_decimal = (abs_decimal - degrees) * 60
    minutes = int(minutes_decimal)
    
    # Extract seconds
    seconds = (minutes_decimal - minutes) * 60
    
    return degrees, minutes, seconds, direction


def dms_to_decimal(degrees: int, minutes: int, seconds: float, direction: str) -> float:
    """
    Convert DMS components to decimal degrees.
    
    Converts Degrees, Minutes, Seconds components with a cardinal direction
    to a single decimal degree value.
    
    Args:
        degrees (int): Degree component (0-360)
        minutes (int): Minute component (0-59)
        seconds (float): Second component (0-59.999)
        direction (str): Cardinal direction ('N', 'S', 'E', 'W')
    
    Returns:
        float: Decimal degree value (-180 to 180 for longitude, -90 to 90 for latitude)
    
    Raises:
        ValueError: If components are outside valid ranges or direction is invalid
    
    Example:
        >>> decimal = dms_to_decimal(57, 30, 45.36, 'N')
        >>> print(f"{decimal:.4f}")
        57.5126
        
        >>> decimal = dms_to_decimal(12, 15, 30.24, 'W')
        >>> print(f"{decimal:.4f}")
        -12.2584
    """
    
    # Validate components
    if not (0 <= degrees <= 360):
        raise ValueError(f"Degrees must be 0-360, got {degrees}")
    
    if not (0 <= minutes <= 59):
        raise ValueError(f"Minutes must be 0-59, got {minutes}")
    
    if not (0 <= seconds < 60):
        raise ValueError(f"Seconds must be 0-59.999, got {seconds}")
    
    # Validate direction
    if direction not in (VALID_LAT_DIRECTIONS | VALID_LON_DIRECTIONS):
        raise ValueError(f"Invalid direction: {direction}. Must be N, S, E, or W")
    
    # Calculate decimal
    decimal = degrees + minutes / 60 + seconds / 3600
    
    # Apply direction (negative for S/W)
    if direction in (CARDINAL_SOUTH, CARDINAL_WEST):
        decimal = -decimal
    
    return decimal


def format_dms(degrees: int, minutes: int, seconds: float, direction: str,
               seconds_decimals: int = 1) -> str:
    """
    Format DMS components as a readable string.
    
    Creates a human-readable DMS string with Unicode symbols or ASCII delimiters.
    
    Args:
        degrees (int): Degree component
        minutes (int): Minute component
        seconds (float): Second component
        direction (str): Cardinal direction
        seconds_decimals (int): Number of decimal places for seconds (default: 1)
    
    Returns:
        str: Formatted DMS string (e.g., "57°30'45.5"N")
    
    Example:
        >>> dms_str = format_dms(57, 30, 45.36, 'N', seconds_decimals=1)
        >>> print(dms_str)
        57°30'45.4"N
    """
    
    # Format with specified decimal places for seconds
    seconds_str = f"{seconds:.{seconds_decimals}f}"
    
    return f"{degrees}{DMS_DEGREE_SYMBOL}{minutes}{DMS_MINUTE_SYMBOL}{seconds_str}{DMS_SECOND_SYMBOL}{direction}"


def format_decimal(decimal: float, include_direction: bool = True,
                  is_longitude: bool = False, decimals: int = 4) -> str:
    """
    Format decimal degrees as a readable string.
    
    Creates a human-readable decimal degrees string with optional direction.
    
    Args:
        decimal (float): Decimal degree value
        include_direction (bool): Whether to include cardinal direction (default: True)
        is_longitude (bool): Whether this is longitude (for direction determination)
        decimals (int): Number of decimal places (default: 4)
    
    Returns:
        str: Formatted decimal string (e.g., "57.5126°N" or "57.5126")
    
    Example:
        >>> dec_str = format_decimal(57.5126, include_direction=True, 
        ...                         is_longitude=False, decimals=4)
        >>> print(dec_str)
        57.5126°N
        
        >>> dec_str = format_decimal(12.2584, include_direction=False, decimals=2)
        >>> print(dec_str)
        12.26
    """
    
    # Format with specified decimal places
    formatted = f"{abs(decimal):.{decimals}f}"
    
    if include_direction:
        # Determine direction
        if is_longitude:
            direction = CARDINAL_WEST if decimal < 0 else CARDINAL_EAST
        else:
            direction = CARDINAL_SOUTH if decimal < 0 else CARDINAL_NORTH
        
        return f"{formatted}{DMS_DEGREE_SYMBOL}{direction}"
    else:
        return f"{formatted}{DMS_DEGREE_SYMBOL}"


def format_coordinate(value: float, is_longitude: bool = False, 
                     format_type: str = 'dms', **kwargs) -> str:
    """
    Format coordinate value for display.
    
    Main function to format coordinates in either DMS or decimal format.
    Automatically determines direction based on sign and coordinate type.
    
    Args:
        value (float): Coordinate value in decimal degrees
        is_longitude (bool): Whether this is longitude (determines direction)
        format_type (str): 'dms' or 'decimal'
        **kwargs: Additional format options:
                 - seconds_decimals (int): For DMS, decimal places for seconds (default: 1)
                 - decimals (int): For decimal, decimal places (default: 4)
    
    Returns:
        str: Formatted coordinate string
    
    Raises:
        ValueError: If value is outside valid range or format_type is invalid
    
    Example:
        >>> print(format_coordinate(57.5126, is_longitude=False, format_type='dms'))
        57°30'45.4"N
        
        >>> print(format_coordinate(57.5126, is_longitude=False, format_type='decimal'))
        57.5126°N
    """
    
    if format_type not in ('dms', 'decimal'):
        raise ValueError(f"Invalid format_type: {format_type}. Must be 'dms' or 'decimal'")
    
    if format_type == 'dms':
        seconds_decimals = kwargs.get('seconds_decimals', 1)
        degrees, minutes, seconds, direction = decimal_to_dms(value, is_longitude)
        return format_dms(degrees, minutes, seconds, direction, seconds_decimals)
    else:  # decimal
        decimals = kwargs.get('decimals', 4)
        return format_decimal(value, include_direction=True, is_longitude=is_longitude, decimals=decimals)


def parse_coordinate(coord_string: str, is_longitude: bool = False) -> float:
    """
    Parse coordinate from string (DMS or decimal format).
    
    Auto-detects format and parses the coordinate string.
    Accepts multiple delimiter variations for robustness.
    
    Supported DMS formats:
    - 57°30'45.5"N
    - 57°30'45.5N
    - 57-30-45.5N
    - 57 30 45.5N
    - 57d30m45.5sN
    
    Supported decimal formats:
    - 57.5126N
    - 57.5126°N
    - 57.5126
    
    Args:
        coord_string (str): Coordinate string to parse
        is_longitude (bool): Whether this is longitude (for validation)
    
    Returns:
        float: Decimal degree value
    
    Raises:
        ValueError: If string cannot be parsed or values are invalid
    
    Example:
        >>> decimal = parse_coordinate("57°30'45.5\"N", is_longitude=False)
        >>> print(f"{decimal:.4f}")
        57.5126
        
        >>> decimal = parse_coordinate("57.5126N", is_longitude=False)
        >>> print(f"{decimal:.4f}")
        57.5126
    """
    
    if not isinstance(coord_string, str):
        raise ValueError(f"Coordinate must be string, got {type(coord_string).__name__}")
    
    coord_string = coord_string.strip()
    
    # Try to parse as DMS format
    dms_result = _parse_dms_string(coord_string, is_longitude)
    if dms_result is not None:
        return dms_result
    
    # Try to parse as decimal format
    decimal_result = _parse_decimal_string(coord_string, is_longitude)
    if decimal_result is not None:
        return decimal_result
    
    raise ValueError(f"Cannot parse coordinate: {coord_string}")


def _parse_dms_string(coord_string: str, is_longitude: bool) -> Optional[float]:
    """
    Try to parse string as DMS format.
    
    Accepts multiple delimiter variations:
    - ° ' " (Unicode symbols)
    - d m s (letters)
    - - (dashes)
    - space (space separator)
    
    Args:
        coord_string (str): String to parse
        is_longitude (bool): Whether this is longitude
    
    Returns:
        Optional[float]: Decimal value if parsed successfully, None otherwise
    """
    
    # Pattern to match DMS with various delimiters
    # Matches: 57°30'45.5"N or 57d30m45.5sN or 57-30-45.5N or 57 30 45.5N
    pattern = r'(\d+(?:\.\d+)?)\s*[°d]\s*(\d+(?:\.\d+)?)\s*[\'m]\s*(\d+(?:\.\d+)?)\s*[\"s]?\s*([NSEW])'
    
    match = re.match(pattern, coord_string, re.IGNORECASE)
    if not match:
        # Try with space separators
        pattern = r'(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s*([NSEW])'
        match = re.match(pattern, coord_string, re.IGNORECASE)
    
    if not match:
        # Try with dash separators
        pattern = r'(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)\s*([NSEW])?'
        match = re.match(pattern, coord_string, re.IGNORECASE)
    
    if not match:
        return None
    
    try:
        degrees = int(match.group(1))
        minutes = int(match.group(2))
        seconds = float(match.group(3))
        direction = match.group(4).upper() if match.group(4) else None
        
        # Validate direction if provided
        if direction:
            if is_longitude and direction not in VALID_LON_DIRECTIONS:
                return None
            if not is_longitude and direction not in VALID_LAT_DIRECTIONS:
                return None
        else:
            # Assume positive direction if not specified
            direction = CARDINAL_EAST if is_longitude else CARDINAL_NORTH
        
        return dms_to_decimal(degrees, minutes, seconds, direction)
    
    except (ValueError, IndexError):
        return None


def _parse_decimal_string(coord_string: str, is_longitude: bool) -> Optional[float]:
    """
    Try to parse string as decimal format.
    
    Accepts: 57.5126N or 57.5126°N or 57.5126 or -57.5126
    
    Args:
        coord_string (str): String to parse
        is_longitude (bool): Whether this is longitude
    
    Returns:
        Optional[float]: Decimal value if parsed successfully, None otherwise
    """
    
    # Pattern to match decimal with optional direction
    # Matches: 57.5126N or 57.5126°N or 57.5126 or -57.5126
    pattern = r'(-?\d+(?:\.\d+)?)\s*[°]?\s*([NSEW])?'
    match = re.match(pattern + '$', coord_string, re.IGNORECASE)
    
    if not match:
        return None
    
    try:
        decimal = float(match.group(1))
        direction = match.group(2)
        
        if direction:
            direction = direction.upper()
            # Validate direction
            if is_longitude and direction not in VALID_LON_DIRECTIONS:
                return None
            if not is_longitude and direction not in VALID_LAT_DIRECTIONS:
                return None
            
            # Apply direction
            decimal = dms_to_decimal(
                int(abs(decimal)),
                int((abs(decimal) - int(abs(decimal))) * 60),
                ((abs(decimal) - int(abs(decimal))) * 60 - int((abs(decimal) - int(abs(decimal))) * 60)) * 60,
                direction
            )
        
        # Validate range
        if is_longitude:
            if not (-180 <= decimal <= 180):
                return None
        else:
            if not (-90 <= decimal <= 90):
                return None
        
        return decimal
    
    except (ValueError, IndexError):
        return None


if __name__ == "__main__":
    # Simple test
    print("\n" + "="*70)
    print("Testing Coordinate Formatter Module")
    print("="*70 + "\n")
    
    # Test decimal to DMS
    degrees, minutes, seconds, direction = decimal_to_dms(57.5126, is_longitude=False)
    print(f"✅ Decimal to DMS: 57.5126 → {degrees}° {minutes}' {seconds:.1f}\" {direction}")
    
    # Test DMS to decimal
    decimal = dms_to_decimal(57, 30, 45.36, 'N')
    print(f"✅ DMS to decimal: 57° 30' 45.36\" N → {decimal:.4f}°")
    
    # Test formatting
    dms_str = format_coordinate(57.5126, is_longitude=False, format_type='dms')
    print(f"✅ Format as DMS: {dms_str}")
    
    dec_str = format_coordinate(57.5126, is_longitude=False, format_type='decimal')
    print(f"✅ Format as decimal: {dec_str}")
    
    # Test parsing
    parsed = parse_coordinate("57°30'45.5\"N", is_longitude=False)
    print(f"✅ Parse DMS: 57°30'45.5\"N → {parsed:.4f}°")
    
    parsed = parse_coordinate("57.5126N", is_longitude=False)
    print(f"✅ Parse decimal: 57.5126N → {parsed:.4f}°")
    
    print("\n" + "="*70 + "\n")
