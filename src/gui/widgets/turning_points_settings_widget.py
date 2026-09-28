"""
Turning Points Settings Widget for CourseStudio Settings.

Combines color pickers, size sliders, and toggle switch for turning points appearance.
"""

import logging
from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import pyqtSignal

from config.app_config_yaml import AppConfig
from src.gui.widgets.color_picker_widget import ColorPickerWidget
from src.gui.widgets.slider_setting_widget import SliderSettingWidget
from src.gui.widgets.toggle_switch_widget import ToggleSwitchWidget

logger = logging.getLogger(__name__)


class TurningPointsSettingsWidget(QGroupBox):
    """
    Turning Points (Trackpoints) appearance settings section.
    
    Provides controls for:
    - Show/Hide toggle (Apple-style switch)
    - Turning point color (color picker with presets)
    - Turning point size (slider 2-10px)
    - Selected point color (color picker with presets)
    - Selected point size (slider 4-15px)
    """
    
    settings_changed = pyqtSignal()  # Emitted when settings change
    show_toggled = pyqtSignal(bool)  # Emitted when show/hide toggled
    
    def __init__(self, config: AppConfig = None):
        """
        Initialize turning points settings widget.
        
        Args:
            config: AppConfig instance (optional, for loading defaults)
        """
        super().__init__("Turning Points")
        
        self.config = config or AppConfig()
        
        # Load current values from config
        self.show = self.config.get_bool('Appearance.MapDisplay.TurningPoints.show', True)
        self.color = self.config.get_str('Appearance.MapDisplay.TurningPoints.color', 'FFFF00')
        self.size = self.config.get_int('Appearance.MapDisplay.TurningPoints.size', 4)
        self.selected_color = self.config.get_str('Appearance.MapDisplay.TurningPoints.selected.color', '0000FF')
        self.selected_size = self.config.get_int('Appearance.MapDisplay.TurningPoints.selected.size', 7)
        
        self._init_ui()
        self._connect_signals()
        
        logger.info(f"TurningPointsSettingsWidget initialized (show={self.show}, color={self.color}, size={self.size})")
    
    def _init_ui(self):
        """Initialize the user interface."""
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # ====================================================================
        # Show/Hide Toggle (Apple-style switch)
        # ====================================================================
        
        toggle_layout = QHBoxLayout()
        self.show_toggle = ToggleSwitchWidget(title="Show Points", initial_state=self.show)
        toggle_layout.addWidget(self.show_toggle)
        toggle_layout.addStretch()
        layout.addLayout(toggle_layout)
        
        # ====================================================================
        # Turning Point Color Picker
        # ====================================================================
        
        color_label = QLabel("Turning Point Color:")
        color_label.setStyleSheet("font-weight: bold; font-size: 11px; color: #666;")
        layout.addWidget(color_label)
        
        # Load color palette from config for turning points
        self.color_picker = ColorPickerWidget(
            initial_color=self.color,
            config=self.config,
            config_path='Appearance.MapDisplay.TurningPoints.colors'
        )
        layout.addWidget(self.color_picker)
        
        # ====================================================================
        # Turning Point Size Slider
        # ====================================================================
        
        self.size_slider = SliderSettingWidget(
            title="Size",
            min_val=2,
            max_val=10,
            current_val=self.size,
            suffix="px"
        )
        layout.addWidget(self.size_slider)
        
        # ====================================================================
        # Selected Point Color Picker
        # ====================================================================
        
        selected_color_label = QLabel("Selected Point Color:")
        selected_color_label.setStyleSheet("font-weight: bold; font-size: 11px; color: #666;")
        layout.addWidget(selected_color_label)
        
        # Load color palette from config for selected turning points
        self.selected_color_picker = ColorPickerWidget(
            initial_color=self.selected_color,
            config=self.config,
            config_path='Appearance.MapDisplay.TurningPoints.selected.colors'
        )
        layout.addWidget(self.selected_color_picker)
        
        # ====================================================================
        # Selected Point Size Slider
        # ====================================================================
        
        self.selected_size_slider = SliderSettingWidget(
            title="Selected Size",
            min_val=4,
            max_val=15,
            current_val=self.selected_size,
            suffix="px"
        )
        layout.addWidget(self.selected_size_slider)
        
        # Add stretch to push controls to top
        layout.addStretch()
    
    def _connect_signals(self):
        """Connect widget signals."""
        
        self.show_toggle.toggled.connect(self._on_show_toggled)
        self.color_picker.color_changed.connect(self._on_color_changed)
        self.size_slider.value_changed.connect(self._on_size_changed)
        self.selected_color_picker.color_changed.connect(self._on_selected_color_changed)
        self.selected_size_slider.value_changed.connect(self._on_selected_size_changed)
    
    def _on_show_toggled(self, state: bool):
        """Handle show/hide toggle."""
        self.show = state
        logger.debug(f"Turning points show toggled to: {state}")
        self.show_toggled.emit(state)
        self.settings_changed.emit()
    
    def _on_color_changed(self, hex_color: str):
        """Handle color change."""
        self.color = hex_color
        logger.debug(f"Turning point color changed to: {hex_color}")
        self.settings_changed.emit()
    
    def _on_size_changed(self, size: int):
        """Handle size change."""
        self.size = size
        logger.debug(f"Turning point size changed to: {size}px")
        self.settings_changed.emit()
    
    def _on_selected_color_changed(self, hex_color: str):
        """Handle selected color change."""
        self.selected_color = hex_color
        logger.debug(f"Selected point color changed to: {hex_color}")
        self.settings_changed.emit()
    
    def _on_selected_size_changed(self, size: int):
        """Handle selected size change."""
        self.selected_size = size
        logger.debug(f"Selected point size changed to: {size}px")
        self.settings_changed.emit()
    
    def apply_to_config(self):
        """Apply current settings to configuration."""
        
        self.config.config_data['Appearance']['MapDisplay']['TurningPoints']['show'] = self.get_show()
        self.config.config_data['Appearance']['MapDisplay']['TurningPoints']['color'] = self.get_color()
        self.config.config_data['Appearance']['MapDisplay']['TurningPoints']['size'] = self.get_size()
        self.config.config_data['Appearance']['MapDisplay']['TurningPoints']['selected']['color'] = self.get_selected_color()
        self.config.config_data['Appearance']['MapDisplay']['TurningPoints']['selected']['size'] = self.get_selected_size()
        
        logger.info(f"Turning points settings applied: show={self.get_show()}, color={self.get_color()}, size={self.get_size()}")
    
    def save_to_file(self) -> bool:
        """Save settings to file."""
        
        self.apply_to_config()
        return self.config.save_to_file()
    
    # Getters
    def get_show(self) -> bool:
        """Get show state."""
        return self.show_toggle.get_state()
    
    def get_color(self) -> str:
        """Get turning point color."""
        return self.color_picker.get_color()
    
    def get_size(self) -> int:
        """Get turning point size."""
        return self.size_slider.get_value()
    
    def get_selected_color(self) -> str:
        """Get selected point color."""
        return self.selected_color_picker.get_color()
    
    def get_selected_size(self) -> int:
        """Get selected point size."""
        return self.selected_size_slider.get_value()
