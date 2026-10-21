"""
Performance settings widget for CourseStudio.

Allows user to customize performance-related settings:
- Prune Points minimum distance threshold
"""

import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import pyqtSignal, Qt

from config.app_config_yaml import AppConfig
from src.gui.widgets.slider_setting_widget import SliderSettingWidget

logger = logging.getLogger(__name__)


class PerformanceSettingsWidget(QWidget):
    """
    Settings widget for performance-related options.
    
    Provides controls for:
    - Prune Points minimum distance
    """
    
    settings_changed = pyqtSignal()
    
    def __init__(self, config: AppConfig):
        """
        Initialize performance settings widget.
        
        Args:
            config: AppConfig instance
        """
        super().__init__()
        
        self.config = config
        
        # Load current values from config
        self.min_distance_m = self.config.get_int(
            'performance.prune_points.min_distance_m',
            50  # Default: 50m
        )
        
        self._init_ui()
        
        logger.info("PerformanceSettingsWidget initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # ====================================================================
        # Prune Points Section
        # ====================================================================
        
        section_label = QLabel("Prune Points")
        section_label.setStyleSheet("font-weight: bold; color: white; text-decoration: underline;")
        layout.addWidget(section_label)
        
        # Min Distance slider
        min_distance_layout = QHBoxLayout()
        min_distance_layout.setContentsMargins(0, 0, 0, 0)
        min_distance_layout.setSpacing(15)
        
        min_distance_label = QLabel("Min Distance:")
        min_distance_label.setStyleSheet("font-weight: bold; color: white;")
        min_distance_label.setFixedWidth(120)
        min_distance_layout.addWidget(min_distance_label)
        
        self.min_distance_slider = SliderSettingWidget(
            min_val=20,
            max_val=200,
            current_val=self.min_distance_m,
            suffix="m",
            include_label=False
        )
        self.min_distance_slider.value_changed.connect(self._on_settings_changed)
        min_distance_layout.addWidget(self.min_distance_slider, 1)
        layout.addLayout(min_distance_layout)
        
        # Add stretch at bottom to push content to top
        layout.addStretch()
        
        logger.debug(f"PerformanceSettingsWidget UI initialized with min_distance={self.min_distance_m}m")
    
    def _on_settings_changed(self):
        """Handle settings change."""
        self.settings_changed.emit()
    
    def apply_to_config(self):
        """Apply current settings to config."""
        min_distance = self.min_distance_slider.get_value()
        
        logger.info(f"Performance.apply_to_config: Setting min_distance_m={min_distance}")
        self.config.set('performance.prune_points.min_distance_m', min_distance)
        logger.info(f"Performance settings applied: min_distance_m={min_distance}")
        
        # Debug: show what's in config_data after set
        if hasattr(self.config, 'config_data'):
            perf = self.config.config_data.get('performance', {})
            logger.info(f"DEBUG: config_data['performance'] after set = {perf}")
