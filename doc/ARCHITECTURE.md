# mangpx - Architecture & Design

**Document Purpose:** Visual overview of application architecture, data flow, and component relationships

---

## 1. APPLICATION ARCHITECTURE

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                       mangpx Application                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│                        ┌───────────────────┐                        │
│                        │   MainWindow      │                        │
│                        │  (PyQt5 QMain     │                        │
│                        │   Window)         │                        │
│                        └────────┬──────────┘                        │
│                                 │                                   │
│             ┌───────────────────┼───────────────────┐               │
│             │                   │                   │               │
│      ┌──────▼────────┐  ┌───────▼──────┐  ┌─────────▼──────┐        │
│      │TrackListWidget│  │   MapWidget  │  │Trackpoint      │        │
│      │               │  │              │  │ListWidget      │        │
│      └───────────────┘  └──────────────┘  └────────────────┘        │
│             │                   │                    │              │
│             └───────────────────┼────────────────────┘              │
│                                 │                                   │
│                      ┌──────────▼──────────┐                        │
│                      │  TrackManager       │                        │
│                      │  + CommandHistory   │                        │
│                      └─────────┬───────────┘                        │
│                                │                                    │
│            ┌───────────────────┼──────────────────┐                 │
│            │                   │                  │                 │
│     ┌──────▼─────────┐  ┌──────▼─────┐     ┌──────▼────────┐        │
│     │ GPXHandler     │  │ Calculator │     │Coordinate     │        │
│     │ (read/write)   │  │ (distance) │     │Formatter      │        │
│     └────────────────┘  └────────────┘     │(DMS↔decimal)  │        │
│                                            └───────────────┘        │
│     ┌─────────────────────────────────────┐                         │
│     │      MBTilesProvider                │                         │
│     │      (map tile loading)             │                         │
│     └─────────────────────────────────────┘                         │
│                                                                     │
│     ┌─────────────────────────────────────┐                         │
│     │      AppConfig                      │                         │
│     │      (settings.ini management)      │                         │
│     └─────────────────────────────────────┘                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. DATA FLOW DIAGRAM

### File Open & Display Workflow

```
User opens GPX file
         │
         ▼
    ┌────────────┐
    │ Open Dialog│
    └─────┬──────┘
          │ (file_path)
          ▼
    ┌─────────────────┐
    │  GPXHandler     │
    │  load_gpx()     │
    │  ↓ returns GPX  │
    └────────┬────────┘
             │ (GPX object)
             ▼
    ┌─────────────────┐
    │ TrackManager    │
    │ __init__(gpx)   │
    │ ↓ stores GPX    │
    └────────┬────────┘
             │
      ┌──────┴──────┐
      │             │
      ▼             ▼
┌───────────┐  ┌──────────────┐
│ Display   │  │ Select first │
│ tracks in │  │ track        │
│list widget│  └──────┬───────┘
└───────────┘         │
                      ▼
                ┌────────────────┐
                │ Display track  │
                │points in list  │
                │widget          │
                └────────┬───────┘
                         │
                         ▼
                ┌────────────────┐
                │ Render track   │
                │on map widget   │
                └────────────────┘
```

### Edit & Undo/Redo Workflow

```
User edits track (e.g., rename)
           │
           ▼
    ┌──────────────────┐
    │ Rename Dialog    │
    │ get_new_name()   │
    └────────┬─────────┘
             │ (new_name)
             ▼
    ┌──────────────────┐
    │ Create Command   │
    │ RenameTrack      │
    │ Command(...)     │
    └────────┬─────────┘
             │ (command object)
             ▼
    ┌──────────────────────────┐
    │ CommandHistory           │
    │ execute(command)         │
    │ ├─ command.execute()     │
    │ ├─ push to undo stack    │
    │ └─ clear redo stack      │
    └────────┬─────────────────┘
             │
      ┌──────┴──────┐
      │             │
      ▼             ▼
┌──────────────┐  ┌──────────────┐
│ Update UI    │  │ Set dirty    │
│ (track list) │  │ flag = True  │
└──────────────┘  └──────────────┘

User presses Ctrl+Z (Undo)
           │
           ▼
    ┌──────────────────────────┐
    │ CommandHistory.undo()    │
    │ ├─ pop from undo stack   │
    │ ├─ command.undo()        │
    │ └─ push to redo stack    │
    └────────┬─────────────────┘
             │
             ▼
    ┌──────────────────┐
    │ Update UI        │
    │ (revert changes) │
    └──────────────────┘
```

