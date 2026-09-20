"""
Unit tests for MBTiles provider module.

Tests cover:
- MBTilesProvider initialization and validation
- Loading default and fallback mbtiles files
- Metadata extraction and caching
- Tile data retrieval
- Zoom level validation
- Coordinate to tile conversion
- Error handling and edge cases

Test Files:
- mbtiles/Sweden-Raster-Z10-Z16.mbtiles (primary test file)
- mbtiles/OSM-OpenCPN2-Baltic.mbtiles (fallback test file)
"""

import pytest
import sqlite3
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from dataclasses import astuple

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.map.mbtiles_provider import MBTilesProvider, TileMetadata
from config.app_config import AppConfig


class TestMBTilesProviderInitialization:
    """Test MBTilesProvider initialization and basic setup."""
    
    def test_init_with_valid_config_and_logger(self):
        """Should initialize with valid config and logger."""
        config = Mock()
        logger = Mock()
        
        provider = MBTilesProvider(config, logger)
        
        assert provider.config == config
        assert provider.logger == logger
        assert provider._db_connection is None
        assert provider._metadata is None
        assert provider._loaded_path is None
    
    def test_init_with_none_config_raises_error(self):
        """Should raise ValueError if config is None."""
        logger = Mock()
        
        with pytest.raises(ValueError, match="config cannot be None"):
            MBTilesProvider(None, logger)
    
    def test_init_with_none_logger_raises_error(self):
        """Should raise ValueError if logger is None."""
        config = Mock()
        
        with pytest.raises(ValueError, match="logger cannot be None"):
            MBTilesProvider(config, None)
    
    def test_is_not_loaded_initially(self):
        """Should report as not loaded initially."""
        config = Mock()
        logger = Mock()
        
        provider = MBTilesProvider(config, logger)
        
        assert provider.is_loaded() is False
        assert provider.get_metadata() is None
        assert provider.get_loaded_path() is None


class TestMBTilesProviderMBTilesPathResolution:
    """Test resolution of mbtiles file paths."""
    
    def test_get_mbtiles_path_with_existing_file(self, tmp_path):
        """Should return path if mbtiles file exists."""
        # Create temporary mbtiles file
        mbtiles_dir = tmp_path / "mbtiles"
        mbtiles_dir.mkdir()
        test_file = mbtiles_dir / "test.mbtiles"
        test_file.touch()
        
        config = Mock()
        config.get = Mock(return_value=str(tmp_path))
        logger = Mock()
        
        provider = MBTilesProvider(config, logger)
        
        result = provider._get_mbtiles_path("test.mbtiles")
        
        assert result == test_file
    
    def test_get_mbtiles_path_with_missing_file(self, tmp_path):
        """Should return None if mbtiles file doesn't exist."""
        config = Mock()
        config.get = Mock(return_value=str(tmp_path))
        logger = Mock()
        
        provider = MBTilesProvider(config, logger)
        
        result = provider._get_mbtiles_path("nonexistent.mbtiles")
        
        assert result is None


class TestTileMetadata:
    """Test TileMetadata dataclass."""
    
    def test_tile_metadata_creation(self):
        """Should create TileMetadata with all fields."""
        metadata = TileMetadata(
            name="Test Tiles",
            version="1.0",
            format="png",
            bounds=(10.0, 50.0, 20.0, 60.0),
            center=(15.0, 55.0, 12),
            min_zoom=10,
            max_zoom=16,
            attribution="Test Attribution",
            description="Test Description",
            tile_format="png"
        )
        
        assert metadata.name == "Test Tiles"
        assert metadata.version == "1.0"
        assert metadata.format == "png"
        assert metadata.bounds == (10.0, 50.0, 20.0, 60.0)
        assert metadata.center == (15.0, 55.0, 12)
        assert metadata.min_zoom == 10
        assert metadata.max_zoom == 16
        assert metadata.attribution == "Test Attribution"
        assert metadata.description == "Test Description"
        assert metadata.tile_format == "png"
    
    def test_tile_metadata_with_none_bounds(self):
        """Should handle None bounds."""
        metadata = TileMetadata(
            name="Test",
            version="1.0",
            format="png",
            bounds=None,
            center=None,
            min_zoom=0,
            max_zoom=14,
            attribution="",
            description="",
            tile_format="png"
        )
        
        assert metadata.bounds is None
        assert metadata.center is None


