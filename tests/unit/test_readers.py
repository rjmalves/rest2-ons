from datetime import datetime

import polars as pl
import pytest

from app.readers import InputData, LocationDataBuilder, LocationInputData


class TestLocationInputData:
    """Test LocationInputData dataclass."""

    def test_apply_unit_conversions(self):
        """Test unit conversions are applied correctly."""
        # Create minimal input data
        time_data = pl.DataFrame({"time": [datetime(2024, 1, 15, 12, 0)]})

        location_data = LocationInputData(
            latitude=-22.5,
            longitude=-45.5,
            cod=time_data.with_columns(pl.lit(5.0).alias("valor")),
            albedo=time_data.with_columns(pl.lit(0.2).alias("valor")),
            h2o=time_data.with_columns(
                pl.lit(10.0).alias("valor")
            ),  # kg/m2 -> 1 atm-cm
            no2=time_data.with_columns(
                pl.lit(0.001).alias("valor")
            ),  # kg/m2 -> atm-cm
            o3=time_data.with_columns(
                pl.lit(0.01).alias("valor")
            ),  # kg/m2 -> atm-cm
            od550=time_data.with_columns(pl.lit(0.1).alias("valor")),
            od670=time_data.with_columns(pl.lit(0.08).alias("valor")),
            psurf=time_data.with_columns(
                pl.lit(101325.0).alias("valor")
            ),  # Pa -> hPa
            temp2m=time_data.with_columns(pl.lit(298.0).alias("valor")),
        )

        location_data.apply_unit_conversions()

        # Check conversions
        # psurf: 101325 Pa -> 1013.25 hPa
        assert abs(location_data.psurf["valor"][0] - 1013.25) < 0.01, (
            "Pressure conversion failed"
        )

        # h2o: 10 kg/m2 * 0.1 = 1.0 atm-cm
        assert abs(location_data.h2o["valor"][0] - 1.0) < 0.001, (
            "H2O conversion failed"
        )

    def test_calculate_derived_fields(self):
        """Test Angstrom exponent calculation."""
        time_data = pl.DataFrame({"time": [datetime(2024, 1, 15, 12, 0)]})

        location_data = LocationInputData(
            latitude=-22.5,
            longitude=-45.5,
            cod=time_data.with_columns(pl.lit(5.0).alias("valor")),
            albedo=time_data.with_columns(pl.lit(0.2).alias("valor")),
            h2o=time_data.with_columns(pl.lit(1.0).alias("valor")),
            no2=time_data.with_columns(pl.lit(0.001).alias("valor")),
            o3=time_data.with_columns(pl.lit(0.3).alias("valor")),
            od550=time_data.with_columns(pl.lit(0.2).alias("valor")),
            od670=time_data.with_columns(pl.lit(0.15).alias("valor")),
            psurf=time_data.with_columns(pl.lit(1013.25).alias("valor")),
            temp2m=time_data.with_columns(pl.lit(298.0).alias("valor")),
        )

        location_data.calculate_derived_fields()

        # Angstrom exponent should be calculated
        assert location_data.angstrom_exponent is not None
        assert "valor" in location_data.angstrom_exponent.columns
        assert len(location_data.angstrom_exponent) == 1

    def test_get_rest2_inputs(self):
        """Test REST2 input dictionary generation."""
        time_data = pl.DataFrame({"time": [datetime(2024, 1, 15, 12, 0)]})
        angstrom_data = time_data.with_columns(pl.lit(1.3).alias("valor"))

        location_data = LocationInputData(
            latitude=-22.5,
            longitude=-45.5,
            cod=time_data.with_columns(pl.lit(5.0).alias("valor")),
            albedo=time_data.with_columns(pl.lit(0.2).alias("valor")),
            h2o=time_data.with_columns(pl.lit(1.0).alias("valor")),
            no2=time_data.with_columns(pl.lit(0.001).alias("valor")),
            o3=time_data.with_columns(pl.lit(0.3).alias("valor")),
            od550=time_data.with_columns(pl.lit(0.2).alias("valor")),
            od670=time_data.with_columns(pl.lit(0.15).alias("valor")),
            psurf=time_data.with_columns(pl.lit(1013.25).alias("valor")),
            temp2m=time_data.with_columns(pl.lit(298.0).alias("valor")),
            angstrom_exponent=angstrom_data,
        )

        inputs = location_data.get_rest2_inputs()

        assert "angstrom_exponent" in inputs
        assert "pressure" in inputs
        assert "water_vapour" in inputs
        assert "ozone" in inputs
        assert "nitrogen_dioxide" in inputs
        assert "surface_albedo" in inputs
        assert "optical_depth_550nm" in inputs
        assert "cod" in inputs
        assert "lat" in inputs
        assert "lon" in inputs
        assert inputs["lat"] == -22.5
        assert inputs["lon"] == -45.5


