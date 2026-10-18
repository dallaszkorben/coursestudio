"""
Reusable crosshair drawing utility for map widgets.

This module provides a single, shared function to draw crosshairs consistently
across different map implementations (MapWidget, MapViewer, etc.).

Avoids code duplication by centralizing crosshair rendering logic.
"""

from PIL import Image, ImageDraw


def draw_crosshair(pil_image, center_x, center_y, show_crosshair, 
                   crosshair_color, crosshair_outline_color, 
                   crosshair_outline_width, crosshair_size):
    """
    Draw a crosshair with center circle on a PIL image.
    
    This is a shared, reusable function used by multiple map widgets to ensure
    consistent crosshair appearance across the application.
    
    Crosshair components:
    1. Horizontal line (crosshair_color with outline)
    2. Vertical line (crosshair_color with outline)
    3. Small center circle (crosshair_color with outline)
    
    Args:
        pil_image (PIL.Image): Image to draw on (RGBA format)
        center_x (int): X coordinate of crosshair center
        center_y (int): Y coordinate of crosshair center
        show_crosshair (bool): Whether to draw crosshair
        crosshair_color (tuple): RGB color of crosshair lines (e.g., (255, 0, 0))
        crosshair_outline_color (tuple): RGB color of outline (e.g., (255, 255, 255))
        crosshair_outline_width (int): Outline thickness in pixels
        crosshair_size (int): Length of crosshair arms from center in pixels
    
    Returns:
        PIL.Image: Image with crosshair drawn
    
    Example:
        >>> from PIL import Image, ImageDraw
        >>> from src.shared.map.crosshair_drawer import draw_crosshair
        >>> 
        >>> # Create a white image
        >>> img = Image.new('RGBA', (400, 400), (200, 200, 200, 255))
        >>> 
        >>> # Draw red crosshair with white outline at center
        >>> result = draw_crosshair(
        ...     img, 200, 200, True,
        ...     crosshair_color=(255, 0, 0),
        ...     crosshair_outline_color=(255, 255, 255),
        ...     crosshair_outline_width=1,
        ...     crosshair_size=20
        ... )
    """
    if not show_crosshair:
        return pil_image
    
    # Ensure image is RGBA for drawing
    if pil_image.mode != 'RGBA':
        pil_image = pil_image.convert('RGBA')
    
    overlay = Image.new('RGBA', pil_image.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    
    # ================================================================
    # Draw Horizontal Line
    # ================================================================
    
    # Outline (thicker, outer color)
    overlay_draw.line(
        [(center_x - crosshair_size, center_y), (center_x + crosshair_size, center_y)],
        fill=crosshair_outline_color,
        width=2 + 2 * crosshair_outline_width
    )
    # Body (thinner, inner color)
    overlay_draw.line(
        [(center_x - crosshair_size, center_y), (center_x + crosshair_size, center_y)],
        fill=crosshair_color,
        width=2
    )
    
    # ================================================================
    # Draw Vertical Line
    # ================================================================
    
    # Outline (thicker, outer color)
    overlay_draw.line(
        [(center_x, center_y - crosshair_size), (center_x, center_y + crosshair_size)],
        fill=crosshair_outline_color,
        width=2 + 2 * crosshair_outline_width
    )
    # Body (thinner, inner color)
    overlay_draw.line(
        [(center_x, center_y - crosshair_size), (center_x, center_y + crosshair_size)],
        fill=crosshair_color,
        width=2
    )
    
    # ================================================================
    # Draw Center Circle
    # ================================================================
    
    circle_radius = 4
    
    # Outline circle (outer)
    overlay_draw.ellipse(
        (center_x - circle_radius - crosshair_outline_width,
         center_y - circle_radius - crosshair_outline_width,
         center_x + circle_radius + crosshair_outline_width,
         center_y + circle_radius + crosshair_outline_width),
        outline=crosshair_outline_color,
        width=crosshair_outline_width
    )
    # Inner circle (main color)
    overlay_draw.ellipse(
        (center_x - circle_radius, center_y - circle_radius,
         center_x + circle_radius, center_y + circle_radius),
        outline=crosshair_color,
        width=1
    )
    
    # ================================================================
    # Blend overlay onto image
    # ================================================================
    
    pil_image = Image.alpha_composite(pil_image, overlay)
    return pil_image
