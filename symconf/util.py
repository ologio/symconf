from pathlib import Path
from xdg import BaseDirectory


def absolute_path(path: str | Path) -> Path:
    return Path(path).expanduser().absolute()
    
def xdg_config_path():
    return Path(BaseDirectory.save_config_path('symconf'))
