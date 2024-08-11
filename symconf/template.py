import re
import tomllib
from pathlib import Path

from symconf import util
from symconf.reader import DictReader


class Template:
    def __init__(
        self,
        template_str  : str,
        pattern       : str = r'f{{(\S+?)}}',
    ):
        self.template_str = template_str
        self.pattern = pattern

    def fill(
        self,
        template_dict : dict,
    ) -> str:
        dr = DictReader.from_dict(template_dict)

        return re.sub(
            self.pattern,
            lambda m: str(dr.get(m.group(1))),
            self.template_str
        )

class FileTemplate(Template):
    def __init__(
        self,
        path    : Path,
        pattern : str = r'f{{(\S+)}}',
    ):
        super().__init__(
            path.open('r').read(),
            pattern=pattern
        )

class TOMLTemplate(FileTemplate):
    def __init__(
        self,
        toml_path : Path,
        pattern   : str = r'f{{(\S+)}}',
    ):
        super().__init__(
            toml_path,
            pattern=pattern
        )

    def fill(
        self,
        template_dict : dict,
    ) -> str:
        filled_template = super().fill(template_dict)
        toml_dict = tomllib.loads(filled_template)

        return toml_dict

    @staticmethod
    def stack_toml(
        path_list: list[Path]
    ) -> dict:
        stacked_dict = {}
        for toml_path in path_list:
            updated_map = tomllib.load(toml_path.open('rb'))
            stacked_dict = util.deep_update(stacked_dict, updated_map)

        return stacked_dict
