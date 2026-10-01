"""
Base widget for individual trackpoint type appearance settings.

Used for General, Single-Selected, and Multi-Selected track points.
"""

import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import pyqtSignal, Qt

from config.app_config_yaml import AppConfig
from src.gui.widgets.color_picker_widget import ColorPickerWidget
from src.gui.widgets.slider_setting_widget import SliderSettingWidget

logger = logging.getLogger(__name__)


class TrackpointTypeSettingsWidget(QWidget):
    """
    Settings widget for a specific trackpoint type (General, Selected, Double-Selected).
    
    Provides controls for:
    - Body color and size
    - Outline color and size
    """
    
    settings_changed = pyqtSignal()
    
    def __init__(self, config: AppConfig, point_type: str):
        """
        Initialize trackpoint type settings widget.
        
        Args:
            config: AppConfig instance
            point_type: 'GeneralPoints', 'SelectedPoints', or 'DoubleSelectedPoints'
        """
        super().__init__()
        
        self.config = config
        self.point_type = point_type
        
        # Load current values from config
        self.body_color = self.config.get_str(
            f'Appearance.MapDisplay.Trackpoints.{point_type}.body.color', 
            'FFFF00'
        )
        self.body_size = self.config.get_int(
            f'Appearance.MapDisplay.Trackpoints.{point_type}.body.size', 
            4
        )
        self.outline_color = self.config.get_str(
            f'Appearance.MapDisplay.Trackpoints.{point_type}.outline.color', 
            'FFFFFF'
        )
        self.outline_size = self.config.get_int(
            f'Appearance.MapDisplay.Trackpoints.{point_type}.outline.size', 
            1
        )
        
        self._init_ui()
        self._connect_signals()
        
        logger.info(f"TrackpointTypeSettingsWidget initialized for {point_type}")
    
    def _init_ui(self):
        """Initialize the user interface."""
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # ====================================================================
        # Body Section
        # ====================================================================
        
        body_label = QLabel("Body")
        body_label.setStyleSheet("font-weight: bold; color: white; text-decoration: underline;")
        layout.addWidget(body_label)
        
        # Body color picker
        self.body_color_picker = ColorPickerWidget(
            initial_color=self.body_color,
            config=self.config
        )
        self.body_color_picker.color_changed.connect(self._on_settings_changed)
        layout.addWidget(self.body_color_picker)
        
        # Body size slider
        body_size_layout = QHBoxLayout()
        body_size_layout.setContentsMargins(0, 0, 0, 0)
        body_size_layout.setSpacing(15)
        body_size_label = QLabel("Size:")
        body_size_label.setStyleSheet("font-weight: bold; color: white;")
        body_size_label.setFixedWidth(70)
        body_size_layout.addWidget(body_size_label)
        
        max_size = 15 if self.point_type == 'SelectedPoints' or self.point_type == 'DoubleSelectedPoints' else 10
        self.body_size_slider = SliderSettingWidget(
            min_val=1, 
            max_val=max_size, 
            current_val=self.body_size, 
            suffix="px", 
            include_label=False
        )
        self.body_size_slider.value_changed.connect(self._on_settings_changed)
        body_size_layout.addWidget(self.body_size_slider, 1)
        layout.addLayout(body_size_layout)
        
        # Outline Section
        outline_label = QLabel("Outline")
        outline_label.setStyleSheet("font-weight: bold; color: white; text-decoration: underline;")
        layout.addWidget(outline_label)
        
        # Outline color picker
        self.outline_color_picker = ColorPickerWidget(
            initial_color=self.outline_color,
            config=self.config
        )
        self.outline_color_picker.color_changed.connect(self._on_settings_changed)
        layout.addWidget(self.outline_color_picker)
        
        # Outline size slider
        outline_size_layout = QHBoxLayout()
        outline_size_layout.setContentsMargins(0, 0, 0, 0)
        outline_size_layout.setSpacing(15)
        outline_size_label = QLabel("Size:")
        outline_size_label.setStyleSheet("font-weight: bold; color: white;")
        outline_size_label.setFixedWidth(70)
        outline_size_layout.addWidget(outline_size_label)
        
        self.outline_size_slider = SliderSettingWidget(
            min_val=0, 
            max_val=5, 
            current_val=self.outline_size, 
            suffix="px", 
            include_label=False
        )
        self.outline_size_slider.value_changed.connect(self._on_settings_changed)
        outline_size_layout.addWidget(self.outline_size_slider, 1)
        layout.addLayout(outline_size_layout)
        
        # Add stretch
        layout.addStretch()
    
    def _connect_signals(self):
        """Connect signals for settings changes."""
        pass
    
    def _on_settings_changed(self):
        """Handle settings change."""
        self.settings_changed.emit()
    
    def apply_to_config(self):
        """Apply current settings to config."""
        body_color = self.body_color_picker.get_color_hex()
        body_size = self.body_size_slider.get_value()
        outline_color = self.outline_color_picker.get_color_hex()
        outline_size = self.outline_size_slider.get_value()
        
        self.config.set_str(f'Appearance.MapDisplay.Trackpoints.{self.point_type}.body.color', body_color)
        self.config.set_int(f'Appearance.MapDisplay.Trackpoints.{self.point_type}.body.size', body_size)
        self.config.set_str(f'Appearance.MapDisplay.Trackpoints.{self.point_type}.outline.color', outline_color)
        self.config.set_int(f'Appearance.MapDisplay.Trackpoints.{self.point_type}.outline.size', outline_size)
