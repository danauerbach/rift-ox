#!/usr/bin/env python3

from pathlib import Path
from typing import Tuple, Union

import toml


class PauseDepths:

    def __init__(self, depths_fn: Path):
        self._depths = sorted(self._read_pause_depths(depths_fn), reverse=True)
        self._depths_completed = []
        self._filepath = depths_fn

    def _read_pause_depths(self, pause_depth_path : Path) -> list[float]:

        depths: list[float] = []
        if not pause_depth_path.exists():
            print(f'CONFIG ERROR: Config file {pause_depth_path} does not exist.')
            return []

        depths_cfg: Union[dict, None] = None
        with pause_depth_path.open(mode="rt") as cfg_fl:
            depths_cfg = toml.load(cfg_fl)
            if depths_cfg:
                depths = depths_cfg['DEPTHS']
                if not isinstance(depths, list):
                    print(f'ERROR reading depths file {pause_depth_path}')
                    depths = []

        return depths
    
    def refresh(self):
        self._depths = sorted(self._read_pause_depths(self._filepath), reverse=True)

    def get_next_depth(self, max_depth: Union[float, None]) -> Union[float, None]:

        while len(self._depths) > 0:
            if max_depth:
                if self._depths[0] < max_depth:
                    return self._depths[0]
                else:
                    del self._depths[0]
                    continue

            if len(self._depths) > 0:
                return self._depths[0]
            else:
                return None

    def use_next_depth(self) -> None:

        if len(self._depths) > 0:
            next: float = self._depths[0]
            self._depths_completed.append(next)
            del self._depths[0]

        return
