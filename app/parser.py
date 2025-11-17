import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
            description="ML Pipeline for Cloud Optical Depth and Solar Irradiance Forecasting"
        )
    parser.add_argument(
        "--config",
        type=str,
        default="config.jsonc",
        help="Path to configuration JSON file (default: config.json)",
    )
    return parser
