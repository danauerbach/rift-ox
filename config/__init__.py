#!/usr/bin/env python3

import os
from pathlib import Path
from typing import Union

import toml

def read() -> Union[None, dict]:
    # check for config file ENV VAR
    config_file = os.getenv("RIFT_OX_CONFIG_FILE", "")
    if not config_file:
        print(f'CONFIG ERROR: Config file ENV VAR $RIFT_OX_CONFIG_FILE not set.')
        return None

    config_path = Path(config_file)
    if not config_path.exists():
        print(f'CONFIG ERROR: Config file {config_path} does not exist.')
        return None

    cfg = None
    with config_path.open(mode="rt") as cfg_fl:
        cfg = toml.load(cfg_fl)

    if type(cfg) is not dict:
        print(f"ERROR parsing cfg file: {config_path.absolute()}.")
        return None

    return cfg

