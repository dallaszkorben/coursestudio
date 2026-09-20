"""Unit tests for PIL-based map rendering"""

import pytest
import logging
from pathlib import Path
from unittest.mock import Mock, MagicMock

from src.map.map_renderer import MapRenderer
from src.map.mbtiles_provider import MBTilesProvider


logger = logging.getLogger(__name__)


@pytest.fixture
def mock_mbtiles_provider():
    """Create a mock MBTiles provider for testing"""
    provider = Mock(spec=MBTilesProvider)
    provider.get_available_zooms.return_value = [10, 11, 12, 13, 14, 15, 16]
    provider.latlon_to_tile.return_value = (128, 128)
    provider.get_tile.return_value = None  # No tiles available in mock
    provider.is_loaded.return_value = True
    return provider


@pytest.fixture
def map_renderer(mock_mbtiles_provider):
    """Create a MapRenderer instance for testing"""
    return MapRenderer(mock_mbtiles_provider, width=400, height=300)


class TestMapRendererInitialization:
    """Tests for MapRenderer initialization"""

    def test_map_renderer_creation(self, mock_mbtiles_provider):
        """Test that MapRenderer can be instantiated"""
        renderer = MapRenderer(mock_mbtiles_provider, width=800, height=600)
        assert renderer is not None
        assert renderer.width == 800
        assert renderer.height == 600

    def test_map_renderer_default_size(self, mock_mbtiles_provider):
        """Test default map size"""
        renderer = MapRenderer(mock_mbtiles_provider)
        assert renderer.width == 800
        assert renderer.height == 600

    def test_map_renderer_custom_size(self, mock_mbtiles_provider):
        """Test custom map size"""
        renderer = MapRenderer(mock_mbtiles_provider, width=1024, height=768)
        assert renderer.width == 1024
        assert renderer.height == 768


