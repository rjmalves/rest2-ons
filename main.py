import sys
from pathlib import Path
from traceback import print_exc

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


def load_config(config_path: str) -> Config:
    if not Path(config_path).exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    return Config.from_json(config_path)


def main():
    parser = build_parser()
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        reader = InputData(config.input)

        mode = config.mode

        if mode == "train":
            print("Starting training mode...")
            manager = TrainManager(config, reader)
            results = manager.train()
            print("Training completed successfully!")
            write_plant_artifacts(config, results)
            if config.postprocessing.plots:
                write_plant_train_plots(config, results, reader)
            print("Artifacts written successfully!")
        elif mode == "inference":
            print("Starting inference mode...")
            artifacts = read_plant_artifacts(config)
            manager = InferenceManager(config, reader)
            results = manager.predict(artifacts)
            print("Inference completed successfully!")
            write_inference_results(config, results)
            if config.postprocessing.plots:
                write_plant_inference_plots(config, results, reader)
            print("Results written successfully!")
        else:
            print(f"Unknown mode: {mode}")
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
