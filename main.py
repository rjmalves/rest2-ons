import logging
import sys
from pathlib import Path

from app.inference import InferenceManager
from app.internal.config import Config
from app.parser import build_parser
from app.readers import InputData, read_plant_artifacts
from app.train import TrainManager
from app.writers import (
    write_inference_results,
    write_plant_artifacts,
    write_plant_inference_plots,
    write_plant_train_plots,
)

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Show rest2's own INFO progress; third-party loggers stay at WARNING."""
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    for name in ("app", __name__):
        logging.getLogger(name).setLevel(logging.INFO)


def load_config(config_path: str) -> Config:
    if not Path(config_path).exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    return Config.from_json(config_path)


def main():
    _configure_logging()
    parser = build_parser()
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        reader = InputData(config.input)

        mode = config.mode

        if mode == "train":
            logger.info("Starting training mode...")
            manager = TrainManager(config, reader)
            results = manager.train()
            logger.info("Training completed successfully!")
            write_plant_artifacts(config, results)
            if config.postprocessing.plots:
                write_plant_train_plots(config, results, reader)
            logger.info("Artifacts written successfully!")
        elif mode == "inference":
            logger.info("Starting inference mode...")
            artifacts = read_plant_artifacts(config)
            manager = InferenceManager(config, reader)
            results = manager.predict(artifacts)
            logger.info("Inference completed successfully!")
            write_inference_results(config, results)
            if config.postprocessing.plots:
                write_plant_inference_plots(config, results, reader)
            logger.info("Results written successfully!")
        else:
            logger.error("Unknown mode: %s", mode)
            sys.exit(1)

    except Exception as e:
        logger.exception("Error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