class TestMBTilesProviderWithRealFiles:
    """Test MBTilesProvider with actual mbtiles files."""
    
    @pytest.fixture
    def config(self):
        """Create AppConfig for testing."""
        # Use actual configuration
        return AppConfig()
    
    @pytest.fixture
    def logger(self):
        """Create logger for testing."""
        return logging.getLogger("test_mbtiles")
    
    def test_load_default_mbtiles_sweden_raster(self, config, logger):
        """Should successfully load Sweden-Raster-Z10-Z16.mbtiles."""
        provider = MBTilesProvider(config, logger)
        
        result = provider.load_default_mbtiles()
        
        assert result is True
        assert provider.is_loaded() is True
        assert provider.get_metadata() is not None
        assert provider.get_loaded_path() is not None
    
    def test_metadata_contains_expected_fields(self, config, logger):
        """Should load metadata with all expected fields."""
        provider = MBTilesProvider(config, logger)
        provider.load_default_mbtiles()
        
        metadata = provider.get_metadata()
        
        assert metadata is not None
        assert metadata.name != ""
        assert metadata.min_zoom >= 0
        assert metadata.max_zoom <= 18
        assert metadata.min_zoom <= metadata.max_zoom
        assert metadata.tile_format in ("png", "jpg", "pbf")
    
    def test_supported_zoom_range(self, config, logger):
        """Should return correct zoom range."""
        provider = MBTilesProvider(config, logger)
        provider.load_default_mbtiles()
        
        zoom_range = provider.get_supported_zoom_range()
        
        assert zoom_range is not None
        min_zoom, max_zoom = zoom_range
        assert min_zoom >= 0
        assert max_zoom <= 18
        assert min_zoom <= max_zoom
    
    def test_validate_zoom_level_within_range(self, config, logger):
        """Should validate zoom level within supported range."""
        provider = MBTilesProvider(config, logger)
        provider.load_default_mbtiles()
        
        min_zoom, max_zoom = provider.get_supported_zoom_range()
        
        # Test minimum and maximum
        assert provider.validate_zoom_level(min_zoom) is True
        assert provider.validate_zoom_level(max_zoom) is True
        
        # Test middle zoom
        mid_zoom = (min_zoom + max_zoom) // 2
        assert provider.validate_zoom_level(mid_zoom) is True
    
    def test_validate_zoom_level_outside_range(self, config, logger):
        """Should reject zoom levels outside supported range."""
        provider = MBTilesProvider(config, logger)
        provider.load_default_mbtiles()
        
        min_zoom, max_zoom = provider.get_supported_zoom_range()
        
        # Test below minimum
        assert provider.validate_zoom_level(min_zoom - 1) is False
        
        # Test above maximum
        assert provider.validate_zoom_level(max_zoom + 1) is False
    
    def test_validate_zoom_level_no_file_loaded(self, config, logger):
        """Should return False if no file loaded."""
        provider = MBTilesProvider(config, logger)
        
        assert provider.validate_zoom_level(13) is False
    
    def test_get_tile_returns_bytes(self, config, logger):
        """Should return tile data as bytes."""
        provider = MBTilesProvider(config, logger)
        provider.load_default_mbtiles()
        
        min_zoom, max_zoom = provider.get_supported_zoom_range()
        
        # Try to get a tile at various zoom levels
        for zoom in [min_zoom, min_zoom + 1]:
            # Don't try max_zoom if it's > min_zoom + 3, to avoid invalid tiles
            if zoom <= max_zoom:
                tile_data = provider.get_tile(zoom, 0, 0)
                
                if tile_data is not None:
                    assert isinstance(tile_data, bytes)
                    assert len(tile_data) > 0
    
    def test_get_tile_invalid_zoom_raises_error(self, config, logger):
        """Should raise ValueError for unsupported zoom level."""
        provider = MBTilesProvider(config, logger)
        provider.load_default_mbtiles()
        
        min_zoom, max_zoom = provider.get_supported_zoom_range()
        
        with pytest.raises(ValueError, match="Zoom level .* not supported"):
            provider.get_tile(max_zoom + 5, 0, 0)
    
    def test_get_tile_invalid_coordinates(self, config, logger):
        """Should return None for invalid tile coordinates."""
        provider = MBTilesProvider(config, logger)
        provider.load_default_mbtiles()
        
        min_zoom, _ = provider.get_supported_zoom_range()
        
        # X out of range
        result = provider.get_tile(min_zoom, -1, 0)
        assert result is None
        
        # Y out of range
        result = provider.get_tile(min_zoom, 0, -1)
        assert result is None
        
        # Both out of range
        max_tile = 2 ** min_zoom
        result = provider.get_tile(min_zoom, max_tile, max_tile)
        assert result is None
    
    def test_tile_exists_returns_boolean(self, config, logger):
        """Should return boolean for tile existence check."""
        provider = MBTilesProvider(config, logger)
        provider.load_default_mbtiles()
        
        min_zoom, _ = provider.get_supported_zoom_range()
        
        # Should not raise error for invalid zoom (should return False)
        result = provider.tile_exists(min_zoom, 0, 0)
        assert isinstance(result, bool)


