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

#### 2.5.7 Prune Trackpoints by Distance
**Requirement:** Remove trackpoints that are closer than configured minimum distance

**Purpose:**
Remove redundant 'close' trackpoints from tracks while maintaining proper geographic spacing. 
Useful for cleaning up dense GPS recordings or merging multiple track segments with excessive detail.

**Algorithm:**
The pruning algorithm uses a reference-point approach:
1. Start with first trackpoint as 'reference_point'
2. Calculate cumulative distance to next trackpoint
3. If distance < minimum threshold:
   - Remove the next trackpoint (too close)
   - Keep reference unchanged
   - Accumulate distance to next-next point
4. If distance >= minimum threshold:
   - Keep the next trackpoint
   - Make it new reference_point
   - Reset accumulated distance
5. Stop when reference is second-to-last point (preserve end point)

**Configuration:**
- Setting: `performance.prune_points.min_distance_m` (default: 50 meters)
- User can modify in `config/settings.yaml`
- Applied per-track when user clicks button

**UI:**
- Button: "Prune Points" (next to "Clear Selection" in TrackEditor tab)
- Available only when a track is selected
- Shows progress dialog during pruning with:
  - Real-time progress bar (points processed / total points)
  - Statistics: removed count, kept count, processed count
  - Status messages showing progress
  - Cancel button to stop pruning (changes are not reverted)
- Results shown in status bar: "Pruned X point(s)" or "No points pruned"
- Dialog auto-closes after 2 seconds on success

**Implementation:**
- Runs in background thread (PruneWorker) to keep UI responsive
- Uses progress callbacks for real-time updates
- Supports cancellation via `worker.cancel()`
- Updates track list, trackpoint list, and map after completion
- Marks track as dirty (unsaved changes)

**Icons:**
- Button icon: Blue circle with slash (clear/deselect concept)
- Indicates removal/filtering of trackpoints

**Example:**
```
Track: P1 --5m-- P2 --15m-- P3 --30m-- P4 (min_distance=50m)

Step 1: ref=P1, next=P2, dist=5m < 50m    → Remove P2
Step 2: ref=P1, next=P3, dist=20m < 50m   → Remove P3
Step 3: ref=P1, next=P4, dist=50m >= 50m  → Keep P4, ref=P4
Result: P1 --50m-- P4
```

**Distance Calculation:**
- Uses Haversine formula for accurate great-circle distance
- Handles Earth's curvature correctly
- Results in meters

**Side Effects:**
- Modifies track.trackpoints list
- Recalculates track.distance_km
- Updates track list display (distance and point count)
- Marks track as dirty (unsaved changes)
- Does NOT support undo/redo (changes are permanent)

