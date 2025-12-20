"""
Support for basic config templates
"""

import re
import tomllib
from typing import Any
from pathlib import Path

from symconf import util
from symconf.reader import DictReader


class Template:
    def __init__(
        self,
        template_str: str,
        key_pattern: str = r"f{{(\S+?)}}",
        exe_pattern: str = r"x{{((?:(?!x{{).)*)}}",
    ) -> None:
        self.template_str = template_str
        self.key_pattern = key_pattern
        self.exe_pattern = exe_pattern

    def fill(
        self,
        template_dict: dict,
    ) -> str:
        dr = DictReader.from_dict(template_dict)

        exe_filled = re.sub(
            self.exe_pattern,
            lambda m: self._exe_fill(m, dr),
            self.template_str,
        )

        key_filled = re.sub(
            self.key_pattern, lambda m: self._key_fill(m, dr), exe_filled
        )

        return key_filled

    def _key_fill(
        self,
        match: re.Match,
        dict_reader: DictReader,
    ) -> str:
        key = match.group(1)

        return str(dict_reader.get(key))

    def _exe_fill(
        self,
        match: re.Match,
        dict_reader: DictReader,
    ) -> str:
        key_fill = re.sub(
            self.key_pattern,
            lambda m: f'"{self._key_fill(m, dict_reader)}"',
            match.group(1),
        )

        return str(eval(key_fill))


class FileTemplate(Template):
    def __init__(
        self,
        path: Path,
        key_pattern: str = r"f{{(\S+?)}}",
        exe_pattern: str = r"x{{((?:(?!x{{).)*)}}",
    ) -> None:
        super().__init__(
            path.open("r").read(),
            key_pattern=key_pattern,
            exe_pattern=exe_pattern,
        )


class TOMLTemplate(FileTemplate):
    def __init__(
        self,
        toml_path: Path,
        key_pattern: str = r"f{{(\S+?)}}",
        exe_pattern: str = r"x{{((?:(?!x{{).)*)}}",
    ) -> None:
        super().__init__(
            toml_path,
            key_pattern=key_pattern,
            exe_pattern=exe_pattern,
        )

    def fill_dict(
        self,
        template_dict: dict,
    ) -> dict[str, Any]:
        filled_template = super().fill(template_dict)
        toml_dict = tomllib.loads(filled_template)

        return toml_dict

    @staticmethod
    def stack_toml(path_list: list[Path]) -> dict:
        stacked_dict = {}
        for toml_path in path_list:
            updated_map = tomllib.load(toml_path.open("rb"))
            stacked_dict = util.deep_update(stacked_dict, updated_map)

        return stacked_dict
