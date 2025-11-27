import os
import pandas as pd
import xarray as xr
from datetime import datetime
import numpy as np


EARTH_RADIUS_KM = 6371.0

def haversine_distance(
    lat_array: float, lon_array: float, lat: float, lon: float
) -> float:
    R = EARTH_RADIUS_KM
    lat_array, lon_array, lat, lon = map(
        np.radians, [lat_array, lon_array, lat, lon]
    )  # Convert degrees to radians

    dlat = lat - lat_array
    dlon = lon - lon_array

    a = (
        np.sin(dlat / 2.0) ** 2
        + np.cos(lat_array) * np.cos(lat) * np.sin(dlon / 2.0) ** 2
    )
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    distance = R * c
    return distance



def nearest_point(data: xr.DataArray, lat: float, lon: float) -> float:
    points = np.array(
        data.stack(points=["latitude", "longitude"]).indexes["points"]
    )
    lat_array = [p[0] for p in points]
    lon_array = [p[1] for p in points]
    distances = haversine_distance(lat_array, lon_array, lat, lon)
    index = np.argmin(distances)
    return lat_array[index], lon_array[index]



class CAMSData:
    def __init__(
        self,
        od550: xr.DataArray,
        od670: xr.DataArray,
        no2: xr.DataArray,
        o3: xr.DataArray,
        h2o: xr.DataArray,
        psurf: xr.DataArray,
        albedo: xr.DataArray,
        dni_cs: xr.DataArray,
        dni: xr.DataArray,
        ghi_cs: xr.DataArray,
        ghi: xr.DataArray,
        angstrom_exponent: xr.DataArray | None = None,
    ):
        self.od550 = od550
        self.od670 = od670
        self.no2 = no2
        self.o3 = o3
        self.h2o = h2o
        self.psurf = psurf
        self.albedo = albedo
        self.dni_cs = dni_cs
        self.dni = dni
        self.ghi_cs = ghi_cs
        self.ghi = ghi
        self.angstrom_exponent = angstrom_exponent

    @staticmethod
    def read_data(
        data_root: str,
        start_date: datetime,
        end_date: datetime,
        forecasting_days: list[int],
        lat_bounds: list,
        lon_bounds: list,
    ) -> "CAMSData":
        instance = CAMSData.read_variables(
            data_root,
            start_date,
            end_date,
            forecasting_days,
            lat_bounds,
            lon_bounds,
        )
        instance.convert_units()
        instance.angstrom_exponent = -1 * (
            (np.log(instance.od550 / instance.od670)) / (np.log(550.0 / 670.0))
        )  # Angstrom coeff - https://en.wikipedia.org/wiki/Angstrom_exponent
        return instance

    @staticmethod
    def read_variables(
        data_root: str,
        start_date: datetime,
        end_date: datetime,
        forecasting_days: list[int],
        lat_bounds: list,
        lon_bounds: list,
    ) -> "CAMSData":
        od550 = CAMSData.read_variable(
            data_root,
            "optical_depth_550nm",
            start_date,
            end_date,
            forecasting_days,
            lat_bounds,
            lon_bounds,
        )
        od670 = CAMSData.read_variable(
            data_root,
            "optical_depth_670nm",
            start_date,
            end_date,
            forecasting_days,
            lat_bounds,
            lon_bounds,
        )
        no2 = CAMSData.read_variable(
            data_root,
            "nitrogen_dioxide",
            start_date,
            end_date,
            forecasting_days,
            lat_bounds,
            lon_bounds,
        )
        o3 = CAMSData.read_variable(
            data_root,
            "ozone",
            start_date,
            end_date,
            forecasting_days,
            lat_bounds,
            lon_bounds,
        )
        h2o = CAMSData.read_variable(
            data_root,
            "water_vapour",
            start_date,
            end_date,
            forecasting_days,
            lat_bounds,
            lon_bounds,
        )
        psurf = CAMSData.read_variable(
            data_root,
            "surface_pressure",
            start_date,
            end_date,
            forecasting_days,
            lat_bounds,
            lon_bounds,
        )
        albedo = CAMSData.read_variable(
            data_root,
            "albedo",
            start_date,
            end_date,
            forecasting_days,
            lat_bounds,
            lon_bounds,
        )
        dni_cs = CAMSData.read_variable(
            data_root,
            "dni_clear_sky",
            start_date,
            end_date,
            forecasting_days,
            lat_bounds,
            lon_bounds,
        )
        dni = CAMSData.read_variable(
            data_root,
            "dni",
            start_date,
            end_date,
            forecasting_days,
            lat_bounds,
            lon_bounds,
        )
        ghi_cs = CAMSData.read_variable(
            data_root,
            "ghi_clear_sky",
            start_date,
            end_date,
            forecasting_days,
            lat_bounds,
            lon_bounds,
        )
        ghi = CAMSData.read_variable(
            data_root,
            "ghi",
            start_date,
            end_date,
            forecasting_days,
            lat_bounds,
            lon_bounds,
        )

        return CAMSData(
            od550=od550,
            od670=od670,
            no2=no2,
            o3=o3,
            h2o=h2o,
            psurf=psurf,
            albedo=albedo,
            dni_cs=dni_cs,
            dni=dni,
            ghi_cs=ghi_cs,
            ghi=ghi,
        )

    @staticmethod
    def read_variable_file(
        root_path: str,
        variable: str,
        date: datetime,
        forecasting_days: list[int],
        lat_bounds: list,
        lon_bounds: list,
    ) -> pd.DataFrame:
        df = pd.read_parquet(
            os.path.join(
                root_path, variable, date.strftime("%Y%m%d-%H.parquet")
            ),
            filters=[
                ("latitude", ">=", lat_bounds[0]),
                ("latitude", "<=", lat_bounds[1]),
                ("longitude", ">=", lon_bounds[0]),
                ("longitude", "<=", lon_bounds[1]),
            ],
        )
        df["data_hora_rodada"] = date
        df["data_hora_previsao"] = df["data_hora_previsao"].dt.tz_convert("UTC")
        df["data_hora_previsao"] = df["data_hora_previsao"].dt.tz_convert(None)
        df["dia_previsao"] = np.floor(
            (df["data_hora_previsao"] - date).dt.total_seconds() / 86400.0
        )
        df = df.loc[df["dia_previsao"].isin(forecasting_days)]
        df = df.astype({"dia_previsao": "int32"})
        return df

    @staticmethod
    def read_variable(
        root_path: str,
        variable: str,
        start_date: datetime,
        end_date: datetime,
        forecasting_days: list[int],
        lat_bounds: list,
        lon_bounds: list,
    ) -> xr.DataArray:
        dfs = []
        for date in pd.date_range(start_date, end_date, freq="1D"):
            df = CAMSData.read_variable_file(
                root_path,
                variable,
                date,
                forecasting_days,
                lat_bounds,
                lon_bounds,
            )
            dfs.append(df)
        df = pd.concat(dfs, ignore_index=True)
        df = df.drop(columns=["dia_previsao"])
        index_cols = [
            "latitude",
            "longitude",
            "data_hora_rodada",
            "data_hora_previsao",
        ]

        value_col = [c for c in df.columns if c not in index_cols][0]
        return df.set_index(index_cols).to_xarray()[value_col]


