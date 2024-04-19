import argparse
import inspect
import subprocess
import json
import os
import tomllib as toml
from pathlib import Path

from colorama import Fore


parser = argparse.ArgumentParser(
    description='Generate theme files for various applications. Uses a template (in TOML ' \
              + 'format) to map application-specific config keywords to colors (in JSON '  \
              + 'format).' 
)
parser.add_argument(
    '-p', '--palette',
    required=True,
    help='Palette name, must match a folder in themes/'
)
parser.add_argument(
    '-s', '--scheme',
    required=True,
    help='Preferred lightness scheme, either "light" or "dark".'
)
parser.add_argument(
    '-a', '--app',
    required=True,
    help='Application target for theme. App must be present in the registry. ' \
       + 'Use "*" to apply to all registered apps'
)
args = parser.parse_args()


def get_running_path():
    calling_module = inspect.getmodule(inspect.stack()[-1][0])
    return Path(calling_module.__file__).parent

def os_scheme_settings(scheme):
    '''
    Groups of settings/commands to invoke globally based on the provided `scheme`. This
    may control things like default app light/dark behavior, for instance.
    '''
    os_cmd_groups = {
        'Linux': [
            "gsettings set org.gnome.desktop.interface color-scheme 'prefer-{scheme}'",
        ],
        'Darwin': [],
    }

    if scheme not in ['light', 'dark']: return
    osname = os.uname().sysname
    cmd_list = os_cmd_groups.get(osname, [])

    for cmd in cmd_list:
        subprocess.check_call(cmd.format(scheme=scheme).split())

def update_theme_settings():
    osname       = os.uname().sysname
    basepath     = get_running_path()
    app_registry = toml.load(Path(basepath, 'app_registry.toml').open('rb'))
    app_registry = app_registry.get('app', {})

    if args.app not in app_registry and args.app != '*':
        print(f'App {args.app} not registered, exiting')
        return

    app_list = []
    if args.app == '*':
        app_list = list(app_registry.items())
    else:
        app_list = [(args.app, app_registry[args.app])]

    links_succ = {}
    links_fail = {}
    for app_name, app_settings in app_list:
        config_dir  = Path(app_settings['config_dir']).expanduser()
        config_file = app_settings['config_file']
        config_path = Path(config_dir, config_file)

        if osname not in app_settings['supported_oses']:
            print(f'OS [{osname}] not support for app [{app_name}]')
            continue

        if app_settings['external_theme']:
            # symlink from "current-theme.conf" in app's config-dir ...
            from_conf_path = Path(config_dir, 'current-theme.conf')

            # ... to appropriate generated theme path here in local-config
            to_conf_path = Path(
                basepath,
                f'themes/{args.palette}/apps/{app_name}/generated/{args.scheme}.conf'
            )
        else:
            # symlink from the canonical config file ...
            from_conf_path = config_path

            # ... to appropriate theme variant
            to_conf_path = Path(
                config_dir, 
                f'{app_name}-{args.palette}-{args.scheme}{config_path.suffix}'
            )

        if not to_conf_path.exists():
            print(
                f'Expected symlink target [{to_conf_path}] doesn\'t exist, skipping'
            )
            links_fail[app_name] = (from_conf_path.name, to_conf_path.name)
            continue

        # if config file being symlinked exists & isn't already a symlink (i.e.,
        # previously set by this script), throw an error. 
        if from_conf_path.exists() and not from_conf_path.is_symlink():
            print(
                f'Symlink origin [{from_conf_path}] exists and isn\'t a symlink; please ' \
               + 'first manually remove this file so this script can set the symlink.'
            )
            links_fail[app_name] = (from_conf_path.name, to_conf_path.name)
            continue
        else:
            # if path doesn't exist, or exists and is symlink, remove the symlink in
            # preparation for the new symlink setting
            from_conf_path.unlink(missing_ok=True)

        print(f'Linking [{from_conf_path}] -> [{to_conf_path}]')

        # run color scheme live-reload for app, if available
        # TODO: store the status of this cmd & print with the messages
        if 'refresh_cmd' in app_settings:
            subprocess.check_call(app_settings['refresh_cmd'], shell=True)

        from_conf_path.symlink_to(to_conf_path)
        links_succ[app_name] = (from_conf_path.name, to_conf_path.name)

    for app, (from_p, to_p) in links_succ.items():
        print(Fore.GREEN + f'> {app} :: {from_p} -> {to_p}')

    for app, (from_p, to_p) in links_fail.items():
        print(Fore.RED + f'> {app} :: {from_p} -> {to_p}')


if __name__ == '__main__':
    os_scheme_settings(args.scheme)
    update_theme_settings()