### Save & Export Workflow

```
 User clicks Save
        │
        ▼
 ┌────────────────────────┐
 │ GPXHandler             │
 │ validate_garmin_       │
 │ compatibility()        │
 │ ├─ Check namespaces    │
 │ ├─ Validate coords     │
 │ ├─ Check encoding      │
 │ └─ return (bool, msgs) │
 └────────┬───────────────┘
          │
    ┌─────▼─────┐
    │Valid?     │
    └┬────────┬─┘
     │        │
   YES       NO
     │        │
     ▼        ▼
 ┌──────┐  ┌──────────┐
 │Save  │  │Show error│
 │file  │  │dialog    │
 └──┬───┘  └──────────┘
    │
    ├─ Create backup (.bak)
    ├─ Write GPX to file
    ├─ Update window title
    └─ Set dirty = False

File ready for Garmin import
       │
       ▼
Garmin EchoMAP 50s
├─ Connect USB
├─ Copy to /GARMIN/GPX/
├─ On device: Import from SD
└─ Track appears in Saved Tracks
```

---

## 3. CLASS HIERARCHY

### Core Classes

```
┌──────────────────┐
│ GPXHandler       │
├──────────────────┤
│ load_gpx()       │
│ save_gpx()       │
│ validate_gpx()   │
│ get_tracks()     │
│ calculate_dist() │
└──────────────────┘

┌──────────────────┐
│ TrackManager     │
├──────────────────┤
│ tracks           │
│ selected_track   │
│ dirty            │
├──────────────────┤
│ select_track()   │
│ rename_track()   │
│ add_trackpoint() │
│ remove_trkpt()   │
│ recalc_distance()│
└──────────────────┘

┌──────────────────┐
│ CommandHistory   │
├──────────────────┤
│ undo_stack       │
│ redo_stack       │
├──────────────────┤
│ execute(cmd)     │
│ undo()           │
│ redo()           │
│ can_undo()       │
│ can_redo()       │
│ clear()          │
└──────────────────┘

┌──────────────────┐
│ Command (ABC)    │
├──────────────────┤
│ execute()        │
│ undo()           │
│ description      │
└──────────────────┘
    │
    ├──► RenameTrackCommand
    ├──► AddTrackpointCommand
    ├──► RemoveTrackpointCommand
    └──► RemoveRangeCommand
```

### UI Classes

```
┌──────────────────┐
│ MainWindow       │
│ (QMainWindow)    │
├──────────────────┤
│ track_list_wgt   │
│ map_widget       │
│ trackpt_list_wgt │
│ track_manager    │
│ command_history  │
├──────────────────┤
│ open_file()      │
│ save_file()      │
│ on_track_select()│
│ on_undo()        │
│ on_redo()        │
└──────────────────┘

┌────────────────────────┐
│ TrackListWidget        │
│ (QWidget)              │
├────────────────────────┤
│ table_widget           │
│ track_manager          │
├────────────────────────┤
│ load_tracks()          │
│ get_selected_track()   │
│ on_track_selected()    │
└────────────────────────┘
    │ signal: track_selected

┌────────────────────────┐
│ TrackpointListWidget   │
│ (QWidget)              │
├────────────────────────┤
│ table_widget           │
│ track_manager          │
├────────────────────────┤
│ load_trackpoints()     │
│ get_selected_index()   │
│ on_point_selected()    │
└────────────────────────┘
    │ signal: trackpoint_selected

┌────────────────────────┐
│ MapWidget              │
│ (QWebEngineView)       │
├────────────────────────┤
│ map_renderer           │
│ mbtiles_provider       │
├────────────────────────┤
│ load_track()           │
│ zoom_in()              │
│ zoom_out()             │
│ fit_track()            │
└────────────────────────┘
    │ signal: point_clicked
```

### Utility Classes

