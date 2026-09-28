"""
Track Path Settings Widget for CourseStudio Settings.

Combines color picker and width slider for track path appearance settings.
"""

import logging
from PyQt5.QtWidgets import QGroupBox, QVBoxLayout
from PyQt5.QtCore import pyqtSignal

from config.app_config_yaml import AppConfig
from src.gui.widgets.color_picker_widget import ColorPickerWidget
from src.gui.widgets.slider_setting_widget import SliderSettingWidget

logger = logging.getLogger(__name__)


class TrackPathSettingsWidget(QGroupBox):
    """
    Track Path appearance settings section.
    
    Provides controls for:
    - Track path color (color picker with presets + RGB sliders)
    - Track path width (slider 1-9px)
    """
    
    settings_changed = pyqtSignal()  # Emitted when settings change
    
    def __init__(self, config: AppConfig = None):
        """
        Initialize track path settings widget.
        
        Args:
            config: AppConfig instance (optional, for loading defaults)
        """
        super().__init__("Track Path")
        
        self.config = config or AppConfig()
        
        # Load current values from config
        self.color = self.config.get_str('Appearance.MapDisplay.TrackPath.color', 'FF0000')
        self.width = self.config.get_int('Appearance.MapDisplay.TrackPath.width', 3)
        
        # Apply white frame styling (main section)
        self.setStyleSheet("""
            QGroupBox {
                border: 1px solid white;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                font-weight: bold;
                color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0px 4px;
            }
        """)
        
        self._init_ui()
        self._connect_signals()
        
        logger.info(f"TrackPathSettingsWidget initialized (color={self.color}, width={self.width})")
    
    def _init_ui(self):
        """Initialize the user interface."""
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # ====================================================================
        # Color Picker Widget
        # ====================================================================
        
        self.color_picker = ColorPickerWidget(initial_color=self.color, config=self.config)
        layout.addWidget(self.color_picker)
        
        # ====================================================================
        # Width Slider Widget
        # ====================================================================
        
        self.width_slider = SliderSettingWidget(
            title="Width",
            min_val=1,
            max_val=9,
            current_val=self.width,
            suffix="px"
        )
        layout.addWidget(self.width_slider)
        
        # Add stretch to push controls to top
        layout.addStretch()
    
    def _connect_signals(self):
        """Connect widget signals."""
        
        self.color_picker.color_changed.connect(self._on_color_changed)
        self.width_slider.value_changed.connect(self._on_width_changed)
    
    def _on_color_changed(self, hex_color: str):
        """Handle color change."""
        self.color = hex_color
        logger.debug(f"Track path color changed to: {hex_color}")
        self.settings_changed.emit()
    
    def _on_width_changed(self, width: int):
        """Handle width change."""
        self.width = width
        logger.debug(f"Track path width changed to: {width}px")
        self.settings_changed.emit()
    
    def get_color(self) -> str:
        """Get current track path color."""
        return self.color_picker.get_color()
    
    def set_color(self, hex_color: str):
        """Set track path color."""
        self.color_picker.set_color(hex_color)
    
    def get_width(self) -> int:
        """Get current track path width."""
        return self.width_slider.get_value()
    
    def set_width(self, width: int):
        """Set track path width."""
        self.width_slider.set_value(width)
    
    def apply_to_config(self):
        """Apply current settings to configuration."""
        
        self.config.config_data['Appearance']['MapDisplay']['TrackPath']['color'] = self.get_color()
        self.config.config_data['Appearance']['MapDisplay']['TrackPath']['width'] = self.get_width()
        
        logger.info(f"Track path settings applied: color={self.get_color()}, width={self.get_width()}")
    
    def save_to_file(self) -> bool:
        """Save settings to file."""
        
        self.apply_to_config()
        return self.config.save_to_file()
