import os
import json
import inspect
import tomllib
import argparse
import subprocess
from pathlib import Path

from colorama import Fore, Back, Style

from symconf import util


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
                        ``"$XDG_CONFIG_HOME/symconf/"``.
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

    def _resolve_scheme(self, scheme):
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

    def _resolve_palette(self, palette):
        if palette == 'auto':
            return 'any'

        return palette

    def app_config_map(self, app_name) -> dict[str, Path]:
        '''
        Get the config map for a provided app.

        The config map is a dict mapping from config file **path names** to their absolute
        path locations. That is, 

        ```sh
        <config_path_name> -> <config_dir>/apps/<app_name>/<subdir>/<palette>-<scheme>.<config_path_name>
        ```

        For example,

        ```
        palette1-light.conf.ini -> ~/.config/symconf/apps/user/palette1-light.conf.ini
        palette2-dark.app.conf -> ~/.config/symconf/apps/generated/palette2-dark.app.conf
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

    def _get_file_parts(self, pathnames):
        # now match theme files in order of inc. specificity; for each unique config file
        # tail, only the most specific matching file sticks
        file_parts = []
        for pathname in pathnames:
            parts = str(pathname).split('.')

            if len(parts) < 2:
                print(f'Filename "{pathname}" incorrectly formatted, ignoring')
                continue

            theme_part, conf_part = parts[0], '.'.join(parts[1:])
            file_parts.append((theme_part, conf_part, pathname))

        return file_parts

    def _get_prefix_order(
        self, 
        scheme,
        palette,
        strict=False,
    ):
        if strict:
            theme_order = [
                (palette, scheme),
            ]
        else:
            # inverse order of match relaxation; intention being to overwrite with
            # results from increasingly relevant groups given the conditions
            if palette == 'any' and scheme == 'any':
                # prefer both be "none", with preference for specific scheme
                theme_order = [
                    (palette , scheme),
                    (palette , 'none'),
                    ('none'  , scheme),
                    ('none'  , 'none'),
                ]
            elif palette == 'any':
                # prefer palette to be "none", then specific, then relax specific scheme
                # to "none"
                theme_order = [
                    (palette , 'none'),
                    ('none'  , 'none'),
                    (palette , scheme),
                    ('none'  , scheme),
                ]
            elif scheme == 'any':
                # prefer scheme to be "none", then specific, then relax specific palette
                # to "none"
                theme_order = [
                    ('none'  , scheme),
                    ('none'  , 'none'),
                    (palette , scheme),
                    (palette , 'none'),
                ]
            else:
                # neither component is any; prefer most specific
                theme_order = [
                    ('none'  , 'none'),
                    ('none'  , scheme),
                    (palette , 'none'),
                    (palette , scheme),
                ]

        return theme_order

    def match_pathnames(
        self, 
        pathnames,
        scheme,
        palette,
        prefix_order=None,
        strict=False,
    ):
        file_parts = self._get_file_parts(pathnames)

        if prefix_order is None:
            prefix_order = self._get_prefix_order(
                scheme,
                palette,
                strict=strict,
            )

        ordered_matches = []
        for palette_prefix, scheme_prefix in prefix_order:
            for theme_part, conf_part, pathname in file_parts:
                theme_split = theme_part.split('-')
                palette_part, scheme_part = '-'.join(theme_split[:-1]), theme_split[-1]

                palette_match = palette_prefix == palette_part or palette_prefix == 'any'
                scheme_match = scheme_prefix == scheme_part or scheme_prefix == 'any'
                if palette_match and scheme_match:
                    ordered_matches.append((conf_part, theme_part, pathname))

        return ordered_matches

    def get_matching_configs(
        self, 
        app_name,
        scheme='auto',
        palette='auto',
        strict=False,
    ) -> dict[str, Path]:
        '''
        Get app config files that match the provided scheme and palette.

        Unique config file path names are written to the file map in order of specificity.
        All config files follow the naming scheme ``<palette>-<scheme>.<path-name>``,
        where ``<palette>-<scheme>`` is the "theme part" and ``<path-name>`` is the "conf
        part." For those config files with the same "conf part," only the entry with the
        most specific "theme part" will be stored. By "most specific," we mean those
        entries with the fewest possible components named ``none``, with ties broken in
        favor of a more specific ``palette`` (the only "tie" really possible here is when
        ``none-<scheme>`` and ``<palette>-none`` are both available, in which case the latter
        will overwrite the former).

        .. admonition: Edge cases

            There are a few quirks to this matching scheme that yield potentially
            unintuitive results. As a recap:

            - The "theme part" of a config file name includes both a palette and a scheme
              component. Either of those parts may be "none," which simply indicates that
              that particular file does not attempt to change that factor. "none-light,"
              for instance, might simply set a light background, having no effect on other
              theme settings.
            - Non-keyword queries for scheme and palette will always be matched exactly.
              However, if an exact match is not available, we also look for "none" in each
              component's place. For example, if we wanted to set "solarized-light" but
              only "none-light" was available, it would still be set because we can still
              satisfy the desire scheme (light). The same goes for the palette
              specification, and if neither match, "none-none" will always be matched if
              available. Note that if "none" is specified exactly, it will be matched
              exactly, just like any other value.
            - During a query, "any" may also be specified for either component, indicating
              we're okay to match any file's text for that part. For example, if I have
              two config files ``"p1-dark"`` and ``"p2-dark"``, the query for ``("any",
              "dark")`` would suggest I'd like the dark scheme but am okay with either
              palette.

            It's under the "any" keyword where possibly counter-intuitive results may come
            about. Specifying "any" does not change the mechanism that seeks to optionally
            match "none" if no specific match is available. For example, suppose we have
            the config file ``red-none`` (setting red colors regardless of a light/dark
            mode). If I query for ``("any", "dark")``, ``red-none`` will be matched
            (supposing there are no more direct matches available). Because we don't a
            match specifically for the scheme "dark," it gets relaxed to "none." But we
            indicated we're okay to match any palette. So despite asking for a config that
            sets a dark scheme and not caring about the palette, we end up with a config
            that explicitly does nothing about the scheme but sets a particular palette.
            This matching process is still consistent with what we expect the keywords to
            do, it just slightly muddies the waters with regard to what can be matched
            (mostly due to the amount that's happening under the hood here).

            This example is the primary driver behind the optional ``strict`` setting,
            which in this case would force the dark scheme to be matched (and ultimately
            find no matches).

            Also: when "any" is used for a component, options with "none" are prioritized,
            allowing "any" to be as flexible and unassuming as possible (only matching a
            random specific config among the options if there is no "none" available).
        '''
        app_dir = Path(self.apps_dir, app_name)

        scheme  = self._resolve_scheme(scheme)
        palette = self._resolve_palette(palette)

        app_config_map = self.app_config_map(app_name)

        ordered_matches = self.match_pathnames(
            app_config_map,
            scheme,
            palette,
            strict=strict,
        )

        matching_file_map = {}
        for conf_part, theme_part, pathname in ordered_matches:
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
        procedure (see ``get_matching_configs()``), albeit with a forced ``prefix_order``,
        ordered by increasing specificity. The order is then reversed, and the final list
        orders the scripts by the first time they appear (intention being to reload
        specific settings first).

        TODO: consider running just the most specific script? Users might want to design
        their scripts to be stackable, or they may just be independent.
        '''
        app_dir  = Path(self.apps_dir, app_name)
        call_dir = Path(app_dir, 'call')
        
        if not call_dir.is_dir():
            return

        prefix_order = [
            ('none'  , 'none'),
            ('none'  , scheme),
            (palette , 'none'),
            (palette , scheme),
        ]

        pathnames = [path.name for path in call_dir.iterdir()]
        ordered_matches = self.match_pathnames(
            pathnames,
            scheme,
            palette,
            prefix_order=prefix_order
        )

        # flip list to execute by decreasing specificity
        return list(dict.fromkeys(map(lambda x:Path(call_dir, x[2]), ordered_matches)))[::-1]

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

        print('├─ ' + Fore.YELLOW + f'{app_name} :: matched {len(to_symlink)} config files')

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

        # link report
        for from_p, to_p in links_succ:
            from_p = from_p
            to_p   = to_p.relative_to(self.config_dir)
            print(Fore.GREEN + f'│  > linked {from_p} -> {to_p}')

        for from_p, to_p in links_fail:
            from_p = from_p
            to_p   = to_p.relative_to(self.config_dir)
            print(Fore.RED + f'│  > failed to link {from_p} -> {to_p}')

        # run matching scripts for app-specific reload
        script_list = self.get_matching_scripts(
            app_name,
            scheme=scheme,
            palette=palette,
        )

        for script in script_list:
            print(Fore.BLUE + f'│  > running script "{script.relative_to(self.config_dir)}"')
            output = subprocess.check_output(str(script), shell=True)
            if output:
                fmt_output = output.decode().strip().replace('\n','\n│    ')
                print(
                    Fore.BLUE + Style.DIM \
                    + f'│  > captured script output "{fmt_output}"' \
                    + Style.RESET_ALL
                )

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
            app_list = [a for a in apps if a in self.app_registry]

        if not app_list:
            print(f'None of the apps "{apps}" are registered, exiting')
            return

        print('> symconf parameters: ')
        print('  > registered apps :: ' + Fore.YELLOW + f'{app_list}' + Style.RESET_ALL)
        print('  > palette         :: ' + Fore.YELLOW + f'{palette}'  + Style.RESET_ALL)
        print('  > scheme          :: ' + Fore.YELLOW + f'{scheme}\n' + Style.RESET_ALL)

        for app_name in app_list:
            self.update_app_config(
                app_name,
                app_settings=self.app_registry[app_name],
                scheme=scheme,
                palette=palette,
            )
