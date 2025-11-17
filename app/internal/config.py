from dataclasses import dataclass
from datetime import datetime

import pyjson5


@dataclass
class TimeWindow:
    start: datetime
    end: datetime

    @classmethod
    def parse(cls, window_str: str) -> "TimeWindow":
        start, end = window_str.split("/")

        return cls(
            start=datetime.fromisoformat(start), end=datetime.fromisoformat(end)
        )


@dataclass
class TimeWindows:
    training: TimeWindow
    validation: TimeWindow
    test: TimeWindow
    inference: TimeWindow

    @classmethod
    def parse(cls, windows: dict[str, str]) -> "TimeWindows":
        return cls(
            training=TimeWindow.parse(windows["training"]),
            validation=TimeWindow.parse(windows["validation"]),
            test=TimeWindow.parse(windows["test"]),
            inference=TimeWindow.parse(windows["inference"]),
        )


@dataclass
class PostprocessingConfig:
    errors: bool
    plots: bool

    @classmethod
    def parse(cls, config: dict) -> "PostprocessingConfig":
        return cls(
            errors=config.get("errors", False),
            plots=config.get("plots", False),
        )


@dataclass
class Config:
    mode: str
    input: str
    output: str
    artifact: str
    time_windows: TimeWindows
    postprocessing: PostprocessingConfig
    plant_ids: list[str] | None = None
    forecasting_day_ahead: int = 0
    target_radiation_type: str = "ghi"

    @classmethod
    def parse(cls, config: dict) -> "Config":
        return cls(
            mode=config["mode"],
            input=config["input"],
            output=config["output"],
            artifact=config["artifact"],
            plant_ids=config["plant_ids"],
            forecasting_day_ahead=config["forecasting_day_ahead"],
            target_radiation_type=config["target_radiation_type"],
            time_windows=TimeWindows.parse(config["time_windows"]),
            postprocessing=PostprocessingConfig.parse(
                config.get("postprocessing", {})
            ),
        )

    @classmethod
    def from_json(cls, json_path: str) -> "Config":
        with open(json_path, "r") as f:
            config = pyjson5.decode(f.read())

        return cls.parse(config)
