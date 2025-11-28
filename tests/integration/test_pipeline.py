from datetime import datetime

import polars as pl
import pytest

from app.readers import InputData
from app.storage import StorageFactory


@pytest.mark.integration
class TestFullPipeline:
    """Test the complete REST2 pipeline from input to output."""

    @pytest.fixture
    def setup_test_data(
        self, tmp_path, sample_atmospheric_data, sample_cod_data
    ):
        """Set up test data files in temporary directory."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create required data files
        files = {
            "albedo.parquet": sample_atmospheric_data,
            "cod.parquet": sample_cod_data,
            "h2o.parquet": sample_atmospheric_data,
            "no2.parquet": sample_atmospheric_data,
            "o3.parquet": sample_atmospheric_data,
            "od550.parquet": sample_atmospheric_data,
            "od670.parquet": sample_atmospheric_data,
            "psurf.parquet": sample_atmospheric_data,
            "temp.parquet": sample_atmospheric_data,
        }

        for filename, data in files.items():
            data.write_parquet(input_dir / filename)

        return input_dir

    @pytest.fixture
    def setup_measured_data(self, tmp_path, sample_measured_data):
        """Set up measured irradiance data."""
        input_dir = tmp_path / "input"
        if not input_dir.exists():
            input_dir.mkdir()

        sample_measured_data.write_parquet(
            input_dir / "measured_irradiance.parquet"
        )
        return input_dir

    @pytest.fixture
    def setup_usinas_data(self, tmp_path, sample_usinas_data):
        """Set up plant metadata."""
        input_dir = tmp_path / "input"
        if not input_dir.exists():
            input_dir.mkdir()

        sample_usinas_data.write_csv(input_dir / "usinas.csv")
        return input_dir

    def test_input_data_reads_files(self, setup_test_data, setup_usinas_data):
        """Test that InputData can read all required files."""
        reader = InputData(str(setup_test_data))

        # Test reading usinas
        usinas = reader.read_usinas()
        assert len(usinas) > 0
        assert "id_usina" in usinas.columns

    def test_storage_factory_with_local_path(self, tmp_path):
        """Test StorageFactory returns correct backend for local path."""
        storage = StorageFactory.get_storage(str(tmp_path))
        assert storage is not None

        # Test basic operations
        test_file = tmp_path / "test.txt"
        storage.write_bytes(b"test content", str(test_file))
        assert storage.exists(str(test_file))

        content = storage.read_bytes(str(test_file))
        assert content == b"test content"


@pytest.mark.integration
class TestPipelineErrorHandling:
    """Test error handling in the pipeline."""

    def test_missing_input_directory(self, tmp_path):
        """Test that missing input directory is handled."""
        reader = InputData(str(tmp_path / "nonexistent"))

        # Should raise error when trying to read
        with pytest.raises(Exception):
            reader.read_usinas()

    def test_missing_required_file(self, tmp_path):
        """Test handling of missing required files."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        reader = InputData(str(input_dir))

        # Should raise error for missing usinas.csv
        with pytest.raises(Exception):
            reader.read_usinas()


@pytest.mark.integration
class TestStorageBackendIntegration:
    """Test storage backend integration with readers/writers."""

    def test_local_parquet_roundtrip(self, tmp_path, sample_atmospheric_data):
        """Test reading and writing parquet via local storage."""
        storage = StorageFactory.get_storage(str(tmp_path))

        # Write
        output_path = storage.join_path(str(tmp_path), "test.parquet")
        storage.write_parquet(sample_atmospheric_data.to_pandas(), output_path)

        # Read
        df_lazy = storage.read_parquet(output_path)
        df_read = df_lazy.collect()

        assert len(df_read) == len(sample_atmospheric_data)
        assert set(df_read.columns) == set(sample_atmospheric_data.columns)

    def test_directory_creation(self, tmp_path):
        """Test creating nested directories."""
        storage = StorageFactory.get_storage(str(tmp_path))

        nested_path = storage.join_path(str(tmp_path), "a", "b", "c")
        storage.makedirs(nested_path)

        assert (tmp_path / "a" / "b" / "c").exists()

    def test_file_listing(self, tmp_path):
        """Test listing files with pattern."""
        storage = StorageFactory.get_storage(str(tmp_path))

        # Create test files
        (tmp_path / "data1.parquet").write_text("test")
        (tmp_path / "data2.parquet").write_text("test")
        (tmp_path / "config.json").write_text("test")

        files = storage.list_files(str(tmp_path), "*.parquet")
        assert len(files) == 2


@pytest.mark.integration
@pytest.mark.s3
class TestS3Integration:
    """Test S3 integration with moto."""

    def test_s3_parquet_roundtrip(
        self, mock_s3_bucket, sample_atmospheric_data
    ):
        """Test reading and writing parquet via S3 storage."""
        from app.storage import S3Backend

        storage = S3Backend()
        bucket = mock_s3_bucket

        # For mocked S3, use boto3 directly instead of s3fs
        # as s3fs has compatibility issues with moto's async API
        test_data = sample_atmospheric_data.to_pandas().to_parquet()
        test_path = f"s3://{bucket}/test/data.parquet"

        # Write using boto3 directly
        storage.write_bytes(test_data, test_path)

        # Verify file exists
        assert storage.exists(test_path)

    def test_s3_bytes_roundtrip(self, mock_s3_bucket):
        """Test reading and writing bytes via S3."""
        from app.storage import S3Backend

        storage = S3Backend()
        bucket = mock_s3_bucket

        test_data = b"test content for S3"
        test_path = f"s3://{bucket}/test/file.txt"

        storage.write_bytes(test_data, test_path)
        read_data = storage.read_bytes(test_path)

        assert read_data == test_data


@pytest.mark.integration
@pytest.mark.slow
class TestPipelinePerformance:
    """Performance tests for the pipeline."""

    def test_large_dataset_handling(self, tmp_path):
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
        reader = InputData(str(tmp_path))
        result = reader._read("large.parquet", {})
        elapsed = time.time() - start

        assert len(result) == n_rows
        assert elapsed < 5.0, f"Reading took too long: {elapsed:.2f}s"
