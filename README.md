# CourseStudio - GPX File Manipulator

A PyQt5-based desktop application for viewing, editing, and manipulating GPX (GPS Exchange Format) files with interactive map visualization. Designed for marine navigation and track management with support for Garmin GPS devices.

## Screenshots & Features by Tab

### Track Editor Tab - GPS Track Editing

![Track Editor Tab](wiki/track-editor-tab-general.jpg)

The main Track Editor interface for GPX file manipulation:
- **Left Panel:** Track list showing all tracks in the current file with distance and point count
- **Top-Right Panel:** Trackpoint list with coordinates in DMS or Decimal format, elevation, and timestamps
- **Bottom-Right Panel:** Interactive map with real-time track visualization, pan/zoom controls, and trackpoint markers
- Full undo/redo support for all edits
- Drag trackpoints on the map to reposition them
- Prune points by minimum distance with progress tracking

### Map Editor Tab - MBTiles Tile File Editing

![Map Editor Tab](wiki/map-editor-tab-general.jpg)

The Map Editor for managing MBTiles tile files:
- **Left Panel:** Characteristics panel showing file metadata, available zoom levels, and statistics
- **Right Panel:** Interactive map viewer for previewing tiles and managing zoom levels
- Generate missing zoom levels from existing tiles
- Mark map center and zoom as defaults
- Pan and zoom the map to explore tile coverage
- Recenter to marked default position

### Settings Tab - Appearance Configuration

![Settings Tab](wiki/settings-tab-general.jpg)

Customize visual appearance and behavior:
- **Track Path Settings:** Configure track line color, width, outline color, and outline width
- **Turning Points Settings:** Customize general, single-selected, and multi-selected trackpoint appearance
- **Crosshair Settings:** Enable/disable crosshair and customize appearance
- **Performance Settings:** Configure pruning distance and other performance parameters
- Real-time map updates as you change settings
- All settings auto-saved to config file

## Features

### Core Functionality
- **GPX File Management**
  - Load, edit, and save GPX files
  - Support for multiple tracks in a single file
  - Undo/redo support for all edits
  - Backup creation before saving
  - Batch processing capabilities

- **Track Visualization**
  - Interactive map with mbtiles-based tile support
  - Real-time track rendering
  - Pan and zoom controls
  - Track path color and width customization with outline effects

- **Trackpoint Management**
  - View all trackpoints in tabular format
  - DMS (Degrees, Minutes, Seconds) and Decimal coordinate formats
  - Toggle between formats instantly
  - Track elevation and timestamp data (when available)

- **Map Navigation**
  - Smooth panning with Web Mercator projection
  - Mouse wheel zoom support
  - Zoom in/out buttons with visual feedback
  - Recenter to default position
  - Turning points (trackpoints) visualization on map with customizable outline

- **Turning Points Display**
  - Visualize trackpoints as circles on the map
  - Toggle visibility with toggle switch
  - Customizable colors and sizes for general, single-selected, and multi-selected points
  - Configurable outline colors and widths
  - Selected point highlighting

- **Layout Control**
  - Horizontal splitter between Track List and Trackpoints/Map panel (manually resizable)
  - Vertical splitter between Trackpoints list and Map (manually resizable)
  - Expand/collapse sections without losing work

- **Settings Panel**
  - **Appearance tab** with sub-tabs:
    - Track Path: Configure body and outline colors/widths
    - General Track Point: Settings for unselected trackpoints
    - Single-Selected Track Point: Settings for single-selected trackpoints
    - Multi-Selected Track Point: Settings for multi-selected trackpoints
  - Real-time map updates when settings change
  - Auto-save configuration to file

## Requirements

### System Requirements
- Python 3.8+
- PyQt5
- PIL (Pillow)
- GPXpy
- Configparser

### Recommended Hardware
- Linux/macOS/Windows
- Minimum 4GB RAM
- 100MB disk space for mbtiles data

## Installation

### Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/CourseStudio.git
cd CourseStudio
```

2. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run the application**
```bash
python src/main.py
```

### Development Setup

```bash
# Install with development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Run with debug logging
python src/main.py --debug
```

## Usage

### Opening a GPX File

1. Click **File → Open** or use Ctrl+O
2. Select your GPX file
3. File contents load into the Tracks and Trackpoints panels

### Viewing Tracks on Map

1. Select a track from the **Tracks** list on the left
2. Track path appears on the map in **red (configurable)**
3. All trackpoints appear as **yellow circles** (if "Show points" = Yes)
4. Click on a trackpoint in the **Trackpoints** list to highlight it in **blue**

### Map Controls

| Action | Control |
|--------|---------|
| Pan | Left-click and drag |
| Zoom In | Click **+** button or scroll wheel up |
| Zoom Out | Click **-** button or scroll wheel down |
| Recenter | Click **⊙** button |
| Toggle Points | Use **"Show points"** dropdown in Trackpoints window |

### Coordinate Formats

**DMS (Degrees, Minutes, Seconds)**
```
57°30'45.5"N 12°15'30.2"E
```

**Decimal**
```
57.5126°N 12.2584°E
```

Switch between formats using the **Format** dropdown in the Trackpoints window.

### Customizing Appearance

Edit `config/settings.yaml`:

```yaml
map:
  # Track path color (hex RRGGBB)
  track_path_color: FF0000          # Red
  track_path_width: 3               # 3 pixels

  # Turning points (trackpoints)
  show_turning_points: true         # Show/hide all points
  turning_point_color: FFFF00       # Yellow
  selected_turning_point_color: 0000FF  # Blue
  turning_point_size: 4             # 4 pixel radius
```

### Supported Coordinate Formats

- **DMS**: Degrees, Minutes, Seconds (57°30'45.5"N)
- **Decimal**: Decimal degrees (57.5126°)

Change format in Trackpoints window using the **Format** dropdown.

## Architecture

### Directory Structure (Feature-Based Organization)

```
CourseStudio/
├── src/
│   ├── main.py                    # Application entry point
│   ├── features/                  # Feature-based modules
│   │   ├── track_editor/          # Track editing feature
│   │   │   ├── core/
│   │   │   │   ├── track_manager.py
│   │   │   │   ├── gpx_handler.py
│   │   │   │   ├── calculator.py
│   │   │   │   ├── command_history.py
│   │   │   │   └── __init__.py
│   │   │   ├── ui/
│   │   │   │   ├── widgets/
│   │   │   │   │   ├── map_widget.py
│   │   │   │   │   ├── track_list_widget.py
│   │   │   │   │   ├── trackpoint_list_widget.py
│   │   │   │   │   └── __init__.py
│   │   │   │   ├── dialogs/
│   │   │   │   │   ├── add_trackpoint_dialog.py
│   │   │   │   │   └── __init__.py
│   │   │   │   └── __init__.py
│   │   │   └── __init__.py
│   │   ├── map_editor/            # Map tile editing feature
│   │   │   ├── core/
│   │   │   │   ├── mbtiles_reader.py
│   │   │   │   ├── tile_processor.py
│   │   │   │   ├── zoom_generator.py
│   │   │   │   └── __init__.py
│   │   │   ├── ui/
│   │   │   │   ├── widgets/
│   │   │   │   │   ├── map_viewer.py
│   │   │   │   │   ├── characteristics_panel.py
│   │   │   │   │   └── __init__.py
│   │   │   │   ├── dialogs/
│   │   │   │   │   └── __init__.py
│   │   │   │   └── __init__.py
│   │   │   └── __init__.py
│   │   └── settings/              # Settings/configuration feature
│   │       ├── ui/
│   │       │   ├── widgets/
│   │       │   │   ├── settings_widget.py
│   │       │   │   ├── color_picker_widget.py
│   │       │   │   ├── crosshair_settings_widget.py
│   │       │   │   ├── track_path_settings_widget.py
│   │       │   │   ├── trackpoint_type_settings_widget.py
│   │       │   │   ├── performance_settings_widget.py
│   │       │   │   ├── slider_setting_widget.py
│   │       │   │   ├── toggle_switch_widget.py
│   │       │   │   ├── turning_points_settings_widget.py
│   │       │   │   └── __init__.py
│   │       │   ├── tab_handler_settings.py
│   │       │   └── __init__.py
│   │       └── __init__.py
│   ├── shared/                    # Shared/reusable components
│   │   ├── core/
│   │   │   ├── prune_worker.py
│   │   │   ├── zoom_generation_worker.py
│   │   │   ├── coordinate_formatter.py
│   │   │   └── __init__.py
│   │   ├── map/                   # Shared map utilities
│   │   │   ├── mbtiles_provider.py
│   │   │   ├── map_renderer.py
│   │   │   ├── crosshair_drawer.py
│   │   │   ├── mbtiles_file_loader.py
│   │   │   ├── map_buttons.py
│   │   │   ├── map_button_manager.py
│   │   │   ├── map_button_widget.py
│   │   │   ├── tile_server.py
│   │   │   └── __init__.py
│   │   ├── ui/                    # Shared UI components
│   │   │   ├── dialogs/
│   │   │   │   ├── help_dialog.py
│   │   │   │   ├── prune_progress_dialog.py
│   │   │   │   ├── zoom_generation_progress_dialog.py
│   │   │   │   ├── zoom_selection_dialog.py
│   │   │   │   └── __init__.py
│   │   │   ├── widgets/
│   │   │   │   ├── custom_tab_bar.py
│   │   │   │   └── __init__.py
│   │   │   └── __init__.py
│   │   ├── config/
│   │   │   ├── crosshair_config.py
│   │   │   └── __init__.py
│   │   └── __init__.py
│   ├── gui/                       # Application shell
│   │   ├── main_window.py         # Main application window
│   │   ├── tab_handlers/          # Tab orchestration layer
│   │   │   ├── tab_handler_track_editor.py
│   │   │   ├── tab_handler_map_editor.py
│   │   │   ├── tab_handler_settings.py
│   │   │   └── __init__.py
│   │   └── __init__.py
│   └── __init__.py
├── config/
│   ├── settings.yaml              # Configuration file (YAML format)
│   └── app_config_yaml.py         # Config loader for YAML
├── mbtiles/
│   └── (MBTiles tile files)       # Map tile data
├── tests/
│   ├── test_*.py                  # Unit tests
│   └── gpx/
│       └── *.gpx                  # Sample GPX files
├── doc/
│   ├── ARCHITECTURE.md            # System architecture and design
│   ├── QUICK_REFERENCE.md         # Quick reference for common tasks
│   ├── USER_GUIDE.md              # Complete user guide with all features
│   ├── PROJECT_SPECIFICATION.md   # Project specification
│   ├── PROJECT_SUMMARY.md         # Project summary
│   ├── UI_DEBUGGING_HARD_PROBLEMS.md  # UI debugging guide
│   ├── TRACKPOINT_OPERATIONS.md   # Trackpoint operations documentation
│   ├── RECENT_IMPROVEMENTS.md     # Recent improvements and fixes
│   └── ... (additional documentation files)
├── wiki/
│   ├── track-editor-tab-general.jpg     # Track Editor tab screenshot
│   ├── map-editor-tab-general.jpg       # Map Editor tab screenshot
│   └── settings-tab-general.jpg         # Settings tab screenshot
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

