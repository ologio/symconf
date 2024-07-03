import os
import json
import inspect
import tomllib
import argparse
import subprocess
from pathlib import Path

from colorama import Fore, Back, Style

from autoconf import util


class ConfigManager:
    def __init__(
        self,
        config_dir=None,
        disable_registry=False,
    ):
        '''
        Configuration manager class

        Parameters:
            config_dir: config parent directory housing expected files (registry,
                        app-specific conf files, etc). Defaults to
                        ``"$XDG_CONFIG_HOME/autoconf/"``.
            disable_registry: disable checks for a registry file in the ``config_dir``.
                              Should really only be set when using this programmatically
                              and manually supplying app settings.
        '''
        if config_dir == None:
            config_dir = util.xdg_config_path()

        self.config_dir = util.absolute_path(config_dir)
        self.apps_dir   = Path(self.config_dir, 'apps')

        self.app_registry = {}

        self._check_paths()

        if not disable_registry:
            self._check_registry()

    def _check_paths(self):
        '''
        Check necessary paths for existence.

        Regardless of programmatic use or ``disable_registry``, we need to a valid
        ``config_dir`` and it must have an ``apps/`` subdirectory (otherwise there are
        simply no files to act on, not even when manually providing app settings).
        '''
        # throw error if config dir doesn't exist
        if not self.config_dir.exists():
            raise ValueError(
                f'Config directory "{self.config_dir}" doesn\'t exist.'
            )
        
        # throw error if apps dir doesn't exist or is empty
        if not self.apps_dir.exists() or not list(self.apps_dir.iterdir()):
            raise ValueError(
                f'Config directory "{self.config_dir}" must have an "apps/" subdirectory.'
            )

    def _check_registry(self):
        registry_path = Path(self.config_dir, 'app_registry.toml')

        self.app_registry = {}
        if not registry_path.exists():
            print(
                Fore.YELLOW \
                + f'No registry file found at expected location "{registry_path}"'
            )
            return

        app_registry = tomllib.load(registry_path.open('rb'))

        if 'app' not in app_registry:
            print(
                Fore.YELLOW \
                + f'Registry file found but is either empty or incorrectly formatted (no "app" key).'
            )

        self.app_registry = app_registry.get('app', {})

    def resolve_scheme(self, scheme):
        # if scheme == 'auto':
        #     os_cmd_groups = {
        #         'Linux': (
        #             "gsettings get org.gnome.desktop.interface color-scheme",
        #             lambda r: r.split('-')[1][:-1],
        #         ),
        #         'Darwin': (),
        #     }

        #     osname = os.uname().sysname
        #     os_group = os_cmd_groups.get(osname, [])

        #     for cmd in cmd_list:
        #         subprocess.check_call(cmd.format(scheme=scheme).split())

        # return scheme

        if scheme == 'auto':
            return 'any'

        return scheme

    def resolve_palette(self, palette):
        if palette == 'auto':
            return 'any'

        return palette

    def app_config_map(self, app_name):
        '''
        Get the config map for a provided app.

        The config map is a dict mapping from config file **path names** to their absolute
        path locations. That is, 

        ```sh
        <config_path_name> -> <config_dir>/apps/<app_name>/<subdir>/<palette>-<scheme>.<config_path_name>
        ```

        For example,

        ```
        palette1-light.conf.ini -> ~/.config/autoconf/apps/user/palette1-light.conf.ini
        palette2-dark.app.conf -> ~/.config/autoconf/apps/generated/palette2-dark.app.conf
        ```

        This ensures we have unique config names pointing to appropriate locations (which
        is mostly important when the same config file names are present across ``user``
        and ``generated`` subdirectories).
        '''
        # first look in "generated", then overwrite with "user"
        file_map = {}
        app_dir  = Path(self.apps_dir, app_name)
        for subdir in ['generated', 'user']:
            subdir_path = Path(app_dir, subdir)

            if not subdir_path.is_dir():
                continue

            for conf_file in subdir_path.iterdir():
                file_map[conf_file.name] = conf_file

        return file_map

    def get_matching_configs(
        self, 
        app_name,
        scheme='auto',
        palette='auto',
    ) -> dict[str, str]:
        '''
        Get app config files that match the provided scheme and palette.

        Unique config file path names are written to the file map in order of specificity.
        All config files follow the naming scheme ``<palette>-<scheme>.<path-name>``,
        where ``<palette>-<scheme>`` is the "theme part" and ``<path-name>`` is the "conf
        part." For those config files with the same "conf part," only the entry with the
        most specific "theme part" will be stored. By "most specific," we mean those
        entries with the fewest possible components named ``any``, with ties broken in
        favor of a more specific ``palette`` (the only "tie" really possible here is when
        `any-<scheme>` and `<palette>-any` are both available, in which case the latter
        will overwrite the former).
        '''
        app_dir = Path(self.apps_dir, app_name)

        scheme  = self.resolve_scheme(scheme)
        palette = self.resolve_palette(palette)

        # now match theme files in order of inc. specificity; for each unique config file
        # tail, only the most specific matching file sticks
        file_parts = []
        app_config_map = self.app_config_map(app_name)
        for pathname in app_config_map:
            parts = pathname.split('.')

            if len(parts) < 2:
                print(f'Filename "{filename}" incorrectly formatted, ignoring')
                continue

            theme_part, conf_part = parts[0], '.'.join(parts[1:])
            file_parts.append((theme_part, conf_part, pathname))

        theme_prefixes = [
            'any-any',
            f'any-{scheme}',
            f'{palette}-any',
            f'{palette}-{scheme}'
        ]

        matching_file_map = {}
        for theme_prefix in theme_prefixes:
            for theme_part, conf_part, pathname in file_parts:
                if theme_part == theme_prefix:
                    matching_file_map[conf_part] = app_config_map[pathname]

        return matching_file_map

    def get_matching_scripts(
        self,
        app_name,
        scheme='any',
        palette='any',
    ):
        '''
        Execute matching scripts in the app's ``call/`` directory.

        Scripts need to be placed in 

        ```sh
        <config_dir>/apps/<app_name>/call/<palette>-<scheme>.sh
        ```

        and are matched using the same heuristic employed by config file symlinking
        procedure (see ``get_matching_configs()``).
        '''
        app_dir  = Path(self.apps_dir, app_name)
        call_dir = Path(app_dir, 'call')
        
        if not call_dir.is_dir():
            return

        theme_prefixes = [
            'any-any',
            f'any-{scheme}',
            f'{palette}-any',
            f'{palette}-{scheme}'
        ]

        # do it this way to keep order for downstream exec
        script_list = []
        for theme_prefix in theme_prefixes:
            for script_path in call_dir.iterdir():
                theme_part = script_path.stem
                if theme_part == theme_prefix:
                    script_list.append(script_path)

        return list(set(script_list))

    def update_app_config(
        self,
        app_name,
        app_settings = None,
        scheme       = 'any',
        palette      = 'any',
    ):
        '''
        Perform full app config update process, applying symlinks and running scripts.

        Note that this explicitly accepts app settings to override or act in place of
        missing app details in the app registry file. This is mostly to provide more
        programmatic control and test settings without needing them present in the
        registry file. The ``update_apps()`` method, however, **will** more strictly
        filter out those apps not in the registry, accepting a list of app keys that
        ultimately call this method.

        Note: symlinks point **from** the target location **to** the known internal config
        file; can be a little confusing.
        '''
        if app_settings is None:
            app_settings = self.app_registry.get(app_name, {})

        if 'config_dir' in app_settings and 'config_map' in app_settings:
            print(f'App "{app_name}" incorrectly configured, skipping')
            return

        to_symlink: list[tuple[Path, Path]] = []
        file_map = self.get_matching_configs(
            app_name,
            scheme=scheme,
            palette=palette,
        )
        if 'config_dir' in app_settings:
            for config_tail, full_path in file_map.items():
                to_symlink.append((
                    util.absolute_path(Path(app_settings['config_dir'], config_tail)), # point from real config dir
                    full_path, # to internal config location
                ))
        elif 'config_map' in app_settings:
            for config_tail, full_path in file_map.items():
                # app's config map points config tails to absolute paths
                if config_tail in app_settings['config_map']:
                    to_symlink.append((
                        abs_pat(Path(app_settings['config_map'][config_tail])), # point from real config path
                        full_path, # to internal config location
                    ))

        links_succ = []
        links_fail = []
        for from_path, to_path in to_symlink:
            if not to_path.exists():
                print(f'Internal config path "{to_path}" doesn\'t exist, skipping')
                links_fail.append((from_path, to_path))
                continue

            if not from_path.parent.exists():
                print(f'Target config parent directory for "{from_path}" doesn\'t exist, skipping')
                links_fail.append((from_path, to_path))
                continue

            # if config file being symlinked exists & isn't already a symlink (i.e.,
            # previously set by this script), throw an error. 
            if from_path.exists() and not from_path.is_symlink():
                print(
                    f'Symlink target "{from_path}" exists and isn\'t a symlink, NOT overwriting;' \
                   + ' please first manually remove this file so a symlink can be set.'
                )
                links_fail.append((from_path, to_path))
                continue
            else:
                # if path doesn't exist, or exists and is symlink, remove the symlink in
                # preparation for the new symlink setting
                from_path.unlink(missing_ok=True)

            #print(f'Linking [{from_path}] -> [{to_path}]')
            from_path.symlink_to(to_path)
            links_succ.append((from_path, to_path))

            # run matching scripts for app-specific reload
            # TODO: store the status of this cmd & print with the messages
            script_list = self.get_matching_scripts(
                app_name,
                scheme=scheme,
                palette=palette,
            )
            for script in script_list:
                print(Fore.BLUE + f'> Running script "{script.relative_to(self.config_dir}"')
                output = subprocess.check_output(str(script), shell=True)
                print(
                    Fore.BLUE + Style.DIM + f'-> Captured script output "{output.decode().strip()}"' + Style.RESET
                )

        for from_p, to_p in links_succ:
            from_p = from_p
            to_p   = to_p.relative_to(self.config_dir)
            print(Fore.GREEN + f'> {app_name} :: {from_p} -> {to_p}')

        for from_p, to_p in links_fail:
            from_p = from_p
            to_p   = to_p.relative_to(self.config_dir)
            print(Fore.RED + f'> {app_name} :: {from_p} -> {to_p}')

    def update_apps(
        self,
        apps: str | list[str] = '*',
        scheme                = 'any',
        palette               = 'any',
    ):
        if apps == '*':
            # get all registered apps
            app_list = list(self.app_registry.keys())
        else:
            # get requested apps that overlap with registry
            app_list = [a for a in app_list if a in app_registry]

        if not app_list:
            print(f'None of the apps "apps" are registered, exiting')
            return

        for app_name in app_list:
            self.update_app_config(
                app_name,
                app_settings=app_registry[app_name],
                scheme=scheme,
                palette=palette,
            )
