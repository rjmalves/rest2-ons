from datetime import datetime

import pytest

from app.internal.config import (
    Config,
    PostprocessingConfig,
    TimeWindow,
    TimeWindows,
)


class TestTimeWindow:
    """Test TimeWindow dataclass."""

    def test_parse_valid(self):
        """Test parsing valid time window string."""
        window_str = "2024-01-01T00:00:00/2024-02-01T00:00:00"
        window = TimeWindow.parse(window_str)

        assert window.start == datetime(2024, 1, 1, 0, 0, 0)
        assert window.end == datetime(2024, 2, 1, 0, 0, 0)

    def test_parse_with_time(self):
        """Test parsing time window with specific times."""
        window_str = "2024-01-01T12:30:00/2024-01-02T18:45:00"
        window = TimeWindow.parse(window_str)

        assert window.start == datetime(2024, 1, 1, 12, 30, 0)
        assert window.end == datetime(2024, 1, 2, 18, 45, 0)

    def test_direct_construction(self):
        """Test direct construction."""
        window = TimeWindow(
            start=datetime(2024, 1, 1), end=datetime(2024, 2, 1)
        )
        assert window.start.year == 2024
        assert window.end.month == 2


class TestTimeWindows:
    """Test TimeWindows dataclass."""

    def test_parse_all_windows(self):
        """Test parsing all time windows."""
        windows_dict = {
            "training": "2024-01-01T00:00:00/2024-02-01T00:00:00",
            "validation": "2024-02-01T00:00:00/2024-03-01T00:00:00",
            "test": "2024-03-01T00:00:00/2024-04-01T00:00:00",
            "inference": "2024-04-01T00:00:00/2024-05-01T00:00:00",
        }
        windows = TimeWindows.parse(windows_dict)

        assert windows.training.start == datetime(2024, 1, 1)
        assert windows.validation.start == datetime(2024, 2, 1)
        assert windows.test.start == datetime(2024, 3, 1)
        assert windows.inference.start == datetime(2024, 4, 1)


class TestPostprocessingConfig:
    """Test PostprocessingConfig dataclass."""

    def test_parse_with_all_options(self):
        """Test parsing with all options enabled."""
        config = PostprocessingConfig.parse({"errors": True, "plots": True})
        assert config.errors is True
        assert config.plots is True

    def test_parse_default(self):
        """Test parsing with missing keys uses defaults."""
        config = PostprocessingConfig.parse({})
        assert config.errors is False
        assert config.plots is False

    def test_parse_partial(self):
        """Test parsing with some options."""
        config = PostprocessingConfig.parse({"errors": True})
        assert config.errors is True
        assert config.plots is False


