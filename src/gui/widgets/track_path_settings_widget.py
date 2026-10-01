"""
Track Path Settings Widget for CourseStudio Settings.

Combines color picker and width slider for track path appearance settings.
"""

import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt, pyqtSignal

from config.app_config_yaml import AppConfig
from src.gui.widgets.color_picker_widget import ColorPickerWidget
from src.gui.widgets.slider_setting_widget import SliderSettingWidget

logger = logging.getLogger(__name__)


class TrackPathSettingsWidget(QWidget):
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
        super().__init__()
        
        self.config = config or AppConfig()
        
        # Load current values from config
        self.body_color = self.config.get_str('Appearance.MapDisplay.TrackPath.body.color', 'FF0000')
        self.body_width = self.config.get_int('Appearance.MapDisplay.TrackPath.body.width', 3)
        self.outline_color = self.config.get_str('Appearance.MapDisplay.TrackPath.outline.color', 'FFFFFF')
        self.outline_width = self.config.get_int('Appearance.MapDisplay.TrackPath.outline.width', 1)
        self._updating = False  # Flag to prevent recursive updates
        
        self._init_ui()
        self._connect_signals()
        
        logger.info(f"TrackPathSettingsWidget initialized (body_color={self.body_color}, body_width={self.body_width}, outline_color={self.outline_color}, outline_width={self.outline_width}")
    
    def _init_ui(self):
        """Initialize the user interface."""
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # ====== BODY (Track line itself) ======
        body_label = QLabel("Body")
        body_label.setStyleSheet("font-weight: bold; color: white; text-decoration: underline;")
        layout.addWidget(body_label)
        
        # Color picker for body
        self.body_color_picker = ColorPickerWidget(initial_color=self.body_color, config=self.config)
        self.body_color_picker.color_changed.connect(self._on_settings_changed)
        layout.addWidget(self.body_color_picker)
        
        # Body width slider
        body_width_layout = QHBoxLayout()
        body_width_layout.setContentsMargins(0, 0, 0, 0)
        body_width_layout.setSpacing(15)
        body_width_label = QLabel("Width:")
        body_width_label.setStyleSheet("font-weight: bold; color: white;")
        body_width_label.setFixedWidth(70)
        body_width_layout.addWidget(body_width_label)
        
        self.body_width_slider = SliderSettingWidget(
            min_val=1, 
            max_val=9, 
            current_val=self.body_width, 
            suffix="px", 
            include_label=False
        )
        self.body_width_slider.value_changed.connect(self._on_settings_changed)
        body_width_layout.addWidget(self.body_width_slider, 1)
        layout.addLayout(body_width_layout)
        
        # ====== OUTLINE (Border around track line) ======
        outline_label = QLabel("Outline")
        outline_label.setStyleSheet("font-weight: bold; color: white; text-decoration: underline;")
        layout.addWidget(outline_label)
        
        # Color picker for outline
        self.outline_color_picker = ColorPickerWidget(initial_color=self.outline_color, config=self.config)
        self.outline_color_picker.color_changed.connect(self._on_settings_changed)
        layout.addWidget(self.outline_color_picker)
        
        # Outline width slider
        outline_width_layout = QHBoxLayout()
        outline_width_layout.setContentsMargins(0, 0, 0, 0)
        outline_width_layout.setSpacing(15)
        outline_width_label = QLabel("Width:")
        outline_width_label.setStyleSheet("font-weight: bold; color: white;")
        outline_width_label.setFixedWidth(70)
        outline_width_layout.addWidget(outline_width_label)
        
        self.outline_width_slider = SliderSettingWidget(
            min_val=0, 
            max_val=5, 
            current_val=self.outline_width, 
            suffix="px", 
            include_label=False
        )
        self.outline_width_slider.value_changed.connect(self._on_settings_changed)
        outline_width_layout.addWidget(self.outline_width_slider, 1)
        layout.addLayout(outline_width_layout)
        
        # Add stretch to push controls to top
        layout.addStretch()
    
    def _connect_signals(self):
        """Connect widget signals."""
        pass
    
    def _on_settings_changed(self):
        """Handle settings change."""
        self.settings_changed.emit()
    
    def get_body_color(self) -> str:
        """Get current track body color."""
        return self.body_color_picker.get_color_hex()
    
    def set_body_color(self, hex_color: str):
        """Set track body color."""
        self.body_color_picker.set_color(hex_color)
    
    def get_body_width(self) -> int:
        """Get current track body width."""
        return self.body_width_slider.get_value()
    
    def set_body_width(self, width: int):
        """Set track body width."""
        self.body_width_slider.set_value(width)
    
    def get_outline_color(self) -> str:
        """Get current track outline color."""
        return self.outline_color_picker.get_color_hex()
    
    def set_outline_color(self, hex_color: str):
        """Set track outline color."""
        self.outline_color_picker.set_color(hex_color)
    
    def get_outline_width(self) -> int:
        """Get current track outline width."""
        return self.outline_width_slider.get_value()
    
    def set_outline_width(self, width: int):
        """Set track outline width."""
        self.outline_width_slider.set_value(width)
    
    def apply_to_config(self):
        """Apply current settings to configuration."""
        body_color = self.body_color_picker.get_color_hex()
        body_width = self.body_width_slider.get_value()
        outline_color = self.outline_color_picker.get_color_hex()
        outline_width = self.outline_width_slider.get_value()
        
        self.config.set_str('Appearance.MapDisplay.TrackPath.body.color', body_color)
        self.config.set_int('Appearance.MapDisplay.TrackPath.body.width', body_width)
        self.config.set_str('Appearance.MapDisplay.TrackPath.outline.color', outline_color)
        self.config.set_int('Appearance.MapDisplay.TrackPath.outline.width', outline_width)
    
    def save_to_file(self) -> bool:
        """Save settings to file."""
        self.apply_to_config()
        return self.config.save_to_file()
