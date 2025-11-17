import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

import numpy as np
import polars as pl
import pyjson5

from app.internal.config import Config
from app.utils.data import PlantArtifact
from app.utils.utils import haversine_distance


@dataclass
class LocationInputData:
    """Container for all forecast data for a specific location."""

    latitude: float
    longitude: float

    # Raw atmospheric data
    cod: pl.DataFrame
    albedo: pl.DataFrame
    h2o: pl.DataFrame
    no2: pl.DataFrame
    o3: pl.DataFrame
    od550: pl.DataFrame
    od670: pl.DataFrame
    psurf: pl.DataFrame
    temp2m: pl.DataFrame

    # Derived fields (computed from raw data)
    angstrom_exponent: pl.DataFrame = None

    # Metadata
    time_range: tuple[datetime, datetime] = None
    forecasting_day: int = None

    def apply_unit_conversions(self) -> "LocationInputData":
        """Apply unit conversions to the data fields."""
        self.o3 = self.o3.with_columns(
            pl.col("valor") * 46.73
        )  # kg/m2 -> atm-cm: ro_o3 = 2.14kg/m3 => o3[kg/m2]/ro_o3 * 100 (m->cm) = 46.73
        self.h2o = self.h2o.with_columns(
            pl.col("valor") * 0.1
        )  # kg/m2 -> atm-cm: ro_h2o = 1000 kg/m3 => h2o[kg/m2]/ro_h2o * 100 (m->cm) = 0.1
        self.no2 = self.no2.with_columns(
            pl.col("valor") * 48.78
        )  # kg/m2 -> atm-cm: ro_no2 = 2.05kg/m3 => no2[kg/m2]/ro_no2 * 100 (m->cm) = 48.78
        self.psurf = self.psurf.with_columns(
            pl.col("valor") * 0.01
        )  # Pa -> hPa

        return self

    def calculate_derived_fields(self) -> "LocationInputData":
        # Calculate angstrom exponent from optical depths
        # Avoid division by zero and log of zero
        od550_safe = self.od550.with_columns(
            pl.col("valor").clip(lower_bound=1e-10)
        )
        od670_safe = self.od670.with_columns(
            pl.col("valor").clip(lower_bound=1e-10)
        )
        angstrom_exponent = -1 * (
            np.log(
                od550_safe["valor"].to_numpy() / od670_safe["valor"].to_numpy()
            )
            / np.log(550.0 / 670.0)
        )
        self.angstrom_exponent = pl.DataFrame({
            "time": self.od550["time"],
            "valor": angstrom_exponent,
        })

        return self

    def _upsample(self, df: pl.DataFrame, interval: str) -> pl.DataFrame:
        return df.upsample(time_column="time", every=interval).fill_null(
            strategy="forward"
        )

    def upsample_to_interval(self, interval: str) -> "LocationInputData":
        self.cod = self._upsample(self.cod, interval)
        self.albedo = self._upsample(self.albedo, interval)
        self.h2o = self._upsample(self.h2o, interval)
        self.no2 = self._upsample(self.no2, interval)
        self.o3 = self._upsample(self.o3, interval)
        self.od550 = self._upsample(self.od550, interval)
        self.od670 = self._upsample(self.od670, interval)
        self.psurf = self._upsample(self.psurf, interval)
        self.temp2m = self._upsample(self.temp2m, interval)
        if self.angstrom_exponent is not None:
            self.angstrom_exponent = self._upsample(
                self.angstrom_exponent, interval
            )
        return self

    def get_rest2_inputs(self) -> Dict[str, pl.DataFrame]:
        """Get inputs formatted for REST2 model."""
        return {
            "angstrom_exponent": self.angstrom_exponent,
            "pressure": self.psurf,
            "water_vapour": self.h2o,
            "ozone": self.o3,
            "nitrogen_dioxide": self.no2,
            "surface_albedo": self.albedo,
            "optical_depth_550nm": self.od550,
            "cod": self.cod,
            "lat": self.latitude,
            "lon": self.longitude,
        }


