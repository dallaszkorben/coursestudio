"""
Coordinate format conversion utilities for CourseStudio.

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
        dms = decimal_to_dms(57.5126, is_longitude=False)
        # Returns: (57, 30, 45.36, 'N')
        
        dms = decimal_to_dms(-12.2584, is_longitude=True)
        # Returns: (12, 15, 30.24, 'W')
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
        decimal = dms_to_decimal(57, 30, 45.36, 'N')
        # Returns: 57.5126°
        
        decimal = dms_to_decimal(12, 15, 30.24, 'W')
        # Returns: -12.2584°
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
        dms_str = format_dms(57, 30, 45.36, 'N', seconds_decimals=1)
        # Returns: "57°30'45.4"N"
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
        dec_str = format_decimal(57.5126, include_direction=True, 
                                is_longitude=False, decimals=4)
        # Returns: "57.5126°N"
        
        dec_str = format_decimal(12.2584, include_direction=False, decimals=2)
        # Returns: "12.26°"
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
        # Format as DMS
        print(format_coordinate(57.5126, is_longitude=False, format_type='dms'))
        # Output: 57°30'45.4"N
        
        # Format as decimal
        print(format_coordinate(57.5126, is_longitude=False, format_type='decimal'))
        # Output: 57.5126°N
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
        decimal = parse_coordinate("57°30'45.5\"N", is_longitude=False)
        # Returns: 57.5126°
        
        decimal = parse_coordinate("57.5126N", is_longitude=False)
        # Returns: 57.5126°
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
    Try to parse string as DMS (Degrees-Minutes-Seconds) format.
    
    ===== DMS PARSING STRATEGY =====
    Robust parsing accepts multiple delimiter variations to handle different input styles.
    Three regex patterns tried in sequence:
    1. Unicode/Letter symbols: 57°30'45.5"N or 57d30m45.5sN (most formal)
    2. Space-separated: 57 30 45.5N (human-readable)
    3. Dash-separated: 57-30-45.5N (ASCII-only, device output)
    
    Why multiple patterns?
    - Different GPS devices output different formats
    - Users may paste from different sources
    - Maximize input flexibility while maintaining accuracy
    
    ===== REGEX PATTERN EXPLANATION =====
    
    Pattern 1 (Unicode/Letters):
    - Components: (\d+(?:\.\d+)?) = integer or decimal number
    - Delimiters: [°d] = degree symbol OR 'd' letter
    - Structure: digits [°d] digits [\'m] digits [\"s]? direction
    - Handles: 57°30'45.5"N, 57d30m45.5sN, 57°30'45.5N
    
    Pattern 2 (Spaces):
    - Simpler: digits spaces digits spaces digits direction
    - Less ambiguous than dashes
    - Handles: 57 30 45.5N
    
    Pattern 3 (Dashes):
    - ASCII-only: digits - digits - digits direction
    - No Unicode required (common on GPS devices)
    - Handles: 57-30-45.5N
    
    ===== VALIDATION ALGORITHM =====
    1. Try to match pattern (skip if no match)
    2. Extract components: degrees, minutes, seconds, direction
    3. Validate direction matches coordinate type:
       - Latitude: direction must be N or S
       - Longitude: direction must be E or W
    4. If direction missing, use default (N for latitude, E for longitude)
    5. Convert to decimal using dms_to_decimal()
    6. Return decimal value or None if validation fails
    
    ===== ERROR HANDLING =====
    Non-fatal errors return None (try next pattern):
    - No pattern matched
    - Direction doesn't match coordinate type
    - Number conversion failed (invalid format)
    
    This graceful failure allows multiple patterns to be tried.
    
    Args:
        coord_string (str): String to parse
        is_longitude (bool): Whether this is longitude (for direction validation)
    
    Returns:
        Optional[float]: Decimal value if parsed successfully, None otherwise
    
    Validation:
        - Degrees: 0-360 (actual limits: 0-90 for latitude, 0-180 for longitude)
        - Minutes: 0-59
        - Seconds: 0-59.999
        - Direction: N/S for latitude, E/W for longitude
    
    Examples:
        # Parse Unicode format
        _parse_dms_string("57°30'45.5\"N", False)
        # Returns: 57.5126
        
        # Parse letter delimiters (GPS device output)
        _parse_dms_string("57d30m45.5sN", False)
        # Returns: 57.5126
        
        # Parse dash separators (ASCII-only)
        _parse_dms_string("57-30-45.5N", False)
        # Returns: 57.5126
        
        # Parse space-separated
        _parse_dms_string("57 30 45.5 N", False)
        # Returns: 57.5126
    """
    
    # ===== PATTERN 1: UNICODE/LETTER DELIMITERS =====
    # Matches: 57°30'45.5"N or 57d30m45.5sN or 57°30'45.5N
    # Most formal format, supports Unicode symbols and letter codes
    pattern = r'(\d+(?:\.\d+)?)\s*[°d]\s*(\d+(?:\.\d+)?)\s*[\'m]\s*(\d+(?:\.\d+)?)\s*[\"s]?\s*([NSEW])'
    match = re.match(pattern, coord_string, re.IGNORECASE)
    
    if not match:
        # ===== PATTERN 2: SPACE-SEPARATED =====
        # Matches: 57 30 45.5N
        # Human-readable format, simple parsing
        pattern = r'(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s*([NSEW])'
        match = re.match(pattern, coord_string, re.IGNORECASE)
    
    if not match:
        # ===== PATTERN 3: DASH-SEPARATED =====
        # Matches: 57-30-45.5N or 57-30-45.5
        # ASCII-only format (common GPS device output), direction optional
        pattern = r'(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)\s*([NSEW])?'
        match = re.match(pattern, coord_string, re.IGNORECASE)
    
    if not match:
        return None  # No DMS pattern matched - return None to try decimal parsing
    
    try:
        # ===== EXTRACT COMPONENTS FROM REGEX =====
        # Regex groups: (1)degrees (2)minutes (3)seconds (4)direction
        degrees = int(match.group(1))
        minutes = int(match.group(2))
        seconds = float(match.group(3))
        direction = match.group(4).upper() if match.group(4) else None
        
        # ===== VALIDATE DIRECTION =====
        # Direction must match coordinate type
        if direction:
            # Direction provided - validate it's appropriate for this coordinate type
            if is_longitude and direction not in VALID_LON_DIRECTIONS:
                # Longitude got N/S instead of E/W - invalid
                return None
            if not is_longitude and direction not in VALID_LAT_DIRECTIONS:
                # Latitude got E/W instead of N/S - invalid
                return None
        else:
            # Direction not in string - use sensible default
            # North for latitude, East for longitude (positive assumed)
            direction = CARDINAL_EAST if is_longitude else CARDINAL_NORTH
        
        # ===== CONVERT TO DECIMAL =====
        # Pass to dms_to_decimal() for component validation and conversion
        # If conversion fails (bad values), exception caught below
        return dms_to_decimal(degrees, minutes, seconds, direction)
    
    except (ValueError, IndexError):
        # Component conversion failed (invalid numbers or indexes)
        # Return None to allow next pattern to be tried or fail gracefully
        return None


