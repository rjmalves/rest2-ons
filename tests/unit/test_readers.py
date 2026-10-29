from datetime import datetime
from pathlib import Path

import polars as pl
import pytest

from app.input_contract import InputUnitMismatchError
from app.readers import InputData, LocationDataBuilder, LocationInputData


class TestLocationInputData:
    """Test LocationInputData dataclass."""

    def test_apply_unit_conversions_leaves_hpa_pressure_unchanged(self) -> None:
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
                pl.lit(1013.25).alias("valor")
            ),  # hPa, declared unit
            temp2m=time_data.with_columns(pl.lit(25.0).alias("valor")),
        )

        location_data.apply_unit_conversions()

        # Check conversions
        # psurf: already hPa, left unchanged
        assert abs(location_data.psurf["valor"][0] - 1013.25) < 1e-12, (
            "Pressure must not be re-converted"
        )

        # h2o: 10 kg/m2 * 0.1 = 1.0 atm-cm
        assert abs(location_data.h2o["valor"][0] - 1.0) < 0.001, (
            "H2O conversion failed"
        )

    def test_calculate_derived_fields(self) -> None:
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
            temp2m=time_data.with_columns(pl.lit(25.0).alias("valor")),
        )

        location_data.calculate_derived_fields()

        # Angstrom exponent should be calculated
        assert location_data.angstrom_exponent is not None
        assert "valor" in location_data.angstrom_exponent.columns
        assert len(location_data.angstrom_exponent) == 1


class TestInputData:
    """Test InputData reader."""

    def test_initialization(self) -> None:
        """Test InputData initialization."""
        reader = InputData("data/input")
        assert reader.path == "data/input"
        assert reader.storage is not None

    def test_initialization_with_s3(self) -> None:
        """Test InputData initialization with S3 path."""
        reader = InputData("s3://bucket/input")
        assert reader.path == "s3://bucket/input"
        assert reader.storage is not None

    def test_apply_filters_single_value(self) -> None:
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

    def test_apply_filters_list_value(self) -> None:
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

    def test_for_location_returns_builder(self) -> None:
        """Test that for_location returns a builder."""
        reader = InputData("data/input")
        builder = reader.for_location(-22.5, -45.5)

        assert isinstance(builder, LocationDataBuilder)
        assert builder.latitude == -22.5
        assert builder.longitude == -45.5

    def test_filter_forecasting_day(self) -> None:
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

    @pytest.mark.parametrize(
        "row_order",
        [[0, 1, 2, 3], [3, 2, 1, 0], [2, 0, 3, 1]],
        ids=["runs-ascending", "runs-descending", "shuffled"],
    )
    def test_filter_forecasting_day_keeps_the_latest_run(
        self, row_order: list[int]
    ) -> None:
        # 2024-01-02 18:00 is 42 h after the 00Z run and 30 h after the 12Z
        # run, both in lead day 1; 06:00 is in lead day 1 only for 00Z (30 h).
        runs = pl.DataFrame(
            {
                "data_hora_rodada": [
                    datetime(2024, 1, 1, 0),
                    datetime(2024, 1, 1, 0),
                    datetime(2024, 1, 1, 12),
                    datetime(2024, 1, 1, 12),
                ],
                "data_hora_previsao": [
                    datetime(2024, 1, 2, 6),
                    datetime(2024, 1, 2, 18),
                    datetime(2024, 1, 2, 6),
                    datetime(2024, 1, 2, 18),
                ],
                "valor": [1.0, 2.0, 3.0, 4.0],
            }
        )

        filtered = InputData.filter_forecasting_day(runs[row_order], 1)

        assert filtered["time"].to_list() == [
            datetime(2024, 1, 2, 6),
            datetime(2024, 1, 2, 18),
        ]
        assert filtered["valor"].to_list() == [1.0, 4.0]


