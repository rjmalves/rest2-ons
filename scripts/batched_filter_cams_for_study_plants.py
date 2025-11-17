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


dates = pd.date_range("2023-06-01", "2924-09-01", freq="MS")
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