### Key Classes

**MainWindow** (`src/gui/main_window.py`)
- Main application window
- File operations (open, save, close)
- Signal coordination between tabs
- Menu and toolbar management
- Tab switching coordination

**Feature-Specific Classes:**

**Track Editor:**
- **TrackManager** (`src/features/track_editor/core/track_manager.py`) - Load/save GPX files, track management, undo/redo
- **GPXHandler** (`src/features/track_editor/core/gpx_handler.py`) - GPX file parsing and serialization
- **MapWidget** (`src/features/track_editor/ui/widgets/map_widget.py`) - Interactive map rendering with pan/zoom
- **TrackListWidget** (`src/features/track_editor/ui/widgets/track_list_widget.py`) - Display all tracks
- **TrackpointListWidget** (`src/features/track_editor/ui/widgets/trackpoint_list_widget.py`) - Display trackpoints with format conversion

**Map Editor:**
- **MBTilesReader** (`src/features/map_editor/core/mbtiles_reader.py`) - Read MBTiles file metadata and zoom levels
- **TileProcessor** (`src/features/map_editor/core/tile_processor.py`) - Process tiles and generate missing zoom levels
- **MapViewer** (`src/features/map_editor/ui/widgets/map_viewer.py`) - Interactive map viewer for MBTiles preview

**Settings:**
- **SettingsWidget** (`src/features/settings/ui/widgets/settings_widget.py`) - Main settings container
- Various setting widgets (color picker, sliders, toggles) for customizing appearance

**Shared Components:**
- **MapRenderer** (`src/shared/map/map_renderer.py`) - Renders tiles from MBTiles provider
- **MBTilesProvider** (`src/shared/map/mbtiles_provider.py`) - Tile data source
- **MapButtonManager** (`src/shared/map/map_button_manager.py`) - Handles map control buttons (zoom, recenter)
- **CoordinateFormatter** (`src/shared/core/coordinate_formatter.py`) - DMS/Decimal coordinate conversion

## Map Data

### Tile Support

CourseStudio uses MBTiles format for map data. Included:
- **Sweden-Raster-Z10-Z16.mbtiles**: Raster tiles for Swedish archipelago

