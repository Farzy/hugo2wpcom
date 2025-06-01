from __future__ import annotations

import configparser
from typing import Union


class Config:
    def __init__(self, filepath: str = "config.ini"):
        self.filepath = filepath
        defaults = {
            'default_post_status': 'draft',
            'default_post_category': 'Imported',
            'default_post_tags': 'hugo, import',
        }
        self.cfg = configparser.ConfigParser(defaults=defaults)
        # Ensure 'Hugo' and 'WordPress' sections exist for default access
        if 'Hugo' not in self.cfg:
            self.cfg.add_section('Hugo')
        if 'WordPress' not in self.cfg:
            self.cfg.add_section('WordPress')
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
        # Ensure the section exists before trying to access it
        # This is important if the config file is empty or sections are missing
        if not self.cfg.has_section(section):
            # We could raise an error or return a SectionProxy for an empty section
            # For now, let's stick to configparser's behavior which would error
            # if trying to access a key from a non-existent section directly.
            # However, our init ensures Hugo and WordPress sections exist.
            raise KeyError(f"Section '{section}' does not exist in the configuration.")
        return self.cfg[section]

    # __setitem__ for transparent updates
    def __setitem__(self, section: str, values: dict) -> None:
        if not isinstance(values, dict):
            raise ValueError(f"Config: Values must be a dictionary, received {type(values)} instead.")
        self.cfg[section] = values
