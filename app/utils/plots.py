import pandas as pd
import plotly.express as px  # type: ignore[import-untyped]
import plotly.graph_objects as go  # type: ignore[import-untyped]
import plotly.io as pio  # type: ignore[import-untyped]
import polars as pl
from plotly.subplots import make_subplots  # type: ignore[import-untyped]

from app.inference import PlantResult as PlantInferenceResult
from app.internal.constants import (
    COD_COLOR,
    DHI_COLOR,
    DNI_COLOR,
    GHI_COLOR,
    GHI_TRACKER_COLOR,
    INFERENCE_COLOR,
    MEASURED_COLOR,
    TEST_COLOR,
    TRAIN_COLOR,
    VALIDATION_COLOR,
)
from app.train import PlantResult as PlantTrainResult

pio.templates.default = "plotly_white"


IRRADIANCE_COLUMNS = ["ghi", "dni", "dhi", "ghi_tracker"]


def _plant_train_result_with_irradiances_to_df(
    result: PlantTrainResult,
) -> pd.DataFrame:
    final_df: pd.DataFrame | None = None
    for radiation_type in IRRADIANCE_COLUMNS:
        df = result.train.radiation.get(radiation_type).to_pandas()
        df["step"] = "train"
        if result.validation is not None:
            df_val = result.validation.radiation.get(radiation_type).to_pandas()
            df_val["step"] = "validation"
            df = pd.concat([df, df_val], ignore_index=True)
        if result.testing is not None:
            df_test = result.testing.radiation.get(radiation_type).to_pandas()
            df_test["step"] = "test"
            df = pd.concat([df, df_test], ignore_index=True)
        df = df.rename(columns={"valor": radiation_type})
        if final_df is None:
            final_df = df
        else:
            final_df = pd.merge(
                final_df, df.drop(columns=["step"]), on=["time"], how="inner"
            )
    if final_df is None:
        raise ValueError("No radiation data found")
    return final_df


def _plant_inference_result_with_irradiances_to_df(
    result: PlantInferenceResult,
) -> pd.DataFrame:
    final_df: pd.DataFrame | None = None
    for radiation_type in IRRADIANCE_COLUMNS:
        df = result.radiation.get(radiation_type).to_pandas()
        df["step"] = "inference"
        df = df.rename(columns={"valor": radiation_type})
        if final_df is None:
            final_df = df
        else:
            final_df = pd.merge(
                final_df, df.drop(columns=["step"]), on=["time"], how="inner"
            )
    if final_df is None:
        raise ValueError("No radiation data found")
    return final_df


def _join_predictions_with_measured_and_cod(
    predictions: pd.DataFrame, measured: pd.DataFrame | None, cod: pd.DataFrame
) -> pd.DataFrame:
    if "valor" in predictions.columns:
        predictions = predictions.rename(columns={"valor": "predicted"})
    if measured is not None and "valor" in measured.columns:
        measured = measured.rename(columns={"valor": "measured"})
    if "valor" in cod.columns:
        cod = cod.rename(columns={"valor": "cod"})
    df = pd.merge(
        predictions,
        cod,
        on="time",
        how="inner",
    )
    if measured is not None:
        df = pd.merge(
            df,
            measured,
            on="time",
            how="inner",
        )
    return df


def rest2_train_steps_scatter_plot(
    df: pd.DataFrame, target_column: str, filepath: str
) -> go.Figure:
    fig = px.scatter(
        df,
        x="measured",
        y=target_column,
        color="step",
        trendline="ols",
        color_discrete_map={
            "train": TRAIN_COLOR,
            "validation": VALIDATION_COLOR,
            "test": TEST_COLOR,
            "inference": INFERENCE_COLOR,
        },
        labels={
            "measured": "Measured",
            "predicted": "Predicted",
            "train": "Train",
            "validation": "Validation",
            "test": "Test",
            "inference": "Inference",
        },
        title="Predicted vs Measured Data",
    )
    fig.update_traces(marker={"size": 5})
    fig.update_layout(xaxis_title="Measured Data", yaxis_title="Predicted Data")
    fig.update_layout(grid={"rows": 1, "columns": 1})
    fig.update_layout(legend_title_text="Step")
    fig.update_layout(
        legend={"x": 0.01, "y": 0.99, "bgcolor": "rgba(255, 255, 255, 0.8)"}
    )
    fig.update_xaxes(range=[0, df["measured"].max() * 1.05])
    fig.update_yaxes(range=[0, df["measured"].max() * 1.05])
    fig.write_html(filepath)
    return fig


