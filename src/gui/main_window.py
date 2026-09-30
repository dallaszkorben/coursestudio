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
    QStatusBar, QMenu, QAction, QFileDialog, QMessageBox, QDialog, QSplitter
)
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtWidgets import QTabWidget

from config.app_config_yaml import AppConfig
from src.core.gpx_handler import GPXHandler
from src.core.track_manager import TrackManager
from src.gui.widgets.track_list_widget import TrackListWidget
from src.gui.widgets.trackpoint_list_widget import TrackpointListWidget
from src.gui.widgets.map_widget import MapWidget
from src.gui.widgets.settings_widget import SettingsWidget
from src.map.mbtiles_provider import MBTilesProvider


# ============================================================================
# Logging Configuration
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# Main Window Class
# ============================================================================

class MainWindow(QMainWindow):
    """
    Main application window for CourseStudio.
    
    Provides the primary interface for GPX file manipulation with:
    - Menu bar (File, Edit, View, Help)
    - Toolbar with quick actions
    - Status bar for feedback
    - Central widget area for content
    - Document management (open, save, recent files)
    - Application state management
    
    Signals:
        file_opened: Emitted when a GPX file is successfully opened
        file_saved: Emitted when a GPX file is successfully saved
        track_selected: Emitted when a track is selected
    
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
        if not self.mbtiles_provider.load_default_mbtiles():
            logger.warning("Could not load default mbtiles file - map may not display")
        
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
        app_name = self.config.get_str('Application.name', 'CourseStudio')
        version = self.config.get_str('Application.version', '1.0.0')
        window_title = self.config.get_str('Application.window_title', '{app_name} - GPX File Manipulator v{version}')
        window_width = self.config.get_int('Application.window_width', 1400)
        window_height = self.config.get_int('Application.window_height', 900)
        
        # Format window title with substitutions
        window_title = window_title.format(name=app_name, version=version)
        
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
            'Application.start_maximized', False
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
        
        # File Menu
        file_menu = menubar.addMenu('&File')
        
        # File > Open
        open_action = QAction('&Open GPX File...', self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.setStatusTip('Open a GPX file')
        open_action.triggered.connect(self.action_open_file)
        file_menu.addAction(open_action)
        
        # File > Save
        save_action = QAction('&Save', self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.setStatusTip('Save current file')
        save_action.triggered.connect(self.action_save_file)
        file_menu.addAction(save_action)
        
        # File > Save As
        save_as_action = QAction('Save &As...', self)
        save_as_action.setShortcut(QKeySequence.SaveAs)
        save_as_action.setStatusTip('Save current file with new name')
        save_as_action.triggered.connect(self.action_save_file_as)
        file_menu.addAction(save_as_action)
        
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
        open_action = QAction('Open', self)
        open_action.setStatusTip('Open a GPX file')
        open_action.triggered.connect(self.action_open_file)
        self.toolbar.addAction(open_action)
        
        # Save file button
        save_action = QAction('Save', self)
        save_action.setStatusTip('Save current file')
        save_action.triggered.connect(self.action_save_file)
        self.toolbar.addAction(save_action)
        
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
        """Create central widget with two main tabs: Editor (Tracks/Trackpoints/Map) and Settings."""
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Import size policy for widget resizing
        from PyQt5.QtWidgets import QSizePolicy
        
        # Main tab widget (top level - Editor vs Settings)
        self.main_tab_widget = QTabWidget()
        
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.main_tab_widget)
        
        # ====================================================================
        # Tab 1: Editor (Tracks + Trackpoints/Map layout)
        # ====================================================================
        
        editor_widget = QWidget()
        editor_layout = QHBoxLayout()
        editor_widget.setLayout(editor_layout)
        editor_layout.setContentsMargins(5, 5, 5, 5)
        editor_layout.setSpacing(5)
        
        # Left Panel: Track List Widget
        self.track_list_widget = TrackListWidget(self.track_manager)
        self.track_list_widget.setMaximumWidth(400)
        self.track_list_widget.setMinimumWidth(80)  # Reduced from 250
        
        # Allow to shrink
        self.track_list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Connect track list signals to main window
        self.track_list_widget.track_selected.connect(self._on_track_list_selection_changed)
        self.track_list_widget.track_double_clicked.connect(self._on_track_list_double_clicked)
        
        editor_layout.addWidget(self.track_list_widget)
        
        # Right Panel: Vertical splitter with Trackpoints and Map
        right_splitter = QSplitter(Qt.Vertical)
        
        # Trackpoint List Widget (top)
        self.trackpoint_list_widget = TrackpointListWidget(self.track_manager, None)
        self.trackpoint_list_widget.setMinimumHeight(50)  # Reduced from 100
        self.trackpoint_list_widget.setMinimumWidth(1)  # Allow horizontal shrinking
        
        # Allow to shrink horizontally
        self.trackpoint_list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Connect trackpoint list signals
        self.trackpoint_list_widget.point_selected.connect(self._on_trackpoint_selected)
        self.trackpoint_list_widget.point_double_clicked.connect(self._on_trackpoint_double_clicked)
        self.trackpoint_list_widget.coordinate_format_changed.connect(self._on_coordinate_format_changed)
        self.trackpoint_list_widget.history_changed.connect(self._update_undo_redo_menu_states)
        
        # NEW: Connect show points combo to update settings toggle
        self.trackpoint_list_widget.show_points_combo.currentIndexChanged.connect(
            self._on_show_points_dropdown_changed
        )
        
        right_splitter.addWidget(self.trackpoint_list_widget)
        
        # Map Widget (bottom)
        self.map_widget = MapWidget(mbtiles_provider=self.mbtiles_provider)
        self.map_widget.setMinimumHeight(150)  # Reduced from 300
        self.map_widget.setMinimumWidth(1)  # Allow horizontal shrinking
        
        # Allow map to shrink horizontally too
        self.map_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.map_widget.set_track_manager(self.track_manager)
        
        # Connect map signals
        self.map_widget.map_ready.connect(self._on_map_ready)
        self.map_widget.track_clicked.connect(self._on_map_track_clicked)
        self.map_widget.point_clicked.connect(self._on_map_point_clicked)
        self.map_widget.range_selection_changed.connect(self._update_insert_menu_state)  # NEW: Connect range signal
        self.map_widget.trackpoint_dragging.connect(self._on_trackpoint_dragging)  # NEW: Real-time drag updates
        
        # Connect track list to map widget to update highlighted track
        self.track_list_widget.track_selected.connect(self.map_widget.on_track_list_selection_changed)
        
        # Update trackpoint list widget with map widget reference
        self.trackpoint_list_widget.map_widget = self.map_widget
        
        right_splitter.addWidget(self.map_widget)
        
        # Set initial sizes (40% trackpoints, 60% map)
        right_splitter.setSizes([400, 600])
        
        # Make splitter draggable - neither side can collapse
        right_splitter.setCollapsible(0, False)  # Trackpoint list can't collapse
        right_splitter.setCollapsible(1, False)  # Map can't collapse
        
        editor_layout.addWidget(right_splitter, 1)
        
        self.main_tab_widget.addTab(editor_widget, "Editor")
        
        # ====================================================================
        # Tab 2: Settings (full-width)
        # ====================================================================
        
        self.settings_widget = SettingsWidget()
        
        # Connect settings changes to map widget for live preview
        self.settings_widget.track_path_widget.color_picker.color_changed.connect(
            self._on_track_path_color_changed
        )
        self.settings_widget.track_path_widget.width_slider_obj.valueChanged.connect(
            self._on_track_path_width_changed
        )
        
        # Connect turning points changes
        self.settings_widget.turning_points_widget.show_toggled.connect(
            self._on_turning_points_show_toggled
        )
        self.settings_widget.turning_points_widget.color_picker.color_changed.connect(
            self._on_turning_points_color_changed
        )
        self.settings_widget.turning_points_widget.size_slider.value_changed.connect(
            self._on_turning_points_size_changed
        )
        self.settings_widget.turning_points_widget.selected_color_picker.color_changed.connect(
            self._on_turning_points_selected_color_changed
        )
        self.settings_widget.turning_points_widget.selected_size_slider.value_changed.connect(
            self._on_turning_points_selected_size_changed
        )
        self.settings_widget.turning_points_settings_applied.connect(
            self._on_turning_points_settings_applied
        )
        
        self.main_tab_widget.addTab(self.settings_widget, "Settings")
        
        logger.info("Central widget created with Editor (Tracks/Trackpoints/Map) and Settings tabs")
    
    # ========================================================================
    # Status Bar
    # ========================================================================
    
    def _create_status_bar(self):
        """Create status bar for user feedback."""
        
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        # Status message
        self.status_label = status_bar.showMessage("Ready")
        
        logger.info("Status bar created")
    
    # ========================================================================
    # Signal Connections
    # ========================================================================
    
    def _connect_signals(self):
        """Connect internal signals."""
        
        # Connect file opened signal to status update
        self.file_opened.connect(self._on_file_opened)
        
        # Connect file saved signal to status update
        self.file_saved.connect(self._on_file_saved)
        
        # Connect track selected signal
        self.track_selected.connect(self._on_track_selected)
        
        # Connect map range selection signal to update insert menu
        if hasattr(self, 'map_widget') and hasattr(self.map_widget, 'range_selection_changed'):
            self.map_widget.range_selection_changed.connect(self._update_insert_menu_state)
    
    # ========================================================================
    # File Operations
    # ========================================================================
    
    def action_open_file(self):
        """Open a GPX file."""
        
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
        Open and load a GPX file.
        
        Args:
            file_path (str): Path to GPX file
        
        Returns:
            bool: True if successful, False otherwise
        """
        
        try:
            # Load GPX file
            gpx = self.gpx_handler.load_gpx(file_path)
            if not gpx:
                self.show_error("Failed to open file", f"Could not parse GPX file: {file_path}")
                return False
            
            # Store GPX object for later saving
            self.gpx_data = gpx
            
            # Load tracks into manager
            count = self.track_manager.load_from_gpx(gpx, file_path)
            
            # Clear all UI selections explicitly
            if hasattr(self, 'track_list_widget'):
                self.track_list_widget.clear_selection()  # Explicit unselect
                self.track_list_widget.refresh_tracks()
            
            if hasattr(self, 'map_widget'):
                self.map_widget.on_track_list_selection_changed(None)
                self.map_widget.render_map()  # Force re-render with cleared selection
            
            if hasattr(self, 'trackpoint_list_widget'):
                self.trackpoint_list_widget.set_track(-1)
            
            # Update application state
            self.current_file_path = file_path
            self.is_modified = False
            
            # Emit signal
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
            self.statusBar().showMessage("Nothing to undo")
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
            self.statusBar().showMessage(f"Undone: {desc}", 3000)
            logger.info(f"Undo: {desc}")
            
            # Update menu states
            self._update_undo_redo_menu_states()
        else:
            self.statusBar().showMessage("Failed to undo")
    
    def action_redo(self):
        """Redo last action."""
        
        if not self.track_manager.can_redo():
            self.statusBar().showMessage("Nothing to redo")
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
            self.statusBar().showMessage(f"Redone: {desc}", 3000)
            logger.info(f"Redo: {desc}")
            
            # Update menu states
            self._update_undo_redo_menu_states()
        else:
            self.statusBar().showMessage("Failed to redo")
    
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
        self.statusBar().showMessage("Zoom in")
    
    def action_zoom_out(self):
        """Zoom out."""
        logger.debug("Zoom out action triggered")
        self.statusBar().showMessage("Zoom out")
    
    # ========================================================================
    # Application Operations
    # ========================================================================
    
    def action_preferences(self):
        """Open preferences dialog."""
        logger.debug("Preferences action triggered (not yet implemented)")
        self.statusBar().showMessage("Preferences not yet implemented")
    
    def action_about(self):
        """Show about dialog."""
        
        app_name = self.config.get_str('Application.name', 'CourseStudio')
        version = self.config.get_str('Application.version', '1.0.0')
        
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
            selected_row = self.trackpoint_list_widget.table_widget.currentRow()
            if selected_row >= 0:
                self.trackpoint_list_widget._delete_trackpoint(selected_row)
            else:
                QMessageBox.information(self, "No Selection", "Please select a trackpoint to delete")
    
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
            
            logger.info(f"[INSERT] Range selected: ({start_idx}, {end_idx}), trackpoint count: {len(trackpoints)}")
            
            if start_idx >= len(trackpoints) or end_idx >= len(trackpoints):
                logger.error(f"[INSERT] Invalid indices: start_idx={start_idx}, end_idx={end_idx}, len={len(trackpoints)}")
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
        """Handle track selection change from track list widget."""
        
        # Handle unselection (track_index == -1)
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
        
        # SELECT THE TRACK IN TRACK_MANAGER
        self.track_manager.select_track(track_index)
        
        track = self.track_manager.get_track_by_index(track_index)
        if track:
            msg = f"Track: {track.name} - {track.distance_km:.2f} km ({track.get_point_count()} points)"
            self.statusBar().showMessage(msg, 5000)
            
            logger.debug(f"Track selected from list: index={track_index}")
        
        # Update internal state
        self._current_track_index = track_index
        self._current_point_index = None
        
        # Update trackpoint list widget with the selected track
        if hasattr(self, 'trackpoint_list_widget'):
            self.trackpoint_list_widget.set_track(track_index)
        
        # Update map widget
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
        
        logger.debug(f"Coordinate format changed to: {coord_format}")
    
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
    
    def _on_track_path_color_changed(self, hex_color: str):
        """Handle track path color change from settings."""
        
        if hasattr(self, 'map_widget'):
            # Convert hex to RGB
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            rgb_color = (r, g, b)
            
            self.map_widget.track_color = rgb_color
            self.map_widget.selected_track_color = rgb_color
            
            # Trigger redraw
            self.map_widget.render_map()
            self.map_widget.update()
            
            logger.debug(f"Track path color changed to: {hex_color}")
    
    def _on_track_path_width_changed(self, width: int):
        """Handle track path width change from settings."""
        
        if hasattr(self, 'map_widget'):
            self.map_widget.track_path_width = width
            
            # Trigger redraw
            self.map_widget.render_map()
            self.map_widget.update()
            
            logger.debug(f"Track path width changed to: {width}px")
    
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
    
    def _on_turning_points_color_changed(self, hex_color: str):
        """Handle turning points color change from settings."""
        
        if hasattr(self, 'map_widget'):
            # Convert hex to RGB
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            rgb_color = (r, g, b)
            
            self.map_widget.turning_point_color = rgb_color
            
            # Trigger redraw
            self.map_widget.render_map()
            self.map_widget.update()
            
            logger.debug(f"Turning points color changed to: {hex_color}")
    
    def _on_turning_points_size_changed(self, size: int):
        """Handle turning points size change from settings."""
        
        if hasattr(self, 'map_widget'):
            self.map_widget.turning_point_size = size
            
            # Trigger redraw
            self.map_widget.render_map()
            self.map_widget.update()
            
            logger.debug(f"Turning points size changed to: {size}px")
    
    def _on_turning_points_selected_color_changed(self, hex_color: str):
        """Handle selected turning point color change from settings."""
        
        if hasattr(self, 'map_widget'):
            # Convert hex to RGB
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            rgb_color = (r, g, b)
            
            self.map_widget.selected_turning_point_color = rgb_color
            
            # Trigger redraw
            self.map_widget.render_map()
            self.map_widget.update()
            
            logger.debug(f"Selected turning point color changed to: {hex_color}")
    
    def _on_turning_points_selected_size_changed(self, size: int):
        """Handle selected turning point size change from settings."""
        
        if hasattr(self, 'map_widget'):
            self.map_widget.selected_turning_point_size = size
            
            # Trigger redraw
            self.map_widget.render_map()
            self.map_widget.update()
    
    def _on_turning_points_settings_applied(self):
        """Handle turning points settings applied from settings widget."""
        
        if hasattr(self, 'map_widget'):
            # Reload all settings from config file
            self.map_widget.reload_settings()
    
    def _on_show_points_dropdown_changed(self, index: int):
        """Handle show points dropdown change from Editor tab - sync to Settings toggle."""
        
        # Get the state from dropdown
        state = self.trackpoint_list_widget.show_points_combo.currentData()
        
        # Update the toggle in settings without triggering its signal
        if hasattr(self, 'settings_widget'):
            self.settings_widget.turning_points_widget.show_toggle.blockSignals(True)
            self.settings_widget.turning_points_widget.show_toggle.set_state(state)
            self.settings_widget.turning_points_widget.show_toggle.blockSignals(False)
        
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
