"""
Turning Points Settings Widget for CourseStudio Settings.

Combines color pickers, size sliders, and toggle switch for turning points appearance.
"""

import logging
from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QWidget
from PyQt5.QtCore import pyqtSignal, Qt

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
        
        logger.info(f"TurningPointsSettingsWidget initialized (show={self.show}, color={self.color}, size={self.size})")
    
    def _init_ui(self):
        """Initialize the user interface."""
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.setSpacing(8)  # Tight spacing between sections
        layout.setContentsMargins(10, 10, 10, 10)
        
        # ====================================================================
        # Subsection 1: General Points Settings
        # ====================================================================
        
        general_section = self._create_subsection("General Points")
        general_layout = QVBoxLayout()
        general_layout.setSpacing(8)
        general_layout.setContentsMargins(8, 8, 8, 8)
        
        # Show/Hide Toggle
        toggle_layout = QHBoxLayout()
        toggle_layout.setContentsMargins(0, 0, 0, 0)
        toggle_layout.setSpacing(0)
        self.show_toggle = ToggleSwitchWidget(title="Show Points", initial_state=self.show)
        toggle_layout.addWidget(self.show_toggle)
        # NO addStretch() - let it stay compact on the left!
        general_layout.addLayout(toggle_layout)
        
        # Color Picker
        color_label = QLabel("Color:")
        color_label.setStyleSheet("font-weight: bold; font-size: 12px; color: white;")
        general_layout.addWidget(color_label)
        
        self.color_picker = ColorPickerWidget(
            initial_color=self.color,
            config=self.config,
            config_path='Appearance.MapDisplay.TurningPoints.colors'
        )
        general_layout.addWidget(self.color_picker)
        
        # Size Slider - with fixed-width label for alignment
        size_layout = QHBoxLayout()
        size_layout.setContentsMargins(0, 0, 0, 0)
        size_layout.setSpacing(8)
        
        size_label = QLabel("Size:")
        size_label.setStyleSheet("font-weight: bold; color: white;")
        size_label.setFixedWidth(70)  # Same width as "Width:" in TrackPath
        size_layout.addWidget(size_label)
        
        self.size_slider = SliderSettingWidget(
            min_val=2,
            max_val=10,
            current_val=self.size,
            suffix="px",
            include_label=False
        )
        size_layout.addWidget(self.size_slider, 1)
        
        general_layout.addLayout(size_layout)
        general_section.setLayout(general_layout)
        layout.addWidget(general_section)
        
        # ====================================================================
        # Subsection 2: Selected Point Settings
        # ====================================================================
        
        selected_section = self._create_subsection("Selected Points")
        selected_layout = QVBoxLayout()
        selected_layout.setSpacing(8)
        selected_layout.setContentsMargins(8, 8, 8, 8)
        
        # Color Picker
        selected_color_label = QLabel("Color:")
        selected_color_label.setStyleSheet("font-weight: bold; font-size: 12px; color: white;")
        selected_layout.addWidget(selected_color_label)
        
        self.selected_color_picker = ColorPickerWidget(
            initial_color=self.selected_color,
            config=self.config,
            config_path='Appearance.MapDisplay.TurningPoints.selected.colors'
        )
        selected_layout.addWidget(self.selected_color_picker)
        
        # Size Slider - with fixed-width label for alignment
        selected_size_layout = QHBoxLayout()
        selected_size_layout.setContentsMargins(0, 0, 0, 0)
        selected_size_layout.setSpacing(8)
        
        selected_size_label = QLabel("Size:")
        selected_size_label.setStyleSheet("font-weight: bold; color: white;")
        selected_size_label.setFixedWidth(70)  # Same width as "Width:" and other "Size:"
        selected_size_layout.addWidget(selected_size_label)
        
        self.selected_size_slider = SliderSettingWidget(
            min_val=4,
            max_val=15,
            current_val=self.selected_size,
            suffix="px",
            include_label=False
        )
        selected_size_layout.addWidget(self.selected_size_slider, 1)
        
        selected_layout.addLayout(selected_size_layout)
        selected_section.setLayout(selected_layout)
        layout.addWidget(selected_section)
        
        # Add stretch to push controls to top
        layout.addStretch()
    
    def _create_subsection(self, title: str) -> QGroupBox:
        """Create a styled subsection container with gray frame."""
        section = QGroupBox(title)
        section.setStyleSheet("""
            QGroupBox {
                border: 1px solid #999999;
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
        return section
    
    def _connect_signals(self):
        """Connect widget signals."""
        
        self.show_toggle.toggled.connect(self._on_show_toggled)
        self.color_picker.color_changed.connect(self._on_color_changed)
        self.size_slider.value_changed.connect(self._on_size_changed)
        self.selected_color_picker.color_changed.connect(self._on_selected_color_changed)
        self.selected_size_slider.value_changed.connect(self._on_selected_size_changed)
        
        # Initialize controls with the correct enabled state
        self._set_controls_enabled(self.show)
    
    def _on_show_toggled(self, state: bool):
        """Handle show/hide toggle."""
        self.show = state
        logger.debug(f"Turning points show toggled to: {state}")
        
        # Enable/disable all appearance controls based on show state
        self._set_controls_enabled(state)
        
        self.show_toggled.emit(state)
        self.settings_changed.emit()
    
    def _set_controls_enabled(self, enabled: bool):
        """Enable or disable all appearance controls based on show state."""
        # ONLY disable/enable controls in GENERAL POINTS section
        # Do NOT touch Selected Points section
        
        # Disable/enable ALL child widgets in color picker (preset buttons, sliders, inputs, etc.)
        self._set_widget_tree_enabled(self.color_picker, enabled)
        
        # Disable/enable size slider and all its children
        self._set_widget_tree_enabled(self.size_slider, enabled)
    
    def _set_widget_tree_enabled(self, widget, enabled: bool):
        """Recursively enable/disable a widget and all its children."""
        widget.setEnabled(enabled)
        
        # Recursively disable all child widgets
        for child in widget.findChildren(QWidget):
            child.setEnabled(enabled)
    
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
