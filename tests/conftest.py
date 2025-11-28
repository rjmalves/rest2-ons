import tempfile
from collections.abc import Generator
from datetime import datetime
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from app.internal.config import (
    Config,
    PostprocessingConfig,
    TimeWindow,
    TimeWindows,
)


@pytest.fixture
def test_data_dir() -> Path:
    """Path to test fixture data directory."""
    return Path(__file__).parent / "fixtures" / "data"


@pytest.fixture
def temp_output_dir() -> Generator[Path, None, None]:
    """Temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_time_windows() -> TimeWindows:
    """Sample time windows configuration for testing."""
    return TimeWindows(
        training=TimeWindow(
            start=datetime(2024, 1, 1), end=datetime(2024, 2, 1)
        ),
        validation=TimeWindow(
            start=datetime(2024, 2, 1), end=datetime(2024, 3, 1)
        ),
        test=TimeWindow(start=datetime(2024, 3, 1), end=datetime(2024, 4, 1)),
        inference=TimeWindow(
            start=datetime(2024, 4, 1), end=datetime(2024, 5, 1)
        ),
    )


@pytest.fixture
def sample_config(
    test_data_dir: Path, temp_output_dir: Path, sample_time_windows: TimeWindows
) -> Config:
    """Sample configuration for testing."""
    return Config(
        mode="train",
        input=str(test_data_dir),
        output=str(temp_output_dir),
        artifact=str(temp_output_dir / "artifacts"),
        time_windows=sample_time_windows,
        postprocessing=PostprocessingConfig(errors=False, plots=False),
        plant_ids=["TEST001"],
        forecasting_day_ahead=0,
        target_radiation_type="ghi",
    )


@pytest.fixture
def sample_atmospheric_data() -> pl.DataFrame:
    """
    Create synthetic atmospheric data for testing.

    Returns a DataFrame with structure matching CAMS forecast data.
    """
    np.random.seed(42)

    # Generate time series
    n_times = 24  # 24 hours
    base_time = datetime(2024, 1, 15, 0, 0)
    times = [
        datetime(
            base_time.year,
            base_time.month,
            base_time.day,
            h,
            0,
        )
        for h in range(n_times)
    ]

    # Grid points
    lats = [-23.0, -22.5, -22.0]
    lons = [-46.0, -45.5, -45.0]

    rows = []
    for time in times:
        for lat in lats:
            for lon in lons:
                rows.append(
                    {
                        "latitude": lat,
                        "longitude": lon,
                        "data_hora_rodada": datetime(2024, 1, 15, 0, 0),
                        "data_hora_previsao": time,
                        "valor": np.random.uniform(0.1, 1.0),
                    }
                )

    return pl.DataFrame(rows)


@pytest.fixture
def sample_cod_data() -> pl.DataFrame:
    """Create synthetic cloud optical depth data."""
    np.random.seed(42)

    n_times = 24
    base_time = datetime(2024, 1, 15, 0, 0)
    times = [
        datetime(
            base_time.year,
            base_time.month,
            base_time.day,
            h,
            0,
        )
        for h in range(n_times)
    ]

    lats = [-23.0, -22.5, -22.0]
    lons = [-46.0, -45.5, -45.0]

    rows = []
    for time in times:
        for lat in lats:
            for lon in lons:
                # COD follows gamma distribution
                cod_value = np.random.gamma(2, 2)
                rows.append(
                    {
                        "latitude": lat,
                        "longitude": lon,
                        "data_hora_rodada": datetime(2024, 1, 15, 0, 0),
                        "data_hora_previsao": time,
                        "valor": cod_value,
                    }
                )

    return pl.DataFrame(rows)


@pytest.fixture
def sample_measured_data() -> pl.DataFrame:
    """Create synthetic measured irradiance data."""
    np.random.seed(42)

    n_times = 24
    base_time = datetime(2024, 1, 15, 0, 0)
    times = [
        datetime(
            base_time.year,
            base_time.month,
            base_time.day,
            h,
            0,
        )
        for h in range(n_times)
    ]

    rows = []
    for time in times:
        # Simulate solar irradiance pattern (zero at night, peak at noon)
        hour = time.hour
        if 6 <= hour <= 18:
            # Simple sinusoidal pattern for daytime
            solar_angle = (hour - 6) * np.pi / 12
            base_irradiance = 1000 * np.sin(solar_angle)
            # Add some noise
            irradiance = base_irradiance + np.random.normal(0, 50)
            irradiance = max(0, irradiance)
        else:
            irradiance = 0.0

        rows.append(
            {
                "id_usina": "TEST001",
                "data_hora_observacao": time,
                "valor": irradiance,
            }
        )

    return pl.DataFrame(rows)


@pytest.fixture
def sample_usinas_data() -> pl.DataFrame:
    """Create synthetic plant metadata."""
    return pl.DataFrame(
        {
            "id_usina": ["TEST001", "TEST002"],
            "latitude": [-22.5, -21.0],
            "longitude": [-45.5, -44.0],
        }
    )


@pytest.fixture
def mock_s3_bucket():
    """
    Create a mock S3 bucket using moto.

    Yields:
        str: Bucket name for testing

    Note:
        This requires moto to be installed: pip install moto[s3]
        Tests using this fixture should be marked with @pytest.mark.s3
    """
    try:
        import boto3
        from moto import mock_aws
    except ImportError:
        pytest.skip("moto not installed - skipping S3 tests")

    # Start mock and keep it active during the test
    mock = mock_aws()
    mock.start()

    try:
        # Create mock S3 client
        s3_client = boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id="testing",
            aws_secret_access_key="testing",
        )

        # Create test bucket
        bucket_name = "test-rest2-ons-bucket"
        s3_client.create_bucket(Bucket=bucket_name)

        yield bucket_name
    finally:
        mock.stop()


# Markers for different test categories
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests for individual components"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests for full pipeline"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take a long time to run"
    )
    config.addinivalue_line(
        "markers", "s3: Tests that require S3/moto (AWS simulation)"
    )
    config.addinivalue_line(
        "markers", "plotting: Tests that generate plots (skip on CI if needed)"
    )
