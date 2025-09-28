import re
from pathlib import Path
from argparse import Action, Namespace, ArgumentParser

from xdg import BaseDirectory
from colorama import Back, Fore, Style
from colorama.ansi import AnsiCodes


def color_text(text: str, *colorama_args: AnsiCodes) -> str:
    """
    Colorama text helper function

    Note: we attempt to preserve expected nested behavior by only resetting the
    groups (Fore, Back, Style) affected the styles passed in. This works when
    an outer call is changing styles in one group, and an inner call is
    changing styles in another, but *not* when affected groups overlap.

    For example, if an outer call is setting the foreground color (e.g.,
    ``Fore.GREEN``), nested calls on the text being passed into the function
    can modify and reset the background or style with affecting the foreground.
    The primary use case here is styling a group of text a single color, but
    applying ``BRIGHT`` or ``DIM`` styles only to some text elements within. If
    we didn't reset by group, the outer coloration request will be "canceled
    out" as soon as the first inner call is made (since the unconditional
    behavior just employs ``Style.RESET_ALL``).
    """

    # reverse map colorama Ansi codes
    resets = []
    for carg in colorama_args:
        match = re.match(r".*\[(\d+)m", carg)
        if match:
            intv = int(match.group(1))
            if (intv >= 30 and intv <= 39) or (intv >= 90 and intv <= 97):
                resets.append(Fore.RESET)
            elif (intv >= 40 and intv <= 49) or (intv >= 100 and intv <= 107):
                resets.append(Back.RESET)
            elif (intv >= 0 and intv <= 2) or intv == 22:
                resets.append(Style.NORMAL)

    return f"{''.join(colorama_args)}{text}{''.join(resets)}"


def printc(text: str, *colorama_args: AnsiCodes) -> None:
    print(color_text(text, *colorama_args))


def absolute_path(path: str | Path) -> Path:
    return Path(path).expanduser().absolute()


def xdg_config_path() -> Path:
    return Path(BaseDirectory.save_config_path("symconf"))


def to_tilde_path(path: Path) -> Path:
    """
    Abbreviate an absolute path by replacing HOME with "~", if applicable.
    """

    try:
        return Path(f"~/{path.relative_to(Path.home())}")
    except ValueError:
        return path


def deep_update(mapping: dict, *updating_mappings: dict) -> dict:
    """Code adapted from pydantic"""

    updated_mapping = mapping.copy()
    for updating_mapping in updating_mappings:
        for k, v in updating_mapping.items():
            if (
                k in updated_mapping
                and isinstance(updated_mapping[k], dict)
                and isinstance(v, dict)
            ):
                updated_mapping[k] = deep_update(updated_mapping[k], v)
            else:
                updated_mapping[k] = v
    return updated_mapping


class KVPair(Action):
    def __call__(
        self,
        parser: ArgumentParser,
        namespace: Namespace,
        values: list[str],
        option_string: str | None = None,
    ) -> None:
        kv_dict = getattr(namespace, self.dest, {})

        if kv_dict is None:
            kv_dict = {}

        for value in values:
            key, val = value.split("=", 1)
            kv_dict[key] = val

        setattr(namespace, self.dest, kv_dict)