class TestMBTilesProviderLoadingBehavior:
    """Test file loading and error handling."""
    
    def test_load_file_closes_previous_connection(self):
        """Should close previous connection when loading new file."""
        config = Mock()
        config.get = Mock(side_effect=lambda sect, key, default=None: {
            ("Map", "default_mbtiles"): "test1.mbtiles",
            ("Map", "fallback_mbtiles"): "",
            ("Application", "project_root"): "./"
        }.get((sect, key), default))
        
        logger = Mock()
        provider = MBTilesProvider(config, logger)
        
        # Create mock connection
        old_connection = Mock()
        provider._db_connection = old_connection
        
        # Mock the path and file operations
        with patch.object(provider, '_get_mbtiles_path', return_value=None):
            provider._load_file("test.mbtiles")
        
        # Previous connection should be closed
        old_connection.close.assert_called_once()
    
    def test_load_file_invalid_mbtiles_structure(self, tmp_path):
        """Should reject file without required mbtiles tables."""
        # Create a valid SQLite file but not a valid mbtiles
        db_file = tmp_path / "invalid.mbtiles"
        conn = sqlite3.connect(str(db_file))
        conn.execute("CREATE TABLE wrong_table (id INTEGER)")
        conn.close()
        
        config = Mock()
        config.get = Mock(return_value=str(tmp_path))
        logger = Mock()
        
        provider = MBTilesProvider(config, logger)
        
        result = provider._load_file("invalid.mbtiles")
        
        assert result is False
        assert provider.is_loaded() is False
    
    def test_load_file_database_error_handling(self, tmp_path):
        """Should handle database errors gracefully."""
        config = Mock()
        config.get = Mock(return_value=str(tmp_path))
        logger = Mock()
        
        provider = MBTilesProvider(config, logger)
        
        # Create corrupted file (not a valid SQLite database)
        bad_file = tmp_path / "mbtiles" / "corrupted.mbtiles"
        bad_file.parent.mkdir(parents=True, exist_ok=True)
        bad_file.write_bytes(b"not a valid sqlite database")
        
        result = provider._load_file("corrupted.mbtiles")
        
        assert result is False
        assert provider.is_loaded() is False


