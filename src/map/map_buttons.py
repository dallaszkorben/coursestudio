"""
Shared map button management for Track Editor and Map Editor.

Centralizes button creation, positioning, and rendering to ensure
consistent appearance and behavior across both map implementations.
"""

import logging
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtCore import Qt
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class MapButtonConfig:
    """Configuration for all map buttons - shared between Track Editor and Map Editor."""
    
    BUTTON_SIZE = 40
    BUTTON_SPACING = 5
    PADDING_LEFT = 10
    PADDING_TOP = 10
    
    # Visual styling
    BUTTON_BG = (52, 144, 220, 200)
    BUTTON_TEXT = (255, 255, 255, 255)
    CORNER_RADIUS = 8
    
    # Font for zoom level display
    FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    FONT_SIZE = 13


class MapButton:
    """Represents a single map button with positioning and rendering."""
    
    def __init__(self, name: str, symbol: str, tooltip: str = ""):
        """
        Initialize a button definition.
        
        Args:
            name: Internal name (e.g., 'zoom_in', 'mark_center')
            symbol: Display symbol (e.g., '+', '⊕', 'Z:15')
            tooltip: Help text for the button
        """
        self.name = name
        self.symbol = symbol
        self.tooltip = tooltip
        self.qbutton = None  # Will be set when creating real button
        self.x = 0
        self.y = 0
        self.hovered = False  # Track hover state
        self.pressed = False  # Track pressed state
    
    def create_qbutton(self, parent, callback):
        """
        Create the real QPushButton widget.
        
        Args:
            parent: Parent widget
            callback: Function to call when clicked
        """
        self.qbutton = QPushButton(self.symbol, parent)
        self.qbutton.setFixedSize(MapButtonConfig.BUTTON_SIZE, MapButtonConfig.BUTTON_SIZE)
        self.qbutton.clicked.connect(callback)
        self.qbutton.setStyleSheet(
            "background-color: transparent; border: none; color: transparent;"
        )
        self.qbutton.setFocusPolicy(Qt.NoFocus)
        return self.qbutton
    
    def set_position(self, x: int, y: int):
        """Set button position on screen."""
        self.x = x
        self.y = y
        if self.qbutton:
            self.qbutton.move(x, y)
    
    def draw(self, draw_context, is_zoom_level_label: bool = False, zoom_level: int = 10):
        """
        Draw button visual on PIL image.
        
        Args:
            draw_context: PIL ImageDraw context
            is_zoom_level_label: If True, render as text label instead of symbol
            zoom_level: Current zoom level (used for zoom_level_label)
        """
        cfg = MapButtonConfig
        
        # Determine button appearance based on state
        if self.pressed:
            # Pressed: dark blue, slightly smaller (inset by 3 pixels)
            button_bg = (30, 100, 160, 255)  # Dark blue, fully opaque
            inset = 3
        elif self.hovered:
            # Hovered: bright blue, fully opaque
            button_bg = (52, 144, 220, 255)
            inset = 0
        else:
            # Normal: semi-transparent blue
            button_bg = (52, 144, 220, 200)
            inset = 0
        
        # Draw rounded rectangle background
        bbox = [self.x + inset, self.y + inset, 
                self.x + cfg.BUTTON_SIZE - inset, 
                self.y + cfg.BUTTON_SIZE - inset]
        draw_context.rounded_rectangle(bbox, radius=cfg.CORNER_RADIUS, fill=button_bg)
        
        # Draw button content
        if is_zoom_level_label:
            # Special handling for zoom level label - render text instead of symbol
            # Store inset so text drawing methods can use it
            self._draw_zoom_level_text(draw_context, zoom_level, inset)
        elif self.name == 'zoom_in':
            self._draw_plus_sign(draw_context, inset)
        elif self.name == 'zoom_out':
            self._draw_minus_sign(draw_context, inset)
        elif self.name == 'mark_center':
            self._draw_circle_with_plus(draw_context, inset)
        elif self.name == 'recenter':
            self._draw_circle_with_dot(draw_context, inset)
    
    def _draw_plus_sign(self, draw_context, inset=0):
        """Draw + symbol."""
        center = MapButtonConfig.BUTTON_SIZE // 2
        center_x = self.x + inset + (MapButtonConfig.BUTTON_SIZE - 2*inset) // 2
        center_y = self.y + inset + (MapButtonConfig.BUTTON_SIZE - 2*inset) // 2
        
        # Horizontal line
        draw_context.line(
            [(center_x - 6, center_y), (center_x + 6, center_y)],
            fill=MapButtonConfig.BUTTON_TEXT,
            width=2
        )
        # Vertical line
        draw_context.line(
            [(center_x, center_y - 6), (center_x, center_y + 6)],
            fill=MapButtonConfig.BUTTON_TEXT,
            width=2
        )
    
    def _draw_minus_sign(self, draw_context, inset=0):
        """Draw - symbol."""
        center = MapButtonConfig.BUTTON_SIZE // 2
        center_x = self.x + inset + (MapButtonConfig.BUTTON_SIZE - 2*inset) // 2
        center_y = self.y + inset + (MapButtonConfig.BUTTON_SIZE - 2*inset) // 2
        
        # Horizontal line only
        draw_context.line(
            [(center_x - 6, center_y), (center_x + 6, center_y)],
            fill=MapButtonConfig.BUTTON_TEXT,
            width=2
        )
    
    def _draw_circle_with_plus(self, draw_context, inset=0):
        """Draw ⊕ (circle with plus sign)."""
        center_x = self.x + inset + (MapButtonConfig.BUTTON_SIZE - 2*inset) // 2
        center_y = self.y + inset + (MapButtonConfig.BUTTON_SIZE - 2*inset) // 2
        
        # Outer circle
        draw_context.ellipse(
            (center_x - 12, center_y - 12, center_x + 12, center_y + 12),
            outline=MapButtonConfig.BUTTON_TEXT,
            width=2
        )
        # Plus sign: horizontal line
        draw_context.line(
            [(center_x - 8, center_y), (center_x + 8, center_y)],
            fill=MapButtonConfig.BUTTON_TEXT,
            width=2
        )
        # Plus sign: vertical line
        draw_context.line(
            [(center_x, center_y - 8), (center_x, center_y + 8)],
            fill=MapButtonConfig.BUTTON_TEXT,
            width=2
        )
    
    def _draw_circle_with_dot(self, draw_context, inset=0):
        """Draw ⊙ (circle with dot in center)."""
        center_x = self.x + inset + (MapButtonConfig.BUTTON_SIZE - 2*inset) // 2
        center_y = self.y + inset + (MapButtonConfig.BUTTON_SIZE - 2*inset) // 2
        
        # Outer circle
        draw_context.ellipse(
            (center_x - 12, center_y - 12, center_x + 12, center_y + 12),
            outline=MapButtonConfig.BUTTON_TEXT,
            width=2
        )
        # Middle circle
        draw_context.ellipse(
            (center_x - 7, center_y - 7, center_x + 7, center_y + 7),
            outline=MapButtonConfig.BUTTON_TEXT,
            width=1
        )
        # Center dot
        draw_context.ellipse(
            (center_x - 3, center_y - 3, center_x + 3, center_y + 3),
            fill=MapButtonConfig.BUTTON_TEXT
        )
    
    def _draw_zoom_level_text(self, draw_context, zoom_level: int, inset=0):
        """Draw zoom level as text (Z:15)."""
        zoom_text = f"Z:{zoom_level}"
        
        # Load font
        try:
            font = ImageFont.truetype(MapButtonConfig.FONT_PATH, MapButtonConfig.FONT_SIZE)
        except (IOError, OSError):
            font = ImageFont.load_default()
        
        # Center text in button
        text_bbox = draw_context.textbbox((0, 0), zoom_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        text_x = self.x + inset + (MapButtonConfig.BUTTON_SIZE - 2*inset - text_width) // 2
        text_y = self.y + inset + (MapButtonConfig.BUTTON_SIZE - 2*inset - text_height) // 2 - 3
        
        draw_context.text((text_x, text_y), zoom_text, font=font, fill=MapButtonConfig.BUTTON_TEXT)


class MapButtonManager:
    """Manages a set of map buttons - positioning, rendering, and state."""
    
    # Button order (same for Track Editor and Map Editor)
    BUTTON_ORDER = ['zoom_in', 'zoom_out', 'zoom_level_label', 'mark_center', 'recenter']
    
    def __init__(self):
        """Initialize button manager with standard button set."""
        self.buttons = {}
        self._setup_buttons()
    
    def _setup_buttons(self):
        """Create button definitions in standard order."""
        self.buttons['zoom_in'] = MapButton('zoom_in', '+', 'Zoom in')
        self.buttons['zoom_out'] = MapButton('zoom_out', '-', 'Zoom out')
        self.buttons['zoom_level_label'] = MapButton('zoom_level_label', 'Z:15', 'Current zoom level')
        self.buttons['mark_center'] = MapButton('mark_center', '⊕', 'Mark as default center')
        self.buttons['recenter'] = MapButton('recenter', '⊙', 'Jump to marked center')
    
    def create_all_buttons(self, parent, callbacks: dict):
        """
        Create all real QPushButton widgets.
        
        Args:
            parent: Parent widget
            callbacks: Dict mapping button names to callback functions
                      e.g., {'zoom_in': self.zoom_in, 'mark_center': self.mark_center}
        """
        for button_name in self.BUTTON_ORDER:
            if button_name in self.buttons:
                callback = callbacks.get(button_name, lambda: None)
                self.buttons[button_name].create_qbutton(parent, callback)
    
    def position_all_buttons(self):
        """Position all buttons vertically starting from top-left."""
        cfg = MapButtonConfig
        x_pos = cfg.PADDING_LEFT
        y_pos = cfg.PADDING_TOP
        
        for button_name in self.BUTTON_ORDER:
            if button_name in self.buttons:
                self.buttons[button_name].set_position(x_pos, y_pos)
                y_pos += cfg.BUTTON_SIZE + cfg.BUTTON_SPACING
                logger.debug(f"Positioned {button_name} at ({x_pos}, {y_pos - cfg.BUTTON_SIZE - cfg.BUTTON_SPACING})")
    
    def draw_all_buttons(self, draw_context, zoom_level: int = 10, hovered_button: str = None, pressed_button: str = None):
        """
        Draw all buttons on PIL image.
        
        Args:
            draw_context: PIL ImageDraw context
            zoom_level: Current zoom level (for zoom_level_label)
            hovered_button: Name of button currently hovered (or None)
            pressed_button: Name of button currently pressed (or None)
        """
        for button_name in self.BUTTON_ORDER:
            if button_name in self.buttons:
                button = self.buttons[button_name]
                button.hovered = (button_name == hovered_button)
                button.pressed = (button_name == pressed_button)
                is_zoom_label = (button_name == 'zoom_level_label')
                button.draw(draw_context, is_zoom_level_label=is_zoom_label, zoom_level=zoom_level)
    
    def get_button(self, name: str) -> MapButton:
        """Get button by name."""
        return self.buttons.get(name)
    
    def get_qbutton(self, name: str) -> QPushButton:
        """Get real QPushButton widget by name."""
        button = self.buttons.get(name)
        return button.qbutton if button else None
