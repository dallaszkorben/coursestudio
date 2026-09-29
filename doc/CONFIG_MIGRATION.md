# CourseStudio Configuration Migration

## Summary

Updated the configuration structure from **technical organization** to **user-centric organization** with collapsible sections in the Settings tab.

## New Structure (settings.yaml)

```
Application (meta info)
├── name, version, window_title
├── window_width, window_height, start_maximized
└── debug, project_root

Appearance (visual settings)
├── MapDisplay
│   ├── TrackPath (color, width)
│   └── TurningPoints (show, color, size, selected color/size)
└── Tiles (mbtiles_file, fallback_files, initial_zoom, default_center)

CoordinatesDisplay (data format)
├── Format (coordinate_format, decimal_places, dms_seconds_decimals)
└── TableDisplay (row_height, show_keyboard_shortcuts)

FileHandling (file operations)
├── Backup (create, extension)
├── RecentFiles (remember_last_directory, max_recent_files)
└── GpxExport (gpx_version, validate_before_save)

Performance (power user settings)
├── TrackLoading (max_trackpoints_no_warning, max_file_size_warning_mb, max_file_size_error_mb)
├── UndoRedo (max_undo_redo_stack, max_history_memory_mb)
└── Rendering (map_render_timer_ms)

Advanced (technical settings)
├── Debugging (log_level, log_file, log_file_max_size_mb, log_backup_count, debug_mode)
├── Technical (file_operation_timeout_s, map_render_timeout_s, max_threads, experimental_features)
└── GarminDevice (show_import_guide)

InternalState (runtime state - not user-editable)
├── Map (last_show_turning_points)
└── Coordinates (last_format)
```

## Path Changes

### Map Widget (map_widget.py)

| Old | New |
|-----|-----|
| `Map.track.path.color` | `Appearance.MapDisplay.TrackPath.color` |
| `Map.track.selected.color` | `Appearance.MapDisplay.TrackPath.color` |
| `Map.turning_points.color` | `Appearance.MapDisplay.TurningPoints.color` |
| `Map.turning_points.selected.color` | `Appearance.MapDisplay.TurningPoints.selected.color` |
| `Map.turning_points.size` | `Appearance.MapDisplay.TurningPoints.size` |
| `Map.turning_points.selected.size` | `Appearance.MapDisplay.TurningPoints.selected.size` |
| `Map.track.path.width` | `Appearance.MapDisplay.TrackPath.width` |
| `Map.last_state.show_turning_points` | `InternalState.Map.last_show_turning_points` |

### Main Window (main_window.py)

| Old | New |
|-----|-----|
| `UI.window.width` | `Application.window_width` |
| `UI.window.height` | `Application.window_height` |
| `UI.start_maximized` | `Application.start_maximized` |

### MBTiles Provider (mbtiles_provider.py)

| Old | New |
|-----|-----|
| `Map.tiles.mbtiles_file` | `Appearance.Tiles.mbtiles_file` |
| `Map.tiles.fallback_files` | `Appearance.Tiles.fallback_files` |

### Trackpoint List Widget (trackpoint_list_widget.py)

| Old | New |
|-----|-----|
| `Coordinates.last_state.format` | `InternalState.Coordinates.last_format` |
| `Map.last_state.show_turning_points` | `InternalState.Map.last_show_turning_points` |

## Benefits

1. **User-Centric**: Settings grouped by task, not technical feature
2. **Scalable**: Easy to add new settings in the right section
3. **Hierarchical**: Logical flow from common → advanced settings
4. **Collapsible**: Users can collapse sections they don't use
5. **Discoverable**: Clear mental model for finding settings

## Files Modified

1. `config/settings.yaml` - Complete restructuring
2. `src/gui/widgets/map_widget.py` - Updated config paths
3. `src/gui/main_window.py` - Updated config paths
4. `src/map/mbtiles_provider.py` - Updated config paths
5. `src/gui/widgets/trackpoint_list_widget.py` - Updated config paths

## Backward Compatibility

**Old settings.yaml files will NOT work.** Users upgrading must use the new structure.

If needed to migrate old configs:
1. Create mapping from old paths to new paths
2. Load old config with AppConfig
3. For each old path, get value and set in new path
4. Save to new settings.yaml

## Next Steps

The code now supports the new structure. Ready to build the Settings tab GUI with collapsible sections:

1. **Phase 1**: APPEARANCE section (Map Display + Tiles)
2. **Phase 2**: COORDINATES & DISPLAY section
3. **Phase 3**: FILE HANDLING section
4. **Phase 4**: PERFORMANCE section (optional)
5. **Phase 5**: ADVANCED section (optional)

## Testing

All 145 tests pass with new configuration structure.

- App loads successfully ✅
- Map displays correctly ✅
- Configuration paths accessible ✅
- All widgets initialize properly ✅
