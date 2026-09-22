"""
Application constants for CourseStudio.

Defines hardcoded application constants that rarely change.
User-configurable settings are in settings.ini (loaded via AppConfig).

Author: Development Team
Date: 2026-09-20
"""

# ============================================================================
# APPLICATION METADATA
# ============================================================================

APP_VERSION = "1.0.0"
APP_NAME = "CourseStudio"
APP_AUTHOR = "Development Team"
APP_DATE = "2026-09-20"

# ============================================================================
# DIRECTORY PATHS
# ============================================================================

# Relative to project root
CONFIG_DIR = "config"
SETTINGS_FILE = "config/settings.ini"
DOC_DIR = "doc"
MBTILES_DIR = "mbtiles"
TESTS_DIR = "tests"
TEST_FIXTURES_DIR = "tests/fixtures"
LOG_DIR = "."  # Logs in project root by default

# ============================================================================
# COORDINATE CONSTANTS
# ============================================================================

# DMS Format constants
DMS_DEGREE_SYMBOL = "°"
DMS_MINUTE_SYMBOL = "'"
DMS_SECOND_SYMBOL = "\""

# Cardinal directions
CARDINAL_NORTH = "N"
CARDINAL_SOUTH = "S"
CARDINAL_EAST = "E"
CARDINAL_WEST = "W"

# Latitude range (degrees)
LATITUDE_MIN = -90.0
LATITUDE_MAX = 90.0

# Longitude range (degrees)
LONGITUDE_MIN = -180.0
LONGITUDE_MAX = 180.0

# ============================================================================
# MAP CONSTANTS
# ============================================================================

# Supported zoom levels
DEFAULT_ZOOM_LEVEL = 13
MIN_ZOOM_LEVEL = 10
MAX_ZOOM_LEVEL = 16

# Map boundaries (Swedish archipelago area for default)
DEFAULT_MAP_CENTER_LAT = 57.5
DEFAULT_MAP_CENTER_LON = 12.0

# ============================================================================
# FILE OPERATIONS
# ============================================================================

# GPX file constants
GPX_FILE_EXTENSION = ".gpx"
BACKUP_FILE_EXTENSION = ".bak"
DEFAULT_ENCODING = "utf-8"

# File size limits (MB)
MAX_FILE_SIZE_WARNING = 25  # Warn if file > 25 MB
MAX_FILE_SIZE_ERROR = 100   # Error if file > 100 MB

# ============================================================================
# UI CONSTANTS
# ============================================================================

# Default window dimensions (pixels)
DEFAULT_WINDOW_WIDTH = 1400
DEFAULT_WINDOW_HEIGHT = 900
DEFAULT_WINDOW_X = 100
DEFAULT_WINDOW_Y = 100

# Panel sizes (proportions)
LEFT_PANEL_WIDTH_RATIO = 0.25   # Track list
CENTER_PANEL_WIDTH_RATIO = 0.50 # Map
RIGHT_PANEL_WIDTH_RATIO = 0.25  # Trackpoint list

# Table row height (pixels)
TABLE_ROW_HEIGHT = 25

# ============================================================================
# PERFORMANCE CONSTANTS
# ============================================================================

# Trackpoint display
MAX_TRACKPOINTS_NO_WARNING = 5000
MAX_TRACKPOINTS_PER_PAGE = 500  # For pagination in Phase 5+

# Undo/Redo stack
MAX_UNDO_REDO_STACK_SIZE = 50
MAX_HISTORY_MEMORY_MB = 500  # Limit history to 500 MB

# Thread timeout (seconds)
FILE_OPERATION_TIMEOUT = 30
MAP_RENDER_TIMEOUT = 10

# ============================================================================
# KEYBOARD SHORTCUTS
# ============================================================================