class TestConfig:
    """Test main Config dataclass."""

    def test_parse_complete_config(self):
        """Test parsing a complete configuration."""
        data = {
            "mode": "train",
            "input": "data/input",
            "output": "data/output",
            "artifact": "data/artifacts",
            "plant_ids": ["PLANT001", "PLANT002"],
            "forecasting_day_ahead": 1,
            "target_radiation_type": "dni",
            "time_windows": {
                "training": "2024-01-01T00:00:00/2024-02-01T00:00:00",
                "validation": "2024-02-01T00:00:00/2024-03-01T00:00:00",
                "test": "2024-03-01T00:00:00/2024-04-01T00:00:00",
                "inference": "2024-04-01T00:00:00/2024-05-01T00:00:00",
            },
            "postprocessing": {"errors": True, "plots": True},
        }

        config = Config.parse(data)

        assert config.mode == "train"
        assert config.input == "data/input"
        assert config.output == "data/output"
        assert config.artifact == "data/artifacts"
        assert config.plant_ids == ["PLANT001", "PLANT002"]
        assert config.forecasting_day_ahead == 1
        assert config.target_radiation_type == "dni"
        assert config.postprocessing.errors is True
        assert config.postprocessing.plots is True

    def test_parse_minimal_config(self):
        """Test parsing minimal configuration (defaults)."""
        data = {
            "mode": "inference",
            "input": "data/input",
            "output": "data/output",
            "artifact": "data/artifacts",
            "plant_ids": None,
            "forecasting_day_ahead": 0,
            "target_radiation_type": "ghi",
            "time_windows": {
                "training": "2024-01-01T00:00:00/2024-02-01T00:00:00",
                "validation": "2024-02-01T00:00:00/2024-03-01T00:00:00",
                "test": "2024-03-01T00:00:00/2024-04-01T00:00:00",
                "inference": "2024-04-01T00:00:00/2024-05-01T00:00:00",
            },
        }

        config = Config.parse(data)
        assert config.postprocessing.plots is False
        assert config.postprocessing.errors is False

    def test_parse_s3_paths(self):
        """Test parsing configuration with S3 paths."""
        data = {
            "mode": "inference",
            "input": "s3://bucket/input",
            "output": "s3://bucket/output",
            "artifact": "s3://bucket/artifacts",
            "plant_ids": ["PLANT001"],
            "forecasting_day_ahead": 0,
            "target_radiation_type": "ghi",
            "time_windows": {
                "training": "2024-01-01T00:00:00/2024-02-01T00:00:00",
                "validation": "2024-02-01T00:00:00/2024-03-01T00:00:00",
                "test": "2024-03-01T00:00:00/2024-04-01T00:00:00",
                "inference": "2024-04-01T00:00:00/2024-05-01T00:00:00",
            },
        }

        config = Config.parse(data)
        assert config.input.startswith("s3://")
        assert config.output.startswith("s3://")
        assert config.artifact.startswith("s3://")

    def test_from_json(self, tmp_path):
        """Test loading configuration from JSON file."""
        config_data = """{
            "mode": "train",
            "input": "data/input",
            "output": "data/output",
            "artifact": "data/artifacts",
            "plant_ids": ["PLANT001"],
            "forecasting_day_ahead": 0,
            "target_radiation_type": "ghi",
            "time_windows": {
                "training": "2024-01-01T00:00:00/2024-02-01T00:00:00",
                "validation": "2024-02-01T00:00:00/2024-03-01T00:00:00",
                "test": "2024-03-01T00:00:00/2024-04-01T00:00:00",
                "inference": "2024-04-01T00:00:00/2024-05-01T00:00:00"
            }
        }"""

        config_file = tmp_path / "config.jsonc"
        config_file.write_text(config_data)

        config = Config.from_json(str(config_file))
        assert config.mode == "train"
        assert config.plant_ids == ["PLANT001"]

    def test_from_json_with_comments(self, tmp_path):
        """Test loading JSON with comments (JSONC format)."""
        config_data = """{
            // This is a comment
            "mode": "inference",
            "input": "data/input",  // inline comment
            "output": "data/output",
            "artifact": "data/artifacts",
            "plant_ids": ["PLANT001"],
            "forecasting_day_ahead": 0,
            "target_radiation_type": "dni",
            /* Multi-line
               comment */
            "time_windows": {
                "training": "2024-01-01T00:00:00/2024-02-01T00:00:00",
                "validation": "2024-02-01T00:00:00/2024-03-01T00:00:00",
                "test": "2024-03-01T00:00:00/2024-04-01T00:00:00",
                "inference": "2024-04-01T00:00:00/2024-05-01T00:00:00"
            }
        }"""

        config_file = tmp_path / "config.jsonc"
        config_file.write_text(config_data)

        config = Config.from_json(str(config_file))
        assert config.mode == "inference"
        assert config.target_radiation_type == "dni"

    def test_missing_required_field(self):
        """Test that missing required field raises error."""
        data = {
            "mode": "train",
            "input": "data/input",
            # Missing output, artifact, etc.
        }

        with pytest.raises(KeyError):
            Config.parse(data)


@pytest.mark.unit
def test_config_roundtrip(tmp_path):
    """Test that config can be saved and loaded preserving values."""
    import json

    original_data = {
        "mode": "train",
        "input": "data/input",
        "output": "data/output",
        "artifact": "data/artifacts",
        "plant_ids": ["PLANT001"],
        "forecasting_day_ahead": 1,
        "target_radiation_type": "dni",
        "time_windows": {
            "training": "2024-01-01T00:00:00/2024-02-01T00:00:00",
            "validation": "2024-02-01T00:00:00/2024-03-01T00:00:00",
            "test": "2024-03-01T00:00:00/2024-04-01T00:00:00",
            "inference": "2024-04-01T00:00:00/2024-05-01T00:00:00",
        },
        "postprocessing": {"errors": True, "plots": True},
    }

    # Save
    config_file = tmp_path / "config.json"
    with open(config_file, "w") as f:
        json.dump(original_data, f)

    # Load
    config = Config.from_json(str(config_file))

    # Verify
    assert config.mode == original_data["mode"]
    assert (
        config.forecasting_day_ahead == original_data["forecasting_day_ahead"]
    )
    assert config.postprocessing.plots is True
