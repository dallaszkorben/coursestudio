# Implementation Notes

**Purpose:** Record design decisions, discoveries, and lessons learned during development

**Started:** 2026-09-20  
**Phase:** 1 (Foundation & Core GPX Handling)  

---

## Design Decisions

### [2026-09-20] Documentation Maintenance as First Priority

**Decision:** Create DOCUMENTATION_MAINTENANCE.md file before any code

**Rationale:** 
- Prevents documentation drift
- Ensures all learnings are captured
- Maintains cross-reference consistency
- Enforces discipline in documentation updates

**Impact:**
- Requires discipline to update docs when code changes
- Prevents accumulated technical debt in documentation
- Makes future maintenance easier

**Related Files:**
- DOCUMENTATION_MAINTENANCE.md
- PROJECT_SPECIFICATION.md
- ARCHITECTURE.md

### [2026-09-20] Configuration System as First Implementation

**Decision:** Implement complete configuration system before any GUI

**Rationale:**
- All application behavior needs configuration access
- Allows entire system to be customized post-deployment
- Per user requirement: app_name, map tiles, coordinate format configurable
- Must be done early to avoid hardcoding later

**Implementation:**
- constants.py: 100+ application constants with detailed comments
- app_config.py: 300+ lines, thread-safe configuration loader
- settings.ini: 11 configuration sections with defaults
- Full type conversion: int, float, bool, string auto-detection

**Impact:**
- No hardcoded values anywhere in codebase
- All user-facing parameters configurable
- Extensible for future settings
- Production-ready from day one

**Related Files:**
- config/constants.py
- config/app_config.py
- config/settings.ini

---

## Issues Resolved

### [2026-09-20] PyQt5 Window Sizing Configuration

**Issue:** Window size should be configurable but PyQt5 needs default dimensions

**Solution:** Added to settings.ini [UI] section with sensible defaults (1400x900)

**Code Reference:** src/main.py line 95-107

---

## Lessons Learned

### [2026-09-20] Lazy Import of PyQt5

**Discovery:** PyQt5 should be imported AFTER configuration loads

**Why Important:** Allows users to see status messages before GUI appears, improves startup transparency

**Implementation:** Moved PyQt5 import to line 86 in src/main.py, after config loads

**Future Note:** Apply same pattern to all heavy dependencies

---

## Technical Discoveries

### [2026-09-20] ConfigParser Encoding Issues

**Discovery:** ConfigParser reads/writes without UTF-8 by default on Windows

**Solution:** Always specify encoding='utf-8' in all file operations

**Implementation:** Added to app_config.py line 37, 176

