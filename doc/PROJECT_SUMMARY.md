# CourseStudio Project - Summary & Quick Reference

**Project Status:** Specification & TODO List Complete - Ready for Development  
**Start Date:** 2026-09-20  
**Target Release:** Version 1.0.0  

---

## PROJECT DOCUMENTS

**Primary Documentation:**
1. **PROJECT_SPECIFICATION.md** - Complete functional & technical specification
2. **TODO_LIST.md** - Step-by-step development tasks (23 steps across 5 phases)
3. **IMPLEMENTATION_NOTES.md** - Design decisions and technical notes (to be created)

**Reference Documentation:**
- MBTILES_ANALYSIS.md - Map tile file information
- garmin-gpx-processing-guide.md - Garmin compatibility & lessons learned

---

## KEY DECISIONS

### 1. Project Name & Configuration
- **Name:** CourseStudio (GPX Manipulator)
- **Configurable via:** `config/settings.ini`
- **Configuration changes update:** Application title, window UI, file operations

### 2. Default Map Tiles
- **Primary:** Sweden-Raster-Z10-Z16.mbtiles
- **Fallback:** OSM-OpenCPN2-Baltic.mbtiles
- **Format:** Raster PNG tiles (not vector)

### 3. Coordinate Formats
- **Default:** DMS (Degrees-Minutes-Seconds): `57°30'45.5"N`
- **Alternative:** Decimal Degrees: `57.5126°N`
- **Configurable:** Via `config/settings.ini` and View menu
- **Input:** Application accepts BOTH formats regardless of display format
- **Output:** Formatted per user selection

### 4. Garmin Compatibility
- **Target Device:** Garmin EchoMAP 50s (and compatible models)
- **GPX Format:** 1.1 with Garmin extensions (namespaces required)
- **Export Validation:** All files validated for Garmin compatibility before save
- **Import Process:** File → Copy to `/GARMIN/GPX/` → Device Import → Saved Tracks

### 5. Architecture Pattern
- **Undo/Redo:** Command Pattern with reversible operations
- **File Handling:** GPXHandler manages I/O + validation
- **Track Management:** TrackManager maintains state + operations
- **GUI:** PyQt5 with three-panel layout (Tracks, Map, Trackpoints)
- **Configuration:** AppConfig centralizes all settings

---

## DEVELOPMENT WORKFLOW

### For Each Step:

1. **Read specification** in PROJECT_SPECIFICATION.md
2. **Execute tasks** as listed in TODO_LIST.md
3. **Write well-commented code** with docstrings
4. **Create unit tests** with timeout protection
5. **Test implementation** to verify correctness
6. **Show results** to user
7. **Get approval** before proceeding to next step
8. **If issues:** Fix before moving forward
9. **Update TODO_LIST.md** with completion status

### Code Quality Standards

✅ **Must Have:**
- Every function: Full docstring (PEP 257 format)
- Complex logic: Inline comments
- Type hints on all function parameters/returns
- Error handling for all user inputs and file operations
- Unit tests for core modules (80%+ coverage target)
- No hardcoded values (use configuration)
- No infinite loops (all loops have safety counters or use generators)

❌ **Never:**
- Silent failures (always inform user of errors)
- Guess at behavior (verify with facts)
- Skip testing (test after every implementation)
- Infinite loops or UI freezes

---

## QUICK REFERENCE

### Configuration File: `config/settings.ini`

Key sections:
```ini
[Application]
app_name = CourseStudio
version = 1.0.0

[Map]
default_mbtiles = Sweden-Raster-Z10-Z16.mbtiles

[Coordinates]
coordinate_format = dms  # or 'decimal'

[File]
create_backup = true
```

### Project Structure
```
src/
├── main.py              # Entry point
├── gui/                 # UI components
├── core/                # Business logic
├── map/                 # Map rendering
└── utils/               # Utilities

config/
├── settings.ini         # User configuration
├── constants.py         # App constants
└── app_config.py        # Config loader

tests/                   # Unit tests
doc/                     # Documentation
```

### Key Classes

- **AppConfig** - Configuration management
- **GPXHandler** - GPX file I/O
- **TrackManager** - Track operations
- **CommandHistory** - Undo/redo stack
- **MainWindow** - PyQt5 main UI
- **TrackListWidget** - Display tracks
- **TrackpointListWidget** - Display points
- **MapWidget** - Map display

---

## PHASE BREAKDOWN

| Phase | Steps | Duration | Goal |
|-------|-------|----------|------|
| **1** | 1-5 | 2-3 days | Core GPX handling + UI skeleton |
| **2** | 6-10 | 2-3 days | Display functionality (track/point lists, map) |
| **3** | 11-14 | 2-3 days | Editing operations (add/remove/rename) |
| **4** | 15-17 | 1-2 days | Undo/redo system |
| **5** | 18-23 | 2-3 days | Save, testing, refinement, deployment |

**Total Estimated Time:** 2-3 weeks of full-time development

---

## NEXT STEP: START PHASE 1

Ready to begin **Step 1: Project Structure & Configuration System**

This step will:
1. Create Python package hierarchy (`src/`, `config/`, `tests/`)
2. Implement AppConfig class for configuration management
3. Create settings.ini with all default values
4. Verify application can start with `python src/main.py`

**Time Estimate:** 1-2 hours

---

## SUCCESS CRITERIA (Final Deliverable)

When complete, the application will:

✅ Open GPX files with single or multiple tracks  
✅ Display track information (name, distance, points)  
✅ Show all trackpoints with coordinates in DMS/decimal format  
✅ Render selected track on interactive map  
✅ Add/remove individual trackpoints  
✅ Remove trackpoint ranges (start-to-point or point-to-end)  
✅ Rename tracks  
✅ Undo/redo all operations  
✅ Save modified GPX with Garmin compatibility validation  
✅ Export files that import successfully into Garmin EchoMAP 50s  
✅ Have all code well-documented and tested  
✅ Run without infinite loops or UI freezes  

---

**Ready to start development? Begin with STEP 1 in TODO_LIST.md**
