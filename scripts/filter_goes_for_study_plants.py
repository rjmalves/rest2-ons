from datetime import datetime

import pandas as pd
import xarray as xr

from app.readers.goes import GOESData
from app.utils.utils import nearest_point


def filter_variable_for_nearest_point(
    data: xr.DataArray, lat: float, lon: float
) -> xr.DataArray:
    nearest_lat, nearest_lon = nearest_point(data, lat, lon)

    return data.sel(latitude=nearest_lat, longitude=nearest_lon)


def filter_data_to_study_plants(
    data: xr.DataArray, plant_df: pd.DataFrame
) -> xr.DataArray:
    dfs = []
    for _, row in plant_df.iterrows():
        df = filter_variable_for_nearest_point(
            data, row["latitude"], row["longitude"]
        ).to_dataframe(name="valor")
        dfs.append(df.reset_index())
    df = pd.concat(dfs, ignore_index=True)
    df["data_hora_rodada"] = df["data_hora_previsao"]
    df = df[
        [
            "data_hora_rodada",
            "data_hora_previsao",
            "latitude",
            "longitude",
            "valor",
        ]
    ]
    df = df.sort_values([
        "latitude",
        "longitude",
        "data_hora_rodada",
        "data_hora_previsao",
    ]).reset_index(drop=True)
    return df


goes = GOESData.read_data(
    "data/goes",
    datetime(2024, 7, 31),
    datetime(2024, 8, 1, 0, 20),
    [-23.0, -2.0],
    [-53.0, -35.0],
)

plant_df = pd.read_csv("data/usinas.csv")

cod = filter_data_to_study_plants(goes.cod, plant_df)
