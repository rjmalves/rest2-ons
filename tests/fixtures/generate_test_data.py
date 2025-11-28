"""
Generate test fixtures for REST2-ONS tests.

This script creates small synthetic datasets for testing the REST2 radiation
model pipeline. The generated data mimics the structure of real CAMS forecast
and measured irradiance data.

Usage:
    python tests/fixtures/generate_test_data.py --output-dir tests/fixtures/data
"""

import argparse
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl


def generate_atmospheric_data(
    output_dir: Path,
    lat_range: tuple[float, float] = (-24.0, -21.0),
    lon_range: tuple[float, float] = (-47.0, -44.0),
    start_date: datetime = datetime(2024, 1, 1),
    num_days: int = 7,
) -> None:
    """
    Generate synthetic atmospheric forecast data.

    Creates parquet files for all required CAMS atmospheric variables.

    Args:
        output_dir: Directory to save test fixtures
        lat_range: (min_lat, max_lat) for grid
        lon_range: (min_lon, max_lon) for grid
        start_date: Starting datetime for test data
        num_days: Number of days of data to generate
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    np.random.seed(42)

    # Grid definition
    lats = np.linspace(lat_range[0], lat_range[1], 4)
    lons = np.linspace(lon_range[0], lon_range[1], 4)

    # Time series (hourly data)
    times = []
    for day in range(num_days):
        for hour in range(24):
            times.append(start_date + timedelta(days=day, hours=hour))

    print(
        f"Generating {len(times)} time steps for {len(lats) * len(lons)} grid points"
    )

    # Variable definitions with typical ranges
    variables = {
        "albedo": (0.1, 0.3),  # Surface albedo
        "h2o": (5.0, 30.0),  # Water vapor (kg/m2)
        "no2": (0.0001, 0.001),  # NO2 (kg/m2)
        "o3": (0.005, 0.015),  # Ozone (kg/m2)
        "od550": (0.05, 0.5),  # Aerosol optical depth at 550nm
        "od670": (0.03, 0.4),  # Aerosol optical depth at 670nm
        "psurf": (95000, 102000),  # Surface pressure (Pa)
        "temp": (280, 310),  # 2m temperature (K)
    }

    total_rows = 0

    for var_name, (min_val, max_val) in variables.items():
        rows = []
        for time in times:
            for lat in lats:
                for lon in lons:
                    value = np.random.uniform(min_val, max_val)
                    rows.append(
                        {
                            "latitude": lat,
                            "longitude": lon,
                            "data_hora_rodada": start_date,
                            "data_hora_previsao": time,
                            "valor": value,
                        }
                    )

        df = pl.DataFrame(rows)
        output_path = output_dir / f"{var_name}.parquet"
        df.write_parquet(output_path)

        total_rows += len(rows)
        size_kb = output_path.stat().st_size / 1024
        print(f"  {var_name}.parquet: {len(rows)} rows, {size_kb:.1f} KB")

    print(f"\nTotal atmospheric data: {total_rows} rows")


def generate_cod_data(
    output_dir: Path,
    lat_range: tuple[float, float] = (-24.0, -21.0),
    lon_range: tuple[float, float] = (-47.0, -44.0),
    start_date: datetime = datetime(2024, 1, 1),
    num_days: int = 7,
) -> None:
    """
    Generate synthetic Cloud Optical Depth data.

    COD follows a gamma distribution which is typical for cloud properties.

    Args:
        output_dir: Directory to save test fixtures
        lat_range: (min_lat, max_lat) for grid
        lon_range: (min_lon, max_lon) for grid
        start_date: Starting datetime for test data
        num_days: Number of days of data to generate
    """
    np.random.seed(43)

    lats = np.linspace(lat_range[0], lat_range[1], 4)
    lons = np.linspace(lon_range[0], lon_range[1], 4)

    times = []
    for day in range(num_days):
        for hour in range(24):
            times.append(start_date + timedelta(days=day, hours=hour))

    rows = []
    for time in times:
        for lat in lats:
            for lon in lons:
                # COD follows gamma distribution
                cod_value = np.random.gamma(2, 3)
                # Cap at reasonable maximum
                cod_value = min(cod_value, 50.0)
                rows.append(
                    {
                        "latitude": lat,
                        "longitude": lon,
                        "data_hora_rodada": start_date,
                        "data_hora_previsao": time,
                        "valor": cod_value,
                    }
                )

    df = pl.DataFrame(rows)
    output_path = output_dir / "cod.parquet"
    df.write_parquet(output_path)

    size_kb = output_path.stat().st_size / 1024
    print(f"  cod.parquet: {len(rows)} rows, {size_kb:.1f} KB")


def generate_measured_data(
    output_dir: Path,
    plant_ids: list[str] = None,
    start_date: datetime = datetime(2024, 1, 1),
    num_days: int = 7,
) -> None:
    """
    Generate synthetic measured irradiance data.

    Simulates realistic solar irradiance patterns (zero at night, peak at noon).

    Args:
        output_dir: Directory to save test fixtures
        plant_ids: List of plant identifiers
        start_date: Starting datetime for test data
        num_days: Number of days of data to generate
    """
    if plant_ids is None:
        plant_ids = ["TEST001", "TEST002"]

    np.random.seed(44)

    times = []
    for day in range(num_days):
        for hour in range(24):
            times.append(start_date + timedelta(days=day, hours=hour))

    rows = []
    for plant_id in plant_ids:
        for time in times:
            hour = time.hour
            if 6 <= hour <= 18:
                # Sinusoidal pattern for daytime
                solar_angle = (hour - 6) * np.pi / 12
                base_irradiance = 1000 * np.sin(solar_angle)
                # Add noise and cloud variability
                irradiance = base_irradiance * np.random.uniform(0.5, 1.0)
                irradiance += np.random.normal(0, 30)
                irradiance = max(0, irradiance)
            else:
                irradiance = 0.0

            rows.append(
                {
                    "id_usina": plant_id,
                    "data_hora_observacao": time,
                    "valor": irradiance,
                }
            )

    df = pl.DataFrame(rows)
    output_path = output_dir / "measured_irradiance.parquet"
    df.write_parquet(output_path)

    size_kb = output_path.stat().st_size / 1024
    print(f"  measured_irradiance.parquet: {len(rows)} rows, {size_kb:.1f} KB")


def generate_usinas_metadata(
    output_dir: Path,
    plant_ids: list[str] = None,
) -> None:
    """
    Generate plant metadata file.

    Args:
        output_dir: Directory to save test fixtures
        plant_ids: List of plant identifiers
    """
    if plant_ids is None:
        plant_ids = ["TEST001", "TEST002"]

    # Coordinates within the test grid
    coordinates = {
        "TEST001": (-22.5, -45.5),
        "TEST002": (-23.0, -46.0),
    }

    rows = []
    for plant_id in plant_ids:
        lat, lon = coordinates.get(plant_id, (-22.5, -45.5))
        rows.append(
            {
                "id_usina": plant_id,
                "latitude": lat,
                "longitude": lon,
            }
        )

    df = pl.DataFrame(rows)
    output_path = output_dir / "usinas.csv"
    df.write_csv(output_path)

    print(f"  usinas.csv: {len(rows)} plants")


def main():
    parser = argparse.ArgumentParser(
        description="Generate test fixtures for REST2-ONS tests"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("tests/fixtures/data"),
        help="Output directory for test fixtures",
    )
    parser.add_argument(
        "--num-days",
        type=int,
        default=7,
        help="Number of days of data to generate",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default="2024-01-01",
        help="Start date (YYYY-MM-DD)",
    )

    args = parser.parse_args()

    start_date = datetime.strptime(args.start_date, "%Y-%m-%d")

    print(f"Generating test fixtures in {args.output_dir}")
    print(f"Start date: {start_date}, Days: {args.num_days}\n")

    print("Generating atmospheric data...")
    generate_atmospheric_data(
        args.output_dir,
        start_date=start_date,
        num_days=args.num_days,
    )

    print("\nGenerating COD data...")
    generate_cod_data(
        args.output_dir,
        start_date=start_date,
        num_days=args.num_days,
    )

    print("\nGenerating measured irradiance data...")
    generate_measured_data(
        args.output_dir,
        start_date=start_date,
        num_days=args.num_days,
    )

    print("\nGenerating plant metadata...")
    generate_usinas_metadata(args.output_dir)

    print(f"\nTest fixtures generated in {args.output_dir}")


if __name__ == "__main__":
    main()
