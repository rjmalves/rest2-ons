import os

import polars as pl

files = os.listdir(".")
files.sort()
groups = {
    "albedo_2": "albedo",
    "dni_2": "dni",
    "dni_cs_2": "dni_cs",
    "ghi_2": "ghi",
    "ghi_cs_2": "ghi_cs",
    "h2o_2": "h2o",
    "no2_2": "no2",
    "o3_2": "o3",
    "od550_2": "od550",
    "od670_2": "od670",
    "psurf_2": "psurf",
}

for prefix, group in groups.items():
    group_dir = "processed"

    os.makedirs(group_dir, exist_ok=True)

    group_files = [g for g in files if g.startswith(prefix)]
    dfs = [pl.read_parquet(f) for f in group_files]
    df = pl.concat(dfs)

    df.write_parquet(os.path.join(group_dir, f"{group}.parquet"))
