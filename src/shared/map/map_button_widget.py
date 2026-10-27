"""
Map button widget - self-contained button with hover/press state management.

Each button is a real QWidget that:
- Handles its own mouse events (hover, press, release)
- Manages its own state (hovered, pressed)
- Draws itself on the parent's canvas
- Triggers callbacks when clicked
"""

import logging
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, pyqtSignal
from PIL import ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class MapButtonConfig:
    """Configuration for all map buttons - shared between Track Editor and Map Editor."""
    
    BUTTON_SIZE = 40
    BUTTON_SPACING = 5
    PADDING_LEFT = 10
    PADDING_TOP = 10
    
    # Visual styling
    BUTTON_BG_NORMAL = (52, 144, 220, 200)      # Semi-transparent blue
    BUTTON_BG_HOVERED = (52, 144, 220, 255)     # Fully opaque blue
    BUTTON_BG_PRESSED = (30, 100, 160, 255)     # Dark blue
    BUTTON_TEXT = (255, 255, 255, 255)
    CORNER_RADIUS = 8
    
    # Font for zoom level display
    FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    FONT_SIZE = 13


class MapButtonWidget(QWidget):
    """A single map button widget with self-contained state and mouse event handling."""
    
    # Signal emitted when button is clicked
    clicked = pyqtSignal(str)  # Emits button name
    
    def __init__(self, name: str, symbol: str, tooltip: str = "", parent=None):
        """
        Initialize button widget.
        
        Args:
            name: Internal name (e.g., 'zoom_in', 'mark_center')
            symbol: Display symbol (e.g., '+', '⊕', 'Z:15')
            tooltip: Help text
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.name = name
        self.symbol = symbol
        self.tooltip = tooltip
        
        # State management
        self.hovered = False
        self.pressed = False
        
        # Fixed size
        self.setFixedSize(MapButtonConfig.BUTTON_SIZE, MapButtonConfig.BUTTON_SIZE)
        
        # Mouse tracking
        self.setMouseTracking(True)
        
        logger.debug(f"Created button: {name}")
    
    def enterEvent(self, event):
        """Mouse enters button - set hover state."""
        self.hovered = True
        logger.debug(f"Button hovered: {self.name}")
        self.parent().render_map() if self.parent() else None
    
    def leaveEvent(self, event):
        """Mouse leaves button - clear hover state."""
        self.hovered = False
        logger.debug(f"Button unhovered: {self.name}")
        self.parent().render_map() if self.parent() else None
    
    def mousePressEvent(self, event):
        """Mouse pressed on button - set pressed state."""
        if event.button() == Qt.LeftButton:
            self.pressed = True
            logger.debug(f"Button pressed: {self.name}")
            self.parent().render_map() if self.parent() else None
    
    def mouseReleaseEvent(self, event):
        """Mouse released - clear pressed state and emit signal."""
        if event.button() == Qt.LeftButton:
            was_pressed = self.pressed
            self.pressed = False
            logger.debug(f"Button released: {self.name}")
            self.parent().render_map() if self.parent() else None
            
            # Emit clicked signal if button was pressed before release
            if was_pressed:
                self.clicked.emit(self.name)
    
    def draw(self, draw_context, x: int, y: int, is_zoom_level_label: bool = False, zoom_level: int = 10):
        """
        Draw button on PIL image.
        
        Args:
            draw_context: PIL ImageDraw context
            x: Button x position
            y: Button y position
            is_zoom_level_label: If True, render as text label
            zoom_level: Current zoom level (for zoom_level_label)
        """
        cfg = MapButtonConfig
        
        # Determine appearance based on state
        if self.pressed:
            button_bg = cfg.BUTTON_BG_PRESSED
            inset = 3  # Smaller when pressed
        elif self.hovered:
            button_bg = cfg.BUTTON_BG_HOVERED
            inset = 0
        else:
            button_bg = cfg.BUTTON_BG_NORMAL
            inset = 0
        
        # Draw button background
        bbox = [x + inset, y + inset, 
                x + cfg.BUTTON_SIZE - inset, 
                y + cfg.BUTTON_SIZE - inset]
        draw_context.rounded_rectangle(bbox, radius=cfg.CORNER_RADIUS, fill=button_bg)
        
        # Draw button icon/text
        if is_zoom_level_label:
            self._draw_zoom_level_text(draw_context, x, y, zoom_level, inset)
        elif self.name == 'zoom_in':
            self._draw_plus_sign(draw_context, x, y, inset)
        elif self.name == 'zoom_out':
            self._draw_minus_sign(draw_context, x, y, inset)
        elif self.name == 'mark_center':
            self._draw_circle_with_plus(draw_context, x, y, inset)
        elif self.name == 'recenter':
            self._draw_circle_with_dot(draw_context, x, y, inset)
    
    def _draw_plus_sign(self, draw_context, x: int, y: int, inset: int = 0):
        """Draw + symbol."""
        cfg = MapButtonConfig
        center_x = x + inset + (cfg.BUTTON_SIZE - 2*inset) // 2
        center_y = y + inset + (cfg.BUTTON_SIZE - 2*inset) // 2
        
        draw_context.line([(center_x - 6, center_y), (center_x + 6, center_y)],
                         fill=cfg.BUTTON_TEXT, width=2)
        draw_context.line([(center_x, center_y - 6), (center_x, center_y + 6)],
                         fill=cfg.BUTTON_TEXT, width=2)
    
    def _draw_minus_sign(self, draw_context, x: int, y: int, inset: int = 0):
        """Draw - symbol."""
        cfg = MapButtonConfig
        center_x = x + inset + (cfg.BUTTON_SIZE - 2*inset) // 2
        center_y = y + inset + (cfg.BUTTON_SIZE - 2*inset) // 2
        
        draw_context.line([(center_x - 6, center_y), (center_x + 6, center_y)],
                         fill=cfg.BUTTON_TEXT, width=2)
    
    def _draw_circle_with_plus(self, draw_context, x: int, y: int, inset: int = 0):
        """Draw ⊕ (circle with plus)."""
        cfg = MapButtonConfig
        center_x = x + inset + (cfg.BUTTON_SIZE - 2*inset) // 2
        center_y = y + inset + (cfg.BUTTON_SIZE - 2*inset) // 2
        
        draw_context.ellipse((center_x - 12, center_y - 12, center_x + 12, center_y + 12),
                            outline=cfg.BUTTON_TEXT, width=2)
        draw_context.line([(center_x - 8, center_y), (center_x + 8, center_y)],
                         fill=cfg.BUTTON_TEXT, width=2)
        draw_context.line([(center_x, center_y - 8), (center_x, center_y + 8)],
                         fill=cfg.BUTTON_TEXT, width=2)
    
    def _draw_circle_with_dot(self, draw_context, x: int, y: int, inset: int = 0):
        """Draw ⊙ (circle with dot)."""
        cfg = MapButtonConfig
        center_x = x + inset + (cfg.BUTTON_SIZE - 2*inset) // 2
        center_y = y + inset + (cfg.BUTTON_SIZE - 2*inset) // 2
        
        draw_context.ellipse((center_x - 12, center_y - 12, center_x + 12, center_y + 12),
                            outline=cfg.BUTTON_TEXT, width=2)
        draw_context.ellipse((center_x - 7, center_y - 7, center_x + 7, center_y + 7),
                            outline=cfg.BUTTON_TEXT, width=1)
        draw_context.ellipse((center_x - 3, center_y - 3, center_x + 3, center_y + 3),
                            fill=cfg.BUTTON_TEXT)
    
    def _draw_zoom_level_text(self, draw_context, x: int, y: int, zoom_level: int, inset: int = 0):
        """Draw zoom level text (Z:15)."""
        cfg = MapButtonConfig
        zoom_text = f"Z:{zoom_level}"
        
        try:
            font = ImageFont.truetype(cfg.FONT_PATH, cfg.FONT_SIZE)
        except (IOError, OSError):
            font = ImageFont.load_default()
        
        text_bbox = draw_context.textbbox((0, 0), zoom_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        text_x = x + inset + (cfg.BUTTON_SIZE - 2*inset - text_width) // 2
        text_y = y + inset + (cfg.BUTTON_SIZE - 2*inset - text_height) // 2 - 3
        
        draw_context.text((text_x, text_y), zoom_text, font=font, fill=cfg.BUTTON_TEXT)