**Impact:** Ensures coordinate format special characters (°, ', ") work on all systems

---

## Configuration Changes

| Date | Section | Key | Old Value | New Value | Reason |
|------|---------|-----|-----------|-----------|--------|
| 2026-09-20 | Application | app_name | [none] | CourseStudio | Project name per spec |
| 2026-09-20 | Map | default_mbtiles | [none] | Sweden-Raster-Z10-Z16.mbtiles | Per user requirement |
| 2026-09-20 | Coordinates | coordinate_format | [none] | dms | Default per user request |

---

## Architecture Changes

### [2026-09-20] Configuration Hierarchy Established

**Pattern:** constants.py → settings.ini → AppConfig → Application

**Structure:**
- constants.py: Hardcoded app behavior constants
- settings.ini: User-configurable parameters
- AppConfig: Centralized access point
- Application: Uses only AppConfig for settings

**Benefit:** Single source of truth for all configuration

---

## Performance Notes

### [2026-09-20] Configuration Loading

**Performance:** 
- Initial load: ~0.010s (measured in tests)
- Per-access lookup: O(1) with ConfigParser
- No noticeable impact on startup time

**Scalability:**
- Tested with 50+ keys across 9 sections
- No performance degradation expected even at 1000+ keys

---

## Testing Findings

### [2026-09-20] Unit Test Suite for AppConfig

**Results:**
- 25 tests written
- 25 tests passing
- 0 failures
- 0 skipped
- Execution time: 0.010s
- Timeout: 30s (no timeout reached)

**Coverage:**
- Configuration loading ✅
- Type conversion ✅
- Default handling ✅
- Missing keys/sections ✅
- Edge cases ✅
- Integration ✅

**Quality:** No infinite loops, comprehensive error handling

---

## Garmin Compatibility Findings

### [2026-09-20] Coordinate Format Configuration

**Finding:** DMS format requires UTF-8 encoding for degree symbol (°)

**Action:** Configured settings.ini encoding and verified in ConfigParser

**Impact:** Will need UTF-8 validation in GPX export (Step 18)

---

## Coordinate Format Discoveries

### [2026-09-20] Configuration Defaults Verified

**DMS Format Default:** 57°30'45.5"N (with proper Unicode symbols)
**Decimal Format Alternative:** 57.5126°N
**Both formats:** Configurable per user requirement

**Next Step:** Implement coordinate_formatter.py utility to convert between formats (Step 3)

---

## TODO Deviations

### [2026-09-20] No Deviations from Step 1 Specification

All acceptance criteria met exactly as specified:
- ✅ All directories created
- ✅ settings.ini has all required keys
- ✅ AppConfig class implemented
- ✅ Type conversion working
- ✅ Default fallbacks working
- ✅ Application launches
- ✅ All tests passing

---

## Documentation Updates Made

| Date | Topic | Files Updated | Reason |
|------|-------|---|---|
| 2026-09-20 | Documentation maintenance rules | DOCUMENTATION_MAINTENANCE.md | Critical reminder system before Step 1 |
| 2026-09-20 | Implementation log template | IMPLEMENTATION_NOTES.md | Established tracking system |
| 2026-09-20 | Step 1 completion | TODO_LIST.md | Marked step as complete with test results |
| 2026-09-20 | Configuration design | IMPLEMENTATION_NOTES.md | Documented configuration system rationale |

---

## Questions & Follow-ups

### [2026-09-20] Configuration File Location

**Question:** Should settings.ini be copied to user home directory on first run?

**Decision:** Keep in project root for now (simplifies development), revisit in Phase 5 for distribution

**Reference:** TODO Step 23 (deployment phase)

---

## Future Considerations

### [2026-09-20] Configuration Migration

**Note:** If config structure changes in future versions, need migration system

**File:** Create config/migrations.py for version management (post-1.0)

### [2026-09-20] Configuration Validation

**Note:** Should add JSON schema for settings.ini validation

**File:** Could create config/schema.json for optional validation

---

### [2026-09-20] Virtual Environment Recreation

**Action:** Recreated venv after user deletion

**Status:** ✅ COMPLETE
- Python 3.12.3
- All dependencies installed and verified
- 25/25 tests passing
- Application launches successfully
- Step 1 code unchanged and working

**Files Created:**
- requirements.txt (with pinned versions)
- INSTALLATION.md (150+ line guide)
- activate_venv.sh (helper script)

---

### [2026-09-20] Application Window Verification

**User Report:** "Window opened but stayed black, no menu, no nothing"

**Analysis:** This is CORRECT and EXPECTED ✅

**Reason:** Step 1 is foundation only - creates minimal placeholder window
- src/main.py line 110-125: Creates empty QMainWindow
- No UI components added yet
- Menu, toolbar, panels come in Step 5

**Status:** Working as designed ✅

---

---

## Hard Problems Encountered

**See also:** [Hard Problems and Solutions](HARD_PROBLEMS_AND_SOLUTIONS.md) ⭐⭐⭐

During development beyond Phase 1, several complex issues were encountered:

- **UI state sync problems** - Map, list, and toolbar selections getting out of sync
- **Signal chain confusion** - Root causes hidden far away in signal chains
- **Coordinate system transformations** - Converting between GPS, Web Mercator, and TMS coordinates
- **PyQt5 size constraint conflicts** - Parent and child size constraints interacting unexpectedly
- **Cached value invalidation** - Track distance not updating after edits
- **Index synchronization** - Table row indices diverging from data list after deletions

Each problem in the linked document includes:
1. What went wrong (symptoms)
2. Failed attempts (what didn't work)
3. Root cause analysis (why it failed)
4. Final solution (what actually worked)
5. Key learning (non-obvious connection)

Critical reading for understanding non-obvious system gotchas and preventing regression.

---

**Last Updated:** 2026-10-06  
**Current Phase:** Complete (Phases 1-11 implemented)  
**Status:** Production-ready with comprehensive hard problem documentation

---

## Implementation Decisions: File Management & Status Display

### [2026-10-20] Close MBTiles File Feature

**Decision:** Implement close functionality with dual file management

**Rationale:**
- MBTiles and GPX files are interdependent (no map = can't display tracks)
- When user closes MBTiles, GPX should close too to prevent confusing state
- User needs confirmation dialog to prevent accidental data loss
- Status bar should always show both file states

**Key Design Choices:**
1. GPX closes automatically with MBTiles (fail-safe)
2. Guard checks prevent operations without required resources
3. Crosshair enable/disable tied to MBTiles availability
4. "Open GPX" disabled when no MBTiles (logical constraint)

**Lessons Learned:**
- Enable/disable checks must happen at multiple points (defense in depth)
- Configuration preferences should be stored but only applied when resources available
- Initialization order matters: disable features first, enable only when ready

### [2026-10-20] Status Bar Architecture

**Decision:** Fixed-position status bar with permanent file information and flexible temporary messages

**Rationale:**
- Users need to always see which files are loaded (never pushed off screen)
- Separators should never flicker/disappear (visual stability)
- Temporary feedback messages need flexible space but shouldn't cover permanent info
- Future features need reserved spaces with no redesign required

**Key Design Choices:**
1. Use `addPermanentWidget()` for fixed positions (MBTiles, GPX, separators)
2. Use `addWidget()` with stretch for flexible temporary message area
3. Reserved positions start at width 0 (hidden until needed)
4. QTimer handles auto-clearing temporary messages

**Lessons Learned:**
- Permanent widgets must be added in reverse order for correct positioning
- Separators need to be managed independently from their adjacent widgets
- QTimer avoids blocking UI during timeout

---

**Last Updated:** 2026-10-20  
**Current Phase:** Complete (Phases 1-11 implemented)  
**Status:** See project_specification.md for functional requirements


### [2026-10-21] Background Thread Workers for UI-Blocking Operations

**Decision:** Use QThread workers for long-running operations (Prune Points, Zoom Generation)

**Rationale:**
- Prune algorithm processes 1000+ trackpoints → can block UI for several seconds
- User expects responsive progress feedback (progress bar, cancel button)
- Qt's main thread cannot process events while algorithm runs → UI freezes
- Solution: Move algorithm to background thread, use signals for updates

**Implementation Pattern (PruneWorker):**
1. Create worker class (extends QObject, not QThread)
2. Define signals: `progress(processed, removed, kept)`, `finished(count)`, `error(msg)`, `cancelled()`
3. Move to thread: `worker.moveToThread(thread)`
4. Connect signals to slots before starting: `worker.progress.connect(dialog.update_progress)`
5. Start thread: `thread.start()`
6. Worker runs in separate thread; main thread stays responsive
7. Progress updates trigger Qt signals → UI updates in main thread

**Key Design Choices:**
1. Worker receives progress callbacks: `progress_callback(processed, removed, kept)`
2. Cancellation via flag: `worker.cancel()` sets `_cancel_requested = True`, loop checks it
3. Dialog stores references: `self.prune_worker = worker` prevents garbage collection
4. Timer monitors cancellation: Check every 500ms if user clicked Cancel button

**Lessons Learned:**
- Signals MUST be connected before thread starts (otherwise signals are ignored)
- Do NOT extend QThread; extend QObject and moveToThread() instead (Qt best practice)
- Worker methods run in thread context; access to UI only via signals
- Progress callbacks allow algorithm to remain agnostic of UI (clean separation)
- Cancel flags checked in loop allow graceful shutdown (no exceptions needed)

---

### [2026-10-21] MBTiles Auto-Save on Zoom Generation

**Decision:** Generated zoom levels are automatically committed to mbtiles file via SQLite transactions

**Rationale:**
- User generates zoom level Z5 → expects to close app and reopen with Z5 still there
- Tiles should be persisted atomically (either all written or none, no partial state)
- Temporary database prevents orphaned incomplete tiles if generation crashes

**Implementation Pattern:**
1. Zoom generation creates temporary SQLite database (safe location)
2. Tiles generated to temp database (original mbtiles untouched during generation)
3. After all tiles complete: `commit_generated_tiles()` runs atomic transaction:
   - Opens real mbtiles file
   - `BEGIN TRANSACTION`
   - `INSERT OR IGNORE` all tiles from temp → real database
   - Updates metadata: `INSERT OR REPLACE INTO metadata (name='generated_zoom_N', value='true')`
   - `COMMIT` (all-or-nothing)
   - Cleanup: delete temp database
4. If generation cancelled/fails: temp database cleaned up, real mbtiles untouched

**Key Design Choices:**
1. Atomic transaction ensures consistency (SQLite ACID guarantees)
2. Temporary database isolation prevents UI from seeing incomplete data
3. Metadata marking allows knowing which zooms were generated
4. `INSERT OR IGNORE` prevents duplicate tiles if regenerating same zoom

**Lessons Learned:**
- SQLite transactions are atomic at database level (crash-safe)
- Temporary files provide safety without complex state management
- Metadata table is the authoritative source for generated zoom levels
- No explicit "Save" needed—persistence happens automatically on completion

---

### [2026-10-21] Track List Update After Point Deletion

**Decision:** Pass track_list_widget reference to TrackpointListWidget to enable direct updates

**Rationale:**
- When user deletes a trackpoint, track distance changes (18 km → 17.5 km)
- Track list on left must update to show new distance and point count
- Attempted `QApplication.activeWindow()` → unreliable (wrong window returned)
- Solution: Pass direct reference at construction time

**Implementation Pattern:**
1. TrackpointListWidget constructor accepts: `track_list_widget=None` parameter
2. Store as instance variable: `self.track_list_widget = track_list_widget`
3. After trackpoint deletion: `self.track_list_widget.update_track_info(track_index)`
4. `update_track_info()` gets track from manager and refreshes single row

**Key Design Choices:**
1. Pass reference at construction (early binding, guaranteed available)
2. Call `update_track_info()` not `refresh_tracks()` (partial update, faster)
3. TrackListWidget queried from manager for fresh distance data

**Lessons Learned:**
- `activeWindow()` unreliable when multiple widgets have focus
- Direct reference passing is more reliable than dynamic window lookup
- Single-item update methods faster than full-list refresh
- UI synchronization requires cross-widget communication (accept as design pattern)

---

**Last Updated:** 2026-10-21  
**Current Phase:** Complete (Phases 1-12 implemented)  
**Status:** See project_specification.md for functional requirements