class TestInputData:
    """Test InputData reader."""

    def test_initialization(self):
        """Test InputData initialization."""
        reader = InputData("data/input")
        assert reader.path == "data/input"
        assert reader.storage is not None

    def test_initialization_with_s3(self):
        """Test InputData initialization with S3 path."""
        reader = InputData("s3://bucket/input")
        assert reader.path == "s3://bucket/input"
        assert reader.storage is not None

    def test_apply_filters_single_value(self):
        """Test filtering with single value."""
        reader = InputData("data/input")

        lf = pl.LazyFrame(
            {
                "id": ["A", "B", "C"],
                "value": [1, 2, 3],
            }
        )

        filtered = reader._apply_filters(lf, {"id": "B"})
        result = filtered.collect()

        assert len(result) == 1
        assert result["id"][0] == "B"

    def test_apply_filters_list_value(self):
        """Test filtering with list of values."""
        reader = InputData("data/input")

        lf = pl.LazyFrame(
            {
                "id": ["A", "B", "C", "D"],
                "value": [1, 2, 3, 4],
            }
        )

        filtered = reader._apply_filters(lf, {"id": ["A", "C"]})
        result = filtered.collect()

        assert len(result) == 2
        assert set(result["id"].to_list()) == {"A", "C"}

    def test_for_location_returns_builder(self):
        """Test that for_location returns a builder."""
        reader = InputData("data/input")
        builder = reader.for_location(-22.5, -45.5)

        assert isinstance(builder, LocationDataBuilder)
        assert builder.latitude == -22.5
        assert builder.longitude == -45.5

    def test_filter_forecasting_day(self):
        """Test filtering by forecasting day."""
        # Create sample data with multiple forecasting days
        df = pl.DataFrame(
            {
                "data_hora_previsao": [
                    datetime(2024, 1, 1, 12, 0),
                    datetime(2024, 1, 2, 12, 0),
                    datetime(2024, 1, 3, 12, 0),
                ],
                "data_hora_rodada": [
                    datetime(2024, 1, 1, 0, 0),
                    datetime(2024, 1, 1, 0, 0),
                    datetime(2024, 1, 1, 0, 0),
                ],
                "valor": [100.0, 200.0, 300.0],
            }
        )

        # Filter for day 1 (second row)
        filtered = InputData.filter_forecasting_day(df, 1)

        assert len(filtered) == 1
        assert filtered["valor"][0] == 200.0


class TestLocationDataBuilder:
    """Test LocationDataBuilder."""

    def test_builder_chain(self):
        """Test builder method chaining."""
        reader = InputData("data/input")
        builder = (
            reader.for_location(-22.5, -45.5)
            .time_range(datetime(2024, 1, 1), datetime(2024, 1, 31))
            .forecasting_day_filter(1)
            .skip_unit_conversions()
            .skip_derived_fields()
        )

        assert builder.latitude == -22.5
        assert builder.longitude == -45.5
        assert builder.start_date == datetime(2024, 1, 1)
        assert builder.end_date == datetime(2024, 1, 31)
        assert builder.forecasting_day == 1
        assert builder._apply_unit_conversions is False
        assert builder._calculate_derived_fields is False


@pytest.mark.unit
class TestReadersDataFlow:
    """Test data flow through readers."""

    def test_read_method_parquet(self, tmp_path, sample_atmospheric_data):
        """Test _read method with parquet files."""
        # Write test data
        test_file = tmp_path / "test.parquet"
        sample_atmospheric_data.write_parquet(test_file)

        reader = InputData(str(tmp_path))
        result = reader._read("test.parquet", {})

        assert len(result) == len(sample_atmospheric_data)

    def test_read_method_csv(self, tmp_path):
        """Test _read method with CSV files."""
        test_df = pl.DataFrame(
            {
                "id": ["A", "B", "C"],
                "value": [1, 2, 3],
            }
        )
        test_file = tmp_path / "test.csv"
        test_df.write_csv(test_file)

        reader = InputData(str(tmp_path))
        result = reader._read("test.csv", {})

        assert len(result) == 3

    def test_read_method_unsupported_format(self):
        """Test _read method with unsupported format raises error."""
        reader = InputData("data/input")

        with pytest.raises(ValueError, match="Unsupported file format"):
            reader._read("test.xlsx", {})
