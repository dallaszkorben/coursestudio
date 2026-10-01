"""
Settings/Configuration Widget for CourseStudio.

Provides a tabbed interface for configuring application settings:
- Map appearance (colors, sizes, line widths)
- Coordinate formats
- Performance settings
"""

import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QTabWidget, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal

from config.app_config_yaml import AppConfig
from src.gui.widgets.track_path_settings_widget import TrackPathSettingsWidget
from src.gui.widgets.trackpoint_type_settings_widget import TrackpointTypeSettingsWidget
from src.gui.widgets.toggle_switch_widget import ToggleSwitchWidget
from src.gui.widgets.custom_tab_bar import ContentAwareTabBar

logger = logging.getLogger(__name__)


class SettingsWidget(QWidget):
    """
    Settings configuration widget.
    
    Main tab structure:
    - Appearance (with sub-tabs)
      - Track Path
      - General Track Point
      - Single-Selected Track Point
      - Multi-Selected Track Point
    """
    
    turning_points_settings_applied = pyqtSignal()  # Emitted when turning points settings are applied
    
    def __init__(self):
        """Initialize the settings widget."""
        super().__init__()
        
        self.config = AppConfig()
        
        self._init_ui()
        
        logger.info("SettingsWidget initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)
        
        # ====================================================================
        # Main Tab Widget (top-level tabs)
        # ====================================================================
        
        main_tab_widget = QTabWidget()
        from PyQt5.QtWidgets import QSizePolicy
        main_tab_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        main_tab_widget.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #3d3d3d; }
            QTabBar::tab { 
                background: #2d2d2d; 
                color: white; 
                padding: 8px 20px; 
                border: 1px solid #3d3d3d;
            }
            QTabBar::tab:selected { 
                background: #404040; 
                border-bottom: 2px solid #0078d4;
            }
        """)
        
        # Replace default tab bar with custom one that sizes to content
        main_custom_tab_bar = ContentAwareTabBar()
        main_tab_widget.setTabBar(main_custom_tab_bar)
        
        # Create Appearance Tab
        appearance_tab = self._create_appearance_tab()
        main_tab_widget.addTab(appearance_tab, "Appearance")
        
        main_layout.addWidget(main_tab_widget)
        
        # ====================================================================
        # Control Buttons (at bottom)
        # ====================================================================
        
        # TODO: Add Apply, Reset, Cancel buttons
        # Placeholder for now
    
    def _create_appearance_tab(self):
        """Create the Appearance tab with sub-tabs for different visual elements."""
        
        # Container for appearance tab
        appearance_container = QWidget()
        appearance_layout = QVBoxLayout()
        appearance_container.setLayout(appearance_layout)
        appearance_layout.setContentsMargins(5, 5, 5, 5)
        appearance_layout.setSpacing(10)
        
        # ====================================================================
        # Show Trackpoints Toggle (global control at top)
        # ====================================================================
        
        show_toggle_layout = QHBoxLayout()
        show_toggle_layout.setContentsMargins(10, 0, 10, 10)
        show_toggle_layout.setSpacing(15)
        
        show_label = QLabel("Show Trackpoints:")
        show_label.setStyleSheet("font-weight: bold; color: white;")
        show_label.setFixedWidth(120)
        show_toggle_layout.addWidget(show_label, 0, Qt.AlignLeft)
        
        # Load show state from config
        self.show_trackpoints = self.config.get_bool('Appearance.MapDisplay.Trackpoints.show', True)
        self.show_toggle = ToggleSwitchWidget(title="", initial_state=self.show_trackpoints)
        self.show_toggle.toggled.connect(self._on_show_trackpoints_toggled)
        show_toggle_layout.addWidget(self.show_toggle, 0, Qt.AlignLeft)
        show_toggle_layout.addStretch()
        
        appearance_layout.addLayout(show_toggle_layout)
        
        # ====================================================================
        # Sub-Tab Widget (under Appearance)
        # ====================================================================
        
        sub_tab_widget = QTabWidget()
        # CRITICAL: Set size policy to allow expansion
        from PyQt5.QtWidgets import QSizePolicy
        sub_tab_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sub_tab_widget.setMinimumWidth(400)  # Ensure minimum width for long tab names
        
        sub_tab_widget.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #3d3d3d; }
            QTabBar::tab { 
                background: #2d2d2d; 
                color: white; 
                padding: 8px 15px; 
                border: 1px solid #3d3d3d;
                font-size: 10pt;
            }
            QTabBar::tab:selected { 
                background: #3d3d3d; 
                border-bottom: 2px solid #0078d4;
            }
        """)
        
        # Replace default tab bar with custom one that sizes to content
        custom_tab_bar = ContentAwareTabBar()
        sub_tab_widget.setTabBar(custom_tab_bar)
        
        # Allow the tab bar to expand horizontally to show all tabs
        sub_tab_widget.tabBar().setExpanding(False)
        sub_tab_widget.tabBar().setElideMode(Qt.ElideNone)
        sub_tab_widget.tabBar().setUsesScrollButtons(True)
        
        # Allow the tab bar to expand horizontally to show all tabs
        sub_tab_widget.tabBar().setExpanding(False)
        sub_tab_widget.tabBar().setElideMode(Qt.ElideNone)
        sub_tab_widget.tabBar().setUsesScrollButtons(True)
        
        # Track Path Sub-Tab
        self.track_path_widget = TrackPathSettingsWidget(self.config)
        self.track_path_widget.settings_changed.connect(self._on_settings_changed)
        sub_tab_widget.addTab(self.track_path_widget, "Track Path")
        
        # General Track Point Sub-Tab
        self.general_point_widget = TrackpointTypeSettingsWidget(self.config, 'GeneralPoints')
        self.general_point_widget.settings_changed.connect(self._on_settings_changed)
        sub_tab_widget.addTab(self.general_point_widget, "General Track Point")
        
        # Single-Selected Track Point Sub-Tab
        self.single_selected_point_widget = TrackpointTypeSettingsWidget(self.config, 'SelectedPoints')
        self.single_selected_point_widget.settings_changed.connect(self._on_settings_changed)
        sub_tab_widget.addTab(self.single_selected_point_widget, "Single-Selected Track Point")
        
        # Multi-Selected Track Point Sub-Tab
        self.multi_selected_point_widget = TrackpointTypeSettingsWidget(self.config, 'DoubleSelectedPoints')
        self.multi_selected_point_widget.settings_changed.connect(self._on_settings_changed)
        sub_tab_widget.addTab(self.multi_selected_point_widget, "Multi-Selected Track Point")
        
        appearance_layout.addWidget(sub_tab_widget)
        
        return appearance_container
    
    def _on_settings_changed(self):
        """Handle settings change - auto-save to config file."""
        logger.debug("Settings changed - auto-saving to config")
        self._apply_all_settings()
    
    def _on_show_trackpoints_toggled(self, state: bool):
        """Handle show trackpoints toggle."""
        logger.debug(f"Show trackpoints toggled to: {state}")
        self.config.set_bool('Appearance.MapDisplay.Trackpoints.show', state)
        self.config.save_to_file()
        self.turning_points_settings_applied.emit()
    
    def _apply_all_settings(self):
        """Apply all settings to config."""
        if hasattr(self, 'track_path_widget'):
            self.track_path_widget.apply_to_config()
        
        if hasattr(self, 'general_point_widget'):
            self.general_point_widget.apply_to_config()
        
        if hasattr(self, 'single_selected_point_widget'):
            self.single_selected_point_widget.apply_to_config()
        
        if hasattr(self, 'multi_selected_point_widget'):
            self.multi_selected_point_widget.apply_to_config()
        
        self.config.save_to_file()
        self.turning_points_settings_applied.emit()
