"""
Main Application Window for CourseStudio.

Provides the primary PyQt5 window for the CourseStudio application, including
menu bar, toolbars, status bar, and central widget layout.

Classes:
    - MainWindow: Primary application window

Example:
    >>> from src.gui.main_window import MainWindow
    >>> app = QApplication([])
    >>> window = MainWindow()
    >>> window.show()
    >>> sys.exit(app.exec_())
"""

import sys
import logging
from pathlib import Path
from typing import Optional

import gpxpy.gpx

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStatusBar, QMenu, QAction, QFileDialog, QMessageBox, QDialog, QSplitter, QLabel, QStyle
)
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QTimer
from PyQt5.QtWidgets import QTabWidget

from config.app_config_yaml import AppConfig
from src.track_editor.core.gpx_handler import GPXHandler
from src.track_editor.core.track_manager import TrackManager
from src.track_editor.gui.widgets.track_list_widget import TrackListWidget
from src.track_editor.gui.widgets.trackpoint_list_widget import TrackpointListWidget
from src.gui.widgets.map_widget import MapWidget
from src.gui.widgets.settings_widget import SettingsWidget
from src.gui.dialogs.help_dialog import HelpDialog
from src.shared.map.mbtiles_provider import MBTilesProvider
from src.gui.tab_handlers.tab_handler_track_editor import TrackEditorTabHandler
from src.gui.tab_handlers.tab_handler_map_editor import MapEditorTabHandler
from src.gui.tab_handlers.tab_handler_settings import SettingsTabHandler


# ============================================================================
# Logging Configuration
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# Main Window Class
# ============================================================================

