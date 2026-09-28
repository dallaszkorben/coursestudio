"""
Color Picker Widget for CourseStudio Settings.

Provides an inline color picker with:
- Preset color buttons (loaded from settings.yaml - not hardcoded!)
- RGB sliders (Apple-style fine-tuning)
- Hex input field (direct entry)
- Live color preview
"""

import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider,
    QLabel, QLineEdit, QSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QIcon, QPixmap

from config.app_config_yaml import AppConfig

logger = logging.getLogger(__name__)

# Apple-style slider stylesheet (matching seeboard pattern)
SLIDER_STYLESHEET = """
QSlider {
    border: none;
    outline: none;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #e0e0e0;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #007AFF;
    border-radius: 3px;
}

QSlider::add-page:horizontal {
    background: #e0e0e0;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    width: 18px;
    height: 18px;
    margin: -6px 0;
    background: #007AFF;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background: #0051D5;
}

QSlider::handle:horizontal:pressed {
    background: #003DA3;
}
"""


class ColorPickerWidget(QWidget):
    """
    Inline color picker with presets, RGB sliders, and hex input.
    
    Features:
    - Preset color buttons (loaded from settings.yaml)
    - RGB sliders for fine-tuning (R, G, B: 0-255)
    - Hex input field for direct hex code entry
    - Live color preview square
    - Signals color changes for real-time feedback
    
    Color palette is configured in settings.yaml, not hardcoded.
    """
    
    color_changed = pyqtSignal(str)  # Emits hex color (e.g., 'FF0000')
    
    def __init__(self, initial_color: str = 'FF0000', config: AppConfig = None, config_path: str = None):
        """
        Initialize color picker.
        
        Args:
            initial_color: Initial hex color without '#' (e.g., 'FF0000')
            config: AppConfig instance (optional, loads from file if None)
            config_path: Custom path to load colors from (e.g., 'Appearance.MapDisplay.TurningPoints.colors')
                        If None, defaults to 'Appearance.MapDisplay.TrackPath.colors'
        """
        super().__init__()
        
        self.config = config or AppConfig()
        self.current_color = initial_color.upper()
        self._updating = False  # Flag to prevent recursive updates
        
        # Load color palette from settings.yaml (not hardcoded!)
        if config_path is None:
            config_path = 'Appearance.MapDisplay.TrackPath.colors'
        
        self.preset_colors = self.config.get_dict(config_path, {})
        
        # If palette not found in config, use empty dict (no presets)
        if not self.preset_colors:
            logger.warning(f"No color palette found at {config_path} - using no presets")
            self.preset_colors = {}
        
        self._init_ui()
        self._set_color(self.current_color)
        
        logger.info(f"ColorPickerWidget initialized with color: {self.current_color}, {len(self.preset_colors)} presets loaded from {config_path}")
    
    def _init_ui(self):
        """Initialize the user interface with proper two-column alignment."""
        
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)  # ZERO spacing
        
        # ====================================================================
        # Grid Layout for proper alignment
        # ====================================================================
        
        from PyQt5.QtWidgets import QGridLayout
        grid = QGridLayout()
        grid.setSpacing(0)  # ZERO spacing by default
        grid.setContentsMargins(0, 0, 0, 0)  # ZERO margins
        grid.setHorizontalSpacing(18)  # 18 pixels horizontal spacing between label and control
        grid.setVerticalSpacing(0)  # ZERO vertical spacing by default
        grid.setColumnStretch(0, 0)  # Label column - fixed width
        grid.setColumnStretch(1, 1)  # Control column - flexible
        
        row = 0
        
        # ====================================================================
        # Row 0: Color Title + Preview Square
        # ====================================================================
        
        title_label = QLabel("Color:")
        title_label.setStyleSheet("font-weight: bold; color: white;")
        grid.addWidget(title_label, row, 0)
        
        # Color preview square
        self.preview_square = QLabel()
        self.preview_square.setStyleSheet(
            "border: 2px solid #ccc; border-radius: 4px; min-width: 30px; "
            "min-height: 30px; max-width: 30px; max-height: 30px;"
        )
        preview_layout = QHBoxLayout()
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(0)
        preview_layout.addWidget(self.preview_square)
        preview_layout.addStretch()
        preview_widget = QWidget()
        preview_widget.setLayout(preview_layout)
        grid.addWidget(preview_widget, row, 1)
        row += 1
        
        # ====================================================================
        # Spacer Row: 4 pixels vertical space before Quick Select
        # ====================================================================
        spacer = QWidget()
        spacer.setMinimumHeight(4)
        spacer.setMaximumHeight(4)
        grid.addWidget(spacer, row, 0, 1, 2)  # Span both columns
        row += 1
        
        # ====================================================================
        # Row 2: Quick Select Label + Preset Buttons
        # ====================================================================
        
        presets_label = QLabel("Quick Select:")
        presets_label.setStyleSheet("font-weight: bold; font-size: 12px; color: white;")
        grid.addWidget(presets_label, row, 0)
        
        presets_layout = QHBoxLayout()
        presets_layout.setContentsMargins(0, 0, 0, 0)
        presets_layout.setSpacing(4)  # 4 pixels spacing between preset buttons
        self.preset_buttons = {}
        for color_name, hex_code in self.preset_colors.items():
            btn = QPushButton()
            btn.setMaximumWidth(35)
            btn.setMaximumHeight(30)
            
            # Set background color
            rgb = self._hex_to_rgb(hex_code)
            btn.setStyleSheet(
                f"QPushButton {{"
                f"  background-color: #{hex_code};"
                f"  border: 2px solid #ddd;"
                f"  border-radius: 4px;"
                f"  padding: 0px;"
                f"}}"
                f"QPushButton:hover {{"
                f"  border: 2px solid #333;"
                f"}}"
            )
            
            btn.setToolTip(f"{color_name} (#{hex_code})")
            btn.clicked.connect(lambda checked, c=hex_code: self._on_preset_clicked(c))
            
            presets_layout.addWidget(btn)
            self.preset_buttons[hex_code] = btn
        
        presets_layout.addStretch()
        presets_widget = QWidget()
        presets_widget.setLayout(presets_layout)
        grid.addWidget(presets_widget, row, 1)
        row += 1
        
        # ====================================================================
        # Spacer Row: 4 pixels vertical space before RGB Sliders
        # ====================================================================
        spacer2 = QWidget()
        spacer2.setMinimumHeight(4)
        spacer2.setMaximumHeight(4)
        grid.addWidget(spacer2, row, 0, 1, 2)  # Span both columns
        row += 1
        
        # ====================================================================
        # Rows for RGB Sliders
        # ====================================================================
        
        # Red slider
        r_label = QLabel("R:")
        r_label.setStyleSheet("font-weight: bold; color: white;")
        grid.addWidget(r_label, row, 0)
        
        r_control_layout = QHBoxLayout()
        r_control_layout.setContentsMargins(0, 0, 0, 0)
        r_control_layout.setSpacing(0)
        self.r_slider = QSlider(Qt.Horizontal)
        self.r_slider.setMinimum(0)
        self.r_slider.setMaximum(255)
        self.r_slider.setTickPosition(QSlider.NoTicks)
        self.r_slider.setValue(255)
        self.r_slider.setStyleSheet(SLIDER_STYLESHEET)
        self.r_slider.setMinimumHeight(30)
        self.r_slider.valueChanged.connect(self._on_rgb_slider_changed)
        r_control_layout.addWidget(self.r_slider)
        
        self.r_spinbox = QSpinBox()
        self.r_spinbox.setMinimum(0)
        self.r_spinbox.setMaximum(255)
        self.r_spinbox.setValue(255)
        self.r_spinbox.setMaximumWidth(50)
        self.r_spinbox.valueChanged.connect(self._on_r_spinbox_changed)
        r_control_layout.addWidget(self.r_spinbox)
        
        r_control_widget = QWidget()
        r_control_widget.setLayout(r_control_layout)
        grid.addWidget(r_control_widget, row, 1)
        row += 1
        
        # Green slider
        g_label = QLabel("G:")
        g_label.setStyleSheet("font-weight: bold; color: white;")
        grid.addWidget(g_label, row, 0)
        
        g_control_layout = QHBoxLayout()
        g_control_layout.setContentsMargins(0, 0, 0, 0)
        g_control_layout.setSpacing(0)
        self.g_slider = QSlider(Qt.Horizontal)
        self.g_slider.setMinimum(0)
        self.g_slider.setMaximum(255)
        self.g_slider.setTickPosition(QSlider.NoTicks)
        self.g_slider.setValue(0)
        self.g_slider.setStyleSheet(SLIDER_STYLESHEET)
        self.g_slider.setMinimumHeight(30)
        self.g_slider.valueChanged.connect(self._on_rgb_slider_changed)
        g_control_layout.addWidget(self.g_slider)
        
        self.g_spinbox = QSpinBox()
        self.g_spinbox.setMinimum(0)
        self.g_spinbox.setMaximum(255)
        self.g_spinbox.setValue(0)
        self.g_spinbox.setMaximumWidth(50)
        self.g_spinbox.valueChanged.connect(self._on_g_spinbox_changed)
        g_control_layout.addWidget(self.g_spinbox)
        
        g_control_widget = QWidget()
        g_control_widget.setLayout(g_control_layout)
        grid.addWidget(g_control_widget, row, 1)
        row += 1
        
        # Blue slider
        b_label = QLabel("B:")
        b_label.setStyleSheet("font-weight: bold; color: white;")
        grid.addWidget(b_label, row, 0)
        
        b_control_layout = QHBoxLayout()
        b_control_layout.setContentsMargins(0, 0, 0, 0)
        b_control_layout.setSpacing(0)
        self.b_slider = QSlider(Qt.Horizontal)
        self.b_slider.setMinimum(0)
        self.b_slider.setMaximum(255)
        self.b_slider.setTickPosition(QSlider.NoTicks)
        self.b_slider.setValue(0)
        self.b_slider.setStyleSheet(SLIDER_STYLESHEET)
        self.b_slider.setMinimumHeight(30)
        self.b_slider.valueChanged.connect(self._on_rgb_slider_changed)
        b_control_layout.addWidget(self.b_slider)
        
        self.b_spinbox = QSpinBox()
        self.b_spinbox.setMinimum(0)
        self.b_spinbox.setMaximum(255)
        self.b_spinbox.setValue(0)
        self.b_spinbox.setMaximumWidth(50)
        self.b_spinbox.valueChanged.connect(self._on_b_spinbox_changed)
        b_control_layout.addWidget(self.b_spinbox)
        
        b_control_widget = QWidget()
        b_control_widget.setLayout(b_control_layout)
        grid.addWidget(b_control_widget, row, 1)
        row += 1
        
        # ====================================================================
        # Row 5: Hex Input
        # ====================================================================
        
        hex_label = QLabel("Hex:")
        hex_label.setStyleSheet("font-weight: bold; color: white;")
        grid.addWidget(hex_label, row, 0)
        
        hex_control_layout = QHBoxLayout()
        hex_control_layout.setContentsMargins(0, 0, 0, 0)
        hex_control_layout.setSpacing(0)
        self.hex_input = QLineEdit()
        self.hex_input.setMaximumWidth(120)
        self.hex_input.setPlaceholderText("FF0000")
        self.hex_input.editingFinished.connect(self._on_hex_input_changed)
        hex_control_layout.addWidget(self.hex_input)
        hex_control_layout.addStretch()
        
        hex_control_widget = QWidget()
        hex_control_widget.setLayout(hex_control_layout)
        grid.addWidget(hex_control_widget, row, 1)
        
        main_layout.addLayout(grid)
        
        # Add stretch at bottom
        main_layout.addStretch()
    
    def _on_preset_clicked(self, hex_color: str):
        """Handle preset color button click."""
        self._set_color(hex_color)
    
    def _on_rgb_slider_changed(self):
        """Handle RGB slider value changes."""
        if self._updating:
            return
        
        r = self.r_slider.value()
        g = self.g_slider.value()
        b = self.b_slider.value()
        
        hex_color = f"{r:02X}{g:02X}{b:02X}"
        self._set_color(hex_color)
    
    def _on_r_spinbox_changed(self, value: int):
        """Handle R spinbox change."""
        if self._updating:
            return
        self._updating = True
        self.r_slider.setValue(value)
        self._updating = False
    
    def _on_g_spinbox_changed(self, value: int):
        """Handle G spinbox change."""
        if self._updating:
            return
        self._updating = True
        self.g_slider.setValue(value)
        self._updating = False
    
    def _on_b_spinbox_changed(self, value: int):
        """Handle B spinbox change."""
        if self._updating:
            return
        self._updating = True
        self.b_slider.setValue(value)
        self._updating = False
    
    def _on_hex_input_changed(self):
        """Handle hex input field change."""
        hex_text = self.hex_input.text().upper().replace('#', '')
        
        # Validate hex format
        if len(hex_text) == 6 and all(c in '0123456789ABCDEF' for c in hex_text):
            self._set_color(hex_text)
        else:
            # Invalid, revert to current color
            self.hex_input.setText(self.current_color)
    
    def _set_color(self, hex_color: str):
        """
        Set the current color and update all UI elements.
        
        Args:
            hex_color: Hex color string without '#' (e.g., 'FF0000')
        """
        self._updating = True
        
        hex_color = hex_color.upper()
        self.current_color = hex_color
        
        # Parse RGB from hex
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
        except ValueError:
            logger.error(f"Invalid hex color: {hex_color}")
            self._updating = False
            return
        
        # Update sliders
        self.r_slider.setValue(r)
        self.g_slider.setValue(g)
        self.b_slider.setValue(b)
        
        # Update spinboxes
        self.r_spinbox.setValue(r)
        self.g_spinbox.setValue(g)
        self.b_spinbox.setValue(b)
        
        # Update hex input
        self.hex_input.setText(hex_color)
        
        # Update preview square
        self.preview_square.setStyleSheet(
            f"background-color: #{hex_color}; border: 2px solid #ccc; "
            f"border-radius: 4px; min-width: 30px; min-height: 30px; "
            f"max-width: 30px; max-height: 30px;"
        )
        
        self._updating = False
        
        # Emit signal
        self.color_changed.emit(hex_color)
    
    def get_color(self) -> str:
        """Get current color as hex string."""
        return self.current_color
    
    def set_color(self, hex_color: str):
        """Set color from hex string."""
        self._set_color(hex_color)
    
    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