class LocationDataBuilder:
    """Builder class for creating LocationInputData with optional filtering and processing."""

    def __init__(self, reader: "InputData", latitude: float, longitude: float):
        self.reader = reader
        self.latitude = latitude
        self.longitude = longitude
        self.start_date: Optional[datetime] = None
        self.end_date: Optional[datetime] = None
        self.forecasting_day: Optional[int] = None
        self._apply_unit_conversions = True
        self._calculate_derived_fields = True

    def time_range(
        self, start_date: datetime, end_date: datetime
    ) -> "LocationDataBuilder":
        """Set the time range filter."""
        self.start_date = start_date
        self.end_date = end_date
        return self

    def forecasting_day_filter(self, day: int) -> "LocationDataBuilder":
        """Set the forecasting day filter."""
        self.forecasting_day = day
        return self

    def skip_unit_conversions(self) -> "LocationDataBuilder":
        """Skip automatic unit conversions."""
        self._apply_unit_conversions = False
        return self

    def skip_derived_fields(self) -> "LocationDataBuilder":
        """Skip calculation of derived fields like angstrom exponent."""
        self._calculate_derived_fields = False
        return self

    def build(self) -> LocationInputData:
        """Build the LocationInputData with all specified filters and processing."""
        return self.reader._build_location_data(
            self.latitude,
            self.longitude,
            self.start_date,
            self.end_date,
            self.forecasting_day,
            self._apply_unit_conversions,
            self._calculate_derived_fields,
        )


