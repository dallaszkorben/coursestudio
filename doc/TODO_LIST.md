# mangpx - Development TODO List

**Project:** GPX File Manipulator (PyQt5-based)  
**Status:** Task Breakdown Complete  
**Last Updated:** 2026-09-20 (Step 4 COMPLETE)
**Current Phase:** Phase 1 - Foundation (4/5 steps complete)  

---

## OVERVIEW

This document contains the complete step-by-step breakdown of all development tasks needed to build the mangpx application from scratch. Tasks are organized by **Phase** (1-5) and **Step** (1-N), progressing from foundational components to advanced features.

**Development Model:**
- Complete each step in sequence
- After each step: Show user result, ask for approval
- If approved: ✅ Move to next step
- If issues: Fix before proceeding
- After every 3-5 steps: Update this document with completion status

---

## PHASE 1: FOUNDATION & CORE GPX HANDLING

### Step 1: Project Structure & Configuration System

**Objective:** Set up Python package hierarchy and configuration management

**Tasks:**
- [ ] Create Python package structure in `src/` directory
  - [ ] Create `src/__init__.py`
  - [ ] Create `src/main.py` (entry point stub)
  - [ ] Create all subdirectories: `gui/`, `core/`, `map/`, `utils/`
  - [ ] Create `__init__.py` in each subdirectory

- [ ] Create `config/` directory structure
  - [ ] Create `config/__init__.py`
  - [ ] Create `config/constants.py` (application constants)
  - [ ] Create `config/app_config.py` (configuration loader)
  - [ ] Create `config/settings.ini` (default settings file)

- [ ] Implement `AppConfig` class
  - [ ] Read settings.ini with ConfigParser
  - [ ] Implement get(), get_int(), get_bool(), get_float() methods
  - [ ] Handle missing values with defaults
  - [ ] Type conversion and error handling

- [ ] Create test directory structure
  - [ ] Create `tests/__init__.py`
  - [ ] Create `tests/fixtures/` directory for test data
  - [ ] Create sample GPX files for testing

- [ ] Create documentation
  - [ ] Create `doc/IMPLEMENTATION_NOTES.md` (for design decisions)

**Acceptance Criteria:**
- ✅ All directories created and accessible
- ✅ `settings.ini` contains all required configuration keys with defaults
- ✅ `AppConfig` class successfully loads and returns configuration values
- ✅ Application can be run with `python src/main.py` (shows "Starting mangpx...")
- ✅ Configuration can be accessed: `config.get('Application', 'app_name')` returns 'mangpx'

**Dependencies:** None

**Testing:**
```bash
# Verify structure
python -c "import sys; sys.path.insert(0, 'src'); from config.app_config import AppConfig"

# Load config
python -c "from config.app_config import AppConfig; c = AppConfig('config/settings.ini'); print(c.get('Application', 'app_name'))"
```

---

### Step 2: Core GPX Handling - Reading GPX Files

**Objective:** Implement GPX file parsing using gpxpy library

**Tasks:**
- [ ] Install required dependencies
  - [ ] Verify `gpxpy` installed in venv: `pip list | grep gpxpy`
  - [ ] Verify `lxml` installed (required by gpxpy)
  - [ ] Create `requirements.txt` with all dependencies

- [ ] Implement `core/gpx_handler.py`
  - [ ] Class `GPXHandler` with methods:
    - [ ] `load_gpx(file_path: str) -> GPX` - Load GPX file using gpxpy
    - [ ] `get_tracks() -> List[Track]` - Extract all tracks from loaded GPX
    - [ ] `get_track_info(track) -> dict` - Return name, points count, distance
    - [ ] `calculate_distance(track) -> float` - Sum of distances between consecutive points
    - [ ] `validate_file(file_path: str) -> tuple(bool, str)` - Check if file valid GPX

  - [ ] Error handling:
    - [ ] Catch FileNotFoundError
    - [ ] Catch XML parsing errors
    - [ ] Catch gpxpy validation errors
    - [ ] Return user-friendly error messages

- [ ] Implement distance calculation
  - [ ] Import/use Haversine formula
  - [ ] Calculate distance in kilometers
  - [ ] Handle edge case: single-point track

- [ ] Create unit tests `tests/test_gpx_handler.py`
  - [ ] Test load_gpx() with valid file
  - [ ] Test load_gpx() with invalid file (error handling)
  - [ ] Test get_tracks() with multi-track GPX
  - [ ] Test calculate_distance() with known distances
  - [ ] Test with KARLSKRONA-HALLARUM.gpx (from doc folder)
  - [ ] Add timeout to prevent infinite loops

**Acceptance Criteria:**
- ✅ Load valid GPX file without errors
- ✅ Extract all tracks from GPX
- ✅ Calculate track distance within 0.1% accuracy
- ✅ Handle file not found gracefully
- ✅ Handle malformed XML gracefully
- ✅ All unit tests pass with timeout protection

**Dependencies:**
- gpxpy (installed in venv)
- math (standard library, for Haversine)

**Testing:**
```bash
# Run unit tests with timeout
pytest tests/test_gpx_handler.py -v --timeout=5

# Manual test with sample GPX
python -c "
from core.gpx_handler import GPXHandler
handler = GPXHandler()
gpx = handler.load_gpx('path/to/sample.gpx')
tracks = handler.get_tracks(gpx)
for track in tracks:
    print(f'{track.name}: {handler.calculate_distance(track):.2f} km')
"
```

---

### Step 3: Core GPX Handling - Coordinate Conversion Utilities

**Objective:** Implement DMS ↔ Decimal coordinate conversion

