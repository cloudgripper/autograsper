import yaml
from typing import Any
import os


def load_config(file_path: str) -> Any:
    """
    Loads and returns the configuration from a YAML file.

    :param file_path: Path to the YAML configuration file.
    :return: A dictionary with the configuration.
    """

    with open(file_path, "r") as f:
        config = yaml.safe_load(f)
    return config