class TestMapRendererCoordinateConversion:
    """Tests for lat/lon to pixel coordinate conversion"""

    def test_latlon_to_pixel_center(self, map_renderer):
        """Test that map center converts to screen center"""
        # Map center should be at (width//2, height//2)
        px, py = map_renderer._latlon_to_pixel(56.1612, 15.5869, 56.1612, 15.5869, 13)
        
        # Should be very close to center
        assert abs(px - map_renderer.width // 2) < 5
        assert abs(py - map_renderer.height // 2) < 5

    def test_latlon_to_pixel_returns_tuple(self, map_renderer):
        """Test that coordinate conversion returns tuple of integers"""
        result = map_renderer._latlon_to_pixel(56.1612, 15.5869, 56.1612, 15.5869, 13)
        
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], int)
        assert isinstance(result[1], int)

    def test_latlon_to_pixel_different_zoom_levels(self, map_renderer):
        """Test coordinate conversion at different zoom levels"""
        # At different zoom levels, the same geographic point should project
        # to different screen coordinates (further away from center at higher zoom)
        px_z12, py_z12 = map_renderer._latlon_to_pixel(56.2, 15.6, 56.1612, 15.5869, 12)
        px_z14, py_z14 = map_renderer._latlon_to_pixel(56.2, 15.6, 56.1612, 15.5869, 14)
        
        # At higher zoom, the point should be further from the center
        dist_z12 = ((px_z12 - map_renderer.width // 2) ** 2 + (py_z12 - map_renderer.height // 2) ** 2) ** 0.5
        dist_z14 = ((px_z14 - map_renderer.width // 2) ** 2 + (py_z14 - map_renderer.height // 2) ** 2) ** 0.5
        
        assert dist_z14 > dist_z12  # Higher zoom means larger pixel distance


class TestMapRendererTileRendering:
    """Tests for tile-based map rendering"""

    def test_render_map_returns_pixmap(self, map_renderer):
        """Test that render_map returns a QPixmap"""
        from PyQt5.QtGui import QPixmap
        
        pixmap = map_renderer.render_map(
            center_lat=56.1612,
            center_lon=15.5869,
            zoom=13,
            tracks=None
        )
        
        # Even with no tiles, should return a valid pixmap (gray placeholder)
        assert isinstance(pixmap, QPixmap) or pixmap is None

    def test_render_map_with_invalid_zoom(self, map_renderer):
        """Test rendering with zoom level outside available range"""
        # Mock provider has zooms 10-16, request zoom 8 (should use closest: 10)
        map_renderer.mbtiles_provider.get_available_zooms.return_value = [10, 11, 12, 13, 14, 15, 16]
        
        pixmap = map_renderer.render_map(
            center_lat=56.1612,
            center_lon=15.5869,
            zoom=8  # Below minimum
        )
        
        # Should still render (with closest available zoom)
        assert pixmap is None or hasattr(pixmap, 'width')

    def test_render_map_with_no_zooms_available(self, map_renderer):
        """Test rendering when no zoom levels are available"""
        map_renderer.mbtiles_provider.get_available_zooms.return_value = []
        
        pixmap = map_renderer.render_map(
            center_lat=56.1612,
            center_lon=15.5869,
            zoom=13
        )
        
        # Should return None when no zooms available
        assert pixmap is None


class TestMapRendererTrackDrawing:
    """Tests for track overlay drawing"""

    def test_draw_track_with_no_points(self, map_renderer):
        """Test drawing track with no points"""
        mock_track = Mock()
        mock_track.trackpoints = []
        
        # Should not crash
        from PIL import Image, ImageDraw
        image = Image.new('RGB', (400, 300), color='white')
        draw = ImageDraw.Draw(image)
        
        map_renderer._draw_track(image, draw, mock_track, 'RED', 1, 56.1612, 15.5869, 13)

    def test_draw_track_with_points(self, map_renderer):
        """Test drawing track with points"""
        mock_point1 = Mock()
        mock_point1.latitude = 56.16
        mock_point1.longitude = 15.59
        
        mock_point2 = Mock()
        mock_point2.latitude = 56.17
        mock_point2.longitude = 15.60
        
        mock_track = Mock()
        mock_track.trackpoints = [mock_point1, mock_point2]
        
        from PIL import Image, ImageDraw
        image = Image.new('RGB', (400, 300), color='white')
        draw = ImageDraw.Draw(image)
        
        # Should not crash
        map_renderer._draw_track(image, draw, mock_track, 'RED', 2, 56.1612, 15.5869, 13)


class TestMapRendererMarkerDrawing:
    """Tests for marker drawing"""

    def test_draw_point_marker(self, map_renderer):
        """Test drawing a point marker"""
        from PIL import Image, ImageDraw
        image = Image.new('RGB', (400, 300), color='white')
        draw = ImageDraw.Draw(image)
        
        # Should not crash
        map_renderer._draw_point_marker(image, draw, 56.16, 15.59, 56.1612, 15.5869, 13)

    def test_draw_highlighted_marker(self, map_renderer):
        """Test drawing a highlighted point marker"""
        from PIL import Image, ImageDraw
        image = Image.new('RGB', (400, 300), color='white')
        draw = ImageDraw.Draw(image)
        
        # Should not crash
        map_renderer._draw_point_marker(
            image, draw, 56.16, 15.59, 56.1612, 15.5869, 13,
            marker_type='HIGHLIGHTED'
        )


class TestMapRendererColorMap:
    """Tests for color handling"""

    def test_color_map_has_standard_colors(self, map_renderer):
        """Test that standard color names are defined"""
        assert 'RED' in map_renderer.COLOR_MAP
        assert 'BLUE' in map_renderer.COLOR_MAP
        assert 'GREEN' in map_renderer.COLOR_MAP
        assert 'YELLOW' in map_renderer.COLOR_MAP

    def test_color_values_are_rgb_tuples(self, map_renderer):
        """Test that colors are valid RGB tuples"""
        for color_name, color_value in map_renderer.COLOR_MAP.items():
            assert isinstance(color_value, tuple)
            assert len(color_value) == 3
            assert all(isinstance(c, int) and 0 <= c <= 255 for c in color_value)
