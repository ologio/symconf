"""
Handle job/script execution
"""

import stat
import subprocess
from pathlib import Path

from colorama import Fore, Style

from symconf.util import color_text


class Runner:
    def run_script(
        self,
        script: str | Path,
    ) -> str | None:
        script_path = Path(script)

        if script_path.stat().st_mode & stat.S_IXUSR == 0:
            print(
                color_text("│", Fore.BLUE),
                color_text(
                    f'   > script "{script_path.name}" missing '
                    "execute permissions, skipping",
                    Fore.RED + Style.DIM,
                ),
            )
            return

        print(
            color_text("│", Fore.BLUE),
            color_text(f' > running script "{script_path.name}"', Fore.BLUE),
        )

        output = subprocess.check_output(str(script_path), shell=True)

        if output:
            fmt_output = (
                output.decode()
                .strip()
                .replace("\n", f"\n{Fore.BLUE}{Style.NORMAL}│{Style.DIM}    ")
            )
            print(
                color_text("│", Fore.BLUE),
                color_text(
                    f'   captured script output "{fmt_output}"',
                    Fore.BLUE + Style.DIM,
                ),
            )

        return output

    def run_many(
        self,
        script_list: list[str | Path],
    ) -> list[str | None]:
        outputs = []
        for script in script_list:
            output = self.run_script(script)
            outputs.append(output)

        return outputs
