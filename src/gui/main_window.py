"""
Main Application Window for mangpx.

Provides the primary PyQt5 window for the mangpx application, including
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
    QStatusBar, QMenu, QAction, QFileDialog, QMessageBox, QDialog
)
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtCore import Qt, QSize, pyqtSignal

from config.app_config_yaml import AppConfig
from src.core.gpx_handler import GPXHandler
from src.core.track_manager import TrackManager
from src.gui.widgets.track_list_widget import TrackListWidget
from src.gui.widgets.trackpoint_list_widget import TrackpointListWidget
from src.gui.widgets.map_widget import MapWidget
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
    Main application window for mangpx.
    
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
        app_name = self.config.get_str('Application.name', 'mangpx')
        version = self.config.get_str('Application.version', '1.0.0')
        window_title = self.config.get_str('Application.window_title', '{app_name} - GPX File Manipulator v{version}')
        window_width = self.config.get_int('UI.window.width', 1400)
        window_height = self.config.get_int('UI.window.height', 900)
        
        # Format window title with substitutions
        window_title = window_title.format(name=app_name, version=version)
        
        # Set window title
        self.setWindowTitle(window_title)
        
        # Set window size
        self.resize(window_width, window_height)
        
        # Center window on screen
        self._center_window()
        
        # Set application icon (if available)
        icon_path = Path(__file__).parent / 'icons' / 'mangpx.png'
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        # Enable window state saving (use legacy attribute for compatibility)
        window_state = Qt.WindowState.WindowMaximized if self.config.get_bool(
            'UI.start_maximized', False
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
        """Create central widget with track list, trackpoint list, and map."""
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout (horizontal - left panel and right panel)
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # ====================================================================
        # Left Panel: Track List Widget
        # ====================================================================
        
        self.track_list_widget = TrackListWidget(self.track_manager)
        self.track_list_widget.setMaximumWidth(400)
        self.track_list_widget.setMinimumWidth(250)
        
        # Connect track list signals to main window
        self.track_list_widget.track_selected.connect(self._on_track_list_selection_changed)
        self.track_list_widget.track_double_clicked.connect(self._on_track_list_double_clicked)
        
        main_layout.addWidget(self.track_list_widget)
        
        # ====================================================================
        # Right Panel: Vertical layout with trackpoint list and map
        # ====================================================================
        
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(5)
        
        # Map Widget (bottom) - SHOULD EXPAND to fill remaining space
        self.map_widget = MapWidget(mbtiles_provider=self.mbtiles_provider)
        self.map_widget.setMinimumHeight(300)
        self.map_widget.set_track_manager(self.track_manager)
        
        # Trackpoint List Widget (top)
        self.trackpoint_list_widget = TrackpointListWidget(self.track_manager, self.map_widget)
        self.trackpoint_list_widget.setMaximumHeight(250)
        self.trackpoint_list_widget.setMinimumHeight(100)
        
        # Connect trackpoint list signals
        self.trackpoint_list_widget.point_selected.connect(self._on_trackpoint_selected)
        self.trackpoint_list_widget.point_double_clicked.connect(self._on_trackpoint_double_clicked)
        self.trackpoint_list_widget.coordinate_format_changed.connect(self._on_coordinate_format_changed)
        self.trackpoint_list_widget.history_changed.connect(self._update_undo_redo_menu_states)
        
        right_layout.addWidget(self.trackpoint_list_widget, 0)  # Fixed size with stretch factor 0
        
        # CRITICAL FIX: Map must have stretch factor 1 to expand to fill available space
        right_layout.addWidget(self.map_widget, 1)  # Stretch factor 1 = expand
        
        # Connect map signals
        self.map_widget.map_ready.connect(self._on_map_ready)
        self.map_widget.track_clicked.connect(self._on_map_track_clicked)
        self.map_widget.point_clicked.connect(self._on_map_point_clicked)
        
        # Connect track list to map widget to update highlighted track
        self.track_list_widget.track_selected.connect(self.map_widget.on_track_list_selection_changed)
        
        main_layout.addWidget(right_panel, 1)
        
        logger.info("Central widget created with track list, trackpoint list, and map")
    
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
            if not self.gpx_data:
                self.show_error("Error", "No GPX data loaded")
                return False
            
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
        
        app_name = self.config.get_str('Application.name', 'mangpx')
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
