# CourseStudio - GPX File Manipulator - SPECIFICATION DOCUMENT

**Project Name:** CourseStudio (GPX Manipulator)  
**Version:** 1.0 (Initial Specification)  
**Date:** 2026-09-20  
**Status:** Specification Approved  
**Framework:** PyQt5 (Python 3.10+)  

---

## 1. PROJECT OVERVIEW

### Purpose
A professional PyQt5-based GUI application for reading, visualizing, editing, and saving GPX files containing single or multiple navigation tracks with full undo/redo capability. The application is specifically designed to work with **Garmin EchoMAP 50s** and compatible marine navigation devices.

### Target User
Navigation professionals, marine enthusiasts, and GPS data managers who need to:
- Inspect GPX file content before importing to Garmin devices
- Modify navigation tracks (rename, add/remove waypoints)
- Clean corrupted or redundant trackpoints
- Export Garmin-compatible GPX files

### Core Design Principle
User-friendly interface with clear feedback. All operations must be reversible via undo/redo. Code must be well-commented and understandable to non-experts.

---

## 2. FUNCTIONAL REQUIREMENTS

### 2.1 File Management

**Requirement:** Open and save GPX files

**Detailed Behaviors:**
- Open single GPX file via file dialog
- Detect and parse tracks/routes/waypoints
- Display loading status with progress indicator
- Save modified GPX file to original or new location
- Support Garmin-format GPX with proper namespace declarations
- Backup original file before saving (optional, configurable)

**Constraints:**
- File size limit: Up to 25 MB (typical Garmin device exports)
- Format: GPX 1.1 with Garmin extensions
- Encoding: UTF-8

---

### 2.2 Track Information Display

**Requirement:** Show summary of all tracks in opened file

**Information Displayed:**
- Track name (or "Unnamed Track" if missing)
- Total distance in km (calculated from trackpoints)
- Number of trackpoints
- Garmin-specific metadata (if present)

**UI Component:**
- Scrollable list/table view
- Single-click selection (highlights selected track)
- Double-click to rename track (inline editing)
- Right-click context menu for operations

**Data Update:**
- Automatically recalculate distance when trackpoints are modified
- Update point count in real-time

---

### 2.3 Trackpoint Details View

**Requirement:** Display all trackpoints for selected track with individual coordinate display

**Information Per Trackpoint:**
- Sequence number (index, 1-based)
- Latitude (in configured format: DMS or decimal degrees)
- Longitude (in configured format: DMS or decimal degrees)
- Altitude (if available in GPX file)
- Timestamp (if available in GPX file)

**UI Component:**
- Scrollable list with large item count support (9,000+ points)
- Column headers with sort capability (optional for later)
- Selection highlighting (selected point highlighted in map)
- Keyboard navigation support
- Right-click context menu for deletion/insertion

**Performance:**
- Must handle 9,000+ points without UI freeze
- Lazy loading/pagination for very large tracks (implement in Phase 3 if needed)

---

### 2.4 Map Visualization

**Requirement:** Display selected track on interactive map with trackpoint markers

**Map Features:**
- Render track path as line on map
- Show all trackpoints as interactive markers
- Support pan and zoom using mouse/trackpad
- Display zoom level indicator
- Support zoom levels Z10-Z16 (from mbtiles)

**Trackpoint Visualization:**
- Regular trackpoints: Small blue circles
- Selected trackpoint: Large red circle or highlighted marker
- Hover tooltip showing coordinate

**Map Interaction:**
- Click on trackpoint in list → highlight on map
- Click on marker on map → select in list
- Zoom to fit entire track button
- Zoom to selected point button

**Data Source:**
- Use Sweden-Raster-Z10-Z16.mbtiles by default
- Fallback to OSM-OpenCPN2-Baltic.mbtiles if available
- Display tile attribution in corner

---

### 2.5 Track Editing Operations

**Requirement:** Modify track content (names, trackpoints)

#### 2.5.1 Rename Track
- Click track name in list → inline edit mode
- Enter new name → press Enter to confirm, Escape to cancel
- Name validation (no empty names, max 100 characters)
- Support special characters (Garmin compatible)

#### 2.5.2 Add Trackpoint
Two methods:

