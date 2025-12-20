"""
Simplified management for nested dictionaries
"""

import copy
import pprint
import hashlib
import logging
import tomllib
from typing import Any
from pathlib import Path

from symconf.util import deep_update

logger = logging.getLogger(__name__)


class DictReader:
    def __init__(self, toml_path: str | None = None) -> None:
        self._config = {}
        self.toml_path = toml_path

        if toml_path is not None:
            self._config = self._load_toml(toml_path)

    def __str__(self) -> str:
        return pprint.pformat(self._config, indent=4)

    @staticmethod
    def _load_toml(toml_path: str) -> dict[str, Any]:
        return tomllib.loads(Path(toml_path).read_text())

    @classmethod
    def from_dict(cls, config_dict: dict) -> "DictReader":
        new_instance = cls()
        new_instance._config = copy.deepcopy(config_dict)
        return new_instance

    def update(
        self, config: "DictReader", in_place: bool = False
    ) -> "DictReader":
        new_config = deep_update(self._config, config._config)

        if in_place:
            self._config = new_config
            return self

        return self.from_dict(new_config)

    def copy(self) -> "DictReader":
        return self.from_dict(copy.deepcopy(self._config))

    def get_subconfig(self, key: str) -> None:  # "DictReader":
        pass

    def get(self, key: str, default: str | None = None) -> str | None:
        keys = key.split(".")

        subconfig = self._config
        for subkey in keys[:-1]:
            subconfig = subconfig.get(subkey)

            if type(subconfig) is not dict:
                return default

        return subconfig.get(keys[-1], default)

    def set(self, key: str, value: str | None) -> bool:
        keys = key.split(".")

        subconfig = self._config
        for subkey in keys[:-1]:
            if subkey in subconfig:
                subconfig = subconfig[subkey]

                if type(subconfig) is not dict:
                    logger.debug(
                        "Attempting to set nested key with an "
                        "existing non-dict parent"
                    )
                    return False

                continue

            subdict = {}
            subconfig[subkey] = subdict
            subconfig = subdict

        subconfig.update({keys[-1]: value})

        return True

    def generate_hash(self, exclude_keys: list[str] | None = None) -> str:
        inst_copy = self.copy()

        if exclude_keys is not None:
            for key in exclude_keys:
                inst_copy.set(key, None)

        items = inst_copy._config.items()

        # create hash from config options
        config_str = str(sorted(items))

        return hashlib.md5(config_str.encode()).hexdigest()