class TestMBTilesProviderCoordinateConversion:
    """Test geographic to tile coordinate conversion."""
    
    def test_lat_lon_to_tile_at_zoom_0(self):
        """Should convert any coordinates to single tile at zoom 0."""
        x, y = MBTilesProvider._lat_lon_to_tile(0.0, 0.0, 0)
        
        assert x == 0
        assert y == 0
    
    def test_lat_lon_to_tile_at_zoom_1(self):
        """Should convert to correct tiles at zoom 1."""
        # Northwest quadrant
        x, y = MBTilesProvider._lat_lon_to_tile(-90.0, 45.0, 1)
        assert 0 <= x < 2
        assert 0 <= y < 2
        
        # Southeast quadrant
        x, y = MBTilesProvider._lat_lon_to_tile(90.0, -45.0, 1)
        assert 0 <= x < 2
        assert 0 <= y < 2
    
    def test_lat_lon_to_tile_europe_sweden(self):
        """Should convert Swedish coordinates correctly."""
        # Stockholm area
        zoom = 13
        x, y = MBTilesProvider._lat_lon_to_tile(18.0, 59.0, zoom)
        
        assert 0 <= x < 2 ** zoom
        assert 0 <= y < 2 ** zoom
    
    def test_lat_lon_to_tile_normalizes_longitude(self):
        """Should normalize longitude to -180 to 180 range."""
        # 360 degrees should wrap around to 0
        x1, y1 = MBTilesProvider._lat_lon_to_tile(0.0, 0.0, 5)
        x2, y2 = MBTilesProvider._lat_lon_to_tile(360.0, 0.0, 5)
        
        assert x1 == x2
        assert y1 == y2
    
    def test_lat_lon_to_tile_clamps_latitude(self):
        """Should clamp latitude to valid Mercator range."""
        # Values beyond Mercator limits should be clamped
        zoom = 5
        
        # Extreme latitude values should not raise error
        x1, y1 = MBTilesProvider._lat_lon_to_tile(0.0, 89.9, zoom)
        x2, y2 = MBTilesProvider._lat_lon_to_tile(0.0, -89.9, zoom)
        
        assert 0 <= x1 < 2 ** zoom
        assert 0 <= y1 < 2 ** zoom
        assert 0 <= x2 < 2 ** zoom
        assert 0 <= y2 < 2 ** zoom


class TestMBTilesProviderCleanup:
    """Test resource cleanup and connection management."""
    
    def test_close_closes_connection(self):
        """Should close database connection."""
        config = Mock()
        logger = Mock()
        
        provider = MBTilesProvider(config, logger)
        mock_conn = Mock()
        provider._db_connection = mock_conn
        
        provider.close()
        
        mock_conn.close.assert_called_once()
        assert provider._db_connection is None
        assert provider._metadata is None
        assert provider._loaded_path is None
    
    def test_close_handles_connection_error(self):
        """Should handle errors when closing connection."""
        config = Mock()
        logger = Mock()
        
        provider = MBTilesProvider(config, logger)
        mock_conn = Mock()
        mock_conn.close.side_effect = sqlite3.Error("Database error")
        provider._db_connection = mock_conn
        
        # Should not raise error
        provider.close()
        
        assert provider._db_connection is None
    
    def test_close_safe_when_not_loaded(self):
        """Should be safe to call close when no file loaded."""
        config = Mock()
        logger = Mock()
        
        provider = MBTilesProvider(config, logger)
        
        # Should not raise error
        provider.close()
        
        assert provider.is_loaded() is False
    
    def test_destructor_closes_connection(self):
        """Should close connection in destructor."""
        config = Mock()
        logger = Mock()
        
        provider = MBTilesProvider(config, logger)
        provider._db_connection = Mock()
        
        # Delete provider to trigger __del__
        del provider
        
        # If we get here, no exception was raised


