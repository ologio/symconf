import argparse
from pathlib import Path
from xdg import BaseDirectory


def absolute_path(path: str | Path) -> Path:
    return Path(path).expanduser().absolute()
    
def xdg_config_path():
    return Path(BaseDirectory.save_config_path('symconf'))

def deep_update(mapping: dict, *updating_mappings: dict) -> dict:
    '''Code adapted from pydantic'''
    updated_mapping = mapping.copy()
    for updating_mapping in updating_mappings:
        for k, v in updating_mapping.items():
            if k in updated_mapping and isinstance(updated_mapping[k], dict) and isinstance(v, dict):
                updated_mapping[k] = deep_update(updated_mapping[k], v)
            else:
                updated_mapping[k] = v
    return updated_mapping


class KVPair(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        kv_dict = getattr(namespace, self.dest, {})
        if kv_dict is None:
            kv_dict = {}
        for value in values:
            key, val = value.split('=', 1)
            kv_dict[key] = val
        setattr(namespace, self.dest, kv_dict)