To use different map data:
1. Place `.mbtiles` file in `mbtiles/` directory
2. Update `config/settings.yaml` with filename
3. Restart application

### Tile Specifications

| Property | Value |
|----------|-------|
| Format | MBTiles (SQLite) |
| Tile Size | 256×256 pixels |
| Projection | Web Mercator (EPSG:3857) |
| Zoom Levels | Varies by tileset |

### Finding New MBTiles Files

For sources and detailed information about obtaining new MBTiles files, including available download locations and format recommendations, see **[doc/mbtiles_analysis.md](doc/mbtiles_analysis.md#mbtiles-sources)** → "MBTiles Sources" section.

## Configuration

### Configuration File (settings.yaml)

The application is configured via `config/settings.yaml` in YAML format. Key sections include:

**Application Settings**
- `app_name`: Application name
- `version`: Version string
- `debug`: Enable debug logging

**Map Settings**
- `default_mbtiles`: Primary tile file to use
- `initial_zoom_level`: Default zoom on startup
- `track_path_color`: Track line color (hex RRGGBB)
- `track_path_width`: Track line width in pixels
- `turning_point_color`: Trackpoint color (hex RRGGBB)
- `selected_turning_point_color`: Selected trackpoint color (hex RRGGBB)
- `turning_point_size`: Trackpoint radius in pixels

**Coordinate Settings**
- `coordinate_format`: Default format (dms or decimal)
- `decimal_places`: Decimal precision for coordinate display
- `dms_seconds_decimals`: Precision for DMS seconds

**Performance Settings**
- `max_trackpoints_no_warning`: Warning threshold for large tracks
- `max_file_size_warning`: File size warning threshold (MB)
- `max_undo_redo_stack_size`: Maximum undo history size

**Logging Settings**
- `log_level`: Logging verbosity (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- `log_file`: Log file path and name

See `config/settings.yaml` for complete list of options and examples.

## Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test Suite

```bash
# Track manager tests
pytest tests/test_track_manager.py -v

# Map widget tests
pytest tests/test_map_widget.py -v

# Configuration tests
pytest tests/test_app_config.py -v
```

### Test Coverage

```bash
pytest tests/ --cov=src --cov-report=html
# Open htmlcov/index.html for coverage report
```

## Development

### Code Style

- Follow PEP 8
- Use meaningful variable names
- Document functions with docstrings
- Include type hints for function parameters

### Adding New Features

1. Create feature branch: `git checkout -b feature/your-feature`
2. Implement feature with tests
3. Ensure all tests pass: `pytest tests/`
4. Submit pull request

### Project Structure

- `src/core/`: Business logic (GPX handling, calculations)
- `src/gui/`: User interface (PyQt5 widgets)
- `src/map/`: Map rendering and tile management
- `config/`: Configuration management
- `tests/`: Unit and integration tests
- `doc/`: Documentation

## Known Limitations

- **Single Tile Set**: Currently displays one tileset at a time
- **Single Zoom Level**: Sweden-Raster-Z10-Z16 supports only zoom 15 (use full tileset for Z10-Z16)
- **One Track Visible**: Only one track displays at a time (by design - prevents clutter)
- **No Track Import/Export**: Can't copy tracks between files yet

## Recent Fixes (Version 1.1.0)

### Track Deletion Behavior
- **Before**: Deleting the last point in a track would auto-select and display another track, causing confusion
- **After**: Deleting a track leaves no track selected - the trackpoint list and map are empty until you select another track

### Trackpoint Deletion Updates
- **Before**: Deleting trackpoints didn't update the track info (distance, point count) in the track list
- **After**: Track info updates dynamically after any trackpoint deletion

### Auto-Track Creation
- **Before**: You could only add points to an empty file if you opened it fresh, not if you deleted all tracks
- **After**: Adding points to the map when no track is selected creates a new track (consistent behavior)

## Future Enhancements

- [ ] Multi-track visualization on map
- [ ] Track comparison tools
- [ ] Waypoint management
- [ ] Route planning
- [ ] Advanced filtering and search
- [ ] Export to KML, GPX with compression
- [ ] Mobile app companion
- [ ] Cloud sync support

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit a pull request

## License

[Your License Here] - See LICENSE file for details

## Support & Documentation

- **Bug Reports**: Open an issue on GitHub
- **Documentation**: See `doc/` directory
- **Configuration**: See `config/settings.yaml` for all options
- **Architecture**: See `doc/ARCHITECTURE.md`

## Author

Akoel - Initial development and design

## Changelog

### Version 1.1.0 (2026-10-02)

**Bug Fixes & Improvements:**
- ✅ Fixed track deletion behavior: Deleting last point in a track no longer auto-selects other tracks
- ✅ Fixed trackpoint deletion: Track info (distance, point count) now updates dynamically when deleting points
- ✅ Improved track/trackpoint creation: Auto-creates new track when no track is selected and points are added (consistent with startup behavior)
- ✅ Fixed UI synchronization: Track list, trackpoint list, and map now properly stay in sync when deleting tracks/points
- ✅ Trackpoint info updates on deletion:
  - Single point deletion updates track info
  - Range deletion from start updates track info
  - Range deletion from end updates track info

**Track Management Behavior:**
- When no track is selected (empty file or after deletion), adding points creates a new track automatically
- Deleting a track leaves no selection (instead of auto-selecting next track)
- Deleting the last point in a track deletes the entire track
- All deletions support undo (Ctrl+Z)

### Version 1.0.0 (2026-09-20)

**Implemented Features:**
- ✅ GPX file loading and basic editing
- ✅ Interactive map with pan/zoom
- ✅ Track visualization with configurable colors
- ✅ Trackpoint display and management
- ✅ Coordinate format conversion (DMS/Decimal)
- ✅ Undo/redo support
- ✅ Configuration file system
- ✅ Web Mercator projection for accurate panning
- ✅ Turning points (trackpoints) visualization
- ✅ Show/hide points toggle

**Known Issues:**
- Zoom limited to available levels in tileset
- Single track visible at a time (by design)

## Quick Reference

| Task | How To |
|------|-------|
| Open GPX | File → Open or Ctrl+O |
| Save GPX | File → Save or Ctrl+S |
| View Track | Click track name in left panel |
| View Points | Auto-loads when track selected |
| Change Format | Use Format dropdown in Trackpoints |
| Toggle Points | Use Show points dropdown |
| Pan Map | Left-click and drag |
| Zoom | Use buttons or mouse wheel |
| Recenter Map | Click ⊙ button |

## Documentation & Guides

### User Documentation
- **[USER_GUIDE.md](doc/USER_GUIDE.md)** - Complete user guide with all features
  - Opening and saving files
  - Map navigation (zooming, panning)
  - Layout control with splitter handles
  - Track and trackpoint management
  - Coordinate formats
  - Undo/redo
  - All keyboard shortcuts

- **[QUICK_REFERENCE.md](doc/QUICK_REFERENCE.md)** - Quick reference for common tasks
  - ⭐ **Mouse wheel zooming** (cursor-centered)
  - **Splitter handle** (resize panels)
  - Quick tips and workflows
  - Keyboard shortcuts cheat sheet

### Developer Documentation
- **[ARCHITECTURE.md](doc/ARCHITECTURE.md)** - System architecture and design
- **[PROJECT_SPECIFICATION.md](doc/PROJECT_SPECIFICATION.md)** - Project specification and requirements

## System Requirements

- **OS**: Linux, macOS, or Windows
- **Python**: 3.8 or higher
- **RAM**: 4GB minimum
- **Display**: 1280×900 minimum resolution
- **Storage**: 100MB for application and sample data

## Performance Tips

- Keep tracks under 5000 trackpoints for smooth performance
- Use reasonable zoom levels (Z10-Z16)
- Enable "Show points: No" for large tracks to improve responsiveness
- Close unused files to free memory

## Troubleshooting

### Application Won't Start
```bash
# Check Python version
python3 --version  # Should be 3.8+

# Verify dependencies
pip list | grep -E "PyQt5|Pillow|gpxpy"

# Run with debug output
python src/main.py --debug
```

### Map Won't Display
- Verify mbtiles file exists in `mbtiles/` directory
- Check `config/settings.yaml` for correct filename
- Ensure coordinate format is valid (DMS or Decimal)
- Check logs in `CourseStudio.log`

### Performance Issues
- Reduce number of visible points ("Show points: No")
- Switch to simpler tileset (fewer zoom levels)
- Close other applications to free RAM
- Check system resources with `htop` or Task Manager

## Contact & Community

- Issues & Bug Reports: GitHub Issues
- Feature Requests: GitHub Discussions
- Questions: GitHub Discussions or Issues
- **User Guide**: See [USER_GUIDE.md](doc/USER_GUIDE.md) for detailed help

---

**CourseStudio** - Making GPS data management simple and visual.
