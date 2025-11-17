import os
from datetime import datetime

import pandas as pd
import pytz
import requests
import xarray as xr
from dotenv import load_dotenv

load_dotenv(override=True)


class MeasuredData:
    def __init__(self, plant_id: str, start_date: datetime, end_date: datetime):
        self.plant_id = plant_id
        self.data = self._load_data(start_date, end_date)

    def _make_url_params(
        self, start_date: datetime, end_date: datetime
    ) -> dict:
        params = {
            "tagPI": f"{self.plant_id}_{os.getenv('TAG_PI')}",
            "dataInicio": start_date.strftime("%Y-%m-%d %H:%M:%S"),
            "dataFim": end_date.strftime("%Y-%m-%d %H:%M:%S"),
            "funcao": "AVG",
            "discretizacao": "M",
            "intervalosDiscretizacao": "10",
            "alocacaoTemporal": "INI",
            "UTC": "true",
        }
        return params

    def _filter_valid_data(self, data: xr.DataArray) -> xr.DataArray:
        return data.where(data >= 0)

    def _load_data(
        self, start_date: datetime, end_date: datetime
    ) -> xr.DataArray:
        res = requests.get(
            os.getenv("PI_API"),
            params=self._make_url_params(start_date, end_date),
            headers={"Accept": "application/json"},
        )
        res_data = res.json()
        times = [
            datetime.strptime(
                res_data[i]["Instante"], "%Y-%m-%dT%H:%M:%S+00:00"
            ).replace(tzinfo=pytz.UTC)
            for i in range(len(res_data))
        ]
        values = [res_data[i]["Valor"] for i in range(len(res_data))]
        df = pd.DataFrame(data={"time": times, "value": values})
        df["time"] = df["time"].dt.tz_convert(None)
        data = df.set_index(["time"]).to_xarray()["value"]
        data = self._filter_valid_data(data)
        return data


plant_df = pd.read_csv("data/usinas.csv")

dfs = []
for plant_id in plant_df["id_usina"].unique()[0:1]:
    print(f"Processing plant {plant_id}...")

    try:
        measured = MeasuredData(
            plant_id,
            datetime(2023, 5, 31, 21, 0, 0),
            datetime(2024, 9, 5, 21, 0, 0),
        )
        df = measured.data.to_dataframe("valor").reset_index()
        df = df.rename(columns={"time": "data_hora_observacao"})
        df["id_usina"] = plant_id
        df = df[["id_usina", "data_hora_observacao", "valor"]]
        dfs.append(df)
    except Exception as e:
        print(f"Error processing plant {plant_id}: {e}")


df = pd.concat(dfs, ignore_index=True)
df.to_parquet("data/measured_irradiance.parquet")
