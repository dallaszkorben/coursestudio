"""
Map button manager - manages a set of map button widgets.

Handles:
- Creating buttons
- Positioning buttons
- Drawing buttons
- Button signal routing
"""

import logging
from src.map.map_button_widget import MapButtonWidget, MapButtonConfig

logger = logging.getLogger(__name__)


class MapButtonManager:
    """Manages all map buttons for a map widget."""
    
    # Button order (same for Track Editor and Map Editor)
    BUTTON_ORDER = ['zoom_in', 'zoom_out', 'zoom_level_label', 'mark_center', 'recenter']
    
    def __init__(self, parent=None):
        """
        Initialize button manager.
        
        Args:
            parent: Parent widget that owns the buttons
        """
        self.parent = parent
        self.buttons = {}
        self._setup_buttons()
    
    def _setup_buttons(self):
        """Create button widgets in standard order."""
        buttons_config = [
            ('zoom_in', '+', 'Zoom in'),
            ('zoom_out', '-', 'Zoom out'),
            ('zoom_level_label', 'Z:15', 'Current zoom level'),
            ('mark_center', '⊕', 'Mark as default center'),
            ('recenter', '⊙', 'Jump to marked center'),
        ]
        
        for name, symbol, tooltip in buttons_config:
            button = MapButtonWidget(name, symbol, tooltip, parent=self.parent)
            self.buttons[name] = button
            logger.debug(f"Created button widget: {name}")
    
    def connect_callbacks(self, callbacks: dict):
        """
        Connect button clicked signals to callbacks.
        
        Args:
            callbacks: Dict mapping button names to callback functions
        """
        for button_name, button in self.buttons.items():
            if button_name in callbacks:
                button.clicked.connect(lambda bn=button_name: callbacks[bn]())
    
    def position_all_buttons(self):
        """Position all buttons vertically starting from top-left."""
        cfg = MapButtonConfig
        x_pos = cfg.PADDING_LEFT
        y_pos = cfg.PADDING_TOP
        
        for button_name in self.BUTTON_ORDER:
            if button_name in self.buttons:
                button = self.buttons[button_name]
                button.move(x_pos, y_pos)
                logger.debug(f"Positioned {button_name} at ({x_pos}, {y_pos})")
                y_pos += cfg.BUTTON_SIZE + cfg.BUTTON_SPACING
    
    def draw_all_buttons(self, draw_context, zoom_level: int = 10):
        """
        Draw all buttons on PIL image.
        
        Args:
            draw_context: PIL ImageDraw context
            zoom_level: Current zoom level (for zoom_level_label)
        """
        cfg = MapButtonConfig
        x_pos = cfg.PADDING_LEFT
        y_pos = cfg.PADDING_TOP
        
        for button_name in self.BUTTON_ORDER:
            if button_name in self.buttons:
                button = self.buttons[button_name]
                is_zoom_label = (button_name == 'zoom_level_label')
                button.draw(draw_context, x_pos, y_pos, is_zoom_level_label=is_zoom_label, zoom_level=zoom_level)
                y_pos += cfg.BUTTON_SIZE + cfg.BUTTON_SPACING
    
    def get_button(self, name: str) -> MapButtonWidget:
        """Get button by name."""
        return self.buttons.get(name)
