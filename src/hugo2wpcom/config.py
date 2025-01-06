from __future__ import annotations

import configparser
from typing import Union


class Config:
    def __init__(self, filepath: str = "config.ini"):
        self.filepath = filepath
        self.cfg = configparser.ConfigParser()
        self.read_config()

    def read_config(self) -> Union[configparser.ConfigParser, None]:
        try:
            self.cfg.read(self.filepath)  # type: ignore[no-untyped-call]
            return self.cfg
        except configparser.Error as e:
            print(f"Error reading config file: {e}")
            return None

    def write_config(self) -> None:
        try:
            with open(self.filepath, 'w') as file:
                self.cfg.write(file)
        except IOError as e:
            print(f"Error writing to config file: {e}")

    # __getitem__ for transparent access
    def __getitem__(self, section: str) -> Union[configparser.SectionProxy, None]:
        return self.cfg[section]

    # __setitem__ for transparent updates
    def __setitem__(self, section: str, values: dict) -> None:
        if not isinstance(values, dict):
            raise ValueError("Values must be a dictionary.")
        self.cfg[section] = values
