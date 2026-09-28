"""
Settings/Configuration Widget for CourseStudio.

Provides a tabbed interface for configuring application settings:
- Map appearance (colors, sizes, line widths)
- Coordinate formats
- Performance settings
"""

import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QScrollArea
from PyQt5.QtCore import Qt

from config.app_config_yaml import AppConfig
from src.gui.widgets.track_path_settings_widget import TrackPathSettingsWidget
from src.gui.widgets.turning_points_settings_widget import TurningPointsSettingsWidget

logger = logging.getLogger(__name__)


class SettingsWidget(QWidget):
    """
    Settings configuration widget.
    
    Allows users to configure:
    - APPEARANCE section: Map rendering settings (colors, sizes)
    - COORDINATES & DISPLAY section: Format preferences
    - FILE HANDLING section: File operation preferences
    - PERFORMANCE section: Performance tuning
    - ADVANCED section: Technical settings
    
    Expandable/collapsible sections implemented step by step.
    """
    
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
        
        # Create scrollable area for settings
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        
        # Container widget for scroll area
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_widget.setLayout(scroll_layout)
        scroll_layout.setSpacing(15)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        
        # ====================================================================
        # APPEARANCE Section
        # ====================================================================
        
        appearance_label = QWidget()
        appearance_layout = QVBoxLayout()
        appearance_label.setLayout(appearance_layout)
        
        # Track Path Settings
        self.track_path_widget = TrackPathSettingsWidget(self.config)
        self.track_path_widget.settings_changed.connect(self._on_settings_changed)
        appearance_layout.addWidget(self.track_path_widget)
        
        # Turning Points Settings
        self.turning_points_widget = TurningPointsSettingsWidget(self.config)
        self.turning_points_widget.settings_changed.connect(self._on_settings_changed)
        self.turning_points_widget.show_toggled.connect(self._on_turning_points_show_toggled)
        appearance_layout.addWidget(self.turning_points_widget)
        
        scroll_layout.addWidget(appearance_label)
        
        # Add stretch to push settings to top
        scroll_layout.addStretch()
        
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)
        
        # ====================================================================
        # Control Buttons (at bottom)
        # ====================================================================
        
        # TODO: Add Apply, Reset, Cancel buttons
        # Placeholder for now
    
    def _on_settings_changed(self):
        """Handle settings change - auto-save to config file."""
        logger.debug("Settings changed - auto-saving to config")
        
        # Save track path settings
        if hasattr(self, 'track_path_widget'):
            self.track_path_widget.apply_to_config()
        
        # Save turning points settings
        if hasattr(self, 'turning_points_widget'):
            self.turning_points_widget.apply_to_config()
        
        # Save config to file
        self.config.save_to_file()
    
    def _on_turning_points_show_toggled(self, state: bool):
        """Handle turning points show/hide toggle."""
        logger.debug(f"Turning points show toggled to: {state}")
        self._on_settings_changed()
    
    def apply_settings(self):
        """Apply all settings changes."""
        self.track_path_widget.apply_to_config()
        self.turning_points_widget.apply_to_config()
        logger.info("Settings applied")
    
    def save_settings(self) -> bool:
        """Save all settings to file."""
        self.apply_settings()
        return self.track_path_widget.save_to_file()
    
    def reset_settings(self):
        """Reset all settings to defaults."""
        # TODO: Implement reset logic
        logger.info("Settings reset")