class TestLocationDataBuilder:
    """Test LocationDataBuilder."""

    def test_builder_chain(self) -> None:
        """Test builder method chaining."""
        reader = InputData("data/input")
        builder = (
            reader.for_location(-22.5, -45.5)
            .time_range(datetime(2024, 1, 1), datetime(2024, 1, 31))
            .forecasting_day_filter(1)
        )

        assert builder.latitude == -22.5
        assert builder.longitude == -45.5
        assert builder.start_date == datetime(2024, 1, 1)
        assert builder.end_date == datetime(2024, 1, 31)
        assert builder.forecasting_day == 1


def _write_input_files(tmp_path: Path, psurf_value: float) -> None:
    hours = [datetime(2024, 1, 15, hour) for hour in range(24)]
    values = {
        "cod": 5.0,
        "albedo": 0.2,
        "h2o": 25.0,
        "no2": 1e-4,
        "o3": 6e-3,
        "od550": 0.12,
        "od670": 0.09,
        "psurf": psurf_value,
        "temp": 25.0,
    }
    for name, value in values.items():
        pl.DataFrame(
            {
                "latitude": [-22.5] * 24,
                "longitude": [-45.5] * 24,
                "data_hora_rodada": [datetime(2024, 1, 15, 0, 0)] * 24,
                "data_hora_previsao": hours,
                "valor": [value] * 24,
            }
        ).write_parquet(tmp_path / f"{name}.parquet")


@pytest.mark.unit
class TestReadBoundaryUnits:
    """The declared input units are enforced where the files are read."""

    def test_pa_pressure_fails_at_read_boundary(self, tmp_path: Path) -> None:
        _write_input_files(tmp_path, psurf_value=101325.0)

        builder = InputData(str(tmp_path)).for_location(-22.5, -45.5)

        with pytest.raises(InputUnitMismatchError, match=r"psurf.*hPa"):
            builder.forecasting_day_filter(0).build()

    def test_hpa_pressure_reads_unchanged(self, tmp_path: Path) -> None:
        _write_input_files(tmp_path, psurf_value=1013.25)

        location_data = (
            InputData(str(tmp_path))
            .for_location(-22.5, -45.5)
            .forecasting_day_filter(0)
            .build()
        )

        assert location_data.psurf["valor"].unique().to_list() == [1013.25]
        assert location_data.psurf.height == 139


@pytest.mark.unit
class TestMissingForecastInputs:
    """A forecast input that cannot be used is named in the error."""

    def test_missing_files_are_named(self, tmp_path: Path) -> None:
        _write_input_files(tmp_path, psurf_value=1013.25)
        (tmp_path / "no2.parquet").unlink()
        (tmp_path / "temp.parquet").unlink()

        builder = InputData(str(tmp_path)).for_location(-22.5, -45.5)

        with pytest.raises(
            FileNotFoundError, match=r"no2\.parquet, temp\.parquet"
        ):
            builder.forecasting_day_filter(0).build()

    def test_file_off_the_albedo_grid_is_named(self, tmp_path: Path) -> None:
        _write_input_files(tmp_path, psurf_value=1013.25)
        o3_path = tmp_path / "o3.parquet"
        pl.read_parquet(o3_path).with_columns(
            pl.lit(-23.0).alias("latitude")
        ).write_parquet(o3_path)

        builder = InputData(str(tmp_path)).for_location(-22.5, -45.5)

        with pytest.raises(ValueError, match=r"o3\.parquet.*albedo\.parquet"):
            builder.forecasting_day_filter(0).build()


@pytest.mark.unit
class TestReadersDataFlow:
    """Test data flow through readers."""

    def test_read_method_parquet(
        self, tmp_path: Path, sample_atmospheric_data: pl.DataFrame
    ) -> None:
        """Test _read method with parquet files."""
        # Write test data
        test_file = tmp_path / "test.parquet"
        sample_atmospheric_data.write_parquet(test_file)

        reader = InputData(str(tmp_path))
        result = reader._read("test.parquet", {})

        assert len(result) == len(sample_atmospheric_data)

    def test_read_method_csv(self, tmp_path: Path) -> None:
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

    def test_read_method_unsupported_format(self) -> None:
        """Test _read method with unsupported format raises error."""
        reader = InputData("data/input")

        with pytest.raises(ValueError, match="Unsupported file format"):
            reader._read("test.xlsx", {})