def _parse_decimal_string(coord_string: str, is_longitude: bool) -> Optional[float]:
    """
    Try to parse string as decimal degrees format.
    
    ===== DECIMAL PARSING STRATEGY =====
    Handles various decimal input styles with flexible direction handling:
    - With direction: 57.5126N or 57.5126°N (direction explicitly provided)
    - Without direction: 57.5126 or -57.5126 (sign indicates direction)
    - Optional Unicode degree symbol (accepted but not required)
    
    ===== DIRECTION CONVERSION LOGIC =====
    Three scenarios:
    
    Scenario 1: Direction provided (N/S/E/W)
    - Input: 57.5126N
    - Process: Use direction to determine sign (N/E=positive, S/W=negative)
    - Output: 57.5126
    
    Scenario 2: Negative sign provided
    - Input: -57.5126
    - Process: Negative implies South (latitude) or West (longitude)
    - Output: -57.5126
    
    Scenario 3: Both direction AND sign provided
    - Input: -57.5126N (direction=N, value=-57.5126)
    - Process: Direction takes precedence over sign
    - Output: Positive value (N overrides negative sign)
    
    ===== REGEX PATTERN EXPLANATION =====
    Pattern: (-?\d+(?:\.\d+)?)\s*[°]?\s*([NSEW])?
    
    Components:
    - (-?\d+(?:\.\d+)?): Numeric value, optionally negative
    - \s*[°]?\s*: Optional degree symbol with surrounding spaces
    - ([NSEW])?: Optional direction letter (N, S, E, or W)
    
    Examples:
    - "57.5126N" → groups: (1)57.5126 (2)N
    - "57.5126°N" → groups: (1)57.5126 (2)N
    - "-57.5126" → groups: (1)-57.5126 (2)None
    - "57.5126" → groups: (1)57.5126 (2)None
    
    ===== VALIDATION ALGORITHM =====
    1. Try to match pattern (return None if no match)
    2. Extract numeric value and optional direction
    3. If direction provided:
       - Validate direction matches coordinate type (N/S for lat, E/W for lon)
       - Validate direction is uppercase
    4. Apply sign based on direction (S/W = negative)
    5. Validate final value is within range:
       - Latitude: -90 to +90
       - Longitude: -180 to +180
    6. Return decimal value or None if validation fails
    
    ===== ERROR HANDLING =====
    Non-fatal errors return None (allow parse_coordinate to try other methods):
    - No pattern matched
    - Direction doesn't match coordinate type
    - Final value outside valid range
    - Number conversion fails
    
    Args:
        coord_string (str): String to parse
        is_longitude (bool): Whether this is longitude (for validation)
    
    Returns:
        Optional[float]: Decimal value if parsed successfully, None otherwise
    
    Examples:
        # Parse with direction
        _parse_decimal_string("57.5126N", False)
        # Returns: 57.5126
        
        # Parse with negative sign (implies South)
        _parse_decimal_string("-57.5126", False)
        # Returns: -57.5126
        
        # Parse with degree symbol and direction
        _parse_decimal_string("57.5126°N", False)
        # Returns: 57.5126
        
        # Parse longitude with direction
        _parse_decimal_string("12.2584E", True)
        # Returns: 12.2584
        
        # Parse negative (implies West for longitude)
        _parse_decimal_string("-12.2584", True)
        # Returns: -12.2584
    """
    
    # ===== DECIMAL PARSING REGEX PATTERN =====
    # Matches: [-]number [°symbol] [direction]
    pattern = r'(-?\d+(?:\.\d+)?)\s*[°]?\s*([NSEW])?'
    match = re.match(pattern + '$', coord_string, re.IGNORECASE)
    
    if not match:
        return None  # Pattern doesn't match - not decimal format
    
    try:
        # ===== EXTRACT COMPONENTS =====
        # Group 1: Numeric value (may be negative)
        # Group 2: Optional cardinal direction (N/S/E/W)
        decimal = float(match.group(1))
        direction = match.group(2)
        
        # ===== APPLY DIRECTION =====
        if direction:
            # Direction provided - validate it matches coordinate type
            direction = direction.upper()
            
            # ===== VALIDATE DIRECTION FOR COORDINATE TYPE =====
            # Latitude uses N/S, Longitude uses E/W
            if is_longitude and direction not in VALID_LON_DIRECTIONS:
                # Longitude got N/S - invalid direction type
                return None
            if not is_longitude and direction not in VALID_LAT_DIRECTIONS:
                # Latitude got E/W - invalid direction type
                return None
            
            # ===== CONVERT DIRECTION TO SIGNED VALUE =====
            # Direction overrides any negative sign in the number
            # Examples:
            #   57.5126 + N → +57.5126
            #   57.5126 + S → -57.5126
            #   57.5126 + E → +57.5126
            #   57.5126 + W → -57.5126
            # Use dms_to_decimal to apply direction properly
            # Extract integer and fractional parts, convert to DMS first
            abs_decimal = abs(decimal)
            deg = int(abs_decimal)
            min_part = (abs_decimal - deg) * 60
            min_int = int(min_part)
            sec = (min_part - min_int) * 60
            
            decimal = dms_to_decimal(deg, min_int, sec, direction)
        
        # ===== VALIDATE FINAL VALUE RANGE =====
        # Ensure coordinate is within valid geographic range
        if is_longitude:
            # Longitude must be -180 to +180
            if not (-180 <= decimal <= 180):
                return None  # Out of range for longitude
        else:
            # Latitude must be -90 to +90
            if not (-90 <= decimal <= 90):
                return None  # Out of range for latitude
        
        return decimal
    
    except (ValueError, IndexError):
        # Number conversion failed (invalid format)
        # Return None to allow other parsing methods to be tried
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