SHORTCUT_OPEN_FILE = "Ctrl+O"
SHORTCUT_SAVE_FILE = "Ctrl+S"
SHORTCUT_SAVE_AS = "Ctrl+Shift+S"
SHORTCUT_QUIT = "Ctrl+Q"
SHORTCUT_UNDO = "Ctrl+Z"
SHORTCUT_REDO = "Ctrl+Y"
SHORTCUT_ADD_POINT = "Ctrl+N"
SHORTCUT_DELETE_POINT = "Delete"
SHORTCUT_RENAME_TRACK = "Ctrl+R"
SHORTCUT_ZOOM_IN = "Ctrl+Plus"
SHORTCUT_ZOOM_OUT = "Ctrl+Minus"
SHORTCUT_FIT_TRACK = "Ctrl+0"
SHORTCUT_REFRESH = "Ctrl+F5"

# ============================================================================
# GARMIN COMPATIBILITY CONSTANTS
# ============================================================================

# GPX version for Garmin export
GPX_VERSION = "1.1"
GPX_CREATOR = "CourseStudio 1.0.0"

# Garmin namespaces (required for device import)
GARMIN_NAMESPACE_MAIN = "http://www.topografix.com/GPX/1/1"
GARMIN_NAMESPACE_EXTENSIONS_V3 = "http://www.garmin.com/xmlschemas/GpxExtensions/v3"
GARMIN_NAMESPACE_WAYPOINT_EXTENSION_V1 = "http://www.garmin.com/xmlschemas/WaypointExtension/v1"
GARMIN_NAMESPACE_TRACKPOINT_EXTENSION_V1 = "http://www.garmin.com/xmlschemas/TrackPointExtension/v1"
GARMIN_NAMESPACE_SCHEMA_INSTANCE = "http://www.w3.org/2001/XMLSchema-instance"

# ============================================================================
# LOGGING CONSTANTS
# ============================================================================

# Log levels
LOG_LEVEL_DEBUG = "DEBUG"
LOG_LEVEL_INFO = "INFO"
LOG_LEVEL_WARNING = "WARNING"
LOG_LEVEL_ERROR = "ERROR"
LOG_LEVEL_CRITICAL = "CRITICAL"

# Log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ============================================================================
# ERROR MESSAGES
# ============================================================================

ERROR_FILE_NOT_FOUND = "File not found: {path}"
ERROR_PERMISSION_DENIED = "Permission denied: {path}"
ERROR_INVALID_GPX = "Invalid GPX file format: {path}"
ERROR_PARSE_ERROR = "Error parsing GPX file: {error}"
ERROR_COORDINATE_INVALID = "Invalid coordinate: {value}"
ERROR_EMPTY_TRACK = "Cannot perform operation on empty track"
ERROR_INVALID_INDEX = "Invalid index: {index}"
ERROR_GARMIN_INVALID = "File does not meet Garmin compatibility requirements"

# ============================================================================
# SUCCESS MESSAGES
# ============================================================================

SUCCESS_FILE_SAVED = "File saved successfully: {path}"
SUCCESS_FILE_OPENED = "File opened successfully: {path}"
SUCCESS_TRACK_RENAMED = "Track renamed to: {name}"
SUCCESS_POINT_ADDED = "Trackpoint added at index: {index}"
SUCCESS_POINT_DELETED = "Trackpoint deleted from index: {index}"
SUCCESS_UNDO_COMPLETE = "Undo completed: {operation}"
SUCCESS_REDO_COMPLETE = "Redo completed: {operation}"

# ============================================================================
# DISTANCE CONSTANTS
# ============================================================================

# Earth radius in kilometers (for Haversine formula)
EARTH_RADIUS_KM = 6371.0

# ============================================================================
# CONFIGURATION VALIDATION
# ============================================================================

# Valid coordinate formats
VALID_COORDINATE_FORMATS = ["dms", "decimal"]

# Valid languages
VALID_LANGUAGES = ["en", "hu"]

# ============================================================================

if __name__ == "__main__":
    print(f"CourseStudio Constants Module v{APP_VERSION}")
    print(f"Loaded configuration constants for {APP_NAME}")