def rest2_train_irradiances_scatter_plot(
    df: pd.DataFrame, target_column: str, filepath: str
) -> go.Figure:
    fig = px.scatter(
        df,
        x="measured",
        y=IRRADIANCE_COLUMNS,
        trendline="ols",
        color_discrete_map={
            "ghi": GHI_COLOR,
            "dni": DNI_COLOR,
            "dhi": DHI_COLOR,
            "ghi_tracker": GHI_TRACKER_COLOR,
        },
        labels={
            "ghi": "GHI (target)" if target_column == "ghi" else "GHI",
            "dni": "DNI (target)" if target_column == "dni" else "DNI",
            "dhi": "DHI (target)" if target_column == "dhi" else "DHI",
            "ghi_tracker": "GHI Tracker (target)"
            if target_column == "ghi_tracker"
            else "GHI Tracker",
            "measured": "Measured",
        },
        title="Predicted Irradiances vs Measured Data",
    )
    fig.update_traces(marker={"size": 5})
    fig.update_layout(xaxis_title="Measured Data", yaxis_title="Predicted Data")
    fig.update_layout(grid={"rows": 1, "columns": 1})
    fig.update_layout(legend_title_text="Irradiance")
    fig.update_layout(
        legend={"x": 0.01, "y": 0.99, "bgcolor": "rgba(255, 255, 255, 0.8)"}
    )
    fig.update_xaxes(range=[0, df["measured"].max() * 1.05])
    fig.update_yaxes(range=[0, df["measured"].max() * 1.05])
    fig.write_html(filepath)
    return fig


def rest2_train_timeseries_plot(
    df: pd.DataFrame,
    target_column: str,
    filepath: str,
):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=df.loc[df["step"] == "train", "time"],
            y=df.loc[df["step"] == "train", target_column],
            name="Train",
            mode="lines",
            line={"width": 2, "color": TRAIN_COLOR},
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df.loc[df["step"] == "validation", "time"],
            y=df.loc[df["step"] == "validation", target_column],
            name="Validation",
            mode="lines",
            line={"width": 2, "color": VALIDATION_COLOR},
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df.loc[df["step"] == "test", "time"],
            y=df.loc[df["step"] == "test", target_column],
            name="Test",
            mode="lines",
            line={"width": 2, "color": TEST_COLOR},
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=df["measured"],
            name="Measured",
            mode="lines",
            line={"width": 2, "color": MEASURED_COLOR},
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            x=df["time"],
            y=df["cod"],
            name="COD",
            marker_color=COD_COLOR,
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title="REST2 and Measured Data",
        xaxis_title="Time (UTC)",
        yaxis_title="Irradiance (W/m²)",
        legend_title_text="Step",
    )
    fig.update_yaxes(
        title_text="Irradiance (W/m²)",
        secondary_y=False,
        range=[0, df["measured"].max() * 1.05],
    )
    fig.update_yaxes(title_text="COD", secondary_y=True, autorange="reversed")
    fig.update_layout(
        legend={
            "orientation": "h",
            "x": 0.5,
            "y": -0.2,
            "xanchor": "center",
            "bgcolor": "rgba(255, 255, 255, 0.8)",
        }
    )
    fig.update_layout(
        grid={"rows": 1, "columns": 1},
    )
    fig.update_xaxes(
        dtick="H1",
        tickformat="%Y-%m-%d %H:%M",
        tickangle=-45,
    )
    fig.write_html(filepath)
    return fig


def rest2_train_steps_timeseries_plot(
    df: pd.DataFrame,
    target_column: str,
    filepath: str,
):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=df.loc[df["step"] == "train", "time"],
            y=df.loc[df["step"] == "train", target_column],
            name="Train",
            mode="lines",
            line={"width": 2, "color": TRAIN_COLOR},
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df.loc[df["step"] == "validation", "time"],
            y=df.loc[df["step"] == "validation", target_column],
            name="Validation",
            mode="lines",
            line={"width": 2, "color": VALIDATION_COLOR},
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df.loc[df["step"] == "test", "time"],
            y=df.loc[df["step"] == "test", target_column],
            name="Test",
            mode="lines",
            line={"width": 2, "color": TEST_COLOR},
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=df["measured"],
            name="Measured",
            mode="lines",
            line={"width": 2, "color": MEASURED_COLOR},
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            x=df["time"],
            y=df["cod"],
            name="COD",
            marker_color=COD_COLOR,
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title="REST2 and Measured Data",
        xaxis_title="Time (UTC)",
        yaxis_title="Irradiance (W/m²)",
        legend_title_text="Step",
    )
    fig.update_yaxes(
        title_text="Irradiance (W/m²)",
        secondary_y=False,
        range=[0, df["measured"].max() * 1.05],
    )
    fig.update_yaxes(title_text="COD", secondary_y=True, autorange="reversed")
    fig.update_layout(
        legend={
            "orientation": "h",
            "x": 0.5,
            "y": -0.2,
            "xanchor": "center",
            "bgcolor": "rgba(255, 255, 255, 0.8)",
        }
    )
    fig.update_layout(
        grid={"rows": 1, "columns": 1},
    )
    fig.update_xaxes(
        dtick="H1",
        tickformat="%Y-%m-%d %H:%M",
        tickangle=-45,
    )
    fig.write_html(filepath)
    return fig


