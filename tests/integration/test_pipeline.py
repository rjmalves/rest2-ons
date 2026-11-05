from datetime import datetime
from pathlib import Path

import polars as pl
import pytest
from nwp_core.errors import LocationUnusableError, ObjectNotFoundError

from rest2_ons.input_contract import validate_input_units
from rest2_ons.readers import InputData
from tests.conftest import local_storage


@pytest.mark.integration
class TestFullPipeline:
    """Test the complete REST2 pipeline from input to output."""

    @pytest.fixture
    def setup_test_data(
        self,
        tmp_path: Path,
        sample_atmospheric_data: pl.DataFrame,
        sample_cod_data: pl.DataFrame,
    ) -> Path:
        """Set up test data files in temporary directory."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create required data files in the declared input units
        files = {
            "albedo.parquet": sample_atmospheric_data,
            "cod.parquet": sample_cod_data,
            "h2o.parquet": sample_atmospheric_data,
            "no2.parquet": sample_atmospheric_data.with_columns(
                pl.col("valor") * 1e-3
            ),
            "o3.parquet": sample_atmospheric_data.with_columns(
                pl.col("valor") * 1e-2
            ),
            "od550.parquet": sample_atmospheric_data,
            "od670.parquet": sample_atmospheric_data,
            "psurf.parquet": sample_atmospheric_data.with_columns(
                pl.col("valor") * 100.0 + 900.0
            ),
            "temp.parquet": sample_atmospheric_data,
        }

        for filename, data in files.items():
            data.write_parquet(input_dir / filename)

        return input_dir

    @pytest.fixture
    def setup_usinas_data(
        self, tmp_path: Path, sample_usinas_data: pl.DataFrame
    ) -> Path:
        """Set up plant metadata."""
        input_dir = tmp_path / "input"
        if not input_dir.exists():
            input_dir.mkdir()

        sample_usinas_data.write_csv(input_dir / "usinas.csv")
        return input_dir

    def test_input_data_reads_files(
        self, setup_test_data: Path, setup_usinas_data: Path
    ) -> None:
        """Test that InputData can read all required files."""
        reader = InputData(local_storage(setup_test_data))

        # Test reading usinas
        usinas = reader.read_usinas()
        assert len(usinas) > 0
        assert "id_usina" in usinas.columns

    def test_fixture_files_match_declared_units(
        self, setup_test_data: Path
    ) -> None:
        """Test that every fixture file is plausible in its declared unit."""
        stem_to_input = {
            "albedo": "albedo",
            "h2o": "h2o",
            "no2": "no2",
            "o3": "o3",
            "od550": "od550",
            "od670": "od670",
            "psurf": "psurf",
            "temp": "temp2m",
            "cod": "cod",
        }

        for stem, input_name in stem_to_input.items():
            df = pl.read_parquet(setup_test_data / f"{stem}.parquet")
            validate_input_units(input_name, df["valor"])


@pytest.mark.integration
class TestPipelineErrorHandling:
    """Test error handling in the pipeline."""

    def test_missing_input_directory(self, tmp_path: Path) -> None:
        """Test that missing input directory is handled."""
        reader = InputData(local_storage(tmp_path / "nonexistent"))

        # Should raise error when trying to read
        with pytest.raises(LocationUnusableError):
            reader.read_usinas()

    def test_missing_required_file(self, tmp_path: Path) -> None:
        """Test handling of missing required files."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        reader = InputData(local_storage(input_dir))

        # Should raise error for missing usinas.csv
        with pytest.raises(ObjectNotFoundError):
            reader.read_usinas()


@pytest.mark.integration
@pytest.mark.slow
class TestPipelinePerformance:
    """Performance tests for the pipeline."""

    def test_large_dataset_handling(self, tmp_path: Path) -> None:
        """Test handling of larger datasets."""
        import time

        import numpy as np

        # Generate larger dataset
        n_rows = 10000
        df = pl.DataFrame(
            {
                "latitude": np.random.uniform(-30, -10, n_rows),
                "longitude": np.random.uniform(-60, -30, n_rows),
                "data_hora_rodada": [datetime(2024, 1, 1)] * n_rows,
                "data_hora_previsao": [datetime(2024, 1, 1, 12, 0)] * n_rows,
                "valor": np.random.uniform(0, 1000, n_rows),
            }
        )

        # Write
        test_file = tmp_path / "large.parquet"
        df.write_parquet(test_file)

        # Time reading
        start = time.time()
        reader = InputData(local_storage(tmp_path))
        result = reader._read("large.parquet", {})
        elapsed = time.time() - start

        assert len(result) == n_rows
        assert elapsed < 5.0, f"Reading took too long: {elapsed:.2f}s"