**Tasks:**
- [ ] Implement `utils/coordinate_formatter.py`
  - [ ] Function `decimal_to_dms(decimal: float, is_longitude: bool) -> tuple`
    - [ ] Convert decimal degrees to (degrees, minutes, seconds, direction)
    - [ ] Determine direction: N/S for latitude, E/W for longitude
    - [ ] Return tuple: (int, int, float, str)

  - [ ] Function `dms_to_decimal(degrees: int, minutes: int, seconds: float, direction: str) -> float`
    - [ ] Validate input ranges (degrees 0-360, minutes 0-59, seconds 0-59.999)
    - [ ] Apply direction sign (N=+, S=-, E=+, W=-)
    - [ ] Return decimal degree as float

  - [ ] Function `format_coordinate(value: float, is_longitude: bool, format_type: str) -> str`
    - [ ] format_type: 'dms' or 'decimal'
    - [ ] DMS format: "57°30'45.5"N" with Unicode degree symbol
    - [ ] Decimal format: "57.5126°N"
    - [ ] Handle negative values correctly

  - [ ] Function `parse_coordinate_string(coord_str: str, is_longitude: bool) -> float`
    - [ ] Parse DMS format: "57°30'45.5"N" or "57-30-45.5N"
    - [ ] Parse decimal format: "57.5126" or "57.5126N"
    - [ ] Auto-detect format
    - [ ] Raise ValueError if invalid

- [ ] Create unit tests `tests/test_coordinate_formatter.py`
  - [ ] Test decimal_to_dms() with known coordinates
  - [ ] Test dms_to_decimal() with known coordinates
  - [ ] Test format_coordinate() DMS output format
  - [ ] Test format_coordinate() Decimal output format
  - [ ] Test parse_coordinate_string() with multiple formats
  - [ ] Test edge cases: 0°0'0", 180°0'0", negative values
  - [ ] Verify round-trip conversion accuracy: decimal → DMS → decimal