```
┌──────────────────────────┐
│ CoordinateFormatter      │
├──────────────────────────┤
│ decimal_to_dms()         │
│ dms_to_decimal()         │
│ format_coordinate()      │
│ parse_coordinate_str()   │
└──────────────────────────┘

┌──────────────────────────┐
│ Calculator               │
├──────────────────────────┤
│ haversine_distance()     │
│ calculate_track_dist()   │
│ point_to_line_dist()     │
└──────────────────────────┘

┌──────────────────────────┐
│ MBTilesProvider          │
├──────────────────────────┤
│ db_connection            │
│ mbtiles_path             │
├──────────────────────────┤
│ get_tile(z,x,y)         │
│ get_bounds()             │
│ get_zoom_levels()        │
└──────────────────────────┘

┌──────────────────────────┐
│ AppConfig                │
├──────────────────────────┤
│ config (ConfigParser)    │
├──────────────────────────┤
│ get()                    │
│ get_int()                │
│ get_bool()               │
│ get_float()              │
└──────────────────────────┘
```

---

## 4. SIGNAL & SLOT CONNECTIONS (PyQt5)

### MainWindow Connections

```
TrackListWidget
├─ track_selected(track) ──► MainWindow.on_track_selected()
│                            ├─ Display trackpoint list
│                            └─ Load map

TrackpointListWidget
├─ trackpoint_selected(idx) ──► MainWindow.on_trackpoint_selected()
│                                └─ Highlight on map

MapWidget
├─ point_clicked_on_map(idx) ──► MainWindow.on_point_clicked()
│                                └─ Select in list

Menu Actions
├─ File → Open ──► MainWindow.on_open_file()
├─ File → Save ──► MainWindow.on_save_file()
├─ Edit → Undo ──► MainWindow.on_undo()
├─ Edit → Redo ──► MainWindow.on_redo()
├─ Edit → Rename ──► MainWindow.on_rename_track()
├─ Edit → Add Point ──► MainWindow.on_add_trackpoint()
└─ Edit → Delete Point ──► MainWindow.on_delete_trackpoint()

CommandHistory
├─ undo_redo_changed(can_undo, can_redo) ──► MainWindow.update_undo_redo_buttons()
```

---

## 5. DATA STRUCTURES

### GPX Data Model (via gpxpy)

```
GPX
├── tracks: List[Track]
│   └── Track
│       ├── name: str
│       ├── segments: List[Segment]
│       │   └── Segment
│       │       └── points: List[Point]
│       │           └── Point
│       │               ├── latitude: float
│       │               ├── longitude: float
│       │               ├── elevation: float (optional)
│       │               └── time: datetime (optional)
│       └── get_points_data() → List[tuple(lat, lon)]
└── waypoints: List[Waypoint]
```

### TrackManager Internal State

```
TrackManager
├── gpx_data: GPX (original from file)
├── tracks: List[Track] (reference to gpx_data.tracks)
├── selected_track: Track (current selection)
├── command_history: CommandHistory (undo/redo stack)
├── dirty: bool (unsaved changes)
└── metadata: dict (cached track info)
    ├── [track_idx]
    │   ├── name: str
    │   ├── distance: float (km)
    │   ├── point_count: int
    │   └── has_altitude: bool
```

### Command History State

```
CommandHistory
├── undo_stack: List[Command]
│   └── Command
│       ├── track_manager: TrackManager (reference)
│       ├── track_index: int
│       ├── operation_data: dict
│       │   └── varies by operation type
│       ├── execute() → modifies track_manager
│       └── undo() → reverts track_manager
├── redo_stack: List[Command]
└── max_history_size: int (memory limit)
```

### UI State (MainWindow)

```
MainWindow
├── current_file_path: str (file being edited)
├── track_manager: TrackManager
├── command_history: CommandHistory
├── config: AppConfig
├── widgets
│   ├── track_list: TrackListWidget (left panel)
│   ├── map: MapWidget (center panel)
│   └── trackpoint_list: TrackpointListWidget (right panel)
├── status
│   ├── current_zoom: int
│   ├── selected_point: int (index or -1 if none)
│   └── is_add_mode: bool
```

---

## 6. FILE I/O FLOW

### Load GPX File

```
User: Open file dialog
         │
         ▼
GPXHandler.load_gpx(path)
├─ Open file (UTF-8)
├─ Parse XML with gpxpy.parse()
├─ Validate structure
├─ Extract tracks & points
└─ Return: GPX object (or raise exception)
         │
         ▼
TrackManager.__init__(gpx)
├─ Store GPX reference
├─ Cache track metadata
├─ Initialize dirty=False
└─ Initialize CommandHistory
         │
         ▼
Display in UI
```

