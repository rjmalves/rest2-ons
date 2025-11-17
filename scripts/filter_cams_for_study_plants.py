from datetime import datetime

import pandas as pd
import xarray as xr

from app.readers.cams import CAMSData
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
    df = df.sort_values([
        "latitude",
        "longitude",
        "data_hora_rodada",
        "data_hora_previsao",
    ]).reset_index(drop=True)
    return df


cams = CAMSData.read_data(
    "data/cams",
    datetime(2024, 7, 31),
    datetime(2024, 8, 1),
    [0, 1, 2, 3, 4, 5],
    [-23.0, -2.0],
    [-53.0, -35.0],
)

plant_df = pd.read_csv("data/usinas.csv")

od550 = filter_data_to_study_plants(cams.od550, plant_df)
od550.to_parquet("od550.parquet")

od670 = filter_data_to_study_plants(cams.od670, plant_df)
od670.to_parquet("od670.parquet")

no2 = filter_data_to_study_plants(cams.no2, plant_df)
no2.to_parquet("no2.parquet")

o3 = filter_data_to_study_plants(cams.o3, plant_df)
o3.to_parquet("o3.parquet")

h2o = filter_data_to_study_plants(cams.h2o, plant_df)
h2o.to_parquet("h2o.parquet")

psurf = filter_data_to_study_plants(cams.psurf, plant_df)
psurf.to_parquet("psurf.parquet")

albedo = filter_data_to_study_plants(cams.albedo, plant_df)
albedo.to_parquet("albedo.parquet")

dni_cs = filter_data_to_study_plants(cams.dni_cs, plant_df)
dni_cs.to_parquet("dni_cs.parquet")

dni = filter_data_to_study_plants(cams.dni, plant_df)
dni.to_parquet("dni.parquet")

ghi_cs = filter_data_to_study_plants(cams.ghi_cs, plant_df)
ghi_cs.to_parquet("ghi_cs.parquet")

ghi = filter_data_to_study_plants(cams.ghi, plant_df)
ghi.to_parquet("ghi.parquet")