class TestMBTilesProviderGetTilesForBounds:
    """Test retrieving tiles for geographic bounds."""
    
    def test_get_tiles_for_bounds_no_file_loaded(self):
        """Should return empty list if no file loaded."""
        config = Mock()
        logger = Mock()
        
        provider = MBTilesProvider(config, logger)
        
        result = provider.get_tiles_for_bounds(13, 10.0, 50.0, 20.0, 60.0)
        
        assert result == []
    
    def test_get_tiles_for_bounds_invalid_zoom(self):
        """Should return empty list for invalid zoom level."""
        config = Mock()
        config.get = Mock(return_value=str(Path.cwd()))
        logger = Mock()
        
        provider = MBTilesProvider(config, logger)
        
        # Don't actually load file, just mock is_loaded
        with patch.object(provider, 'is_loaded', return_value=True):
            with patch.object(provider, 'validate_zoom_level', return_value=False):
                result = provider.get_tiles_for_bounds(25, 10.0, 50.0, 20.0, 60.0)
        
        assert result == []
    
    def test_get_tiles_for_bounds_clamps_coordinates(self):
        """Should clamp tile coordinates to valid ranges."""
        config = Mock()
        logger = Mock()
        
        provider = MBTilesProvider(config, logger)
        provider._db_connection = Mock()
        provider._metadata = TileMetadata(
            name="Test", version="1", format="png",
            bounds=None, center=None,
            min_zoom=10, max_zoom=16,
            attribution="", description="", tile_format="png"
        )
        
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = []
        provider._db_connection.cursor.return_value = mock_cursor
        
        # Call with bounds that extend beyond valid range
        result = provider.get_tiles_for_bounds(10, -200.0, -100.0, 200.0, 100.0)
        
        # Should not raise error and return empty list (or clamped results)
        assert isinstance(result, list)


class TestMBTilesProviderErrorMessages:
    """Test error logging and user feedback."""
    
    def test_no_config_default_mbtiles_logs_error(self):
        """Should log error if default_mbtiles not configured."""
        config = Mock()
        config.get = Mock(return_value=None)
        logger = Mock()
        
        provider = MBTilesProvider(config, logger)
        result = provider.load_default_mbtiles()
        
        assert result is False
        logger.error.assert_called()
    
    def test_tile_access_without_loaded_file_logs_warning(self):
        """Should log warning when accessing tiles without loaded file."""
        config = Mock()
        logger = Mock()
        
        provider = MBTilesProvider(config, logger)
        
        result = provider.get_tile(13, 0, 0)
        
        assert result is None
        logger.warning.assert_called()


# Integration tests with real mbtiles files
class TestMBTilesProviderIntegration:
    """Integration tests using actual mbtiles files."""
    
    @pytest.fixture
    def provider(self):
        """Create provider and load default mbtiles."""
        config = AppConfig()
        logger = logging.getLogger("test_integration")
        provider = MBTilesProvider(config, logger)
        
        if not provider.load_default_mbtiles():
            pytest.skip("Default mbtiles file not found")
        
        yield provider
        provider.close()
    
    def test_full_workflow_load_and_query_tiles(self, provider):
        """Should successfully load and query tiles."""
        assert provider.is_loaded()
        
        metadata = provider.get_metadata()
        assert metadata is not None
        
        # Get a tile at each supported zoom level
        min_zoom, max_zoom = provider.get_supported_zoom_range()
        
        for zoom in range(min_zoom, min(max_zoom + 1, min_zoom + 3)):
            # Try to get tile at origin
            tile = provider.get_tile(zoom, 0, 0)
            
            # Tile may or may not exist (depends on coverage), but no error
            if tile is not None:
                assert isinstance(tile, bytes)
                assert len(tile) > 0
    
    def test_full_workflow_bounds_to_tiles(self, provider):
        """Should retrieve tiles for geographic bounds."""
        # Sweden/Baltic area
        tiles = provider.get_tiles_for_bounds(
            zoom=12,
            west=10.0,
            south=54.0,
            east=24.0,
            north=60.0
        )
        
        # May return empty if no tiles in database, but no error
        assert isinstance(tiles, list)