**Acceptance Criteria:**
- ✅ Convert 57.5126°N ↔ 57°30'45.5"N correctly
- ✅ Parse multiple coordinate formats successfully
- ✅ Format output matches specification (° ' " symbols, direction letter)
- ✅ Round-trip conversion error < 0.001°
- ✅ All unit tests pass

**Dependencies:**
- math (standard library)
- re (for parsing)

**Testing:**
```bash
pytest tests/test_coordinate_formatter.py -v --timeout=5

python -c "
from utils.coordinate_formatter import *
# Test conversion
dec = 57.5126
dms = decimal_to_dms(dec, is_longitude=False)
print(f'DMS: {dms}')
back = dms_to_decimal(*dms)
print(f'Back to decimal: {back}')
print(f'Error: {abs(dec - back):.6f}')
"
```

---

### Step 4: Track Manager - Data Structure & Basic Operations ✅ DONE

**Objective:** Create track manipulation layer

**Status:** ✅ COMPLETE (72/72 tests passing)

**Tasks:**
- [✅] Implement `core/track_manager.py` (~800 LOC)
  - [✅] Dataclass `Trackpoint` - single waypoint with validation
    - Latitude/longitude with range validation (-90° to 90°, -180° to 180°)
    - Optional elevation and timestamp
    - Index tracking in track
  
  - [✅] Dataclass `TrackData` - in-memory track representation
    - Track name and original name (for undo)
    - List of trackpoints
    - Segment count, elevation/time flags
    - Geographic bounds (min/max lat/lon)
    - Distance in kilometers
    - Dirty state tracking

  - [✅] Class `TrackManager` - central track management
    - Constructor: `__init__()` - initialize empty state
    - Method: `load_from_gpx(gpx_data, file_path) -> int`
      - Load all tracks from GPX object
      - Auto-select first track
      - Return number of tracks loaded
    - Method: `clear()` - clear all tracks
    - Method: `select_track(index) -> bool` - select track by index
    - Method: `get_selected_track() -> Optional[TrackData]`
    - Method: `get_track_by_index(index) -> Optional[TrackData]`
    - Method: `get_all_tracks() -> List[TrackData]`
    - Method: `get_track_count() -> int`
    - Method: `get_selected_track_info() -> Optional[Dict]` - summary info
    - Method: `get_track_info(index) -> Optional[Dict]`
    - Method: `rename_track(index, new_name) -> bool`
    - Method: `rename_selected_track(new_name) -> bool`
    - Method: `recalculate_distance(index) -> Optional[float]`
    - Method: `recalculate_selected_distance() -> Optional[float]`
    - Method: `get_trackpoints(index) -> Optional[List[Trackpoint]]`
    - Method: `get_selected_trackpoints() -> Optional[List[Trackpoint]]`
    - Method: `get_trackpoint(track_idx, point_idx) -> Optional[Trackpoint]`
    - Method: `is_any_track_dirty() -> bool`
    - Method: `is_track_dirty(index) -> bool`
    - Method: `is_selected_track_dirty() -> bool`
    - Method: `mark_clean(index) -> bool`
    - Method: `mark_clean_all()` - mark all as saved

- [✅] Create unit tests `tests/test_track_manager.py` (72 tests)
  - [✅] Trackpoint validation: 8 tests
  - [✅] TrackData operations: 8 tests
  - [✅] Loading from GPX: 9 tests
  - [✅] Track selection: 9 tests
  - [✅] Information queries: 8 tests
  - [✅] Track operations: 9 tests
  - [✅] Trackpoint access: 7 tests
  - [✅] Dirty state management: 11 tests
  - [✅] Utility functions: 3 tests
  - [✅] Integration workflows: 2 tests

**Test Results:**
- ✅ 72/72 tests passing
- ✅ All previous tests still passing (161 total)
- ✅ No timeouts or infinite loops
- ✅ 0.17 second execution time

**Key Implementation Details:**
- Trackpoint/TrackData use Python dataclasses for safety
- Coordinate validation in __post_init__
- Distance calculation converts Trackpoints to tuples (matches Calculator API)
- All methods return Optional types or booleans for safe error handling
- Comprehensive logging for debugging
- Full PEP 257 docstrings and type hints

**Acceptance Criteria:** ✅ ALL MET
- ✅ Trackpoint dataclass with validation
- ✅ TrackData class for in-memory storage
- ✅ TrackManager with full track lifecycle
- ✅ Load, select, rename, recalculate distance
- ✅ Track information queries working
- ✅ Dirty state tracking for undo/redo prep
- ✅ 72 comprehensive unit tests (100% pass)
- ✅ All previous tests still passing
- ✅ No regressions

**Dependencies:**
- gpxpy (GPX data handling)
- Calculator module (distance calculation)
- Python dataclasses (standard library)

---

### Step 5: Basic PyQt5 Application Skeleton

**Objective:** Create main application window and menu structure

**Tasks:**
- [ ] Install PyQt5 if not already in venv
  - [ ] Verify: `pip list | grep PyQt5`

- [ ] Create `gui/main_window.py`
  - [ ] Class `MainWindow(QMainWindow)`
  - [ ] Constructor setup:
    - [ ] Window title: "mangpx - GPX File Manipulator"
    - [ ] Window size: 1400x900 (from config)
    - [ ] Window icon (use water-droplet.png)
    - [ ] Central widget placeholder

  - [ ] Create menu bar with structure:
    - [ ] File menu: Open, Save, Save As, Exit
    - [ ] Edit menu: Undo, Redo, Add Trackpoint, Delete Trackpoint, Rename Track
    - [ ] View menu: Coordinate Format, Zoom controls
    - [ ] Help menu: About, Help

  - [ ] Connect menu actions to placeholder methods
    - [ ] Use QAction for each menu item
    - [ ] Connect to methods (currently print to console)

  - [ ] Create toolbar with buttons:
    - [ ] [Open] [Save] [Save As] [Undo] [Redo] [Help]

  - [ ] Create status bar
    - [ ] Show: Ready | Points: 0 | Distance: 0 km | Zoom: Z13

- [ ] Create `src/main.py`
  - [ ] Parse command-line arguments (optional: file path)
  - [ ] Create QApplication
  - [ ] Create MainWindow
  - [ ] Show window
  - [ ] Start event loop

- [ ] Create `tests/test_gui_basic.py`
  - [ ] Test MainWindow initialization
  - [ ] Test menu structure creation
  - [ ] Test window properties (title, size)

**Acceptance Criteria:**
- ✅ Application launches without errors
- ✅ Window displays with correct title and size
- ✅ All menus visible and clickable
- ✅ Toolbar buttons visible
- ✅ Status bar visible
- ✅ Menu actions trigger (print to console)
- ✅ Window closes cleanly

**Dependencies:**
- PyQt5
- config (AppConfig)
- images/water-droplet.png

**Testing:**
```bash
# Run application
python src/main.py

# Should show: "Starting mangpx..." and GUI window
```

---

## PHASE 2: TRACK DISPLAY & MAP VISUALIZATION

### Step 6: Track List Widget

**Objective:** Display tracks from opened GPX file in a list

**Tasks:**
- [ ] Create `gui/widgets/track_list.py`
  - [ ] Class `TrackListWidget(QWidget)`
  - [ ] Contains QTableWidget with columns:
    - [ ] Track Name
    - [ ] Distance (km)
    - [ ] Point Count
    - [ ] Garmin Metadata (show if present)

  - [ ] Method: `load_tracks(track_manager: TrackManager)`
    - [ ] Clear current table
    - [ ] For each track in manager.tracks:
      - [ ] Add row with track info
      - [ ] Set row data: track object reference

  - [ ] Method: `get_selected_track() -> Track`
    - [ ] Return selected row's track object

  - [ ] Signal: `track_selected` - emit when row clicked
    - [ ] Pass track object as parameter

  - [ ] Method: `update_track_distance(track_index: int, distance: float)`
    - [ ] Update distance in specific row

- [ ] Connect to MainWindow
  - [ ] Create TrackListWidget in MainWindow
  - [ ] Place in left panel (layout)
  - [ ] Connect track_selected signal

- [ ] Create unit tests `tests/test_track_list.py`
  - [ ] Test load_tracks() with sample data
  - [ ] Test row selection
  - [ ] Test distance display format

**Acceptance Criteria:**
- ✅ Track list displays all tracks from GPX
- ✅ Each row shows correct name, distance, points
- ✅ Selection working
- ✅ No errors with empty GPX or single track
- ✅ Layout looks reasonable in main window

**Dependencies:**
- PyQt5 (QWidget, QTableWidget)
- TrackManager

---

### Step 7: Trackpoint List Widget

**Objective:** Display trackpoints for selected track

**Tasks:**
- [ ] Create `gui/widgets/trackpoint_list.py`
  - [ ] Class `TrackpointListWidget(QWidget)`
  - [ ] Contains QTableWidget with columns:
    - [ ] Sequence (1-based index)
    - [ ] Latitude (formatted per config)
    - [ ] Longitude (formatted per config)
    - [ ] Altitude (if available)
    - [ ] Timestamp (if available)

  - [ ] Method: `load_trackpoints(track: Track, coord_format: str)`
    - [ ] Clear current table
    - [ ] For each trackpoint in track:
      - [ ] Format coordinates using coordinate_formatter
      - [ ] Add row to table

  - [ ] Method: `get_selected_trackpoint() -> int` (returns index)
    - [ ] Return index of selected row

  - [ ] Signal: `trackpoint_selected` - emit when row clicked
    - [ ] Pass trackpoint index as parameter

  - [ ] Method: `update_coordinate_format(format_type: str)`
    - [ ] Reload table with new format (DMS/decimal)

- [ ] Handle large trackpoint counts (pagination optional in Phase 3)
  - [ ] Load all points for now (Phase 3: implement lazy loading if needed)

- [ ] Create unit tests `tests/test_trackpoint_list.py`
  - [ ] Test load_trackpoints() with sample track
  - [ ] Test coordinate formatting (DMS, decimal)
  - [ ] Test with large trackpoint count (no freeze)

**Acceptance Criteria:**
- ✅ Trackpoints displayed in list
- ✅ Coordinates formatted correctly
- ✅ Coordinates match configuration (DMS/decimal)
- ✅ Selection working
- ✅ No UI freeze with 5000+ points
- ✅ Changing format updates display immediately

**Dependencies:**
- PyQt5 (QWidget, QTableWidget)
- coordinate_formatter
- gpxpy

---

### Step 8: Map Provider & Tile Loading

**Objective:** Load and serve mbtiles data for map rendering

**Tasks:**
- [ ] Create `map/mbtiles_provider.py`
  - [ ] Class `MBTilesProvider`
  - [ ] Constructor: `__init__(mbtiles_path: str)`
    - [ ] Connect to mbtiles SQLite database
    - [ ] Read metadata (name, version, zoom levels)
    - [ ] Validate file integrity

  - [ ] Method: `get_tile(z: int, x: int, y: int) -> bytes`
    - [ ] Query tile from database
    - [ ] Return PNG image data
    - [ ] Return None if tile doesn't exist

  - [ ] Method: `get_bounds() -> tuple(minlon, minlat, maxlon, maxlat)`
    - [ ] Read from mbtiles metadata

  - [ ] Method: `get_zoom_levels() -> list`
    - [ ] Return available zoom levels

  - [ ] Error handling:
    - [ ] Handle missing mbtiles file
    - [ ] Handle database errors
    - [ ] Handle missing tiles gracefully

- [ ] Create `map/map_renderer.py`
  - [ ] Class `MapRenderer(QWidget)`
  - [ ] Use PyQtWebEngine or matplotlib for rendering
  - [ ] Render PNG tiles from MBTilesProvider
  - [ ] Implement pan and zoom

- [ ] Create unit tests `tests/test_mbtiles_provider.py`
  - [ ] Test load mbtiles file (use Sweden-Raster-Z10-Z16.mbtiles)
  - [ ] Test get_tile() with valid coordinates
  - [ ] Test get_tile() with invalid coordinates (returns None)
  - [ ] Test get_bounds() and get_zoom_levels()

**Acceptance Criteria:**
- ✅ Load Sweden-Raster-Z10-Z16.mbtiles without errors
- ✅ Retrieve tiles successfully
- ✅ Tile bounds correct
- ✅ Zoom levels match mbtiles data
- ✅ Handle missing files gracefully

**Dependencies:**
- sqlite3 (standard library)
- Pillow or similar for image handling

---

### Step 9: Interactive Map Display

**Objective:** Show track on map with zoom/pan controls

**Tasks:**
- [ ] Create `gui/widgets/map_widget.py`
  - [ ] Class `MapWidget(QWidget)` using PyQtWebEngine + Leaflet.js
  - [ ] Initialize map centered on default location
  - [ ] Load OSM/mbtiles tiles

  - [ ] Method: `load_track(track: Track, trackpoints: list)`
    - [ ] Draw track path as polyline
    - [ ] Draw trackpoints as markers
    - [ ] Zoom to fit entire track

  - [ ] Method: `highlight_trackpoint(index: int)`
    - [ ] Highlight selected trackpoint with different marker color

  - [ ] Methods: `zoom_in()`, `zoom_out()`, `fit_track()`
    - [ ] Change zoom level
    - [ ] Center on track

  - [ ] Signal: `point_clicked_on_map` - emit when marker clicked
    - [ ] Pass trackpoint index

  - [ ] Use Leaflet.js library for rendering
    - [ ] Create HTML template with Leaflet map
    - [ ] Use WebEngine to render

- [ ] Integrate with MBTilesProvider
  - [ ] Load tiles from mbtiles for map background

- [ ] Create unit tests (manual testing for GUI components)
  - [ ] Verify map loads without errors
  - [ ] Verify track displays on map
  - [ ] Verify zoom controls work

**Acceptance Criteria:**
- ✅ Map displays in GUI
- ✅ Track renders as path on map
- ✅ Trackpoints visible as markers
- ✅ Zoom/pan controls functional
- ✅ Clicking marker selects point in list
- ✅ No lag with 5000+ points

**Dependencies:**
- PyQtWebEngine
- Leaflet.js (included in HTML template)
- MBTilesProvider

---

### Step 10: Integrate Track List + Trackpoint List + Map

**Objective:** Connect all three display components

**Tasks:**
- [ ] Modify `gui/main_window.py`
  - [ ] Create three-panel layout:
    - [ ] Left: TrackListWidget
    - [ ] Center: MapWidget
    - [ ] Right: TrackpointListWidget

  - [ ] Connect signals:
    - [ ] track_selected (from TrackListWidget) → Load map + trackpoint list
    - [ ] trackpoint_selected (from TrackpointListWidget) → Highlight on map
    - [ ] point_clicked_on_map (from MapWidget) → Select in trackpoint list

  - [ ] Implement File → Open action
    - [ ] File dialog: Select GPX file
    - [ ] Load file using GPXHandler
    - [ ] Create TrackManager
    - [ ] Display tracks in list
    - [ ] Select first track (if available)

  - [ ] Update status bar with current info:
    - [ ] Points: [count]
    - [ ] Distance: [km]
    - [ ] Zoom: [Z level]

- [ ] Test manual workflow:
  - [ ] Open GPX file
  - [ ] Select track
  - [ ] See trackpoints on map and in list
  - [ ] Click trackpoint → highlight on map
  - [ ] Click marker on map → select in list

**Acceptance Criteria:**
- ✅ All three panels display correctly
- ✅ Opening GPX file loads data into all panels
- ✅ Selection synchronization works
- ✅ Status bar updates
- ✅ No errors during interactions
- ✅ UI responsive (< 200ms per action)

**Dependencies:**
- All previous components (TrackListWidget, TrackpointListWidget, MapWidget)
- GPXHandler, TrackManager

---

## PHASE 3: EDITING OPERATIONS

### Step 11: Rename Track Functionality

**Objective:** Allow user to rename tracks

**Tasks:**
- [ ] Create `gui/dialogs/rename_track_dialog.py`
  - [ ] Class `RenameTrackDialog(QDialog)`
  - [ ] Display current track name
  - [ ] Input field for new name
  - [ ] Validate: Not empty, max 100 chars
  - [ ] OK/Cancel buttons

  - [ ] Method: `get_new_name() -> str`
    - [ ] Return validated new name

- [ ] Implement rename in TrackManager
  - [ ] Method: `rename_track(track_index: int, new_name: str) -> bool`
    - [ ] Validate name
    - [ ] Update track.name
    - [ ] Set dirty = True
    - [ ] Trigger undo/redo stack (see Step 15)

- [ ] Connect to MainWindow
  - [ ] Edit menu: "Rename Track..." action
  - [ ] Context menu in TrackListWidget: "Rename"
  - [ ] Double-click in TrackListWidget for inline edit (optional)

  - [ ] Action implementation:
    - [ ] Get selected track
    - [ ] Open RenameTrackDialog
    - [ ] Call TrackManager.rename_track()
    - [ ] Update TrackListWidget display
    - [ ] Update window title if file modified

- [ ] Create unit tests `tests/test_rename_track.py`
  - [ ] Test rename with valid name
  - [ ] Test validation (empty, too long)
  - [ ] Test dirty flag

**Acceptance Criteria:**
- ✅ Dialog displays current track name
- ✅ Can input new name
- ✅ Validation prevents empty/too long names
- ✅ Track name updated in list
- ✅ Window title shows modification indicator (*)
- ✅ Dirty flag set

**Dependencies:**
- TrackManager
- TrackListWidget
- PyQt5 (QDialog)

---

### Step 12: Remove Individual Trackpoint

**Objective:** Delete selected trackpoint from track

**Tasks:**
- [ ] Implement in TrackManager
  - [ ] Method: `remove_trackpoint(track_index: int, point_index: int) -> bool`
    - [ ] Validate indices
    - [ ] Remove point from track
    - [ ] Recalculate distance
    - [ ] Set dirty = True
    - [ ] Trigger undo/redo stack

- [ ] Connect to MainWindow and TrackpointListWidget
  - [ ] Edit menu: "Delete Trackpoint" action
  - [ ] TrackpointListWidget context menu: "Delete"
  - [ ] Keyboard shortcut: Delete key

  - [ ] Action implementation:
    - [ ] Get selected trackpoint
    - [ ] Show confirmation dialog
    - [ ] Call TrackManager.remove_trackpoint()
    - [ ] Refresh trackpoint list
    - [ ] Refresh map display
    - [ ] Update track distance in list

- [ ] Create unit tests `tests/test_remove_trackpoint.py`
  - [ ] Test remove with valid index
  - [ ] Test with invalid index (no effect)
  - [ ] Test recalculation of distance
  - [ ] Test dirty flag

**Acceptance Criteria:**
- ✅ Confirmation dialog shows before deletion
- ✅ Trackpoint removed from list and map
- ✅ Distance recalculated
- ✅ Dirty flag set
- ✅ Cannot delete from empty track (error message)

**Dependencies:**
- TrackManager
- TrackpointListWidget, MapWidget
- PyQt5 (QMessageBox for confirmation)

---

### Step 13: Remove Trackpoints (Range Operations)

**Objective:** Delete trackpoint ranges (from start to position or position to end)

**Tasks:**
- [ ] Implement in TrackManager
  - [ ] Method: `remove_trackpoints_from_end(track_index: int, from_index: int) -> bool`
    - [ ] Delete points from `from_index` to end
    - [ ] Keep points before `from_index`
    - [ ] Recalculate distance
    - [ ] Set dirty = True

  - [ ] Method: `remove_trackpoints_from_start(track_index: int, to_index: int) -> bool`
    - [ ] Delete points from start to `to_index`
    - [ ] Keep points after `to_index`
    - [ ] Recalculate distance
    - [ ] Set dirty = True

- [ ] Connect to TrackpointListWidget
  - [ ] Context menu: "Delete from here to end"
  - [ ] Context menu: "Delete from start to here"

  - [ ] Action implementation:
    - [ ] Show confirmation with count of points to delete
    - [ ] Call appropriate TrackManager method
    - [ ] Refresh display

- [ ] Create unit tests `tests/test_remove_range.py`
  - [ ] Test remove from end
  - [ ] Test remove from start
  - [ ] Test with edge indices
  - [ ] Test distance recalculation

**Acceptance Criteria:**
- ✅ Confirmation shows how many points will be deleted
- ✅ Correct range deleted
- ✅ Map updates to show remaining track
- ✅ Distance recalculated correctly
- ✅ Dirty flag set

**Dependencies:**
- TrackManager
- TrackpointListWidget, MapWidget

---

### Step 14: Add Trackpoint Functionality

**Objective:** Add new trackpoints to track

**Tasks:**
- [ ] Create `gui/dialogs/add_trackpoint_dialog.py`
  - [ ] Class `AddTrackpointDialog(QDialog)`
  - [ ] Input fields:
    - [ ] Latitude (formatted per coordinate_format config)
    - [ ] Longitude (formatted per coordinate_format config)
    - [ ] Altitude (optional)
    - [ ] Insert position: "At end" or "At specific index"

  - [ ] Method: `get_trackpoint() -> tuple(lat, lon, alt, position)`
    - [ ] Parse and validate coordinates
    - [ ] Return as decimal degrees
    - [ ] Return position (index or "end")

- [ ] Implement in TrackManager
  - [ ] Method: `add_trackpoint(track_index: int, latitude: float, longitude: float, altitude: float = None, position: int = None) -> bool`
    - [ ] Validate coordinates
    - [ ] Create new trackpoint
    - [ ] Insert at position or append
    - [ ] Recalculate distance
    - [ ] Set dirty = True

- [ ] Implement map-based point addition
  - [ ] Button: "Add Point (Map Mode)"
  - [ ] When active: Crosshair cursor on map
  - [ ] Click map → Show confirmation dialog with coordinates
  - [ ] Confirm → Add point to track

- [ ] Connect to MainWindow
  - [ ] Edit menu: "Add Trackpoint..."
  - [ ] Toolbar button: "Add Point"
  - [ ] Both open AddTrackpointDialog or activate map mode

- [ ] Create unit tests `tests/test_add_trackpoint.py`
  - [ ] Test add with valid coordinates
  - [ ] Test validation (invalid coordinates)
  - [ ] Test insert at specific position
  - [ ] Test append to end
  - [ ] Test distance recalculation

**Acceptance Criteria:**
- ✅ Dialog opens and accepts input
- ✅ Coordinates validated
- ✅ Both DMS and decimal formats accepted
- ✅ Trackpoint added at correct position
- ✅ Map updates with new point
- ✅ Trackpoint list updates
- ✅ Distance recalculated
- ✅ Dirty flag set
- ✅ Map mode: Click on map adds point with confirmation

**Dependencies:**
- TrackManager
- coordinate_formatter
- TrackpointListWidget, MapWidget
- PyQt5 (QDialog)

---

## PHASE 4: UNDO/REDO SYSTEM

### Step 15: Command Pattern & History Stack

**Objective:** Implement reversible operations using Command Pattern

**Tasks:**
- [ ] Create `core/command_history.py`
  - [ ] Abstract class `Command`
    - [ ] Method: `execute()` - Perform the operation
    - [ ] Method: `undo()` - Reverse the operation
    - [ ] Property: `description` - Human-readable text for undo/redo menu

  - [ ] Concrete command classes:
    - [ ] `RenameTrackCommand(track_manager, track_index, old_name, new_name)`
    - [ ] `RemoveTrackpointCommand(track_manager, track_index, point_index, removed_point)`
    - [ ] `RemoveTrackpointRangeCommand(track_manager, track_index, start_index, end_index, removed_points)`
    - [ ] `AddTrackpointCommand(track_manager, track_index, latitude, longitude, altitude, position)`

  - [ ] Class `CommandHistory`
    - [ ] Stack for undo operations
    - [ ] Stack for redo operations
    - [ ] Method: `execute(command: Command) -> bool`
      - [ ] Run command.execute()
      - [ ] Add to undo stack
      - [ ] Clear redo stack
    - [ ] Method: `undo() -> bool`
      - [ ] Pop from undo stack
      - [ ] Run command.undo()
      - [ ] Push to redo stack
    - [ ] Method: `redo() -> bool`
      - [ ] Pop from redo stack
      - [ ] Run command.execute()
      - [ ] Push to undo stack
    - [ ] Method: `can_undo() -> bool`
    - [ ] Method: `can_redo() -> bool`
    - [ ] Method: `clear()` - Clear both stacks

- [ ] Create unit tests `tests/test_command_history.py`
  - [ ] Test command execution
  - [ ] Test undo/redo sequence
  - [ ] Test multiple operations
  - [ ] Test redo stack cleared on new operation

**Acceptance Criteria:**
- ✅ Commands execute and undo correctly
- ✅ Undo/redo stack behavior correct
- ✅ All unit tests pass

**Dependencies:**
- TrackManager (commands operate on it)

---

### Step 16: Integrate Undo/Redo into TrackManager

**Objective:** Replace direct operations with command-based operations

**Tasks:**
- [ ] Modify TrackManager
  - [ ] Constructor: `__init__(gpx_data: GPX, command_history: CommandHistory)`
  - [ ] Store command_history as instance variable

  - [ ] Modify all edit methods:
    - [ ] `rename_track()` → Create RenameTrackCommand, execute via history
    - [ ] `remove_trackpoint()` → Create RemoveTrackpointCommand, execute via history
    - [ ] `remove_trackpoints_from_end()` → Create RemoveTrackpointRangeCommand, execute via history
    - [ ] `remove_trackpoints_from_start()` → Create RemoveTrackpointRangeCommand, execute via history
    - [ ] `add_trackpoint()` → Create AddTrackpointCommand, execute via history

- [ ] Update MainWindow
  - [ ] Create CommandHistory instance
  - [ ] Pass to TrackManager constructor
  - [ ] Implement Edit → Undo action
  - [ ] Implement Edit → Redo action
  - [ ] Update toolbar buttons (enable/disable based on can_undo/can_redo)

- [ ] Create unit tests
  - [ ] Test undo after rename
  - [ ] Test undo after remove
  - [ ] Test undo after add
  - [ ] Test multiple undo/redo sequence

**Acceptance Criteria:**
- ✅ Edit → Undo works
- ✅ Edit → Redo works
- ✅ Toolbar buttons enable/disable correctly
- ✅ All previous operations are reversible
- ✅ UI reflects changes after undo/redo

**Dependencies:**
- CommandHistory (Step 15)
- TrackManager
- MainWindow

---

### Step 17: Keyboard Shortcuts & Menu Integration

**Objective:** Add keyboard shortcuts and ensure menu UI reflects undo/redo state

**Tasks:**
- [ ] Add keyboard shortcuts to MainWindow
  - [ ] Ctrl+Z → Undo
  - [ ] Ctrl+Y → Redo
  - [ ] Delete → Remove trackpoint
  - [ ] Ctrl+N → Add trackpoint
  - [ ] Ctrl+O → Open file
  - [ ] Ctrl+S → Save file

- [ ] Update Edit menu
  - [ ] "Undo" action shows: "Undo [operation]" when available
  - [ ] "Redo" action shows: "Redo [operation]" when available
  - [ ] Grayed out when not available

- [ ] Connect signals
  - [ ] CommandHistory → Signal when undo/redo state changes
  - [ ] MainWindow → Update menu/toolbar on signal

- [ ] Create unit tests (manual testing for UI)

**Acceptance Criteria:**
- ✅ Keyboard shortcuts work
- ✅ Undo/Redo menu items show correct operations
- ✅ Menu items grayed out appropriately
- ✅ Status bar shows hint on hover

**Dependencies:**
- MainWindow
- CommandHistory

---

## PHASE 5: FILE MANAGEMENT & REFINEMENT

### Step 18: Save GPX File Functionality

**Objective:** Write modified GPX back to file with Garmin compatibility

**Tasks:**
- [ ] Implement in `core/gpx_handler.py`
  - [ ] Method: `validate_garmin_compatibility(gpx_data: GPX) -> tuple(bool, list)`
    - [ ] Check all tracks have valid names
    - [ ] Check all trackpoints have valid lat/lon
    - [ ] Check for null bytes or encoding issues
    - [ ] Return: (is_valid, list_of_errors)

  - [ ] Method: `save_gpx(file_path: str, gpx_data: GPX, backup: bool = True) -> tuple(bool, str)`
    - [ ] If backup=True: Copy file to .bak
    - [ ] Validate Garmin compatibility
    - [ ] Write GPX with proper namespaces
    - [ ] Ensure proper XML formatting
    - [ ] Handle encoding: UTF-8
    - [ ] Return: (success, message)

- [ ] Implement in MainWindow
  - [ ] File → Save action
    - [ ] If file already open: Save to same path
    - [ ] Show status message: "Saving..."
    - [ ] On completion: "File saved successfully"
    - [ ] On error: Show error dialog

  - [ ] File → Save As action
    - [ ] File dialog: Select new path
    - [ ] Save to new path
    - [ ] Update window title with new filename

  - [ ] Close/Exit handling
    - [ ] If dirty: Ask "Save changes?"
    - [ ] Options: Save, Discard, Cancel

- [ ] Create unit tests `tests/test_gpx_save.py`
  - [ ] Test save to file
  - [ ] Test backup creation
  - [ ] Test Garmin compatibility validation
  - [ ] Test UTF-8 encoding with special characters

**Acceptance Criteria:**
- ✅ Save creates valid GPX file
- ✅ Backup file created (.bak)
- ✅ File contains proper Garmin namespaces
- ✅ Saved file can be opened again
- ✅ Coordinates preserved accurately
- ✅ Track names preserved
- ✅ Close without save prompts user

**Dependencies:**
- gpxpy
- GPXHandler
- coordinate_formatter

---

### Step 19: Garmin Import Testing & Validation

**Objective:** Verify exported files work on Garmin EchoMAP 50s

**Tasks:**
- [ ] Create documentation: `doc/GARMIN_IMPORT_GUIDE.md`
  - [ ] Step-by-step instructions for importing into Garmin device
  - [ ] Common issues and troubleshooting

- [ ] Manual testing workflow:
  - [ ] Export modified GPX from mangpx
  - [ ] Connect Garmin EchoMAP 50s to computer
  - [ ] Copy file to `/GARMIN/GPX/` directory
  - [ ] On device: Saved Tracks → Import from SD card
  - [ ] Verify track appears in Saved Tracks menu
  - [ ] Verify trackpoints are correct

- [ ] Create test GPX files for validation
  - [ ] Simple track (10 points)
  - [ ] Complex track (1000+ points)
  - [ ] Track with special characters in name
  - [ ] Track with altitude/timestamp data

- [ ] Document any issues and fixes in `doc/GARMIN_COMPATIBILITY_LOG.md`

**Acceptance Criteria:**
- ✅ Exported file imports successfully into Garmin
- ✅ Track appears in Saved Tracks menu
- ✅ Track data (name, points) correct on device
- ✅ No encoding or XML errors
- ✅ Documentation complete

**Dependencies:**
- Real Garmin EchoMAP 50s device
- USB cable and ability to access device SD card

---

### Step 20: Error Handling & User Feedback Refinement

**Objective:** Ensure all error cases handled gracefully

**Tasks:**
- [ ] Audit all file operations
  - [ ] File not found
  - [ ] Permission denied
  - [ ] Disk full
  - [ ] Invalid GPX format
  - [ ] Encoding errors

- [ ] Implement error dialogs
  - [ ] File errors: Show path + suggestion
  - [ ] Parsing errors: Show error details + recovery option
  - [ ] Validation errors: Show what's invalid

- [ ] Add logging
  - [ ] Create `utils/logger.py`
  - [ ] Log all operations to `mangpx.log`
  - [ ] Log level configurable (DEBUG, INFO, WARNING, ERROR, CRITICAL)

- [ ] Test error scenarios
  - [ ] Open non-existent file
  - [ ] Open corrupted GPX
  - [ ] Save to read-only directory
  - [ ] Load very large file (> 25 MB)

**Acceptance Criteria:**
- ✅ All error cases handled (no crashes)
- ✅ User gets helpful error messages
- ✅ Logging functional and useful
- ✅ Application never enters infinite loop
- ✅ All operations have timeout protection

**Dependencies:**
- PyQt5 (QMessageBox)
- Python logging module

---

### Step 21: Code Review & Documentation

**Objective:** Ensure code quality and completeness

**Tasks:**
- [ ] Code review checklist:
  - [ ] All functions have docstrings
  - [ ] All docstrings follow PEP 257
  - [ ] Complex logic has inline comments
  - [ ] Type hints on all function signatures
  - [ ] No hardcoded values (use config)
  - [ ] Error handling complete
  - [ ] No infinite loops

- [ ] Documentation:
  - [ ] Update `README.md` with project description
  - [ ] Create `doc/USER_GUIDE.md` with screenshots
  - [ ] Create `doc/DEVELOPER_GUIDE.md` for future contributors
  - [ ] Create `doc/CONFIGURATION_GUIDE.md`
  - [ ] Keep `doc/IMPLEMENTATION_NOTES.md` updated with decisions

- [ ] Verify requirements.txt
  - [ ] All dependencies listed with versions
  - [ ] Can recreate venv from requirements.txt

- [ ] Create setup.py for package distribution (optional)

**Acceptance Criteria:**
- ✅ All code properly documented
- ✅ README describes project and usage
- ✅ User guide complete with examples
- ✅ Requirements.txt up-to-date
- ✅ No TODO comments in code (all addressed)

**Dependencies:**
- Code review process

---

### Step 22: Testing & Validation

**Objective:** Ensure application is robust and production-ready

**Tasks:**
- [ ] Unit tests review
  - [ ] Run all tests with coverage
  - [ ] Aim for 80%+ coverage on core modules
  - [ ] All tests pass

- [ ] Integration tests
  - [ ] End-to-end workflow: Open → Modify → Save → Reopen
  - [ ] Undo/redo complex sequences
  - [ ] Large file handling (9,000+ points)

- [ ] Manual testing workflow
  - [ ] Create test GPX files with various scenarios
  - [ ] Test each feature in the specification
  - [ ] Test on different screen resolutions
  - [ ] Test with keyboard shortcuts
  - [ ] Test error scenarios

- [ ] Performance testing
  - [ ] Measure load time for large files
  - [ ] Measure map rendering latency
  - [ ] Verify no memory leaks

- [ ] Create test report in `doc/TEST_REPORT.md`

**Acceptance Criteria:**
- ✅ All unit tests pass (80%+ coverage)
- ✅ Integration tests successful
- ✅ Manual testing complete and documented
- ✅ No performance regressions
- ✅ Application ready for production use

**Dependencies:**
- pytest framework
- Test data and scenarios

---

### Step 23: Final Refinement & Deployment

**Objective:** Polish application and prepare for use

**Tasks:**
- [ ] UI Polish
  - [ ] Test on different screen sizes
  - [ ] Ensure layouts adapt (responsive)
  - [ ] Verify all buttons/icons visible
  - [ ] Test dark/light themes (if applicable)

- [ ] Performance optimization
  - [ ] Profile application with py-spy or similar
  - [ ] Optimize slow paths
  - [ ] Verify memory usage reasonable

- [ ] Create executable/package
  - [ ] PyInstaller or cx_Freeze for standalone executable
  - [ ] Test executable runs on clean system

- [ ] Create release notes in `doc/RELEASE_NOTES.md`
  - [ ] Features implemented
  - [ ] Known limitations
  - [ ] Future enhancements

- [ ] Update version number
  - [ ] Update `config/settings.ini` version
  - [ ] Update `setup.py` version
  - [ ] Tag git release (if using git)

**Acceptance Criteria:**
- ✅ UI polished and responsive
- ✅ Application performant
- ✅ Executable runs without dependencies
- ✅ Release notes complete
- ✅ Version numbers consistent

**Dependencies:**
- Testing infrastructure
- Build tools (PyInstaller, etc.)

---

## SUMMARY

**Total Steps:** 23  
**Phases:** 5  
**Estimated Duration:** 2-3 weeks of full-time development  

**Key Milestones:**
- ✅ Phase 1 (Steps 1-5): Foundation complete
- ✅ Phase 2 (Steps 6-10): Display complete
- ✅ Phase 3 (Steps 11-14): Editing complete
- ✅ Phase 4 (Steps 15-17): Undo/redo complete
- ✅ Phase 5 (Steps 18-23): Refinement complete

---

## PROGRESS TRACKING

Update this section after each step completion:

| Step | Status | Completed Date | Notes |
|------|--------|---|---|
| 1 | ✅ DONE | 2026-09-20 | All 8 tasks completed, 25/25 tests passing, 0 errors |
| 2 | ✅ DONE | 2026-09-20 | GPX handler + calculator, 28 new tests + 25 old tests passing (53/53 ✅) |
| 3 | ✅ DONE | 2026-09-20 | Coordinate formatter (DMS ↔ Decimal), 36 new tests (89/89 total ✅) |
| 4 | ✅ DONE | 2026-09-20 | Track manager, 72 tests passing (161 total ✅) |
| 5 | ✅ DONE | 2026-09-20 | PyQt5 skeleton, main window created |
| 6 | ✅ DONE | 2026-09-20 | Track list widget with full integration |
| 7 | ✅ DONE | 2026-09-20 | Trackpoint list widget with DMS/Decimal format toggle |
| 8 | ✅ DONE | 2026-09-20 | MBTiles provider (SQLite tile loading) |
| 9 | ✅ DONE | 2026-09-20 | Leaflet.js-based map widget (Leaflet integration) |
| 10 | ✅ DONE | 2026-09-20 | UI integration of all 3 panels + signal connections |
| 11 | ✅ DONE | 2026-09-20 | PIL-based map rendering (direct mbtiles, Leaflet → PIL migration) |
| 11.1 | ✅ DONE | 2026-09-20 | YAML Configuration Migration - hierarchical settings with persistence ✅ |
| 12 | ✅ DONE | 2026-09-20 | Remove trackpoint - 13 tests (85 total ✅), context menu, keyboard, range deletion, map update, index fix |
| 18 | ✅ DONE | 2026-09-20 | Save GPX file - Full implementation with backup, validation, Garmin compatibility ✅ |
| 13 | ⏳ TODO | | |
| ... | | | |

---

**END OF TODO LIST**