**Method A: Click on Map**
- Button: "Add Point" mode toggle
- When active: Click map to add point at coordinates
- Visual feedback: Crosshair cursor, confirmation dialog
- Ask user to confirm lat/lon before adding

**Method B: Manual Entry**
- Dialog: "Add Trackpoint" with coordinate input fields
- Input format: Current coordinate format (DMS or decimal)
- Validate coordinates before adding
- Option to insert at specific position or append to end

#### 2.5.3 Remove Individual Trackpoint
- Right-click trackpoint in list → "Delete"
- Select trackpoint on map → press Delete key
- Confirmation dialog before deletion

#### 2.5.4 Remove Trackpoints from Position to End
- Right-click trackpoint in list → "Delete from here to end"
- Confirmation: "Delete X trackpoints (from index N to end)?"
- Updates track distance and point count

#### 2.5.5 Remove Trackpoints from Start to Position
- Right-click trackpoint in list → "Delete from start to here"
- Confirmation: "Delete X trackpoints (from start to index N)?"
- Keep selected point or discard it? → User choice
- Updates track distance and point count

#### 2.5.6 Auto-Recalculation
- After any trackpoint edit: Recalculate distance
- Update track summary in list view
- Refresh map visualization

---

### 2.6 Undo/Redo System

**Requirement:** Reverse or reapply any edit operation

**Supported Operations:**
- Rename track
- Add trackpoint
- Remove trackpoint(s)
- Delete from position to end
- Delete from start to position

**Undo/Redo Features:**
- Unlimited undo/redo stack (within memory limits)
- Menu bar: Edit → Undo (Ctrl+Z), Edit → Redo (Ctrl+Y)
- Toolbar buttons: Undo, Redo (disabled when no action available)
- Status bar shows undo/redo availability
- Clear history on file open or file save (optional: prompt user)

**Implementation:**
- Command Pattern: Each operation creates reversible command object
- Stack-based history management
- Memory efficient: Store minimal state change data

---

## 3. NON-FUNCTIONAL REQUIREMENTS

### 3.1 Technical Stack

| Component | Specification |
|-----------|---|
| Language | Python 3.10+ |
| GUI Framework | PyQt5 |
| GPX Parsing | `gpxpy` library |
| Map Rendering | PyQtWebEngine or matplotlib |
| mbtiles Access | `mbtiles` library |
| Testing | `pytest` |
| Code Style | PEP 8 |

### 3.2 Project Structure

```
CourseStudio/
├── src/
│   ├── __init__.py
│   ├── main.py                    # Application entry point
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py         # Main PyQt5 application window
│   │   ├── widgets/
│   │   │   ├── __init__.py
│   │   │   ├── track_list.py      # Track information widget
│   │   │   ├── trackpoint_list.py # Trackpoint details widget
│   │   │   └── map_widget.py      # Map display widget
│   │   └── dialogs/
│   │       ├── __init__.py
│   │       ├── add_trackpoint_dialog.py
│   │       ├── rename_track_dialog.py
│   │       └── confirmation_dialogs.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── gpx_handler.py         # GPX file read/write/validation
│   │   ├── track_manager.py       # Track operations & edit history
│   │   ├── command_history.py     # Undo/redo command stack
│   │   └── calculator.py          # Distance, coordinate conversions
│   ├── map/
│   │   ├── __init__.py
│   │   ├── mbtiles_provider.py    # mbtiles tile loading
│   │   └── map_renderer.py        # Map rendering logic
│   └── utils/
│       ├── __init__.py
│       ├── coordinate_formatter.py # DMS/Decimal conversion
│       └── logger.py              # Logging setup
├── config/
│   ├── __init__.py
│   ├── constants.py               # Application constants
│   ├── app_config.py              # Configuration management
│   └── settings.ini               # Default settings file
├── tests/
│   ├── __init__.py
│   ├── test_gpx_handler.py
│   ├── test_track_manager.py
│   ├── test_calculator.py
│   └── test_coordinate_formatter.py
├── doc/
│   ├── PROJECT_SPECIFICATION.md   # This file
│   ├── TODO_LIST.md               # Development tasks
│   ├── IMPLEMENTATION_NOTES.md    # Design decisions
│   └── USER_GUIDE.md              # User documentation (Phase 5)
├── mbtiles/                       # Map tile files
├── images/                        # UI assets
├── venv/                          # Python virtual environment
├── requirements.txt               # Python dependencies
├── setup.py                       # Package setup
└── README.md                      # Project overview
```

