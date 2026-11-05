import io
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import numpy as np
import polars as pl
from nwp_core.config import TimeWindow
from nwp_core.storage import Storage
from pydantic import ValidationError

from rest2_ons._errors import ArtifactFormatError
from rest2_ons._keys import artifact_key
from rest2_ons.input_contract import GridMismatchError, validate_input_units
from rest2_ons.utils.data import PlantArtifact
from rest2_ons.utils.utils import haversine_distance

FORECAST_FILES = {
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


def _naive_utc(bound: datetime) -> datetime:
    """``bound`` as the naive UTC datetime every frame here is stamped in.

    Convert with ``astimezone`` first: ``replace(tzinfo=None)`` alone keeps
    the wall time of a non-UTC bound. Polars raises ``SchemaError`` when a
    naive column is compared with an aware literal.
    """
    if bound.utcoffset() is None:
        raise ValueError("window bounds must be timezone-aware")
    return bound.astimezone(UTC).replace(tzinfo=None)


@dataclass
class LocationInputData:
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
    angstrom_exponent: pl.DataFrame | None = None

    # Metadata
    time_range: tuple[datetime, datetime] | None = None
    forecasting_day: int | None = None

    def apply_unit_conversions(self) -> "LocationInputData":
        self.o3 = self.o3.with_columns(
            pl.col("valor") * 46.73
        )  # kg/m2 -> atm-cm:
        # ro_o3 = 2.14kg/m3 => o3[kg/m2]/ro_o3 * 100 (m->cm) = 46.73
        self.h2o = self.h2o.with_columns(
            pl.col("valor") * 0.1
        )  # kg/m2 -> atm-cm:
        # ro_h2o = 1000 kg/m3 => h2o[kg/m2]/ro_h2o * 100 (m->cm) = 0.1
        self.no2 = self.no2.with_columns(
            pl.col("valor") * 48.78
        )  # kg/m2 -> atm-cm:
        # ro_no2 = 2.05kg/m3 => no2[kg/m2]/ro_no2 * 100 (m->cm) = 48.78

        return self

    def calculate_derived_fields(self) -> "LocationInputData":
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
        self.angstrom_exponent = pl.DataFrame(
            {
                "time": self.od550["time"],
                "valor": angstrom_exponent,
            }
        )

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


class LocationDataBuilder:
    def __init__(self, reader: "InputData", latitude: float, longitude: float):
        self.reader = reader
        self.latitude = latitude
        self.longitude = longitude
        self.start_date: datetime | None = None
        self.end_date: datetime | None = None
        self.forecasting_day: int | None = None

    def time_range(self, window: TimeWindow) -> "LocationDataBuilder":
        self.start_date = _naive_utc(window.start)
        self.end_date = _naive_utc(window.end)
        return self

    def forecasting_day_filter(self, day: int) -> "LocationDataBuilder":
        self.forecasting_day = day
        return self

    def build(self) -> LocationInputData:
        return self.reader._build_location_data(
            self.latitude,
            self.longitude,
            self.start_date,
            self.end_date,
            self.forecasting_day,
        )


class InputData:
    def __init__(self, storage: Storage):
        self.storage = storage

    def _read_bytes(self, key: str) -> bytes:
        with self.storage.open_read(key) as stream:
            return stream.read()

    def _apply_filters(
        self, df: pl.DataFrame, filters: dict[str, Any]
    ) -> pl.DataFrame:
        for key, value in filters.items():
            if isinstance(value, list):
                df = df.filter(pl.col(key).is_in(value))
            else:
                df = df.filter(pl.col(key) == value)
        return df

    def _read_csv(self, filename: str, filters: dict[str, Any]) -> pl.DataFrame:
        df = pl.read_csv(io.BytesIO(self._read_bytes(filename)))
        return self._apply_filters(df, filters)

    def _read_parquet(
        self, filename: str, filters: dict[str, Any]
    ) -> pl.DataFrame:
        df = pl.read_parquet(io.BytesIO(self._read_bytes(filename)))
        return self._apply_filters(df, filters)

    def _read(self, filename: str, filters: dict[str, Any]) -> pl.DataFrame:
        if filename.endswith(".csv"):
            return self._read_csv(filename, filters)
        if filename.endswith(".parquet"):
            return self._read_parquet(filename, filters)
        raise ValueError(f"Unsupported file format for file: {filename}")

    def read_usinas(self, ids_usinas: list[str] | None = None) -> pl.DataFrame:
        if ids_usinas is None:
            return self._read("usinas.csv", {})
        return self._read("usinas.csv", {"id_usina": ids_usinas})

    def plant_ids(self, selected: list[str] | None) -> list[str]:
        """``selected`` as given, or every ``id_usina`` in usinas.csv if None.

        A given list is not filtered against usinas.csv, so an unknown id
        still fails where its coordinates are looked up.
        """
        if selected is not None:
            return selected
        return self.read_usinas()["id_usina"].to_list()

    def _find_nearest_point(
        self,
        target_lat: float,
        target_lon: float,
        reference_file: str = "albedo.parquet",
    ) -> tuple[float, float]:
        """Find the nearest grid point to target coordinates."""
        df = self._read_parquet(reference_file, {})
        coords = df.select(["latitude", "longitude"]).unique()
        distances = [
            (haversine_distance(target_lat, target_lon, lat, lon), lat, lon)
            for lat, lon in coords.iter_rows()
        ]
        _, closest_lat, closest_lon = min(distances)
        return closest_lat, closest_lon

    def for_location(
        self, latitude: float, longitude: float
    ) -> LocationDataBuilder:
        return LocationDataBuilder(self, latitude, longitude)

    def _build_location_data(
        self,
        latitude: float,
        longitude: float,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        forecasting_day: int | None = None,
    ) -> LocationInputData:
        missing = [
            filename
            for filename in FORECAST_FILES.values()
            if self.storage.stat(filename) is None
        ]
        if missing:
            raise FileNotFoundError(
                f"missing input files: {', '.join(missing)}"
            )

        grid_lat, grid_lon = self._find_nearest_point(latitude, longitude)
        cod_lat, cod_lon = self._find_nearest_point(
            latitude, longitude, "cod.parquet"
        )
        input_data = {
            field_name: self._load_and_filter_field(
                field_name,
                filename,
                grid_lat if field_name != "cod" else cod_lat,
                grid_lon if field_name != "cod" else cod_lon,
                start_date,
                end_date,
                forecasting_day,
            )
            for field_name, filename in FORECAST_FILES.items()
        }

        location_data = LocationInputData(
            latitude=latitude,
            longitude=longitude,
            **input_data,
            time_range=(start_date, end_date)
            if start_date and end_date
            else None,
            forecasting_day=forecasting_day,
        )

        location_data.apply_unit_conversions()
        location_data.calculate_derived_fields()

        return location_data.upsample_to_interval("10m")

    def _load_and_filter_field(
        self,
        input_name: str,
        filename: str,
        latitude: float,
        longitude: float,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        forecasting_day: int | None = None,
    ) -> pl.DataFrame:
        df = self._read_parquet(filename, {})
        validate_input_units(input_name, df["valor"])
        df = df.filter(
            (pl.col("latitude") == latitude)
            & (pl.col("longitude") == longitude)
        )
        if df.height == 0:
            raise GridMismatchError(
                f"{filename} has no rows at grid point ({latitude}, "
                f"{longitude}); every CAMS file must share the grid of "
                f"albedo.parquet"
            )

        if start_date and end_date:
            time_col = "data_hora_previsao"
            df = df.with_columns(pl.col(time_col).cast(pl.Datetime))
            df = df.filter(
                (pl.col(time_col) >= start_date) & (pl.col(time_col) < end_date)
            )

        if forecasting_day is not None:
            df = self.filter_forecasting_day(df, forecasting_day)

        return df

    def read_measured_for_plant(
        self, plant_id: str, window: TimeWindow
    ) -> pl.DataFrame:
        df = self._read("measured_irradiance.parquet", {"id_usina": plant_id})
        df = df.with_columns(pl.col("data_hora_observacao").cast(pl.Datetime))
        df = df.drop("id_usina")
        df = df.rename({"data_hora_observacao": "time"})
        df = df.filter(
            (pl.col("time") >= _naive_utc(window.start))
            & (pl.col("time") < _naive_utc(window.end))
        )
        df = df.upsample(time_column="time", every="10m").fill_null(
            strategy="forward"
        )
        return df

    @classmethod
    def filter_forecasting_day(
        cls, df: pl.DataFrame, forecasting_day: int
    ) -> pl.DataFrame:
        """Rows ``forecasting_day`` whole days of lead time from their run.

        Several runs can forecast one valid time within that day; the latest
        run is kept, never the first row in file order.
        """
        df = df.with_columns(
            [
                pl.col("data_hora_previsao").cast(pl.Datetime),
                pl.col("data_hora_rodada").cast(pl.Datetime),
            ]
        )

        dia_expr = (
            (
                pl.col("data_hora_previsao").cast(pl.Int64)
                - pl.col("data_hora_rodada").cast(pl.Int64)
            )
            / 1_000_000
        ) / 86400.0

        df = df.with_columns(
            [dia_expr.floor().cast(pl.Int32).alias("dia_previsao")]
        )

        return (
            df.filter(pl.col("dia_previsao") == forecasting_day)
            .rename({"data_hora_previsao": "time"})
            .sort("time", "data_hora_rodada")
            .unique(subset="time", keep="last", maintain_order=True)
            .drop("dia_previsao", "data_hora_rodada")
        )


def read_plant_artifact(storage: Storage, plant_id: str) -> PlantArtifact:
    """Read the artifact of ``plant_id``.

    Raises:
        ArtifactFormatError: the stored bytes are not a valid artifact; the
            message names the key and never the bytes.
    """
    key = artifact_key(plant_id)
    with storage.open_read(key) as stream:
        data = stream.read()
    try:
        return PlantArtifact.model_validate(json.loads(data))
    except (json.JSONDecodeError, UnicodeDecodeError, ValidationError):
        raise ArtifactFormatError(
            f"artifact {key} is not a valid rest2 artifact"
        ) from None