def rest2_train_irradiances_timeseries_plot(
    df: pd.DataFrame,
    target_column: str,
    filepath: str,
):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=df["ghi"],
            name="GHI (target)" if target_column == "ghi" else "GHI",
            mode="lines",
            line={"width": 2, "color": GHI_COLOR},
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=df["dni"],
            name="DNI (target)" if target_column == "dni" else "DNI",
            mode="lines",
            line={"width": 2, "color": DNI_COLOR},
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=df["dhi"],
            name="DHI (target)" if target_column == "dhi" else "DHI",
            mode="lines",
            line={"width": 2, "color": DHI_COLOR},
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=df["ghi_tracker"],
            name="GHI Tracker (target)"
            if target_column == "ghi_tracker"
            else "GHI Tracker",
            mode="lines",
            line={"width": 2, "color": GHI_TRACKER_COLOR},
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=df["measured"],
            name="Measured",
            mode="lines",
            line={"width": 2, "color": MEASURED_COLOR},
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            x=df["time"],
            y=df["cod"],
            name="COD",
            marker_color=COD_COLOR,
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title="REST2 Irradiances and Measured Data",
        xaxis_title="Time (UTC)",
        yaxis_title="Irradiance (W/m²)",
        legend_title_text="Step",
    )
    fig.update_yaxes(
        title_text="Irradiance (W/m²)",
        secondary_y=False,
        range=[0, df["measured"].max() * 1.05],
    )
    fig.update_yaxes(title_text="COD", secondary_y=True, autorange="reversed")
    fig.update_layout(
        legend={
            "orientation": "h",
            "x": 0.5,
            "y": -0.2,
            "xanchor": "center",
            "bgcolor": "rgba(255, 255, 255, 0.8)",
        }
    )
    fig.update_layout(
        grid={"rows": 1, "columns": 1},
    )
    fig.update_xaxes(
        dtick="H1",
        tickformat="%Y-%m-%d %H:%M",
        tickangle=-45,
    )
    fig.write_html(filepath)
    return fig


def rest2_inference_irradiances_timeseries_plot(
    df: pd.DataFrame,
    target_column: str,
    filepath: str,
):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=df["ghi"],
            name="GHI (target)" if target_column == "ghi" else "GHI",
            mode="lines",
            line={"width": 2, "color": GHI_COLOR},
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=df["dni"],
            name="DNI (target)" if target_column == "dni" else "DNI",
            mode="lines",
            line={"width": 2, "color": DNI_COLOR},
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=df["dhi"],
            name="DHI (target)" if target_column == "dhi" else "DHI",
            mode="lines",
            line={"width": 2, "color": DHI_COLOR},
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=df["ghi_tracker"],
            name="GHI Tracker (target)"
            if target_column == "ghi_tracker"
            else "GHI Tracker",
            mode="lines",
            line={"width": 2, "color": GHI_TRACKER_COLOR},
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            x=df["time"],
            y=df["cod"],
            name="COD",
            marker_color=COD_COLOR,
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title="REST2 Forecasted Irradiances",
        xaxis_title="Time (UTC)",
        yaxis_title="Irradiance (W/m²)",
        legend_title_text="Step",
    )
    fig.update_yaxes(
        title_text="Irradiance (W/m²)",
        secondary_y=False,
        range=[0, df[target_column].max() * 1.05],
    )
    fig.update_yaxes(title_text="COD", secondary_y=True, autorange="reversed")
    fig.update_layout(
        legend={
            "orientation": "h",
            "x": 0.5,
            "y": -0.2,
            "xanchor": "center",
            "bgcolor": "rgba(255, 255, 255, 0.8)",
        }
    )
    fig.update_layout(
        grid={"rows": 1, "columns": 1},
    )
    fig.update_xaxes(
        dtick="H1",
        tickformat="%Y-%m-%d %H:%M",
        tickangle=-45,
    )
    fig.write_html(filepath)
    return fig


def train_evaluation_plots(
    result: PlantTrainResult,
    measured: pl.DataFrame,
    cod: pl.DataFrame,
    filepath_prefix: str,
):
    predictions_df = _plant_train_result_with_irradiances_to_df(result)
    target_column = result.train.radiation_type
    df = _join_predictions_with_measured_and_cod(
        predictions_df, measured.to_pandas(), cod.to_pandas()
    )
    _ = rest2_train_steps_scatter_plot(
        df, target_column, filepath_prefix + "_train_steps_scatter.html"
    )
    _ = rest2_train_irradiances_scatter_plot(
        df, target_column, filepath_prefix + "_train_irradiances_scatter.html"
    )
    _ = rest2_train_steps_timeseries_plot(
        df, target_column, filepath_prefix + "_train_steps_timeseries.html"
    )
    _ = rest2_train_irradiances_timeseries_plot(
        df,
        target_column,
        filepath_prefix + "_train_irradiances_timeseries.html",
    )


def inference_plots(
    result: PlantInferenceResult,
    cod: pl.DataFrame,
    filepath_prefix: str,
):
    predictions_df = _plant_inference_result_with_irradiances_to_df(result)
    target_column = result.radiation_type
    df = _join_predictions_with_measured_and_cod(
        predictions_df, None, cod.to_pandas()
    )
    _ = rest2_inference_irradiances_timeseries_plot(
        df,
        target_column,
        filepath_prefix + "_inference_irradiances_timeseries.html",
    )