### 3.3 Code Quality Standards

**Documentation:**
- Every function/method: Full docstring (PEP 257)
- Complex algorithms: Inline comments explaining logic
- Class attributes: Type hints + documentation
- Public API: Clear parameter/return documentation

**Example Docstring Format:**
```python
def convert_dms_to_decimal(degrees: int, minutes: int, seconds: float, direction: str) -> float:
    """
    Convert DMS (Degrees-Minutes-Seconds) coordinates to decimal degrees.
    
    Args:
        degrees (int): Degree component (0-360)
        minutes (int): Minute component (0-59)
        seconds (float): Second component (0-59.999)
        direction (str): Cardinal direction ('N', 'S', 'E', 'W')
    
    Returns:
        float: Decimal degree value (-180 to 180)
    
    Raises:
        ValueError: If components are outside valid ranges
    
    Example:
        >>> convert_dms_to_decimal(57, 30, 45.5, 'N')
        57.5126...
    """
```

**Error Handling:**
- All file I/O operations: Try-catch with user-friendly error messages
- User input validation: Validate before processing, show error dialogs
- No silent failures: Always inform user of errors
- Logging: All errors logged to file + displayed to user

**Testing:**
- Every module has unit tests in `tests/` directory
- Test coverage: Minimum 80% for core modules
- All tests include timeout to prevent infinite loops
- Tests use fixtures for common data (sample GPX files, mock data)

**No Infinite Loops:**
- Use timeout decorators for operations with loops
- Implement loop counters with safety limits
- Use generators for large data processing where possible

---

## 4. CONFIGURATION MANAGEMENT

### 4.1 Configuration File: `config/settings.ini`

**Purpose:** Store user preferences and application settings

**Default Configuration:**
```ini
[Application]
# Application name (used in window title, about dialog)
app_name = CourseStudio

# Application version
version = 1.0.0

[Map]
# Default mbtiles file to use
default_mbtiles = Sweden-Raster-Z10-Z16.mbtiles

# Fallback mbtiles files (comma-separated)
fallback_mbtiles = OSM-OpenCPN2-Baltic.mbtiles,OSM-OpenCPN-Baltic.mbtiles

# Initial zoom level when loading track
initial_zoom_level = 13

[Coordinates]
# Format for displaying coordinates: 'dms' or 'decimal'
# dms = Degrees-Minutes-Seconds (°-'-''), e.g., 57°30'45.5"N
# decimal = Decimal degrees, e.g., 57.5126°N
coordinate_format = dms

[File]
# Create backup of original file before saving
create_backup = true

# Backup file extension
backup_extension = .bak

[UI]
# Window size on startup (width x height)
window_width = 1400
window_height = 900

# Remember last opened file directory
remember_last_directory = true

[Performance]
# Maximum trackpoints to display without pagination warning
max_trackpoints_no_warning = 5000

# Maximum file size to load without warning (MB)
max_file_size_warning = 25

[Logging]
# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
log_level = INFO

# Log file location
log_file = ./CourseStudio.log
```

### 4.2 Configuration Access

**Implementation:** `config/app_config.py`

```python
class AppConfig:
    """
    Manages application configuration from settings.ini file.
    
    Provides thread-safe access to configuration values with
    type conversion and default fallbacks.
    """
    
    def __init__(self, config_file: str = 'config/settings.ini'):
        """Load configuration from file."""
        
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get configuration value with type inference."""
        
    def get_int(self, section: str, key: str, default: int = 0) -> int:
        """Get integer configuration value."""
        
    def get_bool(self, section: str, key: str, default: bool = False) -> bool:
        """Get boolean configuration value."""
        
    def get_float(self, section: str, key: str, default: float = 0.0) -> float:
        """Get float configuration value."""
```

### 4.3 Usage in Application

All references to configurable values must use `AppConfig`:

```python
# Instead of: mbtiles_path = "Sweden-Raster-Z10-Z16.mbtiles"
# Use:
config = AppConfig()
mbtiles_path = config.get('Map', 'default_mbtiles')

# Instead of: coordinate_format = "dms"
# Use:
coord_format = config.get('Coordinates', 'coordinate_format')
```

---

## 5. GARMIN COMPATIBILITY

### 5.1 GPX Format Requirements

**For successful import into Garmin EchoMAP 50s:**

1. **XML Declaration:**
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   ```

2. **Garmin Namespaces (Required):**
   ```xml
   <gpx xmlns="http://www.topografix.com/GPX/1/1"
        xmlns:gpxx="http://www.garmin.com/xmlschemas/GpxExtensions/v3"
        xmlns:wptx1="http://www.garmin.com/xmlschemas/WaypointExtension/v1"
        xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
   ```

3. **Metadata Block:**
   ```xml
   <metadata>
     <link href="http://www.garmin.com">
       <text>Garmin</text>
     </link>
   </metadata>
   ```

4. **Track Structure:**
   - One `<trk>` element per track
   - Clean `<trkseg>` with only `<trkpt lat="" lon=""/>` elements
   - No corrupted metadata or null bytes

### 5.2 Export Validation

**Before saving, validate that:**
- ✅ All required namespaces are present
- ✅ Track names are valid (no invalid XML characters)
- ✅ Trackpoints have valid latitude/longitude
- ✅ No null bytes or encoding issues
- ✅ XML structure is well-formed

**Validation performed by:** `gpx_handler.validate_garmin_compatibility()`

### 5.3 Import Process (User Workflow)

1. User modifies track in CourseStudio
2. User saves file (with validation)
3. File is written to Garmin-compatible format
4. User transfers file to Garmin device:
   - Connect Garmin EchoMAP 50s via USB
   - Copy file to `/GARMIN/GPX/` directory
   - On device: Saved Tracks → Import from SD card
   - Select file → Track appears in Saved Tracks menu

---

## 6. COORDINATE FORMAT HANDLING

### 6.1 Supported Formats

**Format 1: DMS (Degrees-Minutes-Seconds) - DEFAULT**
- Display: `57°30'45.5"N`
- Display: `12°15'30.2"E`
- Parsing: Support multiple delimiters (°, °, d; ', '; ", ")
- Internal: Store as separate degree/minute/second values

**Format 2: Decimal Degrees**
- Display: `57.5126°N`
- Display: `12.2584°E`
- Internal: Store as single float value

### 6.2 Conversion Functions

**Module:** `utils/coordinate_formatter.py`

```python
def decimal_to_dms(decimal: float, is_longitude: bool = False) -> tuple:
    """
    Convert decimal degrees to DMS components.
    
    Returns: (degrees, minutes, seconds, direction)
    """

def dms_to_decimal(degrees: int, minutes: int, seconds: float, 
                   direction: str) -> float:
    """
    Convert DMS components to decimal degrees.
    
    Returns: decimal degree value
    """

def format_coordinate(value: float, is_longitude: bool = False, 
                     format_type: str = 'dms') -> str:
    """
    Format coordinate value for display.
    
    format_type: 'dms' or 'decimal'
    Returns: Formatted string (e.g., "57°30'45.5"N")
    """

def parse_coordinate(coord_string: str) -> float:
    """
    Parse coordinate from string (DMS or decimal).
    
    Auto-detects format and returns decimal degrees.
    """
```

### 6.3 Configuration Integration

**User changes coordinate format:**
1. Menu: View → Coordinate Format
2. Select: DMS or Decimal
3. Application updates `settings.ini`
4. All coordinate displays refresh immediately
5. Input fields accept both formats regardless of display format

---

## 7. USER INTERFACE LAYOUT

### 7.1 Main Window Structure