**Constraints:**
- Requires minimum 3 trackpoints (can't prune if only 2 remain)
- Always preserves first and last trackpoints
- Cannot remove end point
- Cancellation stops pruning but keeps changes made so far

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

### 2.7 MBTiles File Management

**Requirement:** Load and manage MBTiles map tile files

**Behaviors:**
- User can open MBTiles file via "File → Open MBTiles File"
- Map loads and displays with crosshair cursor for trackpoint insertion
- User can close MBTiles file via "File → Close MBTiles File"
- When closing: GPX file automatically closes as well (both files together)
- Closing warns about unsaved GPX changes
- Status bar shows current MBTiles filename at all times

**Constraints:**
- MBTiles file is **required** for any map display or trackpoint operations
- Cannot open GPX file without MBTiles loaded (shows error dialog)
- Cannot insert trackpoints without MBTiles loaded (shows error dialog)

---

### 2.8 GPX File Requirements

**Requirement:** Enforce MBTiles prerequisite for GPX file operations

**Behaviors:**
- "Open GPX File" action is **disabled** when no MBTiles loaded
- Clicking "Open GPX File" when MBTiles not loaded shows error: "Please load MBTiles file first"
- Once MBTiles loaded, "Open GPX File" becomes enabled
- Status bar shows current GPX filename when loaded

**Rationale:** 
- GPX files contain tracks that must be displayed on maps
- Cannot display tracks without map tiles
- Prevents confusing state: GPX open but no map visible

---

### 2.9 Trackpoint Insertion

**Requirement:** Insert trackpoints only when map is available

**Behaviors:**
- Crosshair cursor appears only when MBTiles loaded and crosshair enabled
- Shift+click to insert trackpoint at map location (only when MBTiles loaded)
- If user attempts Shift+click without MBTiles loaded: Error dialog shows "Cannot insert trackpoint - MBTiles file required"
- Trackpoint appears immediately on map
- Trackpoint added to selected track's trackpoint list
- Track distance and point count update automatically

**Implementation:**
- Check `mbtiles_provider.is_loaded()` before processing Shift+click
- Guard check at line ~1147 and ~1206 in map_widget.py

---

### 2.10 Crosshair Display Logic

**Requirement:** Show/hide crosshair based on MBTiles file state and user preference

**Behaviors:**
- **At app startup:** Crosshair hidden (no MBTiles loaded yet)
- **When MBTiles loaded:** Crosshair becomes visible (if user has enabled it in config)
- **When MBTiles closed:** Crosshair hidden immediately
- **User preference:** Crosshair enable/disable setting stored in config and honored when file loads
- **Enable mechanism:** `enable_crosshair()` method checks if MBTiles actually loaded before rendering

**Implementation:**
- `show_crosshair` boolean flag: Starts False, only enabled when mbtiles_provider.is_loaded()
- `crosshair_enabled_in_config` stores user's config preference
- enable_crosshair() calls render_map() immediately for instant display
- clear_map() sets show_crosshair = False when files close

**Defense in Depth:**
- Multiple guard layers prevent bugs (initialization order, resource check, render call)
- Configuration preference preserved but not applied until resource available

---

### 2.11 Status Bar Layout and Information Display

**Requirement:** Display file information and status messages without visual flicker or overlap

**Status Bar Structure:**
```
[Position 1: Tooltips/Temporary Messages] | [Position 2: MBTiles] | [Position 3: GPX] | [Position 4-5: Reserved]
```

**Layout Details:**

| Position | Widget | Width | Type | Content |
|----------|--------|-------|------|---------|
| 1 | temp_status_label | Flexible (stretch) | Regular | Tooltips, transient action messages |
| Separator | separator1 | Fixed | Permanent | Always visible divider |
| 2 | mbtiles_status_label | 280px fixed | Permanent | "MBTiles: [filename]" |
| Separator | separator2 | Fixed | Permanent | Always visible divider |
| 3 | gpx_status_label | 250px fixed | Permanent | "GPX: [filename]" |
| Separator | separator_reserved | 0 (hidden) | Permanent | Shows only when reserved positions populated |
| 4 | reserved1_label | 0 (hidden) | Permanent | Future: Track count, etc. |
| 5 | reserved2_label | 0 (hidden) | Permanent | Future: Zoom level, etc. |

**Key Requirements:**

1. **Permanent File Information**
   - MBTiles filename always visible (Position 2), never pushed off screen
   - GPX filename always visible (Position 3), never pushed off screen
   - Both use fixed widths (280px, 250px) to prevent jumping

2. **Stable Separators**
   - Separators never disappear/flicker
   - Separators always visible (except separator_reserved which shows only when needed)
   - Prevents visual instability when messages change length

3. **Temporary Messages**
   - Displayed in flexible Position 1 (left side)
   - Auto-clear after configurable timeout (1-5 seconds)
   - Examples: "Zoom in", "Undone: [action]", "Merged 3 tracks"
   - Cannot cover file information on right side

4. **Reserved Positions**
   - Positions 4-5 hidden by default (width 0)
   - Can be populated by future features (e.g., track count, zoom level)
   - When populated: Show content + unhide separator
   - When cleared: Hide content + hide separator
   - No wasted space when not in use

**State Examples:**

```
App startup (no files):
"(ready)              | MBTiles: None | GPX: None"

MBTiles loaded:
"(ready)              | MBTiles: Sweden-Raster-Z10-Z16.mbtiles | GPX: None"

User merges tracks (temporary message):
"Merged 3 tracks from archive.gpx | MBTiles: Sweden-Raster-Z10-Z16.mbtiles | GPX: tracks.gpx"

After timeout (auto-clear):
"(ready)              | MBTiles: Sweden-Raster-Z10-Z16.mbtiles | GPX: tracks.gpx"

With reserved position populated:
"(ready)              | MBTiles: Sweden-Raster-Z10-Z16.mbtiles | GPX: tracks.gpx | Tracks: 5 | Zoom: 15"
```

**Implementation:**
- Use `addPermanentWidget()` for fixed positions (MBTiles, GPX, separators)
- Use `addWidget()` with stretch=1 for flexible position (temporary messages)
- Use QTimer for auto-clearing temporary messages
- Reserved position helpers: `_set_reserved1_info()`, `_set_reserved2_info()`

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

## 14. GENERATE ZOOM LEVELS FEATURE

### 14.1 Purpose and Overview

**Feature:** Generate missing zoom levels in MBTiles files by intelligently resampling from existing zoom levels.

**Problem Solved:**
- MBTiles files often have incomplete zoom coverage (e.g., Z6, Z8, Z10, Z12, Z14, Z16 - missing odd zooms)
- Users cannot navigate smoothly - jumping between available zoom levels
- Solution: Automatically generate missing zooms through downsampling or upsampling

**User Experience:**
1. User loads MBTiles with incomplete zoom coverage
2. User clicks "⚙️ Generate Zoom Levels" button (only enabled in MapEditor tab with file loaded)
3. Dialog shows:
   - **Available:** Zooms already in file (marked ✓ existing)
   - **Missing:** Gaps in the continuous range (marked ○ missing)
   - **Outside Range:** Zooms below min-1 or above max+2 (marked ⊘ outside range)
4. For each zoom, shows: Tile count estimate, source zoom, quality warnings
5. User selects which zooms to generate
6. Progress dialog shows real-time generation progress
7. New zooms are written to mbtiles file
8. UI automatically updates to show new available zooms

### 14.2 Core Algorithm

#### 14.2.1 Decision Tree for Source Zoom Selection

**Goal:** For a target zoom level, determine which source zoom level to use and whether to downsample or upsample.

```
ALGORITHM SelectSourceZoom(target_zoom):
    available_zooms = read_from_database()
    
    // Strategy 1: Use zoom Z+1 (downsampling - best quality)
    IF (target_zoom + 1) in available_zooms:
        RETURN (target_zoom + 1, "downsampling")
    
    // Strategy 2: Use zoom Z-1 (upsampling)
    IF (target_zoom - 1) in available_zooms:
        RETURN (target_zoom - 1, "upsampling")
    
    // Strategy 3: Find nearest zoom (could be multiple steps away)
    nearest_zoom = FindNearestZoom(target_zoom, available_zooms)
    
    IF nearest_zoom > target_zoom:
        RETURN (nearest_zoom, "downsampling")
    ELSE:
        RETURN (nearest_zoom, "upsampling")
END ALGORITHM
```

**Example Scenarios:**
- File has [6, 8, 10, 12, 14, 16], user wants Z9:
  - Check Z10 → exists → Use Z10 as source (downsampling)
- File has [6, 8, 10, 12, 14, 16], user wants Z7:
  - Check Z8 → exists → Use Z8 as source (downsampling)
- File has [6, 12, 16], user wants Z13:
  - Check Z14 → doesn't exist
  - Check Z12 → exists → Use Z12 as source (upsampling)
- File has [6, 12, 16], user wants Z7:
  - Check Z8 → doesn't exist
  - Check Z6 → exists → Use Z6 as source (upsampling)

#### 14.2.2 Downsampling Algorithm (Source > Target)

**Concept:** Combine 4 tiles from source zoom into 1 tile at target zoom.

**Example:** Z14 → Z13 (source is 1 level higher)
- Each zoom level divides the world into 2^z × 2^z tiles
- Z14: 2^14 × 2^14 = 16,384 × 16,384 tiles
- Z13: 2^13 × 2^13 = 8,192 × 8,192 tiles (half the dimensions)
- Each Z13 tile represents 4 Z14 tiles (2×2 grid)

**Tile Coordinate Mapping:**
```
For target tile at Z13 with coordinates (tx, ty):
    Source tiles at Z14:
    (tx*2,     ty*2)      // top-left
    (tx*2 + 1, ty*2)      // top-right
    (tx*2,     ty*2 + 1)  // bottom-left
    (tx*2 + 1, ty*2 + 1)  // bottom-right
```

**Resampling Process:**
1. Fetch 4 source tiles (256×256 pixels each)
2. Create 512×512 canvas
3. Place tiles in 2×2 grid
4. Resample entire canvas to 256×256 using LANCZOS filter
5. Save as PNG/JPEG (preserve original format)

**Code Pattern:**
```python
def downsample_tile(source_zoom, target_zoom, tile_x, tile_y):
    """Generate target tile by downsampling from source zoom."""
    
    # Calculate source tile coordinates
    source_tiles = [
        (tile_x*2,     tile_y*2),
        (tile_x*2 + 1, tile_y*2),
        (tile_x*2,     tile_y*2 + 1),
        (tile_x*2 + 1, tile_y*2 + 1)
    ]
    
    # Fetch tiles from database
    images = []
    for sx, sy in source_tiles:
        tile_blob = fetch_tile(source_zoom, sx, sy)
        if tile_blob:
            images.append(Image.open(BytesIO(tile_blob)))
        else:
            # Missing source tile - use gray placeholder
            images.append(Image.new('RGB', (256, 256), (200, 200, 200)))
    
    # Create 512×512 canvas
    canvas = Image.new('RGB', (512, 512))
    canvas.paste(images[0], (0, 0))        # top-left
    canvas.paste(images[1], (256, 0))      # top-right
    canvas.paste(images[2], (0, 256))      # bottom-left
    canvas.paste(images[3], (256, 256))    # bottom-right
    
    # Resample to 256×256 using LANCZOS
    result = canvas.resize((256, 256), Image.LANCZOS)
    
    # Encode to blob
    blob = BytesIO()
    result.save(blob, format='PNG')
    return blob.getvalue()
```

#### 14.2.3 Upsampling Algorithm (Source < Target)

**Concept:** Extract appropriate region from source tile and upsample it.

**Example:** Z12 → Z13 (source is 1 level lower)
- Z13 has twice the tile density of Z12
- Each Z12 tile expands to 4 Z13 tiles (2×2 grid)
- Target tile must extract 1/4 of source tile

**Tile Coordinate Mapping:**
```
For target tile at Z13 with coordinates (tx, ty):
    Source tile at Z12: (tx // 2, ty // 2)
    Quadrant within source: ((tx % 2) * 2) + (ty % 2)
    
    Quadrant mapping (within 256×256 source tile):
    ┌─────────┬─────────┐
    │    0    │    1    │
    │[0:128]  │[128:256]│
    ├─────────┼─────────┤
    │    2    │    3    │
    │[0:128]  │[128:256]│
    └─────────┴─────────┘
```

**Resampling Process:**
1. Fetch source tile (256×256)
2. Extract appropriate 128×128 quadrant
3. Resample to 256×256 using LANCZOS filter
4. Save as PNG/JPEG (preserve original format)

**Code Pattern:**
```python
def upsample_tile(source_zoom, target_zoom, tile_x, tile_y):
    """Generate target tile by upsampling from source zoom."""
    
    # Calculate source tile and quadrant
    source_x = tile_x // 2
    source_y = tile_y // 2
    quadrant = ((tile_x % 2) * 2) + (tile_y % 2)
    
    # Fetch source tile
    tile_blob = fetch_tile(source_zoom, source_x, source_y)
    if not tile_blob:
        # No source tile - use gray placeholder
        return Image.new('RGB', (256, 256), (200, 200, 200))
    
    source_image = Image.open(BytesIO(tile_blob))
    if source_image.mode != 'RGB':
        source_image = source_image.convert('RGB')
    
    # Extract quadrant
    quadrant_bounds = {
        0: (0, 0, 128, 128),        # top-left
        1: (128, 0, 256, 128),      # top-right
        2: (0, 128, 128, 256),      # bottom-left
        3: (128, 128, 256, 256)     # bottom-right
    }
    x1, y1, x2, y2 = quadrant_bounds[quadrant]
    quadrant_image = source_image.crop((x1, y1, x2, y2))
    
    # Upsample to 256×256
    result = quadrant_image.resize((256, 256), Image.LANCZOS)
    
    # Encode to blob
    blob = BytesIO()
    result.save(blob, format='PNG')
    return blob.getvalue()
```

### 14.3 Quality Warnings

**When to Warn User:**

| Scenario | Warning | Recommendation |
|----------|---------|---|
| Upsampling 1 level (Z12→Z13) | None | Safe, acceptable quality |
| Upsampling 2 levels (Z12→Z14) | ⚠️ Moderate quality loss | Show warning, require confirmation |
| Upsampling 3+ levels (Z12→Z15) | ⚠️ Poor quality | Show warning, strongly discourage but allow |
| Downsampling any distance | None | Safe, always acceptable |
| No source zoom available | ⚠️ Cannot generate | Show error, disable checkbox |

**Code Pattern:**
```python
def should_warn_user(source_zoom, target_zoom):
    """Determine if user should see quality warning."""
    
    if source_zoom is None:
        return True, "No source zoom available"
    
    if source_zoom >= target_zoom:
        # Downsampling - always safe
        return False, ""
    
    # Upsampling - check distance
    distance = target_zoom - source_zoom
    
    if distance == 1:
        return False, ""  # 1 level OK
    
    if distance == 2:
        return True, f"Upsampling from Z{source_zoom} to Z{target_zoom} (2 levels) - moderate quality loss"
    
    if distance > 2:
        return True, f"Upsampling from Z{source_zoom} to Z{target_zoom} ({distance} levels) - significant quality loss"
    
    return False, ""
```

### 14.4 Tile Count Calculation

**Critical:** Don't use naive formula `4^zoom`. For sparse/regional MBTiles, actual tile count is much smaller.

**Correct Approach:**

1. Query database for bounding box of existing tiles at source zoom
2. Calculate equivalent bounding box at target zoom using coordinate scaling
3. Count tiles within that bounding box

**Code Pattern:**
```python
def calculate_tile_count(source_zoom, target_zoom, mbtiles_reader):
    """Calculate realistic tile count for generation."""
    
    # Get bounding box of tiles at source zoom
    source_min_col, source_max_col, source_min_row, source_max_row = \
        mbtiles_reader.get_tile_bounds(source_zoom)
    
    if source_min_col == 0 and source_max_col == 0:
        # No tiles at source zoom
        return 4 ** target_zoom  # Fallback to theoretical maximum
    
    if source_zoom > target_zoom:
        # Downsampling: divide by 2^(source_zoom - target_zoom)
        divisor = 2 ** (source_zoom - target_zoom)
        target_min_col = source_min_col // divisor
        target_max_col = source_max_col // divisor
        target_min_row = source_min_row // divisor
        target_max_row = source_max_row // divisor
    else:
        # Upsampling: multiply by 2^(target_zoom - source_zoom)
        multiplier = 2 ** (target_zoom - source_zoom)
        target_min_col = source_min_col * multiplier
        target_max_col = (source_max_col + 1) * multiplier - 1
        target_min_row = source_min_row * multiplier
        target_max_row = (source_max_row + 1) * multiplier - 1
    
    # Calculate grid size
    width = target_max_col - target_min_col + 1
    height = target_max_row - target_min_row + 1
    return width * height
```

### 14.5 Dialog Display Strategy

**Key Insight:** Show a **reasonable range**, not just missing zooms.

```
Available range from file: [6, 8, 9, 10, 11, 12, 14, 15]
Missing zooms in range: [7, 13]

Display range: (min - 1) to (max + 2) = Z5 to Z17
Shows:
  Z5  ⊘ outside range
  Z6  ✓ existing
  Z7  ○ missing (can generate from Z6 or Z8)
  Z8  ✓ existing
  Z9  ✓ existing
  ...
  Z17 ⊘ outside range
```

**Why this range:**
- `min - 1`: Allow downsampling from min to generate zoom below minimum
- `max + 2`: Allow upsampling from max to generate 2 zooms above (with warnings)
- Prevents showing hundreds of unreasonable options (Z0-Z31)
- Allows regenerating existing zooms if user wants higher quality

**Code Pattern:**
```python
available_zooms = sorted(generator.reader.get_available_zooms())
min_zoom = min(available_zooms)
max_zoom = max(available_zooms)

# Calculate display range
display_min = max(0, min_zoom - 1)
display_max = min(28, max_zoom + 2)
display_range = list(range(display_min, display_max + 1))

for zoom in display_range:
    if zoom in available_zooms:
        status = "✓ existing"
    elif zoom in missing_zooms:
        status = "○ missing"
    else:
        status = "⊘ outside range"
    
    try:
        plan = generator.create_generation_plan(zoom)
        info_text = f" ({plan.tile_count:,} tiles, from Z{plan.source_zoom})"
        if plan.quality_warning:
            info_text += " ⚠️"
    except:
        info_text = " (Cannot generate)"
        checkbox.setEnabled(False)
```

### 14.6 Database Write Strategy

**Critical:** Use transactions and batch writes for performance.

```python
def write_generated_zoom(db_connection, target_zoom, tiles):
    """Write generated tiles to database atomically."""
    
    try:
        cursor = db_connection.cursor()
        cursor.execute("BEGIN TRANSACTION")
        
        # Insert all tiles for this zoom level
        sql = """
            INSERT OR IGNORE INTO tiles 
            (zoom_level, tile_column, tile_row, tile_data)
            VALUES (?, ?, ?, ?)
        """
        
        for tile_x, tile_y, tile_data in tiles:
            cursor.execute(sql, (target_zoom, tile_x, tile_y, tile_data))
        
        cursor.execute("COMMIT")
        return True
        
    except Exception as e:
        cursor.execute("ROLLBACK")
        logger.error(f"Failed to write zoom {target_zoom}: {e}")
        raise
```

### 14.7 UI State Management

**Button Behavior:**
- **Enabled:** MapEditor tab is active AND mbtiles file is loaded
- **Disabled:** Different tab active OR no file loaded OR generating in progress
- **During Generation:** Disabled, with progress dialog showing

**Code Pattern (in MainWindow):**
```python
def _on_tab_changed(self, index: int) -> None:
    """Update Generate button state when tab changes."""
    is_map_editor_active = (index == 1)  # 0=Track, 1=Map, 2=Settings
    
    should_enable = (is_map_editor_active and 
                    self.mbtiles_provider and 
                    self.mbtiles_provider.is_loaded() and
                    not self.is_generating)
    
    self.map_editor_handler.characteristics_panel.generate_zoom_button.setEnabled(should_enable)
```

### 14.8 Error Handling

| Error | Handling |
|-------|----------|
| No mbtiles file loaded | Warning dialog, disable button |
| No source zoom available for target | Disable checkbox in dialog |
| Corrupted source tile | Use gray placeholder (200, 200, 200) |
| Database locked | Retry with exponential backoff |
| Insufficient disk space | Warn user before starting |
| User cancels mid-generation | Rollback transaction, no partial data |

### 14.9 Performance Considerations

| Operation | Typical Time | Optimization |
|-----------|---|---|
| Generate single tile | 50-100ms | Resampling with LANCZOS |
| Generate entire zoom (Z13) | 1-3 hours | Background thread + progress updates |
| Memory usage | ~500MB | Tile caching (max 256 tiles in RAM) |

**Threading Strategy:**
- Use QThread for background generation
- Progress signals emit every tile or every 100 tiles (configurable)
- Allow user to cancel at any time
- Do NOT block UI during generation

### 14.10 Testing Checklist

- [ ] Generate missing zoom from even to odd (Z6→Z7)
- [ ] Generate missing zoom from odd to even (Z7→Z6)
- [ ] Generate multiple zooms in sequence
- [ ] Quality warnings appear for upsampling >2 levels
- [ ] Regenerate existing zoom (user choice, check quality)
- [ ] Generate outside current range (Z5 from Z6, Z17 from Z16)
- [ ] Cancel mid-generation (no partial data in database)
- [ ] Very large file (sparse coverage) - tile count is realistic, not 4^zoom
- [ ] Dialog shows correct available/missing/outside-range zooms
- [ ] Button enable/disable on tab switch
- [ ] Button enable/disable on file load/unload

### 14.11 Implementation Checklist

- [x] Copy `ZoomGenerator` from MapLoom
- [x] Copy `TileProcessor` from MapLoom
- [x] Copy `ZoomGenerationWorker` from MapLoom
- [x] Create `zoom_selection_dialog.py` showing all reasonable zooms
- [x] Add "⚙️ Generate Zoom Levels" button to CharacteristicsPanel
- [x] Implement button enable/disable based on tab + file state
- [x] Connect button to zoom selection dialog (NO pre-check for gaps)
- [x] Implement threading for background generation
- [x] Implement progress dialog
- [x] Handle completion: reload zoom data, update UI
- [x] Handle errors: show user message, re-enable button
- [ ] Test with actual mbtiles files
- [ ] Performance testing with large files
- [ ] Documentation for users

---

**END OF SPECIFICATION DOCUMENT**