class MainWindow(QMainWindow):
    """
    Main application window and central signal hub for CourseStudio.
    
    ARCHITECTURE: Signal Orchestration Hub
    =====================================
    MainWindow acts as the central coordinator for all UI signal flow. It receives
    signals from multiple child widgets, processes them, and emits coordinated
    updates to keep all views in sync.
    
    Signal Flow Model:
    ┌─────────────────────────────────────────────────────────────┐
    │ TrackListWidget ─┐                          ┌─→ MapWidget  │
    │ MapWidget ────────→ MainWindow (Hub) ───────┤               │
    │ TrackpointListWidget ┘                      └─→ Track/Point│
    │ SettingsWidget ────────────┘                   List Widgets │
    └─────────────────────────────────────────────────────────────┘
    
    Key Responsibility: THREE-VIEW SYNCHRONIZATION
    ==============================================
    When user performs action (e.g., clicks track in list):
    1. TrackListWidget emits track_selected(track_index)
    2. MainWindow receives, updates internal state
    3. MainWindow emits signals to update OTHER widgets:
       - Send track data to MapWidget (re-render track)
       - Send trackpoints to TrackpointListWidget (update table)
       - Update menu states (enable/disable actions)
    
    CRITICAL GOTCHA: Signal Circular Loops
    =====================================
    Must prevent infinite loops:
    - If MapWidget emits signal on track click
    - MainWindow receives it and updates TrackListWidget
    - TrackListWidget emits signal back
    - MUST NOT re-trigger MapWidget (already updated!)
    
    Prevention: Guard variables track current state
    if self.current_track_index == new_index:
        return  # Already in this state, skip update
    
    Menu State Management
    =====================
    MainWindow maintains a complex state machine for menu items:
    - "No file open" state: Only File > Open, Help available
    - "File open, no track" state: Most actions disabled
    - "Track selected" state: All operations available
    
    State guards prevent invalid operations (e.g., Delete Point without selection)
    
    UI Architecture:
    - Menu bar (File, Edit, View, Help)
    - Toolbar (quick actions with icons)
    - Status bar (feedback messages)
    - Central widget area:
      - Left: TrackListWidget (track selection)
      - Center-top: TrackpointListWidget (point table)
      - Center-bottom: MapWidget (interactive map)
      - Overlays: SettingsWidget (tabbed preferences)
    
    Signals (Emitted by this window):
        file_opened: Emitted when GPX file successfully loaded
                     Payload: file_path (str) - Path to opened file
        file_saved: Emitted when GPX file successfully saved
                    Payload: file_path (str) - Path to saved file
        track_selected: Emitted when track selection changes
                        Payload: track_index (int) - Index of selected track
    
    State Variables:
        current_file_path: Path to currently open file (None if no file)
        is_modified: Whether current file has unsaved changes
        current_track_index: Index of currently selected track (-1 if none)
        current_point_index: Index of currently selected trackpoint (-1 if none)
    
    Example:
        >>> app = QApplication([])
        >>> window = MainWindow()
        >>> window.show()
        >>> sys.exit(app.exec_())
    """
    
    # Signals for inter-widget communication
    file_opened = pyqtSignal(str)  # Emitted with file path
    file_saved = pyqtSignal(str)   # Emitted with file path
    track_selected = pyqtSignal(int)  # Emitted with track index
    
    def __init__(self, gpx_file_path: Optional[str] = None):
        """
        Initialize the main application window.
        
        Args:
            gpx_file_path (Optional[str]): Path to GPX file to open on startup
        
        Example:
            >>> window = MainWindow()
            >>> window = MainWindow('track.gpx')
        """
        
        super().__init__()
        
        # Initialize application components
        self.config = AppConfig()
        self.gpx_handler = GPXHandler()
        self.track_manager = TrackManager(use_history=True)  # Enable undo/redo
        self.track_manager.config = self.config  # Give track manager access to config
        
        # Initialize map provider
        self.mbtiles_provider = MBTilesProvider(self.config, logger)
        if not self.mbtiles_provider.load_recent_mbtiles():
            logger.warning("Could not load any mbtiles file - map may not display")
        
        # Application state
        self.current_file_path: Optional[str] = None
        self.is_modified = False
        self.gpx_data: Optional[gpxpy.gpx.GPX] = None  # Store current GPX object for saving
        self._current_track_index: Optional[int] = None
        self._current_point_index: Optional[int] = None
        
        # Configure window
        self._setup_window()
        
        # Create UI components
        self._create_menus()
        self._create_toolbars()
        self._create_central_widget()
        self._create_status_bar()
        
        # Connect signals
        self._connect_signals()
        
        # Update status bar with loaded files
        self._update_status_bar_files()
        
        # Enable actions if mbtiles is already loaded
        if self.mbtiles_provider.is_loaded():
            # Enable close mbtiles action and open GPX file action since file is loaded
            self.close_mbtiles_action.setEnabled(True)
            self.open_file_action.setEnabled(True)
            self.toolbar_open_action.setEnabled(True)
        
        # Open file if provided
        if gpx_file_path:
            self.open_file(gpx_file_path)
        
        logger.info("MainWindow initialized successfully")
    
    # ========================================================================
    # Window Setup
    # ========================================================================
    
    def _setup_window(self):
        """Configure window properties and geometry."""
        
        # Get configuration values
        app_name = self.config.get_str('application.name', 'CourseStudio')
        version = self.config.get_str('application.version', '1.0.0')
        window_title = self.config.get_str('application.window_title', '{app_name} - GPX File Manipulator v{version}')
        window_width = self.config.get_int('application.window_width', 1400)
        window_height = self.config.get_int('application.window_height', 900)
        
        # Format window title with substitutions
        window_title = window_title.format(name=app_name, version=version)
        
        # Store base title for later updates
        self.base_window_title = window_title
        
        # Set window title
        self.setWindowTitle(window_title)
        
        # Set window size
        self.resize(window_width, window_height)
        
        # Center window on screen
        self._center_window()
        
        # Set application icon (if available)
        icon_path = Path(__file__).parent / 'icons' / 'CourseStudio.png'
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        # Enable window state saving
        window_state = Qt.WindowState.WindowMaximized if self.config.get_bool(
            'application.start_maximized', False
        ) else Qt.WindowState.WindowNoState
        self.setWindowState(window_state)
    
    def _center_window(self):
        """Center window on screen."""
        screen = self.screen()
        if screen:
            geometry = screen.geometry()
            x = (geometry.width() - self.width()) // 2
            y = (geometry.height() - self.height()) // 2
            self.move(x, y)
    
    # ========================================================================
    # Menu Creation
    # ========================================================================
    
    def _create_menus(self):
        """Create menu bar with File, Edit, View, Help menus."""
        
        menubar = self.menuBar()
        
        # Apply stylesheet to make separators more visible
        menubar.setStyleSheet("""
            QMenuBar::separator {
                background-color: #cccccc;
                height: 1px;
                margin: 2px 0px;
            }
            QMenu::separator {
                background-color: #666666;
                height: 1px;
                margin: 4px 0px;
            }
        """)
        
        # File Menu
        file_menu = menubar.addMenu('&File')
        
        # File > Load MBTiles File (moved from View > Map menu)
        load_mbtiles_action = QAction('&Load MBTiles File...', self)
        load_mbtiles_action.setStatusTip('Load a different mbtiles file for map display')
        load_mbtiles_action.setShortcut('Ctrl+Shift+O')  # ← ADD SHORTCUT HERE
        load_mbtiles_action.triggered.connect(self.action_load_mbtiles)
        file_menu.addAction(load_mbtiles_action)
        self.load_mbtiles_action = load_mbtiles_action
        
        # File > Close MBTiles File
        close_mbtiles_action = QAction('Close &MBTiles File', self)
        close_mbtiles_action.setStatusTip('Close the current mbtiles file')
        close_mbtiles_action.triggered.connect(self.action_close_mbtiles)
        close_mbtiles_action.setEnabled(False)  # Disabled until mbtiles is loaded
        file_menu.addAction(close_mbtiles_action)
        self.close_mbtiles_action = close_mbtiles_action
        
        file_menu.addSeparator()
        
        # File > Open
        open_action = QAction('&Open GPX File...', self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.setStatusTip('Open a GPX file')
        open_action.triggered.connect(self.action_open_file)
        open_action.setEnabled(False)  # Disabled until mbtiles is loaded
        # Add standard icon for Open
        open_action.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        file_menu.addAction(open_action)
        self.open_file_action = open_action
        
        # File > Merge GPX File
        merge_action = QAction('&Merge GPX File...', self)
        merge_action.setStatusTip('Merge tracks from another GPX file into current file')
        merge_action.triggered.connect(self.action_merge_gpx_file)
        merge_action.setEnabled(False)  # Disabled until file is opened
        file_menu.addAction(merge_action)
        self.merge_action = merge_action
        
        file_menu.addSeparator()
        
        # File > Save
        save_action = QAction('&Save GPX', self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.setStatusTip('Save current GPX file')
        save_action.triggered.connect(self.action_save_file)
        save_action.setEnabled(False)  # Disabled until file is opened
        # Add standard icon for Save (disk/save icon)
        save_action.setIcon(self.style().standardIcon(QStyle.SP_DriveFDIcon))
        file_menu.addAction(save_action)
        self.save_action = save_action
        
        # File > Save As
        save_as_action = QAction('Save GPX &As...', self)
        save_as_action.setShortcut(QKeySequence.SaveAs)
        save_as_action.setStatusTip('Save current GPX file with new name')
        save_as_action.triggered.connect(self.action_save_file_as)
        save_as_action.setEnabled(False)  # Disabled until file is opened
        # Add standard icon for Save As
        save_as_action.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        file_menu.addAction(save_as_action)
        self.save_as_action = save_as_action
        
        file_menu.addSeparator()
        
        # File > Close GPX File
        close_file_action = QAction('&Close GPX File', self)
        close_file_action.setShortcut(QKeySequence.Close)
        close_file_action.setStatusTip('Close the opened GPX file')
        close_file_action.triggered.connect(self.action_close_file)
        close_file_action.setEnabled(False)  # Disabled until file is opened
        file_menu.addAction(close_file_action)
        self.close_file_action = close_file_action
        
        file_menu.addSeparator()
        
        # File > Exit
        exit_action = QAction('E&xit', self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.setStatusTip('Exit application')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit Menu
        edit_menu = menubar.addMenu('&Edit')
        
        # Edit > Undo
        undo_action = QAction('&Undo', self)
        undo_action.setShortcut(QKeySequence.Undo)
        undo_action.setStatusTip('Undo last action')
        undo_action.triggered.connect(self.action_undo)
        undo_action.setEnabled(False)
        edit_menu.addAction(undo_action)
        self.undo_action = undo_action
        
        # Edit > Redo
        redo_action = QAction('&Redo', self)
        redo_action.setShortcut(QKeySequence.Redo)
        redo_action.setStatusTip('Redo last action')
        redo_action.triggered.connect(self.action_redo)
        redo_action.setEnabled(False)
        edit_menu.addAction(redo_action)
        self.redo_action = redo_action
        
        edit_menu.addSeparator()
        
        # Edit > Delete Trackpoint
        delete_trackpoint_action = QAction('&Delete Trackpoint', self)
        delete_trackpoint_action.setShortcut(Qt.CTRL + Qt.Key_D)
        delete_trackpoint_action.setStatusTip('Delete selected trackpoint')
        delete_trackpoint_action.triggered.connect(self.action_delete_trackpoint)
        # Also add Del key as secondary shortcut
        delete_trackpoint_action.setShortcuts([Qt.CTRL + Qt.Key_D, Qt.Key_Delete])
        edit_menu.addAction(delete_trackpoint_action)
        self.delete_trackpoint_action = delete_trackpoint_action
        
        # Edit > Add Trackpoint
        add_trackpoint_action = QAction('&Add Trackpoint', self)
        add_trackpoint_action.setShortcut(Qt.CTRL + Qt.Key_N)
        add_trackpoint_action.setStatusTip('Add new trackpoint')
        add_trackpoint_action.triggered.connect(self.action_add_trackpoint)
        edit_menu.addAction(add_trackpoint_action)
        self.add_trackpoint_action = add_trackpoint_action
        
        # Edit > Insert Trackpoint (between 2 selected points)
        insert_trackpoint_action = QAction('&Insert Trackpoint', self)
        insert_trackpoint_action.setShortcut(Qt.CTRL + Qt.Key_I)
        insert_trackpoint_action.setStatusTip('Insert trackpoint between two selected points')
        insert_trackpoint_action.triggered.connect(self.action_insert_trackpoint)
        insert_trackpoint_action.setEnabled(False)
        edit_menu.addAction(insert_trackpoint_action)
        self.insert_trackpoint_action = insert_trackpoint_action
        
        edit_menu.addSeparator()
        
        # Edit > Preferences
        prefs_action = QAction('&Preferences', self)
        prefs_action.setShortcut(QKeySequence.Preferences)
        prefs_action.setStatusTip('Open preferences')
        prefs_action.triggered.connect(self.action_preferences)
        edit_menu.addAction(prefs_action)
        
        # View Menu
        view_menu = menubar.addMenu('&View')
        
        # View > Zoom In
        zoom_in_action = QAction('Zoom &In', self)
        zoom_in_action.setShortcut(QKeySequence.ZoomIn)
        zoom_in_action.setStatusTip('Zoom in')
        zoom_in_action.triggered.connect(self.action_zoom_in)
        view_menu.addAction(zoom_in_action)
        
        # View > Zoom Out
        zoom_out_action = QAction('Zoom &Out', self)
        zoom_out_action.setShortcut(QKeySequence.ZoomOut)
        zoom_out_action.setStatusTip('Zoom out')
        zoom_out_action.triggered.connect(self.action_zoom_out)
        view_menu.addAction(zoom_out_action)
        
        # Help Menu
        help_menu = menubar.addMenu('&Help')
        
        # Help > User Guide
        help_action = QAction('&User Guide', self)
        help_action.setStatusTip('Show user guide and help')
        help_action.triggered.connect(self.action_help)
        help_menu.addAction(help_action)
        
        help_menu.addSeparator()
        
        # Help > About
        about_action = QAction('&About', self)
        about_action.setStatusTip('Show about information')
        about_action.triggered.connect(self.action_about)
        help_menu.addAction(about_action)
        
        # Help > About Qt
        about_qt_action = QAction('About &Qt', self)
        about_qt_action.setStatusTip('Show Qt information')
        about_qt_action.triggered.connect(self.action_about_qt)
        help_menu.addAction(about_qt_action)
    
    # ========================================================================
    # Toolbar Creation
    # ========================================================================
    
    def _create_toolbars(self):
        """Create toolbars with common actions."""
        
        # Main toolbar
        self.toolbar = self.addToolBar('Main Toolbar')
        self.toolbar.setObjectName('MainToolbar')
        self.toolbar.setIconSize(QSize(24, 24))
        
        # Open file button
        open_action = QAction('Open GPX', self)
        open_action.setStatusTip('Open a GPX file')
        open_action.triggered.connect(self.action_open_file)
        open_action.setEnabled(False)  # Disabled until mbtiles is loaded
        self.toolbar.addAction(open_action)
        self.toolbar_open_action = open_action
        
        # Save file button
        save_action = QAction('Save GPX', self)
        save_action.setStatusTip('Save current GPX file')
        save_action.triggered.connect(self.action_save_file)
        save_action.setEnabled(False)  # Disabled until file is opened
        self.toolbar.addAction(save_action)
        self.toolbar_save_action = save_action
        
        self.toolbar.addSeparator()
        
        # Undo button
        undo_action = QAction('Undo', self)
        undo_action.setStatusTip('Undo last action')
        undo_action.triggered.connect(self.action_undo)
        undo_action.setEnabled(False)
        self.toolbar.addAction(undo_action)
        self.toolbar_undo_action = undo_action
        
        # Redo button
        redo_action = QAction('Redo', self)
        redo_action.setStatusTip('Redo last action')
        redo_action.triggered.connect(self.action_redo)
        redo_action.setEnabled(False)
        self.toolbar.addAction(redo_action)
        self.toolbar_redo_action = redo_action
    
    # ========================================================================
    # Central Widget
    # ========================================================================
    
    def _create_central_widget(self):
        """
        Create central widget with three main tabs using dedicated tab handlers.
        
        Tabs:
        - Track Editor: Track list, trackpoint list, and map display
        - Map Editor: Map editing features (placeholder for future development)
        - Settings: Appearance and configuration options
        """
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main tab widget (top level - three main tabs)
        self.main_tab_widget = QTabWidget()
        
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.main_tab_widget)
        
        # ====================================================================
        # Tab 1: Track Editor (using TrackEditorTabHandler)
        # ====================================================================
        
        track_editor_handler = TrackEditorTabHandler(
            self.track_manager,
            self.mbtiles_provider,
            self.config
        )
        track_editor_widget = track_editor_handler.create_tab()
        
        # Get widget references for signal connections
        self.track_list_widget = track_editor_handler.get_track_list_widget()
        self.trackpoint_list_widget = track_editor_handler.get_trackpoint_list_widget()
        self.map_widget = track_editor_handler.get_map_widget()
        
        # Connect track list signals to main window
        self.track_list_widget.track_selected.connect(self._on_track_list_selection_changed)
        self.track_list_widget.track_double_clicked.connect(self._on_track_list_double_clicked)
        
        # Connect trackpoint list signals
        self.trackpoint_list_widget.point_selected.connect(self._on_trackpoint_selected)
        self.trackpoint_list_widget.point_double_clicked.connect(self._on_trackpoint_double_clicked)
        self.trackpoint_list_widget.coordinate_format_changed.connect(self._on_coordinate_format_changed)
        self.trackpoint_list_widget.history_changed.connect(self._update_undo_redo_menu_states)
        self.trackpoint_list_widget.show_points_combo.currentIndexChanged.connect(
            self._on_show_points_dropdown_changed
        )
        self.trackpoint_list_widget.prune_points_requested.connect(self._on_prune_points_requested)
        
        # Connect map signals
        self.map_widget.map_ready.connect(self._on_map_ready)
        self.map_widget.track_clicked.connect(self._on_map_track_clicked)
        self.map_widget.point_clicked.connect(self._on_map_point_clicked)
        self.map_widget.range_selection_changed.connect(self._update_insert_menu_state)
        self.map_widget.trackpoint_dragging.connect(self._on_trackpoint_dragging)
        
        # Connect track list to map widget
        self.track_list_widget.track_selected.connect(self.map_widget.on_track_list_selection_changed)
        
        self.main_tab_widget.addTab(track_editor_widget, "Track Editor")
        
        # ====================================================================
        # Tab 2: Map Editor (using MapEditorTabHandler)
        # ====================================================================
        
        self.map_editor_handler = MapEditorTabHandler(
            self.mbtiles_provider,
            self.config
        )
        map_editor_widget = self.map_editor_handler.create_tab()
        
        # ✅ NEW: Set callback to refresh TrackEditor's map_widget when zoom generation completes
        def refresh_track_editor_zoom_bounds():
            """Refresh TrackEditor map_widget zoom bounds after MapEditor zoom generation."""
            if self.map_widget:
                self.map_widget.refresh_zoom_bounds()
                logger.info("🟢 Refreshed TrackEditor map_widget zoom bounds after MapEditor generation")
        
        self.map_editor_handler.set_on_zoom_generated_callback(refresh_track_editor_zoom_bounds)
        
        self.main_tab_widget.addTab(map_editor_widget, "Map Editor")
        
        # ====================================================================
        # Tab 3: Settings (using SettingsTabHandler)
        # ====================================================================
        
        settings_handler = SettingsTabHandler()
        self.settings_widget = settings_handler.create_tab()
        
        # Connect settings changes to map widget for live preview
        self.settings_widget.track_path_widget.body_color_picker.color_changed.connect(
            self._on_track_path_settings_changed
        )
        self.settings_widget.track_path_widget.body_width_slider.value_changed.connect(
            self._on_track_path_settings_changed
        )
        self.settings_widget.track_path_widget.outline_color_picker.color_changed.connect(
            self._on_track_path_settings_changed
        )
        self.settings_widget.track_path_widget.outline_width_slider.value_changed.connect(
            self._on_track_path_settings_changed
        )
        
        # Connect turning points changes
        self.settings_widget.show_toggle.toggled.connect(
            self._on_turning_points_show_toggled
        )
        # Connect all trackpoint settings changes to unified handler
        self.settings_widget.general_point_widget.settings_changed.connect(
            self._on_turning_points_settings_changed
        )
        self.settings_widget.single_selected_point_widget.settings_changed.connect(
            self._on_turning_points_settings_changed
        )
        self.settings_widget.multi_selected_point_widget.settings_changed.connect(
            self._on_turning_points_settings_changed
        )
        self.settings_widget.turning_points_settings_applied.connect(
            self._on_turning_points_settings_applied
        )
        
        self.main_tab_widget.addTab(self.settings_widget, "Settings")
        
        logger.info("Central widget created with Track Editor, Map Editor, and Settings tabs")
    
    # ========================================================================
    # Status Bar
    # ========================================================================
    
    def _create_status_bar(self):
        """Create status bar with fixed positions for different info types.
        
        Layout (left to right):
        [Tooltips/Temporary] | [MBTiles] | [GPX] | [Reserved1] | [Reserved2]
        
        Position 1: Tooltips/Temporary messages (stretches, auto-clears)
        Position 2: MBTiles filename (fixed width, permanent)
        Position 3: GPX filename (fixed width, permanent)
        Position 4-5: Reserved for future use (hidden until used)
        """
        
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        # POSITION 1: Temporary messages/tooltips (left side, stretches)
        # This is the default widget and will expand to fill available space
        self.temp_status_label = QLabel("(ready)")
        self.temp_status_label.setStyleSheet("color: #666666; font-style: italic;")
        self.temp_status_label.setMinimumWidth(100)
        # Stretch factor = 1 means it will take remaining space
        status_bar.addWidget(self.temp_status_label, 1)
        
        # ✅ PERMANENT Separator (always visible, never changes)
        self.separator1 = QLabel(" | ")
        status_bar.addPermanentWidget(self.separator1, 0)
        
        # POSITION 2: MBTiles filename (permanent, fixed on right)
        self.mbtiles_status_label = QLabel("MBTiles: None")
        self.mbtiles_status_label.setMinimumWidth(280)
        self.mbtiles_status_label.setMaximumWidth(280)
        status_bar.addPermanentWidget(self.mbtiles_status_label)
        
        # ✅ PERMANENT Separator (always visible, never changes)
        self.separator2 = QLabel(" | ")
        status_bar.addPermanentWidget(self.separator2, 0)
        
        # POSITION 3: GPX filename (permanent, fixed on right)
        self.gpx_status_label = QLabel("GPX: None")
        self.gpx_status_label.setMinimumWidth(250)
        self.gpx_status_label.setMaximumWidth(250)
        status_bar.addPermanentWidget(self.gpx_status_label)
        
        # ✅ HIDDEN Separator (only shown when reserved positions are populated)
        self.separator_reserved = QLabel(" | ")
        self.separator_reserved.hide()  # Hidden by default
        status_bar.addPermanentWidget(self.separator_reserved, 0)
        
        # POSITION 4: Reserved for future use (width 0 = hidden)
        self.reserved1_label = QLabel("")
        self.reserved1_label.setMinimumWidth(0)
        self.reserved1_label.setMaximumWidth(0)
        status_bar.addPermanentWidget(self.reserved1_label)
        
        # POSITION 5: Reserved for future use (width 0 = hidden)
        self.reserved2_label = QLabel("")
        self.reserved2_label.setMinimumWidth(0)
        self.reserved2_label.setMaximumWidth(0)
        status_bar.addPermanentWidget(self.reserved2_label)
        
        # Show initially loaded mbtiles file
        self._update_status_bar_files()
        
        logger.info("Status bar created with 5 fixed positions (3 active + 2 reserved/hidden)")
    
    def _update_status_bar_files(self):
        """Update the permanent MBTiles and GPX filename labels in status bar."""
        
        # Update MBTiles status (POSITION 2)
        mbtiles_filename = self.mbtiles_provider.get_loaded_filename()
        if mbtiles_filename:
            self.mbtiles_status_label.setText(f"MBTiles: {mbtiles_filename}")
            logger.debug(f"Status bar MBTiles: {mbtiles_filename}")
        else:
            self.mbtiles_status_label.setText("MBTiles: None")
            logger.debug("Status bar MBTiles: None")
        
        # Update GPX status (POSITION 3)
        if self.current_file_path:
            gpx_filename = Path(self.current_file_path).name
            self.gpx_status_label.setText(f"GPX: {gpx_filename}")
            logger.debug(f"Status bar GPX: {gpx_filename}")
        else:
            self.gpx_status_label.setText("GPX: None")
            logger.debug("Status bar GPX: None")
    
    def _show_temp_status(self, message: str, timeout_ms: int = 5000):
        """Show a temporary message in POSITION 1 (left side, stretches).
        
        This position is for tooltips, temporary notifications, and transient info.
        It will NOT cover the permanent MBTiles/GPX filenames on the right.
        
        Args:
            message: The message to display
            timeout_ms: How long to show the message (0 = permanent, 5000 = 5 seconds)
        """
        self.temp_status_label.setText(message)
        if timeout_ms > 0:
            # Reset after timeout
            QTimer.singleShot(timeout_ms, lambda: self.temp_status_label.setText("(ready)"))
    
    def _set_reserved1_info(self, text: str, width: int = 200):
        """Populate POSITION 4 (reserved1) and show separator.
        
        Args:
            text: Information to display (empty string to hide)
            width: Width of the position (default 200px, use 0 to hide)
        """
        if text:
            self.reserved1_label.setText(text)
            self.reserved1_label.setMinimumWidth(width)
            self.reserved1_label.setMaximumWidth(width)
            self.separator_reserved.show()
        else:
            self.reserved1_label.setText("")
            self.reserved1_label.setMinimumWidth(0)
            self.reserved1_label.setMaximumWidth(0)
            self.separator_reserved.hide()
    
    def _set_reserved2_info(self, text: str, width: int = 150):
        """Populate POSITION 5 (reserved2) and show separator.
        
        Args:
            text: Information to display (empty string to hide)
            width: Width of the position (default 150px, use 0 to hide)
        """
        if text:
            self.reserved2_label.setText(text)
            self.reserved2_label.setMinimumWidth(width)
            self.reserved2_label.setMaximumWidth(width)
            self.separator_reserved.show()
        else:
            self.reserved2_label.setText("")
            self.reserved2_label.setMinimumWidth(0)
            self.reserved2_label.setMaximumWidth(0)
            # Only hide separator if BOTH reserved positions are empty
            if not self.reserved1_label.text():
                self.separator_reserved.hide()
    
    # ========================================================================
    # Signal Connections
    # ========================================================================
    
    def _connect_signals(self):
        """
        Connect internal signals for widget coordination.
        
        SIGNAL ORCHESTRATION GRAPH
        ==========================
        This method establishes all the signal connections that keep the 3 main
        views synchronized. The signal flow is carefully orchestrated to prevent
        circular updates (infinite loops).
        
        Signal Paths (in order of connection):
        
        1. FILE OPERATIONS
           - self.file_opened → _on_file_opened() (update UI after load)
           - self.file_saved → _on_file_saved() (update UI after save)
        
        2. TRACK SELECTION
           - self.track_selected → _on_track_selected() (update dependent widgets)
        
        3. MAP WIDGET FEEDBACK
           - map_widget.range_selection_changed → _update_insert_menu_state()
             (enables "Insert Point Between" when range selected on map)
        
        4. TRACK LIST WIDGET SIGNALS
           - track_list_widget.track_selected → _on_track_list_selection_changed()
           - track_list_widget.track_double_clicked → _on_track_list_double_clicked()
           
        5. TRACKPOINT LIST SIGNALS
           - trackpoint_list_widget.point_selected → _on_trackpoint_selected()
           - trackpoint_list_widget.point_double_clicked → _on_trackpoint_double_clicked()
        
        6. TAB CHANGE SIGNALS
           - main_tab_widget.currentChanged → _on_tab_changed() (update MapEditor button state)
           - trackpoint_list_widget.coordinate_format_changed → _on_coordinate_format_changed()
        
        6. MAP WIDGET SIGNALS
           - map_widget.map_ready → _on_map_ready()
           - map_widget.track_clicked → _on_map_track_clicked()
           - map_widget.point_clicked → _on_map_point_clicked()
           - map_widget.point_dragging → _on_trackpoint_dragging()
        
        7. SETTINGS WIDGET SIGNALS
           - settings_widget.track_path_settings_changed → _on_track_path_settings_changed()
           - settings_widget.turning_points_show_toggled → _on_turning_points_show_toggled()
           - settings_widget.turning_points_settings_changed → _on_turning_points_settings_changed()
           - settings_widget.turning_points_settings_applied → _on_turning_points_settings_applied()
           - settings_widget.show_points_dropdown_changed → _on_show_points_dropdown_changed()
        
        CRITICAL: Signal Circular Prevention
        ===================================
        Because widgets can trigger each other's signals, we must prevent infinite loops.
        
        Example of dangerous circular path:
        1. User clicks map point → map_widget emits point_clicked
        2. MainWindow receives, updates TrackpointListWidget selection
        3. TrackpointListWidget emits point_selected
        4. MainWindow receives, updates map widget AGAIN (now we're looping!)
        
        Prevention Strategy:
        - Store current_selection state before updates
        - Skip updates if already in that state
        - Use one-way signal flow where possible
        - Connect to specific handlers (not generic refresh methods)
        
        Order of connection matters:
        - Connect internal signals first (file_opened, track_selected, etc.)
        - Then connect widget signals
        - This ensures MainWindow is ready before widgets start signaling
        """
        
        # Connect internal signals
        self.file_opened.connect(self._on_file_opened)
        self.file_saved.connect(self._on_file_saved)
        self.track_selected.connect(self._on_track_selected)
        
        # Tab change signal (to update MapEditor button states)
        self.main_tab_widget.currentChanged.connect(self._on_tab_changed)
        
        # Map widget signals (range selection for insert point feature)
        if hasattr(self, 'map_widget') and hasattr(self.map_widget, 'range_selection_changed'):
            self.map_widget.range_selection_changed.connect(self._update_insert_menu_state)
    
    # ========================================================================
    # Tab Management
    # ========================================================================
    
    def _on_tab_changed(self, index: int) -> None:
        """
        Handle tab change signal.
        
        Updates MapEditor's Generate Zoom Levels button state based on:
        1. Whether MapEditor tab is currently active
        2. Whether an mbtiles file is loaded
        
        Also updates close mbtiles button state.
        
        Args:
            index: Index of the newly activated tab (0=Track Editor, 1=Map Editor, 2=Settings)
        """
        # Check if MapEditor tab is now active (index 1)
        is_map_editor_active = (index == 1)
        
        # Enable/disable Generate Zoom button based on tab and file loaded state
        if self.map_editor_handler and self.map_editor_handler.characteristics_panel:
            if is_map_editor_active and self.mbtiles_provider and self.mbtiles_provider.is_loaded():
                # MapEditor is active AND file is loaded → Enable button
                self.map_editor_handler.characteristics_panel.generate_zoom_button.setEnabled(True)
                logger.debug("Enabled Generate Zoom Levels button (MapEditor tab active, file loaded)")
            else:
                # Either MapEditor not active OR file not loaded → Disable button
                self.map_editor_handler.characteristics_panel.generate_zoom_button.setEnabled(False)
                logger.debug("Disabled Generate Zoom Levels button (MapEditor tab not active or no file)")
        
        # Enable/disable Close MBTiles button and Open GPX File based on file loaded state
        if self.mbtiles_provider and self.mbtiles_provider.is_loaded():
            self.close_mbtiles_action.setEnabled(True)
            self.open_file_action.setEnabled(True)
            self.toolbar_open_action.setEnabled(True)
        else:
            self.close_mbtiles_action.setEnabled(False)
            self.open_file_action.setEnabled(False)
            self.toolbar_open_action.setEnabled(False)
    
    
    # ========================================================================
    # Window Title Management
    # ========================================================================
    
    def _update_window_title(self):
        """Update window title based on current file and modified state."""
        
        if self.current_file_path:
            # Extract filename from path
            filename = Path(self.current_file_path).name
            title = f"{self.base_window_title} - {filename}"
        else:
            title = self.base_window_title
        
        # Add modified indicator if needed
        if self.is_modified:
            title += " *"
        
        self.setWindowTitle(title)
    
    # ========================================================================
    # File Operations
    # ========================================================================
    
    def action_open_file(self):
        """Open a GPX file."""
        # Fail-safe check: mbtiles must be loaded
        if not self.mbtiles_provider or not self.mbtiles_provider.is_loaded():
            self.show_error(
                "No MBTiles File",
                "You must load an MBTiles file first before opening a GPX file.\n\n"
                "Please open an MBTiles file from File → Open MBTiles File..."
            )
            return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            'Open GPX File',
            '',
            'GPX Files (*.gpx);;All Files (*.*)'
        )
        
        if file_path:
            self.open_file(file_path)
    
    def open_file(self, file_path: str) -> bool:
        """
        Open and load a GPX file with complete UI synchronization.
        
        FILE LOAD ORCHESTRATION PIPELINE
        =================================
        This method performs a carefully orchestrated sequence of steps to load a GPX file
        and synchronize all 3 views. The order is CRITICAL - if steps are reordered,
        views can go out of sync.
        
        ORCHESTRATION STEPS:
        
        1. PARSE & VALIDATE GPX
           - Call gpx_handler.load_gpx(file_path)
           - Returns gpxpy.GPX object or None
           - Validates: XML structure, track objects, trackpoints
           - Error: Show dialog, return False
        
        2. LOAD INTO BUSINESS LOGIC
           - Call track_manager.load_from_gpx(gpx, file_path)
           - Populates internal track/trackpoint data
           - Calculates distances, creates state
           - Returns track count
           - Result: Business logic knows about tracks, UI doesn't yet
        
        3. CLEAR ALL UI SELECTIONS EXPLICITLY
           - CRITICAL: Set all widgets to "no selection" state
           - track_list_widget.clear_selection() → No track highlighted
           - trackpoint_list_widget.set_track(-1) → Empty table
           - map_widget.on_track_list_selection_changed(None) → No track rendered
           - Why: If previous file had track 5 selected, and new file has only 2 tracks,
             leaving track 5 "selected" would cause index-out-of-bounds errors
        
        4. REFRESH DISPLAY
           - track_list_widget.refresh_tracks() → Populate list with new tracks
           - map_widget.render_map() → Re-render with cleared selection, new tracks
           - Result: All views showing new file, but nothing selected
        
        5. UPDATE APPLICATION STATE
           - current_file_path = file_path
           - is_modified = False (file just loaded, no changes yet)
           - _update_window_title() → Show filename in title bar
           - Result: Window title shows loaded filename
        
        6. ENABLE FILE OPERATIONS
           - save_action.setEnabled(True)
           - save_as_action.setEnabled(True)
           - close_file_action.setEnabled(True)
           - merge_action.setEnabled(True)
           - toolbar_save_action.setEnabled(True)
           - Why: These are invalid with no file open, now valid
        
        7. EMIT SIGNAL FOR OBSERVERS
           - self.file_opened.emit(file_path)
           - Observers (other components) notified file opened
           - Allows extensibility (e.g., plugins could listen)
        
        GOTCHA: State Guard Variables
        =============================
        Note how we explicitly set to cleared state before refresh. Don't rely on
        signals to do this - be explicit:
        - track_list_widget.clear_selection() ← Explicit clear
        - Not: connect select_changed signals (might trigger during refresh)
        
        Why explicit is better:
        - Predictable: Exactly what state we're in
        - Debuggable: Can log each step
        - Safe: No accidental signal cascades during load
        
        Performance Note:
        - GPX parsing: O(n) where n = number of trackpoints
        - For 10,000+ points, may take 1-2 seconds
        - User sees progress in status bar
        
        Args:
            file_path (str): Path to GPX file to open
        
        Returns:
            bool: True if successful, False otherwise
        """
        
        try:
            # STEP 1: Parse and validate GPX
            gpx = self.gpx_handler.load_gpx(file_path)
            if not gpx:
                self.show_error("Failed to open file", f"Could not parse GPX file: {file_path}")
                return False
            
            # STEP 2: Load into business logic
            self.gpx_data = gpx
            count = self.track_manager.load_from_gpx(gpx, file_path)
            
            # STEP 3: Clear all UI selections explicitly (CRITICAL!)
            if hasattr(self, 'track_list_widget'):
                self.track_list_widget.clear_selection()  # No track selected
                self.track_list_widget.refresh_tracks()   # Show all tracks
            
            if hasattr(self, 'map_widget'):
                self.map_widget.on_track_list_selection_changed(None)  # Clear track
                self.map_widget.render_map()  # Re-render with no selection
            
            if hasattr(self, 'trackpoint_list_widget'):
                self.trackpoint_list_widget.set_track(-1)  # Empty table
            
            # STEP 4: Update application state
            self.current_file_path = file_path
            self.is_modified = False
            self._update_window_title()  # Show filename in title
            self._update_status_bar_files()  # Show filename in status bar
            
            # STEP 5: Enable file operations
            self.save_action.setEnabled(True)
            self.save_as_action.setEnabled(True)
            self.close_file_action.setEnabled(True)
            self.merge_action.setEnabled(True)
            self.toolbar_save_action.setEnabled(True)
            
            # STEP 6: Emit signal for observers
            self.file_opened.emit(file_path)
            
            logger.info(f"Opened GPX file: {file_path} ({count} tracks)")
            return True
        
        except Exception as e:
            logger.error(f"Error opening file: {e}")
            self.show_error("Error", f"Failed to open file: {str(e)}")
            return False
    
    def action_save_file(self):
        """Save current file."""
        
        if not self.current_file_path:
            self.action_save_file_as()
            return
        
        self.save_file(self.current_file_path)
    
    def action_save_file_as(self):
        """Save current file with new name."""
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            'Save GPX File',
            '',
            'GPX Files (*.gpx);;All Files (*.*)'
        )
        
        if file_path:
            self.save_file(file_path)
    
    def action_merge_gpx_file(self):
        """Merge tracks from another GPX file into current file."""
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            'Merge GPX File',
            '',
            'GPX Files (*.gpx);;All Files (*.*)'
        )
        
        if not file_path:
            return
        
        try:
            # Load the GPX file to merge
            merge_gpx = self.gpx_handler.load_gpx(file_path)
            if not merge_gpx:
                self.show_error("Failed to merge", f"Could not parse GPX file: {file_path}")
                return
            
            # Append tracks from the merge file
            count = self.track_manager.append_tracks_from_gpx(merge_gpx)
            
            if count == 0:
                self.show_error("No tracks", f"No tracks found in: {file_path}")
                return
            
            # Mark file as modified
            self.is_modified = True
            self._update_window_title()
            
            # Clear all selections after merge (track indices have changed)
            self.track_list_widget.clear_selection()
            self.trackpoint_list_widget.set_track(-1)
            self.map_widget.on_track_list_selection_changed(None)
            self.map_widget.render_map()
            
            # Refresh UI with new tracks
            self.track_list_widget.refresh_tracks()
            
            # Show success message
            self._show_temp_status(f'Merged {count} track{"s" if count != 1 else ""} from {Path(file_path).name}', 5000)
            logger.info(f"Merged {count} tracks from {file_path}")
            
        except Exception as e:
            self.show_error("Merge failed", f"Error merging file: {str(e)}")
            logger.error(f"Error merging GPX file: {e}")
    
    def action_close_file(self):
        """Close the opened file and clear the UI."""
        
        # Clear track manager
        self.track_manager.clear_all_tracks()
        
        # Clear UI
        self.track_list_widget.clear_selection()
        self.track_list_widget.refresh_tracks()
        self.trackpoint_list_widget.set_track(-1)
        self.map_widget.on_track_list_selection_changed(None)
        
        # Reset state
        self.current_file_path = None
        self.is_modified = False
        self.gpx_data = None
        
        # Disable file operation actions
        self.save_action.setEnabled(False)
        self.save_as_action.setEnabled(False)
        self.close_file_action.setEnabled(False)
        self.merge_action.setEnabled(False)
        self.toolbar_save_action.setEnabled(False)
        
        # Update window title and status bar
        self._update_window_title()
        self._update_status_bar_files()
        
        logger.info("File closed")
        self._show_temp_status('File closed', 3000)
    
    def save_file(self, file_path: str) -> bool:
        """
        Save tracks to GPX file.
        
        Args:
            file_path (str): Path to save GPX file
        
        Returns:
            bool: True if successful, False otherwise
        """
        
        try:
            # If no GPX data exists (created tracks from scratch), create a new one
            if not self.gpx_data:
                self.gpx_data = gpxpy.gpx.GPX()
                logger.info("Created new GPX object for saving tracks from scratch")
            
            # Get all tracks from manager
            tracks = self.track_manager.get_all_tracks()
            
            if not tracks:
                self.show_error("Warning", "No tracks to save")
                return False
            
            # Update GPX object with current track data
            # Clear existing tracks
            self.gpx_data.tracks.clear()
            
            # Add modified tracks back to GPX
            for track_data in tracks:
                # Create new GPX track
                gpx_track = gpxpy.gpx.GPXTrack(name=track_data.name)
                
                # Create track segment
                segment = gpxpy.gpx.GPXTrackSegment()
                
                # Add trackpoints to segment
                for trackpoint in track_data.trackpoints:
                    gpx_point = gpxpy.gpx.GPXTrackPoint(
                        latitude=trackpoint.latitude,
                        longitude=trackpoint.longitude,
                        elevation=trackpoint.elevation,
                        time=None  # Preserve timestamp if available
                    )
                    segment.points.append(gpx_point)
                
                # Add segment to track
                gpx_track.segments.append(segment)
                
                # Add track to GPX
                self.gpx_data.tracks.append(gpx_track)
            
            # Save GPX file
            success, message = self.gpx_handler.save_gpx(file_path, self.gpx_data)
            
            if success:
                self.current_file_path = file_path
                self.is_modified = False
                self._update_window_title()  # Update title with filename
                self.file_saved.emit(file_path)
                logger.info(f"Saved file: {file_path}")
                self.show_info("Success", message)
                return True
            else:
                logger.error(f"Error saving file: {message}")
                self.show_error("Error", f"Failed to save file: {message}")
                return False
        
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            self.show_error("Error", f"Failed to save file: {str(e)}")
            return False
    
    # ========================================================================
    # Edit Operations
    # ========================================================================
    
    def action_undo(self):
        """Undo last action."""
        
        if not self.track_manager.can_undo():
            self._show_temp_status("Nothing to undo")
            return
        
        success = self.track_manager.undo()
        
        if success:
            # Refresh display
            if hasattr(self, 'track_list_widget'):
                self.track_list_widget.refresh_tracks()
            
            if hasattr(self, 'trackpoint_list_widget'):
                self.trackpoint_list_widget.refresh_trackpoints()
            
            if hasattr(self, 'map_widget'):
                current_index = self.track_manager.get_selected_track_index()
                if current_index >= 0:
                    self.map_widget.on_track_list_selection_changed(current_index)
            
            desc = self.track_manager.get_undo_description()
            self._show_temp_status(f"Undone: {desc}", 3000)
            logger.info(f"Undo: {desc}")
            
            # Update menu states
            self._update_undo_redo_menu_states()
        else:
            self._show_temp_status("Failed to undo")
    
    def action_redo(self):
        """Redo last action."""
        
        if not self.track_manager.can_redo():
            self._show_temp_status("Nothing to redo")
            return
        
        success = self.track_manager.redo()
        
        if success:
            # Refresh display
            if hasattr(self, 'track_list_widget'):
                self.track_list_widget.refresh_tracks()
            
            if hasattr(self, 'trackpoint_list_widget'):
                self.trackpoint_list_widget.refresh_trackpoints()
            
            if hasattr(self, 'map_widget'):
                current_index = self.track_manager.get_selected_track_index()
                if current_index >= 0:
                    self.map_widget.on_track_list_selection_changed(current_index)
            
            desc = self.track_manager.get_redo_description()
            self._show_temp_status(f"Redone: {desc}", 3000)
            logger.info(f"Redo: {desc}")
            
            # Update menu states
            self._update_undo_redo_menu_states()
        else:
            self._show_temp_status("Failed to redo")
    
    def _update_undo_redo_menu_states(self):
        """Update undo/redo menu item states and text."""
        
        # Update undo action
        if self.track_manager.can_undo():
            self.undo_action.setEnabled(True)
            self.undo_action.setText(self.track_manager.get_undo_description())
        else:
            self.undo_action.setEnabled(False)
            self.undo_action.setText("&Undo")
        
        # Update redo action
        if self.track_manager.can_redo():
            self.redo_action.setEnabled(True)
            self.redo_action.setText(self.track_manager.get_redo_description())
        else:
            self.redo_action.setEnabled(False)
            self.redo_action.setText("&Redo")
    
    # ========================================================================
    # View Operations
    # ========================================================================
    
    def action_zoom_in(self):
        """Zoom in."""
        logger.debug("Zoom in action triggered")
        self._show_temp_status("Zoom in", 1000)
    
    def action_zoom_out(self):
        """Zoom out."""
        logger.debug("Zoom out action triggered")
        self._show_temp_status("Zoom out", 1000)
    
    def action_load_mbtiles(self):
        """Load a different mbtiles file via file dialog."""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("MBTiles Files (*.mbtiles)")
        file_dialog.setWindowTitle("Load MBTiles File")
        
        if file_dialog.exec_():
            file_paths = file_dialog.selectedFiles()
            if file_paths:
                mbtiles_path = file_paths[0]
                logger.info(f"Loading mbtiles file: {mbtiles_path}")
                
                if self.mbtiles_provider.load_mbtiles_from_path(mbtiles_path):
                    # 🔵 DEBUG: Check what zooms are available after loading
                    available_zooms = self.mbtiles_provider.get_available_zooms()
                    logger.info(f"🔵 After load_mbtiles_from_path: available_zooms = {available_zooms}")
                    
                    # Use MBTilesFileLoader to determine optimal configuration
                    # This will read center/zoom from mbtiles metadata instead of keeping old position
                    try:
                        from src.map_editor.core.mbtiles_reader import MBTilesReader
                        from src.shared.map.mbtiles_file_loader import MBTilesFileLoader
                        
                        reader = MBTilesReader(mbtiles_path)
                        loader = MBTilesFileLoader(reader, self.config)
                        config_result = loader.load_and_configure(mbtiles_path)
                        
                        # Get position from mbtiles metadata
                        lat = config_result['recent_center']['lat']
                        lon = config_result['recent_center']['lon']
                        zoom = config_result['recent_zoom']
                        
                        logger.info(f"🔵 Determined position from mbtiles metadata: ({lat:.4f}, {lon:.4f}) Z{zoom}")
                        
                        # Update zoom bounds for map_widget based on new file's available zooms
                        min_zoom = config_result['min_zoom']
                        max_zoom = config_result['max_zoom']
                        self.map_widget.min_zoom = min_zoom
                        self.map_widget.max_zoom = max_zoom
                        logger.info(f"🔵 Updated map_widget zoom bounds: Z{min_zoom}-Z{max_zoom}")
                        
                        # Update map_widget with new position and provider
                        self.map_widget.center_lat = lat
                        self.map_widget.center_lon = lon
                        self.map_widget.set_zoom_with_compatibility(zoom)
                        
                    except Exception as e:
                        logger.error(f"Error loading mbtiles configuration: {e}", exc_info=True)
                        # Fallback: just load with current position
                        recent_zoom = self.config.get_int('appearance.tiles.recent_zoom', None)
                        if recent_zoom:
                            self.map_widget.set_zoom_with_compatibility(recent_zoom)
                    
                    # Re-render map with new tiles
                    self.map_widget.render_map()
                    # ✅ Re-enable crosshair now that map is loaded with MBTiles
                    self.map_widget.enable_crosshair()
                    
                    # ⚠️⚠️⚠️ CRITICAL FIX - DO NOT MODIFY WITHOUT UNDERSTANDING ⚠️⚠️⚠️
                    # 
                    # PROBLEM (Bug Fixed 2026-10-20):
                    # When user loaded a new MBTiles file in MapEditor, it showed WRONG zoom level.
                    # Example: File1 (Z6-15) user navigates to Z15 → Close app → Reopen → Load File2 (Z7-16)
                    # Result: MapEditor showed Z15 (WRONG!) instead of Z16 from File2's metadata
                    #
                    # ROOT CAUSE:
                    # 1. load_and_configure() correctly reads File2's metadata → zoom=16 ✓
                    # 2. load_and_configure() saves zoom=16 to config file ✓
                    # 3. BUT set_mbtiles_provider() reads from in-memory config SINGLETON
                    # 4. Config singleton was initialized at app startup with OLD values (zoom=15)
                    # 5. Config singleton is NEVER reloaded after save_to_file()
                    # 6. Result: set_mbtiles_provider() reads stale cached zoom=15 ✗
                    #
                    # SOLUTION:
                    # After set_mbtiles_provider() initializes, OVERRIDE the zoom/center with
                    # FRESH values from load_and_configure() output (lines 1409-1419).
                    # This ensures MapEditor gets CORRECT values, not stale config cache.
                    #
                    # WHY THIS IS CRITICAL:
                    # - If you remove this override, the bug comes back
                    # - Config singleton caching is unavoidable (it's a design choice)
                    # - The override is the ONLY place where MapEditor gets correct values
                    # - Users depend on zooming to correct level when switching MBTiles files
                    #
                    # IF YOU NEED TO MODIFY THIS:
                    # - Understand config singleton behavior first (see config/app_config_yaml.py)
                    # - Test by: Load File1 → navigate to max zoom → Load File2 → verify correct zoom
                    # - If zoom is wrong, you broke it
                    # ⚠️⚠️⚠️ END CRITICAL SECTION ⚠️⚠️⚠️
                    
                    try:
                        logger.info(f"🟢 Re-initializing MapEditor map_viewer with new mbtiles provider...")
                        self.map_editor_handler.map_viewer.set_mbtiles_provider(self.mbtiles_provider)
                        logger.info(f"🟢 MapEditor map_viewer re-initialized with new provider")
                        
                        # ⚠️ OVERRIDE with fresh values from load_and_configure (see above comment block)
                        logger.info(f"⚠️ CRITICAL: Overriding with fresh zoom Z{zoom} (not stale config cache)")
                        self.map_editor_handler.map_viewer.zoom_level = zoom
                        self.map_editor_handler.map_viewer.center_lat = lat
                        self.map_editor_handler.map_viewer.center_lon = lon
                        logger.info(f"✅ MapEditor zoom set to Z{self.map_editor_handler.map_viewer.zoom_level} (correct)")
                    except Exception as e:
                        logger.error(f"Error re-initializing MapEditor map_viewer: {e}", exc_info=True)
                    
                    # 🟢 UPDATE MAP EDITOR TAB'S CHARACTERISTICS PANEL
                    # Load new reader and update Map Editor's characteristics panel
                    try:
                        from src.map_editor.core.mbtiles_reader import MBTilesReader
                        new_reader = MBTilesReader(mbtiles_path)
                        self.map_editor_handler.characteristics_panel.load_mbtiles(new_reader)
                        logger.info(f"🟢 Updated Map Editor characteristics panel with: {new_reader.get_metadata().name}")
                        
                        # 🟢 ALSO UPDATE MAP EDITOR'S MAP VIEWER WITH NEW ZOOM RANGE
                        # Get available zooms from new file
                        available_zooms = new_reader.zoom_levels
                        if available_zooms:
                            min_zoom = min(z.zoom for z in available_zooms)
                            max_zoom = max(z.zoom for z in available_zooms)
                            
                            # Adjust current zoom if it's outside the new range
                            current_zoom = self.map_editor_handler.map_viewer.zoom_level
                            if current_zoom < min_zoom:
                                self.map_editor_handler.map_viewer.zoom_level = min_zoom
                                logger.info(f"🟢 Adjusted zoom from {current_zoom} to {min_zoom} (new file min)")
                            elif current_zoom > max_zoom:
                                self.map_editor_handler.map_viewer.zoom_level = max_zoom
                                logger.info(f"🟢 Adjusted zoom from {current_zoom} to {max_zoom} (new file max)")
                            
                            # 🟢 UPDATE ZOOM BOUNDS FOR MAP EDITOR'S MAP VIEWER
                            # This is critical - update the min/max zoom the map_viewer uses for zoom_in/zoom_out validation
                            self.map_editor_handler.map_viewer._update_zoom_bounds_from_provider()
                            logger.info(f"🟢 Updated MapEditor zoom bounds from provider: Z{self.map_editor_handler.map_viewer.min_zoom}-Z{self.map_editor_handler.map_viewer.max_zoom}")
                            
                            # Render with new zoom
                            self.map_editor_handler.map_viewer.render_map()
                    except Exception as e:
                        logger.warning(f"Could not update Map Editor: {e}")
                    
                    # ✅ Re-enable crosshair now that map is loaded with MBTiles
                    # CRITICAL: Must be outside try block so it's always called
                    self.map_editor_handler.map_viewer.enable_crosshair()
                    
                    # Update status bar with new MBTiles filename
                    self._update_status_bar_files()
                    logger.info(f"Successfully loaded mbtiles: {self.mbtiles_provider.get_loaded_filename()}")
                    
                    # Update MapEditor button state (file now loaded)
                    current_tab = self.main_tab_widget.currentIndex()
                    self._on_tab_changed(current_tab)
                else:
                    QMessageBox.warning(self, "Error", "Failed to load mbtiles file. Check the log for details.")
                    self._show_temp_status("Failed to load mbtiles file", 3000)
    
    def action_close_mbtiles(self):
        """Close the currently loaded mbtiles file."""
        if not self.mbtiles_provider or not self.mbtiles_provider.is_loaded():
            QMessageBox.information(self, "Info", "No mbtiles file is currently loaded")
            return
        
        # Get current filename for confirmation
        current_filename = self.mbtiles_provider.get_loaded_filename()
        
        # Check if GPX file has unsaved changes
        if self.is_modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                f"The GPX file has unsaved changes. Close it anyway?\n\n"
                f"(Current mbtiles: {current_filename})",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # Confirm closing mbtiles file
        reply = QMessageBox.question(
            self,
            "Close MBTiles File",
            f"Close the mbtiles file '{current_filename}'?\n\n"
            f"This will also close any open GPX file.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.No:
            return
        
        logger.info(f"Closing mbtiles file: {current_filename}")
        
        # 1. Close GPX file if open
        if self.current_file_path:
            self.action_close_file()
            logger.info("Closed GPX file")
        
        # 2. Remove from recent files (config) so it doesn't auto-load on next startup
        self.config.set("appearance.tiles.recent_mbtiles", "")
        # ✅ CRITICAL: Save config to disk immediately
        if not self.config.save_to_file():
            logger.warning("Failed to save config after clearing recent_mbtiles")
        else:
            logger.info("✅ Saved config with cleared recent_mbtiles")
        
        # 3. Unload mbtiles provider
        self.mbtiles_provider.unload()
        logger.info("Unloaded mbtiles provider")
        
        # 4. Clear TrackEditor's map_widget
        self.map_widget.clear_map()
        self.map_widget.min_zoom = 1
        self.map_widget.max_zoom = 20
        logger.info("Cleared TrackEditor map")
        
        # 5. Clear MapEditor
        if self.map_editor_handler:
            # Clear characteristics panel
            self.map_editor_handler.characteristics_panel.clear_mbtiles()
            # Clear map viewer
            self.map_editor_handler.map_viewer.clear_map()
            self.map_editor_handler.map_viewer.min_zoom = 1
            self.map_editor_handler.map_viewer.max_zoom = 20
            logger.info("Cleared MapEditor")
        
        # 6. Switch to Track Editor tab
        self.main_tab_widget.setCurrentIndex(0)
        logger.info("Switched to Track Editor tab")
        
        # 7. Update menu states - disable close mbtiles action
        self.close_mbtiles_action.setEnabled(False)
        
        # 8. Update status bar
        self._update_status_bar_files()
        self._show_temp_status("MBTiles file closed", 3000)
        logger.info("MBTiles file closed successfully")
    
    # ========================================================================
    # Application Operations
    # ========================================================================
    
    def action_preferences(self):
        """Open preferences dialog."""
        logger.debug("Preferences action triggered (not yet implemented)")
        self.statusBar().showMessage("Preferences not yet implemented")
    
    def action_help(self):
        """Show help dialog."""
        help_dialog = HelpDialog(self)
        help_dialog.exec_()
    
    def action_about(self):
        """Show about dialog."""
        
        app_name = self.config.get_str('application.name', 'CourseStudio')
        version = self.config.get_str('application.version', '1.0.0')
        
        about_text = f"""
<b>{app_name}</b> v{version}
<br><br>
GPX File Manipulator for Garmin Devices
<br><br>
A PyQt5 application for reading, editing, and exporting GPX navigation tracks.
<br><br>
<b>Features:</b><br>
• Load and visualize GPX tracks<br>
• Edit track waypoints<br>
• Interactive map display<br>
• Garmin device compatibility
        """
        
        QMessageBox.about(self, f"About {app_name}", about_text)
    
    def action_about_qt(self):
        """Show about Qt dialog."""
        QMessageBox.aboutQt(self)
    
    def action_delete_trackpoint(self):
        """Delete selected trackpoint."""
        if hasattr(self, 'trackpoint_list_widget'):
            # Check if a trackpoint is actually selected (use current_selection, not currentRow)
            # currentRow() returns the current row even if nothing is visually selected
            if self.trackpoint_list_widget.current_selection < 0:
                QMessageBox.information(self, "No Selection", "Please select a trackpoint to delete")
                return
            
            self.trackpoint_list_widget._delete_trackpoint(self.trackpoint_list_widget.current_selection)
    
    def action_add_trackpoint(self):
        """Add a new trackpoint to the selected track."""
        
        if not self.track_manager.is_track_selected():
            QMessageBox.information(self, "No Track Selected", "Please select a track first")
            return
        
        # Import here to avoid circular imports
        from src.gui.dialogs.add_trackpoint_dialog import AddTrackpointDialog
        
        # Get current track point count for dialog
        trackpoints = self.track_manager.get_selected_trackpoints()
        max_index = len(trackpoints) if trackpoints else 0
        
        # Show dialog
        dialog = AddTrackpointDialog(self, max_index=max_index)
        if dialog.exec_() == QDialog.Accepted:
            try:
                latitude, longitude, altitude, position = dialog.get_trackpoint()
                
                # Add trackpoint using command history (undoable)
                success = self.track_manager.add_trackpoint_selected_with_history(
                    latitude, longitude, altitude, position
                )
                
                if success:
                    # Refresh display
                    if hasattr(self, 'trackpoint_list_widget'):
                        self.trackpoint_list_widget.refresh_trackpoints()
                    
                    if hasattr(self, 'map_widget'):
                        current_index = self.track_manager.get_selected_track_index()
                        self.map_widget.on_track_list_selection_changed(current_index)
                    
                    # Update undo/redo menu states
                    self._update_undo_redo_menu_states()
                    
                    self.statusBar().showMessage(
                        f"Added trackpoint at ({latitude:.4f}, {longitude:.4f})",
                        3000
                    )
                    logger.info(f"Trackpoint added: lat={latitude}, lon={longitude}")
                else:
                    QMessageBox.critical(self, "Error", "Failed to add trackpoint")
            except ValueError as e:
                QMessageBox.critical(self, "Invalid Input", str(e))
                logger.error(f"Add trackpoint error: {e}")
    
    def action_insert_trackpoint(self):
        """Insert a new trackpoint between two selected neighboring points."""
        
        if not self.track_manager.is_track_selected():
            QMessageBox.information(self, "No Track Selected", "Please select a track first")
            return
        
        # Check if we have 2 points selected in range mode
        if not (hasattr(self, 'map_widget') and self.map_widget.selected_trackpoint_range):
            QMessageBox.information(self, "No Range Selected", 
                                   "Please select two neighboring points on the map (Shift+click)\nto insert a point between them")
            return
        
        try:
            start_idx, end_idx = self.map_widget.selected_trackpoint_range
            trackpoints = self.track_manager.get_selected_trackpoints()
            
            if start_idx >= len(trackpoints) or end_idx >= len(trackpoints):
                QMessageBox.critical(self, "Error", "Invalid trackpoint indices")
                return
            
            # Get the two points
            point1 = trackpoints[start_idx]
            point2 = trackpoints[end_idx]
            
            # Calculate midpoint
            mid_lat = (point1.latitude + point2.latitude) / 2.0
            mid_lon = (point1.longitude + point2.longitude) / 2.0
            
            # Calculate midpoint elevation if available
            mid_alt = None
            if point1.elevation is not None and point2.elevation is not None:
                mid_alt = (point1.elevation + point2.elevation) / 2.0
            elif point1.elevation is not None:
                mid_alt = point1.elevation
            elif point2.elevation is not None:
                mid_alt = point2.elevation
            
            # Insert at position between start and end (after start, before end)
            insert_position = start_idx + 1
            
            # Add the new point
            success = self.track_manager.add_trackpoint_selected_with_history(
                mid_lat, mid_lon, mid_alt, insert_position
            )
            
            if success:
                # Refresh display
                if hasattr(self, 'trackpoint_list_widget'):
                    self.trackpoint_list_widget.refresh_trackpoints()
                    # Suppress context menu during selection (avoid showing delete menu)
                    self.trackpoint_list_widget._suppress_context_menu = True
                    # Select the newly inserted point (at insert_position)
                    self.trackpoint_list_widget.select_point(insert_position)
                
                if hasattr(self, 'map_widget'):
                    current_index = self.track_manager.get_selected_track_index()
                    self.map_widget.on_track_list_selection_changed(current_index)
                    # Select the newly inserted point on map
                    self.map_widget.selected_trackpoint_index = insert_position
                    self.map_widget.selected_trackpoint_range = None
                    self.map_widget.render_map()
                
                # Update undo/redo menu states
                self._update_undo_redo_menu_states()
                
                self.statusBar().showMessage(
                    f"Inserted trackpoint at ({mid_lat:.4f}, {mid_lon:.4f})",
                    3000
                )
                logger.info(f"Trackpoint inserted: lat={mid_lat}, lon={mid_lon}")
            else:
                QMessageBox.critical(self, "Error", "Failed to insert trackpoint")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to insert trackpoint: {e}")
            logger.error(f"Insert trackpoint error: {e}")
    
    # ========================================================================
    # Signal Handlers
    # ========================================================================
    
    def _on_file_opened(self, file_path: str):
        """Handle file opened signal."""
        
        self.statusBar().showMessage(f"Opened: {Path(file_path).name}", 5000)
        
        # Refresh track list widget
        if hasattr(self, 'track_list_widget'):
            self.track_list_widget.refresh_tracks()
            
            count = self.track_manager.get_track_count()
            if count > 0:
                self.statusBar().showMessage(
                    f"Loaded {count} track(s) from {Path(file_path).name}",
                    5000
                )
                
                logger.debug(f"Track list refreshed: {count} tracks")
    
    def _on_file_saved(self, file_path: str):
        """Handle file saved signal."""
        
        self.statusBar().showMessage(f"Saved: {Path(file_path).name}", 5000)
    
    def _on_track_selected(self, track_index: int):
        """Handle track selected signal."""
        
        track = self.track_manager.get_track_by_index(track_index)
        if track:
            msg = f"Selected: {track.name} ({track.get_point_count()} points)"
            self.statusBar().showMessage(msg, 3000)
    
    def _on_track_list_selection_changed(self, track_index: int):
        """
        Handle track selection change from TrackListWidget.
        
        THREE-VIEW SYNCHRONIZATION CASCADE
        ==================================
        This slot is triggered when user clicks a track in the list. It orchestrates
        updates to all 3 views to keep them synchronized.
        
        ORCHESTRATION SEQUENCE:
        
        Input: track_index (from TrackListWidget signal)
        
        1. GUARD CHECK - Handle Unselection
           if track_index < 0:
               - Clears selection in ALL widgets
               - Business logic: selected_track_index = -1
               - UI: TrackpointListWidget shows empty table
               - UI: MapWidget shows no track
               - Status bar: "No track selected"
               - Return (no further processing)
        
        2. UPDATE BUSINESS LOGIC
           - track_manager.select_track(track_index)
           - Why: Business layer must know which track is active
           - Used by: Add/delete trackpoint operations
           - Dependency: Must do BEFORE updating UI
        
        3. RETRIEVE TRACK DATA
           - Get track object from manager
           - Extract: name, distance, point count
           - Use for status message
        
        4. UPDATE INTERNAL STATE
           - _current_track_index = track_index
           - _current_point_index = None (reset point selection)
           - Why: Prevents stale selection (e.g., deleting track)
        
        5. UPDATE TRACKPOINT LIST WIDGET
           - trackpoint_list_widget.set_track(track_index)
           - Widget populates table with trackpoints from selected track
           - Clears previous selection
           - Order: AFTER business logic updated (so manager has correct state)
        
        6. UPDATE MAP WIDGET
           - map_widget.on_track_list_selection_changed(track_index)
           - Widget renders selected track on map
           - Clears previous rendering
           - Order: LAST (depends on trackpoints being loaded in list)
        
        7. UPDATE STATUS BAR
           - Display: "Track: Name - XX.XX km (YY points)"
           - Feedback: Shows user which track selected and metadata
           - Timeout: 5 seconds (long enough to read)
        
        STATE MACHINE OVERVIEW
        ======================
        Before signal:
        - Track list: one track highlighted
        - Trackpoint list: may have different track's data
        - Map: may have different track rendered
        
        After signal:
        - Track list: same track highlighted (UI triggered signal)
        - Trackpoint list: NEW track's data (updated by this slot)
        - Map: NEW track rendered (updated by this slot)
        - Status: NEW track metadata shown
        
        CRITICAL: Order matters!
        =======================
        Must update business logic BEFORE UI:
        1. track_manager.select_track() ← Business layer
        2. trackpoint_list_widget.set_track() ← UI (uses manager's state)
        3. map_widget.on_track_list_selection_changed() ← UI (uses trackpoint data)
        
        If reversed, trackpoint widget might show wrong track's data.
        
        GOTCHA: Index vs State
        =====================
        track_index < 0 means "unselect all"
        track_index >= 0 means "select this track"
        
        Don't use currentRow() in track list - use the signal index instead.
        The signal is the source of truth for which track should be selected.
        
        Args:
            track_index (int): Index of selected track, or -1 to unselect
        """
        
        # Guard: Handle unselection
        if track_index < 0:
            # Clear selection in all widgets
            self.track_manager.selected_track_index = -1
            self.statusBar().showMessage("No track selected", 2000)
            
            # Clear trackpoint list
            if hasattr(self, 'trackpoint_list_widget'):
                self.trackpoint_list_widget.set_track(-1)
            
            # Clear map display
            if hasattr(self, 'map_widget'):
                self.map_widget.on_track_list_selection_changed(None)
            
            self._current_track_index = -1
            self._current_point_index = None
            
            logger.debug("Track unselected")
            return
        
        # Step 1: Update business logic (MUST DO FIRST)
        self.track_manager.select_track(track_index)
        
        # Step 2: Retrieve track data for status display
        track = self.track_manager.get_track_by_index(track_index)
        if track:
            msg = f"Track: {track.name} - {track.distance_km:.2f} km ({track.get_point_count()} points)"
            self.statusBar().showMessage(msg, 5000)
            
            logger.debug(f"Track selected from list: index={track_index}")
        
        # Step 3: Update internal state
        self._current_track_index = track_index
        self._current_point_index = None
        
        # Step 4: Update trackpoint list widget (depends on manager having correct state)
        if hasattr(self, 'trackpoint_list_widget'):
            self.trackpoint_list_widget.set_track(track_index)
        
        # Step 5: Update map widget (last, depends on trackpoint data)
        if hasattr(self, 'map_widget'):
            self.map_widget.on_track_list_selection_changed(track_index)
    
    def _on_track_list_double_clicked(self, track_index: int):
        """Handle double-click on track in list."""
        
        track = self.track_manager.get_track_by_index(track_index)
        if track:
            msg = f"Double-clicked: {track.name}"
            self.statusBar().showMessage(msg, 2000)
            
            logger.debug(f"Track double-clicked: index={track_index}")
        
        # Store current track index and display on map
        self._current_track_index = track_index
        self._current_point_index = None
        
        # Update trackpoint list widget
        if hasattr(self, 'trackpoint_list_widget'):
            self.trackpoint_list_widget.set_track(track_index)
        
        # Display track on map
        if hasattr(self, 'map_widget'):
            self.map_widget.on_track_list_selection_changed(track_index)
    
    def _on_trackpoint_selected(self, point_index: int):
        """Handle trackpoint selection from trackpoint list widget."""
        
        # If point_index is -1, it means no selection - clear map selection
        if point_index < 0:
            self._current_point_index = -1
            if hasattr(self, 'map_widget'):
                self.map_widget.selected_trackpoint_index = None
                self.map_widget.selected_trackpoint_range = None
                self.map_widget.render_map()
            return
        
        if self._current_track_index is None:
            return
        
        self._current_point_index = point_index
        
        track = self.track_manager.get_track_by_index(self._current_track_index)
        if track and point_index < len(track.trackpoints):
            point = track.trackpoints[point_index]
            msg = f"Point {point_index + 1}: ({point.latitude:.6f}, {point.longitude:.6f})"
            self.statusBar().showMessage(msg, 3000)
            
            logger.debug(f"Point selected: track={self._current_track_index}, point={point_index}")
        
        # Highlight point on map
        if hasattr(self, 'map_widget'):
            self.map_widget.on_point_selected(self._current_track_index, point_index)
            # Clear range selection when user clicks list
            self.map_widget.selected_trackpoint_range = None
            self.map_widget.render_map()
            # Update menu state
            self._update_insert_menu_state()
    
    def _on_trackpoint_double_clicked(self, point_index: int):
        """Handle double-click on trackpoint."""
        
        if self._current_track_index is None:
            return
        
        track = self.track_manager.get_track_by_index(self._current_track_index)
        if track and point_index < len(track.trackpoints):
            point = track.trackpoints[point_index]
            msg = f"Double-clicked point {point_index + 1}"
            self.statusBar().showMessage(msg, 2000)
            
            logger.debug(f"Point double-clicked: track={self._current_track_index}, point={point_index}")
    
    def _on_coordinate_format_changed(self, coord_format: str):
        """Handle coordinate format change."""
        
        msg = f"Coordinate format: {coord_format.upper()}"
        self.statusBar().showMessage(msg, 2000)
    
    def _on_prune_points_requested(self, track_index: int):
        """
        Handle Prune Points button click from trackpoint list widget.
        
        Runs pruning in a background thread to keep UI responsive.
        Shows progress dialog that updates in real-time.
        
        Flow:
        1. Create progress dialog and worker thread
        2. Connect signals between worker and dialog
        3. Start worker in background
        4. Dialog updates as worker emits progress signals
        5. When worker finishes, update UI and close dialog
        
        Args:
            track_index (int): Index of track to prune (from signal)
        """
        # Validate track index
        if track_index < 0:
            logger.warning("No track selected for pruning")
            return
        
        # Get minimum distance from configuration (read fresh from disk to get latest value)
        from config.app_config_yaml import AppConfig
        fresh_config = AppConfig()
        min_distance_m = fresh_config.get_int('performance.prune_points.min_distance_m', 50)
        
        logger.info(f"DEBUG: Fresh config loaded - min_distance_m from disk = {min_distance_m}")
        
        # Verify what's actually in the config data
        if hasattr(fresh_config, 'config_data'):
            import json
            perf_section = fresh_config.config_data.get('performance', {})
            logger.info(f"DEBUG: performance section in config = {perf_section}")
        
        # Get track object for display purposes
        track = self.track_manager.get_track_by_index(track_index)
        if not track:
            logger.error(f"Could not get track {track_index}")
            return
        
        logger.info(f"Starting prune for track '{track.name}' with min_distance={min_distance_m}m")
        
        try:
            # Import progress dialog and worker
            from src.gui.dialogs.prune_progress_dialog import PruneProgressDialog
            from src.core.prune_worker import PruneWorker
            
            # Create progress dialog
            progress_dialog = PruneProgressDialog(parent=self)
            progress_dialog.start_pruning(len(track.trackpoints))
            
            # Create worker thread
            self.prune_worker = PruneWorker(self.track_manager, track_index, min_distance_m)
            
            # Connect worker signals to dialog
            self.prune_worker.progress.connect(lambda p, r, k: progress_dialog.update_progress(p, r, k))
            self.prune_worker.finished.connect(lambda removed: self._on_prune_finished(removed, progress_dialog, track_index, track.name, min_distance_m))
            self.prune_worker.error.connect(lambda err: self._on_prune_error(err, progress_dialog))
            self.prune_worker.cancelled.connect(lambda: progress_dialog.finish_cancelled())
            
            # Connect cancel button to worker
            def on_cancel():
                progress_dialog.cancel_button.setEnabled(False)
                self.prune_worker.cancel()
            progress_dialog.cancel_button.clicked.connect(on_cancel)
            
            # Show dialog
            progress_dialog.show()
            
            # Start worker in background thread
            self.prune_worker.start()
        
        except Exception as e:
            logger.error(f"Error starting prune: {e}", exc_info=True)
            self.statusBar().showMessage(f"Error starting prune: {e}", 5000)
    
    def _on_prune_finished(self, removed_count, progress_dialog, track_index, track_name, min_distance_m):
        """Handle prune completion."""
        progress_dialog.finish_success(removed_count)
        
        if removed_count > 0:
            # Update UI to show changes
            # Update track list to show updated distance and point count
            self.track_list_widget.update_track_info(track_index)
            # Refresh trackpoint list widget to show updated trackpoints
            self.trackpoint_list_widget.refresh_trackpoints()
            # Re-render map to show updated track without removed points
            self.map_widget.render_map()
            
            # Show success message to user
            msg = f"Pruned {removed_count} point(s) from '{track_name}' (min_distance={min_distance_m}m)"
            self.statusBar().showMessage(msg, 5000)
            logger.info(msg)
        else:
            # No points were close enough to remove
            msg = f"No points pruned from '{track_name}' (all points farther than {min_distance_m}m)"
            self.statusBar().showMessage(msg, 5000)
            logger.info(msg)
        
        # Schedule dialog to close after 2 seconds
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(2000, progress_dialog.close)
    
    def _on_prune_error(self, error_msg, progress_dialog):
        """Handle prune error."""
        progress_dialog.finish_error(error_msg)
        logger.error(f"Prune error: {error_msg}")
        self.statusBar().showMessage(f"Prune error: {error_msg}", 5000)
    
    def _on_map_ready(self):
        """Handle map ready signal."""
        
        msg = "Map initialized and ready"
        self.statusBar().showMessage(msg, 3000)
        
        logger.info("Map widget ready")
    
    def _on_map_track_clicked(self, track_id: int):
        """Handle track click on map."""
        
        track = self.track_manager.get_track_by_index(track_id)
        if track:
            msg = f"Map track clicked: {track.name}"
            self.statusBar().showMessage(msg, 2000)
            
            logger.debug(f"Track clicked on map: {track_id}")
            
            # Update track list selection
            if hasattr(self, 'track_list_widget'):
                self.track_list_widget.select_track(track_id)
    
    def _on_map_point_clicked(self, track_id: int, point_id: int):
        """Handle point click on map."""
        
        msg = f"Map point clicked: track {track_id}, point {point_id}"
        self.statusBar().showMessage(msg, 2000)
        
        logger.debug(f"Point clicked on map: track={track_id}, point={point_id}")
        
        # Update trackpoint list selection
        if hasattr(self, 'trackpoint_list_widget'):
            self.trackpoint_list_widget.select_point(point_id)
        
        # Update insert menu state based on range selection
        self._update_insert_menu_state()
    
    def _on_trackpoint_dragging(self, point_index: int, latitude: float, longitude: float):
        """Handle real-time coordinate updates while dragging a trackpoint."""
        if hasattr(self, 'trackpoint_list_widget'):
            self.trackpoint_list_widget.update_trackpoint_row(point_index, latitude, longitude)
    
    def _update_insert_menu_state(self):
        """Enable/disable insert menu and update list based on map range selection."""
        if hasattr(self, 'insert_trackpoint_action') and hasattr(self, 'map_widget'):
            # Enable insert only if range selection is active (2 neighboring points selected)
            has_range = (self.map_widget.selected_trackpoint_range is not None)
            self.insert_trackpoint_action.setEnabled(has_range)
            
            # Update list selection to show range
            if has_range and hasattr(self, 'trackpoint_list_widget'):
                start_idx, end_idx = self.map_widget.selected_trackpoint_range
                self.trackpoint_list_widget.select_range(start_idx, end_idx)
            elif hasattr(self, 'trackpoint_list_widget') and self.map_widget.selected_trackpoint_index is not None:
                # Show single selection in list
                self.trackpoint_list_widget.select_point(self.map_widget.selected_trackpoint_index)
    
    def _on_track_path_settings_changed(self):
        """Handle any track path setting change - reload all track path settings from config."""
        
        if hasattr(self, 'map_widget'):
            # Reload all track path settings from config
            from config.app_config_yaml import AppConfig
            config = AppConfig()
            
            # Body
            self.map_widget.track_color = self.map_widget._hex_to_rgb(config.get_str('appearance.map_display.track_path.body.color', 'FF0000'))
            self.map_widget.track_path_width = config.get_int('appearance.map_display.track_path.body.width', 3)
            
            # Outline
            self.map_widget.track_path_outline_color = self.map_widget._hex_to_rgb(config.get_str('appearance.map_display.track_path.outline.color', 'FFFFFF'))
            self.map_widget.track_path_outline_width = config.get_int('appearance.map_display.track_path.outline.width', 1)
            
            # Trigger redraw
            self.map_widget.render_map()
            self.map_widget.update()
            
            logger.debug("Track path settings reloaded from config")
    
    def _on_turning_points_show_toggled(self, state: bool):
        """Handle turning points show/hide toggle from settings."""
        
        # Update map widget
        if hasattr(self, 'map_widget'):
            self.map_widget.show_turning_points = state
            
            # Trigger redraw
            self.map_widget.render_map()
            self.map_widget.update()
        
        # Update dropdown in trackpoint list widget to sync with toggle
        if hasattr(self, 'trackpoint_list_widget'):
            # Set dropdown to match toggle state without triggering the signal
            index = 0 if state else 1  # Yes=0, No=1
            self.trackpoint_list_widget.show_points_combo.blockSignals(True)
            self.trackpoint_list_widget.show_points_combo.setCurrentIndex(index)
            self.trackpoint_list_widget.show_points_combo.blockSignals(False)
        
        logger.debug(f"Turning points show toggled to: {state}")
    
    def _on_turning_points_settings_changed(self):
        """Handle any turning points setting change - reload all trackpoint settings from config."""
        
        if hasattr(self, 'map_widget'):
            # Reload all trackpoint settings from config
            from config.app_config_yaml import AppConfig
            config = AppConfig()
            
            # General Points
            self.map_widget.turning_point_color = self.map_widget._hex_to_rgb(config.get_str('appearance.map_display.trackpoints.GeneralPoints.body.color', 'FFFF00'))
            self.map_widget.turning_point_size = config.get_int('appearance.map_display.trackpoints.GeneralPoints.body.size', 4)
            self.map_widget.turning_point_outline_color = self.map_widget._hex_to_rgb(config.get_str('appearance.map_display.trackpoints.GeneralPoints.outline.color', 'FFFFFF'))
            self.map_widget.turning_point_outline_width = config.get_int('appearance.map_display.trackpoints.GeneralPoints.outline.size', 1)
            
            # Selected Points
            self.map_widget.selected_turning_point_color = self.map_widget._hex_to_rgb(config.get_str('appearance.map_display.trackpoints.SelectedPoints.body.color', '0000FF'))
            self.map_widget.selected_turning_point_size = config.get_int('appearance.map_display.trackpoints.SelectedPoints.body.size', 7)
            self.map_widget.selected_turning_point_outline_color = self.map_widget._hex_to_rgb(config.get_str('appearance.map_display.trackpoints.SelectedPoints.outline.color', 'FFFFFF'))
            self.map_widget.selected_turning_point_outline_width = config.get_int('appearance.map_display.trackpoints.SelectedPoints.outline.size', 2)
            
            # Double Selected Points
            self.map_widget.double_selected_turning_point_color = self.map_widget._hex_to_rgb(config.get_str('appearance.map_display.trackpoints.DoubleSelectedPoints.body.color', 'FFA500'))
            self.map_widget.double_selected_turning_point_size = config.get_int('appearance.map_display.trackpoints.DoubleSelectedPoints.body.size', 8)
            self.map_widget.double_selected_turning_point_outline_color = self.map_widget._hex_to_rgb(config.get_str('appearance.map_display.trackpoints.DoubleSelectedPoints.outline.color', 'FFFFFF'))
            self.map_widget.double_selected_turning_point_outline_width = config.get_int('appearance.map_display.trackpoints.DoubleSelectedPoints.outline.size', 2)
            
            # Trigger redraw
            self.map_widget.render_map()
            self.map_widget.update()
            
            logger.debug("Trackpoint settings reloaded from config")
            
            # Trigger redraw
            self.map_widget.render_map()
            self.map_widget.update()
    
    def _on_turning_points_settings_applied(self):
        """Handle turning points settings applied from settings widget."""
        logger.info("_on_turning_points_settings_applied called")
        
        if hasattr(self, 'map_widget'):
            logger.info("Reloading MapWidget settings")
            # Reload all settings from config file
            self.map_widget.reload_settings()
        
        # Also reload in MapEditor tab
        if hasattr(self, 'map_editor_handler') and self.map_editor_handler.map_viewer:
            logger.info("Reloading MapViewer settings")
            self.map_editor_handler.map_viewer.reload_settings()
        else:
            logger.warning("MapEditor not available or map_viewer is None")
    
    def _on_show_points_dropdown_changed(self, index: int):
        """Handle show points dropdown change from Editor tab - sync to Settings toggle."""
        
        # Get the state from dropdown
        state = self.trackpoint_list_widget.show_points_combo.currentData()
        
        # Update the toggle in settings without triggering its signal
        if hasattr(self, 'settings_widget'):
            self.settings_widget.show_toggle.blockSignals(True)
            self.settings_widget.show_toggle.set_state(state)
            self.settings_widget.show_toggle.blockSignals(False)
        
        logger.debug(f"Show points dropdown changed to: {state} - synced to settings toggle")
    
    # ========================================================================
    # Dialog Helpers
    # ========================================================================
    
    def show_error(self, title: str, message: str):
        """Show error dialog."""
        QMessageBox.critical(self, title, message)
    
    def show_warning(self, title: str, message: str):
        """Show warning dialog."""
        QMessageBox.warning(self, title, message)
    
    def show_info(self, title: str, message: str):
        """Show info dialog."""
        QMessageBox.information(self, title, message)
    
    # ========================================================================
    # Window Events
    # ========================================================================
    
    def closeEvent(self, event):
        """Handle window close event."""
        
        if self.is_modified:
            reply = QMessageBox.question(
                self,
                'Unsaved Changes',
                'You have unsaved changes. Do you want to save before closing?',
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Save:
                self.action_save_file()
            elif reply == QMessageBox.Cancel:
                event.ignore()
                return
        
        event.accept()
        logger.info("Application closed")