```
┌─────────────────────────────────────────────────────────────────────────┐
│ CourseStudio - GPX File Manipulator [File Name]                          _ □ X│
├─────────────────────────────────────────────────────────────────────────┤
│ File  Edit  View  Help                                                  │
├─────────────────────────────────────────────────────────────────────────┤
│ [Open] [Save] [Save As] │ [Undo] [Redo] │ [Add Point] [Delete] │ [Help]│
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─ TRACKS (Left Panel) ──────────┬─ MAP (Center Panel) ──────────────┐ │
│  │ Track Name    Dist    Points    │                                  │ │
│  │ ─────────────────────────────── │                                  │ │
│  │ KARLSKRONA-H  19.12   519       │         [Map Visualization]      │ │
│  │ TR-HALLARUM   25.5    1787      │         with trackpoints         │ │
│  │               Zoom: Z13  [↗]    │         and selected track       │ │
│  │                                 │                                  │ │
│  ├─ TRACKPOINTS (Right Panel) ────┤                                  │ │
│  │ Sequence  Latitude      Longitude│                                  │ │
│  │ ────────────────────────────────│                                  │ │
│  │ 1     57°30'45.5"N   12°15'30.2"E│                                  │ │
│  │ 2     57°30'46.1"N   12°15'31.5"E│  [Zoom Fit] [Zoom Point]       │ │
│  │ 3     57°30'47.2"N   12°15'33.1"E│                                  │ │
│  │ ...                              │                                  │ │
│  │ [Scroll down for more points]    │                                  │ │
│  └──────────────────────────────────┴──────────────────────────────────┘ │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│ Ready | Points: 519 | Distance: 19.12 km | Format: DMS | Zoom: Z13     │
└──────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Menu Structure

**File Menu:**
- Open... (Ctrl+O)
- Save (Ctrl+S)
- Save As... (Ctrl+Shift+S)
- Recent Files (submenu)
- Close
- Exit (Ctrl+Q)

**Edit Menu:**
- Undo (Ctrl+Z)
- Redo (Ctrl+Y)
- ─────────
- Add Trackpoint (Ctrl+N)
- Delete Trackpoint (Delete)
- ─────────
- Rename Track...

**View Menu:**
- Coordinate Format → DMS (radio) / Decimal (radio)
- Map Controls → Pan / Zoom / Fit
- ─────────
- Zoom In (Ctrl++)
- Zoom Out (Ctrl+-)
- Fit Track (Ctrl+0)
- ─────────
- Refresh (Ctrl+R)

**Help Menu:**
- About CourseStudio
- User Guide
- Keyboard Shortcuts
- Report Bug

---

## 8. ERROR HANDLING & USER FEEDBACK

### 8.1 Error Categories

| Category | Example | User Feedback |
|----------|---------|---|
| File Errors | File not found, permission denied | Error dialog with path + suggestion |
| Parsing Errors | Invalid GPX, corrupt XML | Error dialog + line number + recovery option |
| Validation Errors | Invalid coordinates, empty track name | Input validation message in dialog |
| Map Errors | mbtiles not found, rendering failed | Warning dialog + fallback option |
| Operation Errors | Delete from empty track, undo on empty stack | Status bar message (non-blocking) |

### 8.2 User Feedback Methods

1. **Blocking Dialogs:** File errors, validation errors (require user action)
2. **Status Bar Messages:** Operation feedback, non-blocking (auto-hide after 5s)
3. **Toast Notifications:** Quick confirmations (optional, Phase 2+)
4. **Log File:** All errors logged to `CourseStudio.log` for debugging

---

## 9. PERFORMANCE CONSTRAINTS

| Constraint | Limit | Handling |
|-----------|-------|----------|
| Max trackpoints per track | 100,000 | Lazy load / pagination in Phase 3 |
| Max file size | 25 MB | Warn user on load, proceed on confirmation |
| Map pan/zoom latency | < 200ms | Use threaded tile loading |
| Undo/redo stack size | Unlimited | Limit to 50 operations if memory exceeds 500MB |
| Startup time | < 3 seconds | Lazy load mbtiles on first map use |

---

## 10. TESTING STRATEGY

### 10.1 Unit Tests

**Test Files:**
- `tests/test_gpx_handler.py` - GPX parsing/writing
- `tests/test_track_manager.py` - Track operations & undo/redo
- `tests/test_calculator.py` - Distance/coordinate calculations
- `tests/test_coordinate_formatter.py` - DMS/decimal conversions

**Test Data:**
- Sample GPX files in `tests/fixtures/` directory
- Garmin-format GPX files
- Edge cases: empty tracks, missing coordinates, special characters

### 10.2 Integration Tests (Phase 4+)

- Open file → Display tracks → Modify → Save → Verify
- Undo/redo sequences
- Map rendering with real mbtiles data

### 10.3 Manual Testing (Phase 5)

- Import saved files into actual Garmin EchoMAP 50s
- Verify tracks appear in Saved Tracks menu
- Test on Windows, Linux, macOS if applicable

---

## 11. DEVELOPMENT PHASES & MILESTONES

| Phase | Focus | Deliverable |
|-------|-------|---|
| **Phase 1** | Core GPX handling + UI skeleton | Open/save GPX, basic window layout |
| **Phase 2** | Track info + map display | Track list, trackpoint list, map rendering |
| **Phase 3** | Edit operations | Add/remove trackpoints, rename tracks |
| **Phase 4** | Undo/redo system | Command-based history management |
| **Phase 5** | Refinement | Testing, documentation, polish |

---

## 12. SUCCESS CRITERIA

**Application is complete when:**

✅ Open GPX file with multiple tracks  
✅ Display track names, distances, point counts  
✅ Show all trackpoints with coordinates (DMS/decimal)  
✅ Render track on map with zoom/pan control  
✅ Add, remove, delete trackpoints individually  
✅ Remove trackpoints from position to end or start to position  
✅ Rename tracks  
✅ Undo/redo all operations  
✅ Save modified GPX with Garmin compatibility  
✅ Verify export into actual Garmin EchoMAP 50s device  
✅ All code well-commented and tested  
✅ No infinite loops or UI freezes  
✅ Configuration file supports app customization  

---

## 13. MAP CENTER AND ZOOM MANAGEMENT

### 13.1 Three Levels of Center/Zoom State

The application manages three separate center/zoom values:

#### Level 1: mbtiles_center / mbtiles_zoom
**Stored:** In the mbtiles file metadata (immutable by user directly)
**Purpose:** The tileset's recommended default position
**Format:** Metadata fields `center` (format: "lon,lat,zoom") and individual zoom fields
**Lifecycle:**
- Read from mbtiles file when loaded
- Used to initialize both current_center/current_zoom AND default_center/default_zoom
- Updated to current position when user clicks "Update" button next to "Default Center" field
- Written back to the mbtiles file metadata

#### Level 2: default_center / default_zoom
**Stored:** In `settings.yaml` under `appearance.tiles`
**Purpose:** User's saved "home" position for manual recenter
**Configuration Keys:**
- `appearance.tiles.default_center.lat`
- `appearance.tiles.default_center.lon`
- `appearance.tiles.default_zoom`
**Lifecycle:**
- Initialized from mbtiles_center/mbtiles_zoom on app startup or mbtiles load
- Updated when user clicks "Mark Center" button (sets to current position)
- Used when user clicks "Recenter" button (navigates to this position + zoom)
- Updated when user clicks "Update" button (takes mbtiles_center/zoom and stores here)

#### Level 3: recent_center / recent_zoom
**Stored:** In `settings.yaml` under `appearance.tiles`
**Purpose:** Preserve user's last viewed position across app restarts
**Configuration Keys:**
- `appearance.tiles.recent_center.lat`
- `appearance.tiles.recent_center.lon`
- `appearance.tiles.recent_zoom`
**Lifecycle:**
- Auto-updated whenever user pans or zooms the map
- Persisted to `settings.yaml` after each navigation
- Used on app restart to restore map to last position
- Fallback: If recent_center/zoom unavailable, use default_center/zoom

### 13.2 Initialization Sequence

**Scenario A: App Startup**
1. Load mbtiles file (from `appearance.tiles.recent_mbtiles` in settings.yaml)
2. Read `mbtiles_center` and `mbtiles_zoom` from file metadata
3. Set `current_center = mbtiles_center`, `current_zoom = mbtiles_zoom`
4. Set `default_center = mbtiles_center`, `default_zoom = mbtiles_zoom`
5. If mbtiles doesn't have center/zoom metadata:
   - Find lowest existing zoom level in mbtiles
   - Find an existing tile at that zoom level
   - Randomly select a position within that tile
   - Use as mbtiles_center and mbtiles_zoom
   - Set both current_center/zoom and default_center/zoom to this position

**Scenario B: User Loads New MBTiles**
- Same as Scenario A: Read mbtiles metadata and reinitialize both center/zoom values

**Scenario C: App Restart (After User Sessions)**
1. Load mbtiles file
2. Initialize center/zoom as per Scenario A
3. Override with `recent_center/recent_zoom` from settings.yaml (user's last position)
   - Only override if both recent values exist
   - Clamp zoom to valid range for loaded mbtiles

### 13.3 User Actions and State Updates

| User Action | Effect on mbtiles_center | Effect on default_center | Effect on recent_center |
|-------------|-------------------------|------------------------|----------------------|
| **Pan/Zoom map** | No change | No change | Update automatically |
| **Click "Mark Center"** | No change | Update to current | Update automatically |
| **Click "Recenter"** | No change | No change (go to it) | Update to default_zoom/center |
| **Click "Update" button** | Update with current | Update with current | Update automatically |

### 13.4 Button Behaviors

#### "Mark Center" Button
- **Action:** Saves current map position as the "home" position
- **Updates:** `default_center` and `default_zoom` in settings.yaml
- **Visual Feedback:** Confirmation message or status bar update
- **Storage:** Persists to settings.yaml immediately

#### "Recenter" Button
- **Action:** Navigate map to saved "home" position
- **Navigates to:** `default_center` with `default_zoom`
- **Effect on recent_center:** Updates to default_center (user is now viewing that position)
- **Effect on recent_zoom:** Updates to default_zoom

#### "Update" Button (next to "Default Center" field)
- **Action:** Save current viewing position to mbtiles and settings
- **Updates mbtiles file:**
  - Write current_center.lon and current_center.lat to metadata `center` field
  - Write current_zoom to metadata zoom field
- **Updates settings.yaml:**
  - Update `default_center.lat`, `default_center.lon`, `default_zoom`
- **Confirmation:** Show confirmation that mbtiles file was updated
- **Persistence:** Both mbtiles file and settings.yaml saved immediately

### 13.5 Fallback Strategy (When mbtiles_center/zoom Missing)

If the mbtiles file doesn't contain center/zoom metadata:

1. Query the `tiles` table to find available zoom levels
2. Select the LOWEST available zoom level (Z_min)
3. Query for ANY existing tile at Z_min
   - SELECT one tile with zoom_level = Z_min
4. Calculate the geographic bounds of that tile (using Web Mercator inverse)
5. Generate random coordinates within that tile's bounds
6. Use that position as mbtiles_center and mbtiles_zoom
7. Set both current_center/zoom and default_center/zoom to this position

**Rationale:** Ensures user sees a valid position from the tileset, no matter what zoom levels are available.

### 13.6 Configuration Storage Format

**In mbtiles file (metadata table):**
```
center = "15.591959953308105,56.16647275741994,15"
```
Format: comma-separated `longitude,latitude,zoom` (same as MBTiles spec)

**In settings.yaml:**
```yaml
appearance:
  tiles:
    recent_mbtiles: Sweeden-Z6-Z15.mbtiles
    recent_center:
      lat: 56.16647275741994
      lon: 15.591959953308105
    recent_zoom: 15
    default_center:
      lat: 56.16647275741994
      lon: 15.591959953308105
    default_zoom: 15
```

### 13.7 Implementation Checklist

- [ ] Add `mbtiles_center` and `mbtiles_zoom` as distinct from `default_center/zoom`
- [ ] Extract center/zoom from mbtiles metadata on file load
- [ ] Implement fallback strategy for missing center/zoom in mbtiles
- [ ] Initialize both current and default from mbtiles on startup
- [ ] Auto-update recent_center/zoom on every pan/zoom action
- [ ] Implement "Mark Center" button → updates default_center/zoom
- [ ] Implement "Recenter" button → navigates to default_center/zoom
- [ ] Implement "Update" button → writes to mbtiles + updates default_center/zoom
- [ ] Validate zoom levels are within mbtiles min/max range
- [ ] Clamp zoom on app restart if recent_zoom exceeds mbtiles limits
- [ ] Test initialization with and without center/zoom in mbtiles metadata
- [ ] Test app restart: recent_center/zoom are restored correctly
- [ ] Test loading new mbtiles: center/zoom properly reinitialized

---

**END OF SPECIFICATION DOCUMENT**