def filter_variable_for_nearest_point(
    data: xr.DataArray, lat: float, lon: float
) -> xr.DataArray:
    nearest_lat, nearest_lon = nearest_point(data, lat, lon)

    return data.sel(latitude=nearest_lat, longitude=nearest_lon)


def filter_data_to_study_plants(
    data: xr.DataArray, plant_df: pd.DataFrame
) -> pd.DataFrame:
    dfs = []
    for _, row in plant_df.iterrows():
        df = filter_variable_for_nearest_point(
            data, row["latitude"], row["longitude"]
        ).to_dataframe(name="valor")
        dfs.append(df.reset_index())
    df = pd.concat(dfs, ignore_index=True)
    df = df.sort_values([
        "latitude",
        "longitude",
        "data_hora_rodada",
        "data_hora_previsao",
    ]).reset_index(drop=True)
    return df


dates = pd.date_range("2023-06-01", "2024-09-01", freq="MS")
plant_df = pd.read_csv("data/usinas.csv")

for d_ini, d_fin in zip(dates[:-1], dates[1:]):
    cams = CAMSData.read_data(
        "data/cams",
        d_ini,
        d_fin,
        [0, 1, 2, 3, 4, 5],
        [-23.0, -2.0],
        [-53.0, -35.0],
    )

    d_ini_str = d_ini.strftime("%Y-%m-%d")
    d_fin_str = d_fin.strftime("%Y-%m-%d")

    od550 = filter_data_to_study_plants(cams.od550, plant_df)
    od550.to_parquet(f"od550_{d_ini_str}_{d_fin_str}.parquet")

    od670 = filter_data_to_study_plants(cams.od670, plant_df)
    od670.to_parquet(f"od670_{d_ini_str}_{d_fin_str}.parquet")

    no2 = filter_data_to_study_plants(cams.no2, plant_df)
    no2.to_parquet(f"no2_{d_ini_str}_{d_fin_str}.parquet")

    o3 = filter_data_to_study_plants(cams.o3, plant_df)
    o3.to_parquet(f"o3_{d_ini_str}_{d_fin_str}.parquet")

    h2o = filter_data_to_study_plants(cams.h2o, plant_df)
    h2o.to_parquet(f"h2o_{d_ini_str}_{d_fin_str}.parquet")

    psurf = filter_data_to_study_plants(cams.psurf, plant_df)
    psurf.to_parquet(f"psurf_{d_ini_str}_{d_fin_str}.parquet")

    albedo = filter_data_to_study_plants(cams.albedo, plant_df)
    albedo.to_parquet(f"albedo_{d_ini_str}_{d_fin_str}.parquet")

    dni_cs = filter_data_to_study_plants(cams.dni_cs, plant_df)
    dni_cs.to_parquet(f"dni_cs_{d_ini_str}_{d_fin_str}.parquet")

    dni = filter_data_to_study_plants(cams.dni, plant_df)
    dni.to_parquet(f"dni_{d_ini_str}_{d_fin_str}.parquet")

    ghi_cs = filter_data_to_study_plants(cams.ghi_cs, plant_df)
    ghi_cs.to_parquet(f"ghi_cs_{d_ini_str}_{d_fin_str}.parquet")

    ghi = filter_data_to_study_plants(cams.ghi, plant_df)
    ghi.to_parquet(f"ghi_{d_ini_str}_{d_fin_str}.parquet")