### Save GPX File

```
User: Save (Ctrl+S)
         │
         ▼
MainWindow.on_save_file()
├─ Get file path (if first save: ask user)
├─ Validate with TrackManager.validate_garmin_compatible()
│  ├─ Check all track names valid
│  ├─ Check all coordinates valid
│  ├─ Check no encoding issues
│  └─ Return: (bool, error_list)
├─ If valid:
│  │  ├─ Create backup (if configured)
│  │  ├─ Write GPX file
│  │  ├─ Set dirty=False
│  │  └─ Show success message
└─ If invalid:
   └─ Show error dialog with issues
```

### Export to Garmin

```
mangpx saves GPX file
         │
         ▼
User connects Garmin EchoMAP 50s
         │
         ▼
User copies file to /GARMIN/GPX/ directory
         │
         ▼
On device: Saved Tracks → Import from SD card
         │
         ▼
Select GPX file from list
         │
         ▼
Device validates & imports
         │
         ▼
Track appears in Saved Tracks menu
```

---

## 7. ERROR HANDLING FLOW

### Generic Error Pattern

```
User action
         │
         ▼
    try:
    ├─ Execute operation
    └─ Return result
    
    except SpecificException:
    ├─ Create error message
    ├─ Log to file
    ├─ Show user dialog
    └─ Return error status

User sees error → Can take action or retry
```

### File Error Examples

```
File Operation → Possible Errors
├─ File not found ──► Show path + "File does not exist"
├─ Permission denied ──► Show path + "Access denied"
├─ Corrupted XML ──► Show line number + snippet
├─ Invalid GPX ──► Show validation errors
└─ Encoding error ──► Show encoding + suggest UTF-8
```

---

## 8. THREAD SAFETY

**Note:** For Phase 1-4, single-threaded operation is acceptable.

**Phase 5+ Considerations:**
- Long operations (large file load, map render) may move to background threads
- Use QThread for file I/O
- Use signals/slots for thread-safe UI updates
- Protect TrackManager state with locks if multi-threaded

---

## 9. CONFIGURATION HIERARCHY

```
Default Settings (in code)
         │
         ▼
config/settings.ini (user can modify)
         │
         ▼
AppConfig class (loads & provides access)
         │
         ├─ get() → type auto-detected
         ├─ get_int() → forced to int
         ├─ get_bool() → forced to bool
         └─ get_float() → forced to float
         │
         ▼
Application uses AppConfig throughout
```

**All configurable settings:**
- app_name, version
- default_mbtiles, fallback_mbtiles
- coordinate_format (dms/decimal)
- create_backup, backup_extension
- window size, remember_last_directory
- max_trackpoints_warning
- log_level, log_file

---

## 10. PERFORMANCE CONSIDERATIONS

### For 5,000+ Trackpoints

**Current Design (Phase 1-4):**
- Load all points into QTableWidget
- May have slight lag with 5,000+ points
- Acceptable for initial release

**Phase 5 Optimization (if needed):**
- Implement lazy loading: Only render visible rows
- Use QAbstractTableModel instead of QTableWidget
- Implement pagination: Show 100-500 points per page
- Cache formatted coordinates to avoid repeated conversions

### For Large GPX Files (25+ MB)

**Current Design:**
- Load entire file into memory
- May have startup delay
- Show progress dialog while loading

**Phase 5 Optimization (if needed):**
- Implement streaming parser for huge files
- Process tracks incrementally
- Cache to disk for later access

### Map Rendering

**Current Design:**
- Render all trackpoints as markers
- Use Leaflet.js in PyQtWebEngine
- Acceptable for 10,000+ points with optimization

**If Issues Arise:**
- Use clustering library (Leaflet.markercluster)
- Show fewer markers at lower zoom levels
- Render polyline only, show points on demand

---

## 11. EXTENSION POINTS (Future Features)

### Planned for Future Versions

1. **Multi-track editing**
   - Merge multiple tracks
   - Split track at point
   - Copy/paste tracks

2. **Advanced analysis**
   - Elevation profile
   - Speed analysis
   - Segment statistics

3. **Import/export formats**
   - KML, CSV, GeoJSON
   - Garmin device sync
   - Cloud storage

4. **Collaborative features**
   - Share tracks
   - Comment on tracks
   - Version control

---

**End of Architecture Document**
