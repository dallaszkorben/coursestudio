"""
Unified crosshair configuration management.

Provides a centralized way to load and apply crosshair settings from config
to both MapWidget (TrackEditor) and MapViewer (MapEditor).

This eliminates code duplication and ensures consistent behavior across both map implementations.
"""

import logging

logger = logging.getLogger(__name__)


def load_crosshair_settings(config, widget):
    """
    Load crosshair settings from config and apply to a map widget.
    
    Works with both MapWidget (TrackEditor) and MapViewer (MapEditor).
    
    Args:
        config: AppConfig instance
        widget: Map widget with crosshair properties (MapWidget or MapViewer)
    
    Sets on widget:
        - crosshair_enabled_in_config: User preference for enabled/disabled
        - show_crosshair: Whether to actually show (depends on mbtiles loaded)
        - crosshair_color: RGB tuple for body color
        - crosshair_size: Size in pixels (5-30)
        - crosshair_outline_color: RGB tuple for outline color
        - crosshair_outline_width: Width in pixels
    """
    if not config or not widget:
        logger.warning("load_crosshair_settings: config or widget is None")
        return
    
    # Load user preference
    enabled_in_config = config.get_bool('appearance.map_display.crosshair.enabled', True)
    widget.crosshair_enabled_in_config = enabled_in_config
    
    # Only show if both enabled in config AND mbtiles is loaded
    if hasattr(widget, 'mbtiles_provider') and widget.mbtiles_provider:
        widget.show_crosshair = enabled_in_config
    else:
        widget.show_crosshair = False
    
    # Load visual settings
    body_color_hex = config.get_str('appearance.map_display.crosshair.body.color', 'FF0000')
    widget.crosshair_color = widget._hex_to_rgb(body_color_hex)
    
    widget.crosshair_size = config.get_int('appearance.map_display.crosshair.body.size', 4)
    
    outline_color_hex = config.get_str('appearance.map_display.crosshair.outline.color', 'FFFFFF')
    widget.crosshair_outline_color = widget._hex_to_rgb(outline_color_hex)
    
    widget.crosshair_outline_width = config.get_int('appearance.map_display.crosshair.outline.width', 1)
    
    logger.debug(f"Crosshair settings loaded: enabled_in_config={enabled_in_config}, "
                f"show_crosshair={widget.show_crosshair}, size={widget.crosshair_size}, "
                f"outline_width={widget.crosshair_outline_width}, "
                f"color={body_color_hex}, outline_color={outline_color_hex}")
