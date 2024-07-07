import os
import re
import json
import inspect
import tomllib
import argparse
import subprocess
from pathlib import Path

from colorama import Fore, Back, Style

from symconf import util
from symconf.reader import DictReader

def y(t):
    return Style.RESET_ALL + Fore.YELLOW + t + Style.RESET_ALL

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

    def _resolve_group(self, group, value='auto'):
        if value == 'auto':
            # look group up in app cache and set to current value
            return 'any'

        return value

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
        user_app_dir = Path(self.apps_dir, app_name, 'user')

        if user_app_dir.is_dir():
            for conf_file in user_app_dir.iterdir():
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
        '''
        Find and return matches along the "match trajectory."
        '''
        file_parts = self._get_file_parts(pathnames)

        if prefix_order is None:
            prefix_order = self._get_prefix_order(
                scheme,
                palette,
                strict=strict,
            )

        ordered_matches = []
        for i, (palette_prefix, scheme_prefix) in enumerate(prefix_order):
            for theme_part, conf_part, pathname in file_parts:
                theme_split  = theme_part.split('-')
                scheme_part  = theme_split[-1]
                palette_part = '-'.join(theme_split[:-1])

                palette_match = palette_prefix == palette_part or palette_prefix == 'any'
                scheme_match = scheme_prefix == scheme_part or scheme_prefix == 'any'
                if palette_match and scheme_match:
                    ordered_matches.append((conf_part, theme_part, pathname, i+1))

        return ordered_matches

    def _get_relaxed_set(
        self,
        match_list
    ):
        '''
        Mostly to filter "any" matches, latching onto a particular result and getting
        only its relaxed variants.

        Note that palette-scheme files can be named ``<variant>-<palette>-<scheme>``
        '''
        if not match_list:
            return []

        match = match_list[-1]
        theme_split = match[1].split('-')
        palette_tgt, scheme_tgt = '-'.join(theme_split[:-1]), theme_split[-1]

        relaxed_map = {}
        for conf_part, theme_part, pathname, idx in match_list:
            #theme_split  = theme_part.split('-')[::-1]
            #scheme_part  = theme_split[0]
            #palette_part = theme_split[1]
            theme_split  = theme_part.split('-')
            scheme_part  = theme_split[-1]
            palette_part = '-'.join(theme_split[:-1])
            #pvar_part    = '-'.join(theme_split[2:])

            palette_match = palette_part == palette_tgt or palette_part == 'none'
            scheme_match = scheme_part == scheme_tgt or scheme_part == 'none'

            if palette_match and scheme_match:
                relaxed_map[pathname] = (conf_part, theme_part, pathname, idx)

        return list(relaxed_map.values())

    def _stack_toml(
        self,
        path_list
    ):
        stacked_dict = {}
        for toml_path in path_list:
            updated_map = tomllib.load(toml_path.open('rb'))
            stacked_dict = util.deep_update(stacked_dict, updated_map)

        return stacked_dict

    def template_fill(
        self,
        template_str  : str,
        template_dict : dict,
        pattern       : str = r'f{{(\S+)}}',
    ):
        dr = DictReader.from_dict(template_dict)
        return re.sub(
            pattern,
            lambda m:str(dr.get(m.group(1))),
            template_str
        )

    def get_matching_group_dict(
        self, 
        scheme='auto',
        palette='auto',
        **kw_groups,
    ) -> dict:
        '''
        Note that "strictness" doesn't really apply in this setting. In the config
        matching setting, setting strict means there's no relaxation to "none," but here,
        any "none" group files just help fill any gaps (but are otherwise totally
        overwritten, even if matched, by more precise matches). You can match ``nones``
        directly if you want as well. ``get_matching_scripts()`` is similar in this sense.
        '''
        scheme  = self._resolve_group('scheme', scheme)
        palette = self._resolve_group('palette', palette)
        groups = {
            k : self._resolve_group(k, v)
            for k, v in kw_groups.items()
        }
        # palette lookup will behave like other groups
        groups['palette'] = palette.split('-')[-1]

        group_dir = Path(self.config_dir, 'groups')
        if not group_dir.exists():
            return {}

        # handle non-palette-scheme groups
        group_matches = {}
        for fkey, fval in groups.items():
            key_group_dir = Path(group_dir, fkey)

            if not key_group_dir.exists():
                print(f'Group directory {fkey} doesn\'t exist, skipping')
                continue

            # mirror matching scheme: 1) prefix order, 2) full enumeration, 3) select
            # best, 4) make unique, 5) ordered relaxation
            stem_map = {path.stem : path for path in key_group_dir.iterdir()}

            if fval == 'any':
                prefix_order = [fval, 'none']
            else:
                prefix_order = ['none', fval]

            matches = []
            for prefix in prefix_order:
                for stem in stem_map:
                    if prefix == stem or prefix == 'any':
                        matches.append(stem)

            if not matches:
                # no matches for group, skip
                continue

            match_dict = {}
            tgt = matches[-1] # select best based on order, make new target
            for stem in matches:
                if stem == tgt or stem == 'none':
                    match_dict[stem] = stem_map[stem]

            group_matches[fkey] = list(match_dict.values())

        print(group_matches)

        # first handle scheme maps; matching palette files should already be found in the
        # regular group matching process
        palette_dict = self._stack_toml(group_matches.get('palette', []))

        # then palette-scheme groups (require 2-combo logic)
        scheme_group_dir = Path(group_dir, 'scheme')
        scheme_pathnames = [path.name for path in scheme_group_dir.iterdir()]
        ordered_matches = self.match_pathnames(
            scheme_pathnames,
            scheme,
            palette,
        )
        relaxed_matches = self._get_relaxed_set(ordered_matches)

        scheme_dict = {}
        for conf_part, theme_part, toml_path, _ in relaxed_matches:
            toml_str = Path(scheme_group_dir, toml_path).open('r').read()
            filled_toml = self.template_fill(toml_str, palette_dict)

            toml_dict = tomllib.loads(filled_toml)
            scheme_dict = util.deep_update(scheme_dict, toml_dict)

        template_dict = {
            group : self._stack_toml(ordered_matches)
            for group, ordered_matches in group_matches.items()
        }
        template_dict['scheme'] = scheme_dict

        return template_dict, relaxed_matches

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

        scheme  = self._resolve_group('scheme', scheme)
        palette = self._resolve_group('palette', palette)

        app_config_map = self.app_config_map(app_name)

        ordered_matches = self.match_pathnames(
            app_config_map,
            scheme,
            palette,
            strict=strict,
        )

        matching_file_map = {}
        for conf_part, theme_part, pathname, idx in ordered_matches:
            matching_file_map[conf_part] = (app_config_map[pathname], idx)

        return matching_file_map

    def get_matching_templates(
        self,
        app_name,
        scheme='auto',
        palette='auto',
        **kw_groups,
    ) -> dict:
        template_dict, relaxed_matches = self.get_matching_group_dict(
            scheme=scheme,
            palette=palette,
            **kw_groups,
        )
        max_idx = 0
        if relaxed_matches:
            max_idx = max([m[3] for m in relaxed_matches])

        template_map = {}
        template_dir = Path(self.apps_dir, app_name, 'templates')
        if template_dir.is_dir():
            for template_file in template_dir.iterdir():
                template_map[template_file.name] = template_file

        return template_map, template_dict, relaxed_matches, max_idx

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
        relaxed_matches = self._get_relaxed_set(ordered_matches)

        # flip list to execute by decreasing specificity
        return list(map(lambda x:Path(call_dir, x[2]), relaxed_matches))[::-1]

    def update_app_config(
        self,
        app_name,
        app_settings = None,
        strict       = False,
        scheme       = 'any',
        palette      = 'any',
        **kw_groups,
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

        # merge templates and user-provided configs
        template_map, template_dict, template_matches, tidx = self.get_matching_templates(
            app_name,
            scheme=scheme,
            palette=palette,
            **kw_groups
        )
        # set file map to user configs if yields a strictly better match
        config_map = self.get_matching_configs(
            app_name,
            scheme=scheme,
            palette=palette,
            strict=strict,
        )
        
        # tuples of 1) full paths and 2) whether to fill template
        generated_path = Path(self.apps_dir, app_name, 'generated')
        generated_path.mkdir(parents=True, exist_ok=True)

        # flatten matches
        generated_paths  = [m[2] for m in template_matches]
        generated_config = {}

        file_map = {}
        for tail, full_path in template_map.items():
            # use config only if strictly better match
            # the P-S match forms rules the match quality; if additional args from
            # templates (e.g. "font") match available groups but there is still a better
            # P-S match in "user/", it will beat out the template (b/c the "user" config
            # is concrete). If they're on the same level, prefer the template match for
            # flexibility (guarantees same P-S match and extra group customization).
            if tail in config_map and config_map[tail][1] > tidx:
                file_map[tail] = config_map[tail][0]
            else:
                template_str = full_path.open('r').read()
                filled_template = self.template_fill(template_str, template_dict)

                config_path = Path(generated_path, tail)
                config_path.write_text(filled_template)
                file_map[tail] = config_path

                generated_config[tail] = generated_paths

        for tail, (full_path, idx) in config_map.items():
            if tail not in file_map:
                file_map[tail] = full_path

        to_symlink: list[tuple[Path, Path]] = []
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

        # run matching scripts for app-specific reload
        script_list = self.get_matching_scripts(
            app_name,
            scheme=scheme,
            palette=palette,
        )

        print(
            f'{y("├─")} ' + Fore.YELLOW + f'{app_name} :: matched ({len(to_symlink)}) config files and ({len(script_list)}) scripts'
        )
        for tail, gen_paths in generated_config.items():
            print(
                f'{y("│")}' + Fore.GREEN + Style.DIM + \
                f'  > generating config "{tail}" from {gen_paths}' + Style.RESET_ALL
            )

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
            print(f'{y("│")}' + Fore.GREEN + f'  > linked {from_p} -> {to_p}')

        for from_p, to_p in links_fail:
            from_p = from_p
            to_p   = to_p.relative_to(self.config_dir)
            print(f'{y("│")}' + Fore.RED + f'  > failed to link {from_p} -> {to_p}')


        for script in script_list:
            print(f'{y("│")}' + Fore.BLUE + f'  > running script "{script.relative_to(self.config_dir)}"')
            output = subprocess.check_output(str(script), shell=True)
            if output:
                fmt_output = output.decode().strip().replace('\n',f'\n{y("│")}    ')
                print(
                    f'{y("│")}' + \
                    Fore.BLUE + Style.DIM + \
                    f'  > captured script output "{fmt_output}"' \
                    + Style.RESET_ALL
                )

    def update_apps(
        self,
        apps: str | list[str] = '*',
        scheme                = 'any',
        palette               = 'any',
        strict=False,
        **kw_groups,
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
                strict=False,
                **kw_groups,
            )