class InputData:
    """Improved InputData class with fluent API and separation of concerns."""

    def __init__(self, path: str):
        self.path = path

    def _apply_filters(self, lf: pl.LazyFrame, filters: dict) -> pl.LazyFrame:
        for key, value in filters.items():
            if isinstance(value, list):
                lf = lf.filter(pl.col(key).is_in(value))
            else:
                lf = lf.filter(pl.col(key) == value)
        return lf

    def _read_csv(self, filename: str, filters: dict) -> pl.DataFrame:
        file_path = os.path.join(self.path, filename)
        lf = pl.scan_csv(file_path)
        lf = self._apply_filters(lf, filters)
        return lf.collect()

    def _read_parquet(self, filename: str, filters: dict) -> pl.DataFrame:
        file_path = os.path.join(self.path, filename)
        lf = pl.scan_parquet(file_path)
        lf = self._apply_filters(lf, filters)
        return lf.collect()

    def _read(self, filename: str, filters: dict) -> pl.DataFrame:
        if filename.endswith(".csv"):
            return self._read_csv(filename, filters)
        elif filename.endswith(".parquet"):
            return self._read_parquet(filename, filters)
        else:
            raise ValueError(f"Unsupported file format for file: {filename}")

    def read_usinas(self, ids_usinas: list = None) -> pl.DataFrame:
        if ids_usinas is None:
            return self._read("usinas.csv", {})
        return self._read("usinas.csv", {"id_usina": ids_usinas})

    def _find_nearest_point(
        self,
        target_lat: float,
        target_lon: float,
        reference_file: str = "albedo.parquet",
    ) -> tuple[float, float]:
        """Find the nearest grid point to target coordinates."""
        file_path = os.path.join(self.path, reference_file)
        df = pl.read_parquet(file_path)

        # Get unique coordinate pairs
        coords = df.select(["latitude", "longitude"]).unique()

        # Calculate distances to all points
        distances = []
        for row in coords.iter_rows():
            lat, lon = row
            dist = haversine_distance(target_lat, target_lon, lat, lon)
            distances.append((dist, lat, lon))

        # Find the closest point
        _, closest_lat, closest_lon = min(distances)
        return closest_lat, closest_lon

    def for_location(
        self, latitude: float, longitude: float
    ) -> LocationDataBuilder:
        """Create a LocationDataBuilder for the specified coordinates."""
        return LocationDataBuilder(self, latitude, longitude)

    def _build_location_data(
        self,
        latitude: float,
        longitude: float,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        forecasting_day: Optional[int] = None,
        apply_unit_conversions: bool = True,
        calculate_derived_fields: bool = True,
    ) -> LocationInputData:
        # Find nearest grid point
        grid_lat, grid_lon = self._find_nearest_point(latitude, longitude)
        cod_lat, cod_lon = self._find_nearest_point(
            latitude, longitude, "cod.parquet"
        )
        # Define the data fields mapping
        data_mapping = {
            "cod": "cod.parquet",
            "albedo": "albedo.parquet",
            "h2o": "h2o.parquet",
            "no2": "no2.parquet",
            "o3": "o3.parquet",
            "od550": "od550.parquet",
            "od670": "od670.parquet",
            "psurf": "psurf.parquet",
            "temp2m": "temp.parquet",
        }

        # Load and process each data field
        input_data = {}
        for field_name, filename in data_mapping.items():
            data = self._load_and_filter_field(
                filename,
                grid_lat if field_name != "cod" else cod_lat,
                grid_lon if field_name != "cod" else cod_lon,
                start_date,
                end_date,
                forecasting_day,
            )
            if data is not None:
                input_data[field_name] = data

        # Create LocationInputData instance
        location_data = LocationInputData(
            latitude=latitude,
            longitude=longitude,
            **input_data,
            time_range=(start_date, end_date),
            forecasting_day=forecasting_day,
        )

        # Apply post-processing steps
        if apply_unit_conversions:
            location_data.apply_unit_conversions()

        if calculate_derived_fields:
            location_data.calculate_derived_fields()

        # Upsample data to 10-minute intervals
        location_data = location_data.upsample_to_interval("10m")
        return location_data

    def _upsample(self, df: pl.DataFrame, interval: str) -> pl.DataFrame:
        return df.upsample(time_column="time", every=interval).fill_null(
            strategy="forward"
        )

    def _load_and_filter_field(
        self,
        filename: str,
        latitude: float,
        longitude: float,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        forecasting_day: Optional[int] = None,
    ) -> Optional[pl.DataFrame]:
        """Load and filter a single data field."""
        try:
            file_path = os.path.join(self.path, filename)
            if not os.path.exists(file_path):
                return None
            df = pl.read_parquet(file_path)
            # Filter by coordinates
            df = df.filter(
                (pl.col("latitude") == latitude)
                & (pl.col("longitude") == longitude)
            )

            if df.height == 0:
                return None

            # Apply time range filter if specified
            if start_date and end_date:
                time_col = "data_hora_previsao"
                df = df.with_columns(pl.col(time_col).cast(pl.Datetime))
                df = df.filter(
                    (pl.col(time_col) >= start_date)
                    & (pl.col(time_col) <= end_date)
                )

            # Apply forecasting day filter if specified
            if forecasting_day is not None:
                df = self.filter_forecasting_day(df, forecasting_day)

            return df

        except Exception as e:
            print(f"Warning: Could not load {self.path}/{filename}: {e}")
            return None

    def read_measured_for_plant(
        self,
        plant_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> pl.DataFrame:
        df = self._read("measured_irradiance.parquet", {"id_usina": plant_id})
        df = df.with_columns([
            pl.col("data_hora_observacao").cast(pl.Datetime),
        ])
        df = df.drop("id_usina")
        df = df.rename({"data_hora_observacao": "time"})
        df = df.filter(pl.col("time") >= start_date) if start_date else df
        df = df.filter(pl.col("time") <= end_date) if end_date else df
        df = df.upsample(time_column="time", every="10m").fill_null(
            strategy="forward"
        )
        return df

    @classmethod
    def filter_forecasting_day(
        cls, df: pl.DataFrame, forecasting_day: int
    ) -> pl.DataFrame:
        df = df.with_columns([
            pl.col("data_hora_previsao").cast(pl.Datetime),
            pl.col("data_hora_rodada").cast(pl.Datetime),
        ])

        dia_expr = (
            (
                pl.col("data_hora_previsao").cast(pl.Int64)
                - pl.col("data_hora_rodada").cast(pl.Int64)
            )
            / 1_000_000
        ) / 86400.0

        df = df.with_columns([
            dia_expr.floor().cast(pl.Int32).alias("dia_previsao")
        ])

        df = df.filter(pl.col("dia_previsao") == forecasting_day)
        df = df.drop(["dia_previsao", "data_hora_rodada"])
        df = df.rename({"data_hora_previsao": "time"})
        df = df.sort("time").unique(subset=["time"])
        return df


def read_plant_artifacts(config: Config) -> dict[str, PlantArtifact]:
    artifacts = {}
    for plant_id in config.plant_ids or []:
        with open(os.path.join(config.artifact, f"{plant_id}.json"), "r") as f:
            data = f.read()
            artifact_dict = pyjson5.decode(data)
            artifacts[plant_id] = PlantArtifact(
                parameters=artifact_dict["parameters"],
                metrics=artifact_dict["metrics"],
                radiation_type=artifact_dict["radiation_type"],
            )
    return artifacts
