"""
Primary config management abstractions

The config map is a dict mapping from config file **path names** to their
absolute path locations. That is,

.. code-block:: sh

    <config_path_name>
    ->
    <config_dir>/apps/<app_name>/<subdir>/<palette>-<scheme>.<config_path_name>

For example,

.. code-block:: sh

    palette1-light.conf.ini
    ->
    ~/.config/symconf/apps/user/palette1-light.conf.ini

    palette2-dark.app.conf
    ->
    ~/.config/symconf/apps/generated/palette2-dark.app.conf

This ensures we have unique config names pointing to appropriate locations
(which is mostly important when the same config file names are present across
``user`` and ``generated`` subdirectories; unique path names need to be
resolved to unique path locations).
"""

import sys
import tomllib
import subprocess
from pathlib import Path

from colorama import Fore, Style

from symconf import util
from symconf.util import printc, color_text
from symconf.runner import Runner
from symconf.matching import Matcher, FilePart
from symconf.template import FileTemplate, TOMLTemplate


class ConfigManager:
    def __init__(
        self,
        config_dir: str | Path | None = None,
        disable_registry: bool = False,
    ) -> None:
        """
        Configuration manager class

        Parameters:
            config_dir: config parent directory housing expected files
                (registry, app-specific conf files, etc). Defaults to
                ``"$XDG_CONFIG_HOME/symconf/"``.
            disable_registry: disable checks for a registry file in the
                ``config_dir``. Should really only be set when using this
                programmatically and manually supplying app settings.
        """

        if config_dir is None:
            config_dir = util.xdg_config_path()

        self.config_dir = util.absolute_path(config_dir)
        self.apps_dir = Path(self.config_dir, "apps")
        self.group_dir = Path(self.config_dir, "groups")

        self.app_registry = {}
        self.matcher = Matcher()
        self.runner = Runner()

        self._check_dirs()
        if not disable_registry:
            self._check_registry()

    def _check_dirs(self) -> None:
        """
        Check necessary config directories for existence.

        Regardless of programmatic use or ``disable_registry``, we need a valid
        ``config_dir`` and it must have an ``apps/`` subdirectory (otherwise
        there are simply no files to act on, not even when manually providing
        app settings).
        """

        # throw error if config dir doesn't exist
        if not self.config_dir.exists():
            raise ValueError(
                f'Config directory "{self.config_dir}" doesn\'t exist.'
            )

        # throw error if apps dir doesn't exist or is empty
        if not self.apps_dir.exists() or not list(self.apps_dir.iterdir()):
            raise ValueError(
                f'Config directory "{self.config_dir}" must'
                ' have an "apps/" subdirectory.'
            )

    def _check_registry(self) -> None:
        """
        Check the existence and format of the registry file
        ``<config_dir>/app_registry.toml``.

        All that's needed to pass the format check is the existence of the key
        `"app"` in the registry dict. If this isn't present, the TOML file is
        either incorrectly configured, or it's empty and there are no apps to
        operate on.
        """

        registry_path = Path(self.config_dir, "app_registry.toml")

        if not registry_path.exists():
            printc(
                f"No registry file found at expected"
                f' location "{registry_path}"',
                Fore.YELLOW,
            )
            return

        app_registry = tomllib.load(registry_path.open("rb"))

        if "app" not in app_registry:
            printc(
                "Registry file found but is either empty or"
                ' incorrectly formatted (no "app" key).',
                Fore.YELLOW,
            )

        self.app_registry = app_registry.get("app", {})

    def _resolve_group(self, group: str, value: str = "auto") -> str:
        """
        Resolve group inputs to concrete values.

        This method is mostly meant to handle values like ``auto`` which can be
        provided by the user, but need to be interpreted in the system context
        (e.g., either resolving to "any" or using the app's currently set
        option from the cache).
        """

        if value == "auto":
            # look group up in app cache and set to current value
            return "any"

        return value

    def _symlink_paths(
        self,
        to_symlink: list[tuple[Path, Path]],
        user: str | None = None,
    ) -> None:
        """
        Symlink paths safely from target paths to internal config paths.

        This method upholds the consistent symlink model: target locations are
        only symlinked from if they don't exist or are already a symlink. We
        never overwrite any concrete files, preventing accidental deletion of
        config files. This means users must physically delete/move their
        existing configs into a ``symconf`` config directory if they want it to
        be managed; otherwise, we don't touch it.

        Parameters:
            to_symlink: path pairs to symlink, from target (external) path to
                source (internal) path
        """

        links_succ = []
        links_fail = []
        for from_path, to_path in to_symlink:
            if not to_path.exists():
                reason = f'Config path "{to_path}" doesn\'t exist, skipping'
                links_fail.append((from_path, to_path, reason))
                continue

            # if config file being symlinked exists & isn't already a symlink
            # (i.e., previously set by this script), throw an error.
            if from_path.exists() and not from_path.is_symlink():
                reason = (
                    f'Symlink target "{from_path}" exists and isn\'t a '
                    "symlink, NOT overwriting; please first manually remove "
                    "this file so a symlink can be set."
                )
                links_fail.append((from_path, to_path, reason))
                continue

            try:
                self.symlink(from_path, to_path, user)
                links_succ.append((from_path, to_path))
            except Exception as e:
                reason = f"Symlink failed: {e}"
                links_fail.append((from_path, to_path, reason))

        # link report
        for from_p, to_p in links_succ:
            from_p = util.to_tilde_path(from_p)
            to_p = to_p.relative_to(self.config_dir)
            print(
                color_text("│", Fore.BLUE),
                color_text(
                    f" > linked {color_text(from_p, Style.BRIGHT)} "
                    f"-> {color_text(to_p, Style.BRIGHT)}",
                    Fore.GREEN,
                ),
            )

        for from_p, to_p, reason in links_fail:
            from_p = util.to_tilde_path(from_p)
            to_p = to_p.relative_to(self.config_dir)

            print(
                color_text("│", Fore.BLUE),
                color_text(f" > failed to link {from_p} -> {to_p}", Fore.RED),
            )
            print(
                color_text("│", Fore.BLUE),
                color_text(f" > {reason}", Fore.RED + Style.DIM),
            )

    def _matching_template_groups(
        self,
        scheme: str = "auto",
        style: str = "auto",
        **kw_groups: dict,
    ) -> tuple[dict, list[FilePart]]:
        """
        Find matching template files for provided template groups.

        For template groups other than "scheme" and "style," this method
        performs a basic search for matching filenames in the respective group
        directory. For example, a KW group like ``font = "mono"`` would look
        for ``font/mono.toml`` (as well as the relaxation ``font/none.toml``).
        These template TOML files are stacked and ultimately presented to
        downstream config templates to be filled. Note how there is no
        dependence on the scheme during the filename match (e.g., we don't look
        for ``font/mono-dark.toml``).

        For "scheme" and "style," we have slightly different behavior, more
        closely aligning with the non-template matching. We don't have "scheme"
        and "style" template folders, but a single "theme" folder, within which
        we match template files just the same as we do for non-template config
        files. That is, we will look for files of the format

        .. code-block:: sh

            <style>-<scheme>.toml

        The only difference is that, while ``style`` can still include
        arbitrary style variants, it *must* have the form

        .. code-block:: sh

            <variant-1>-...-<variant-N>-<palette>

        if you want to match a ``palette`` template. Palettes are like regular
        template groups, and should be placed in their own template folder. But
        when applying those palette colors, they almost always need to be
        coupled with a scheme setting (e.g., "solarized-dark"). This is the one
        place where the templating system allows "intermediate templates:" raw
        palette colors can fill theme templates, which then fill user config
        templates.

        So in summary: palette files can be used to populate theme templates by
        providing a style string that matches the format
        ``<variant>-<palette>``. The ``<palette>`` will be extracted and used
        to match filenames in the palette template folder. The term
        ``<variant>-<palette>-<scheme>`` will be used to match templates in the
        theme folder, where ``<variant>-<palette> = <style>`` and ``<scheme>``
        are independently specifiable with supported for ``auto``, ``none``,
        etc.

        Note that "strictness" doesn't really apply in this setting. In the
        non-template config matching setting, setting strict means there's no
        relaxation to "none," but here, any "none" group template files just
        help fill any gaps (but are otherwise totally overwritten, even if
        matched, by more precise matches). You can match ``nones`` directly if
        you want by specifying that directly. ``get_matching_scripts()`` is
        similar in this sense.
        """

        scheme = self._resolve_group("scheme", scheme)
        style = self._resolve_group("style", style)

        groups = {k: self._resolve_group(k, v) for k, v in kw_groups.items()}

        if not self.group_dir.exists():
            return {}, []

        # palette lookup will behave like other groups; strip it out of the
        # `style` string and it to the keyword groups to be searched regularly
        # (but only if the palette group exists)
        if Path(self.group_dir, "palette").exists():
            palette = style.split("-")[-1]
            groups["palette"] = palette

        # handle individual groups (not part of joint style-scheme)
        group_matches = {}
        for fkey, fval in groups.items():
            key_group_dir = Path(self.group_dir, fkey)

            if not key_group_dir.exists():
                print(f'Group directory "{fkey}" doesn\'t exist, skipping')
                continue

            # mirror matching scheme: 1) prefix order, 2) full enumeration, 3)
            # select best, 4) make unique, 5) ordered relaxation
            stem_map = {path.stem: path for path in key_group_dir.iterdir()}

            # 1) establish prefix order
            prefix_order = [fval, "none"] if fval == "any" else ["none", fval]

            # 2) fully enumerate matches, including "any"
            matches = []
            for prefix in prefix_order:
                matches.extend(
                    [
                        stem
                        for stem in stem_map
                        if prefix == stem or prefix == "any"
                    ]
                )

            if not matches:
                # no matches for group, skip
                continue

            # 3) select best matches; done in a loop to smooth the logic, else
            # we'd need to check if the last match is "none," and if not, find
            # out if it was available. This alone makes the following loop more
            # easy to follow: walk through full enumeration, and if it's the
            # target match or "none," take the file, nicely handling the fact
            # those may both be the same.
            #
            # also 4) uniqueness happening here
            match_dict = {}
            target = matches[-1]  # select best based on order, make new target
            for stem in matches:
                if stem == target or stem == "none":
                    match_dict[stem] = stem_map[stem]

            group_matches[fkey] = list(match_dict.values())

        # first handle scheme maps; matching palette files should already be
        # found in the regular group matching process. This is the one template
        # group that gets nested treatment
        palette_dict = TOMLTemplate.stack_toml(
            group_matches.get("palette", [])
        )

        # then palette-scheme groups (require 2-combo logic)
        theme_matches = []
        theme_group_dir = Path(self.group_dir, "theme")

        if theme_group_dir.exists():
            theme_matches = self.matcher.match_paths(
                theme_group_dir.iterdir(),  # match files in groups/theme/
                self.matcher.prefix_order(
                    scheme, style
                ),  # reg non-template order
            )

        # 5) final match relaxation
        relaxed_theme_matches = self.matcher.relaxed_match(theme_matches)

        theme_dict = {}
        for file_part in relaxed_theme_matches:
            toml_dict = TOMLTemplate(file_part.path).fill_dict(palette_dict)
            theme_dict = util.deep_update(theme_dict, toml_dict)

        template_dict = {
            group: TOMLTemplate.stack_toml(ordered_matches)
            for group, ordered_matches in group_matches.items()
        }
        template_dict["theme"] = theme_dict

        return template_dict, relaxed_theme_matches

    def _prepare_all_templates(
        self,
        scheme: str = "any",
        style: str = "any",
    ) -> dict[str, dict]:
        palette_map = {}
        palette_group_dir = Path(self.group_dir, "palette")
        if palette_group_dir.exists():
            for palette_path in palette_group_dir.iterdir():
                palette_map[palette_path.stem] = palette_path

        palette_base = []
        if "none" in palette_map:
            palette_base.append(palette_map["none"])

        # then palette-scheme groups (require 2-combo logic)
        theme_matches = []
        theme_group_dir = Path(self.group_dir, "theme")
        if theme_group_dir.exists():
            theme_matches = self.matcher.match_paths(
                theme_group_dir.iterdir(),  # match files in groups/theme/
                self.matcher.prefix_order(  # reg non-template order
                    scheme,
                    style,
                    strict=True,  # set strict=True to ignore "nones"
                ),
            )

        theme_map = {}
        for fp in theme_matches:
            # still look through whole theme dir here (eg to match nones)
            theme_matches = self.matcher.match_paths(
                theme_group_dir.iterdir(),  # match files in groups/theme/
                self.matcher.prefix_order(
                    fp.scheme, fp.style
                ),  # reg non-template order
            )
            relaxed_theme_matches = self.matcher.relaxed_match(theme_matches)

            palette = fp.style.split("-")[-1]
            palette_paths = [*palette_base]
            if palette in palette_map:
                palette_paths.append(palette_map[palette])

            theme_dict = {}
            palette_dict = TOMLTemplate.stack_toml(palette_paths)
            for file_part in relaxed_theme_matches:
                toml_template = TOMLTemplate(file_part.path)
                toml_dict = toml_template.fill_dict(palette_dict)
                theme_dict = util.deep_update(theme_dict, toml_dict)

            theme_map[fp.path.stem] = {"theme": theme_dict}

        return theme_map

    def get_matching_configs(
        self,
        app_name: str,
        scheme: str = "auto",
        style: str = "auto",
        strict: bool = False,
    ) -> dict[str, FilePart]:
        """
        Get user-provided app config files that match the provided scheme and
        style specifications.

        Unique config file path names are written to the file map in order of
        specificity. All config files follow the naming scheme
        ``<style>-<scheme>.<path-name>``, where ``<style>-<scheme>`` is the
        "theme part" and ``<path-name>`` is the "conf part." For those config
        files with the same "conf part," only the entry with the most specific
        "theme part" will be stored. By "most specific," we mean those entries
        with the fewest possible components named ``none``, with ties broken in
        favor of a more specific ``style`` (the only "tie" really possible here
        is when ``none-<scheme>`` and ``<style>-none`` are both available, in
        which case the latter will overwrite the former).

        .. admonition:: Edge cases

            There are a few quirks to this matching scheme that yield
            potentially unintuitive results. As a recap:

            - The "theme part" of a config file name includes both a style
              (palette and more) and a scheme component. Either of those parts
              may be "none," which simply indicates that that particular file
              does not attempt to change that factor. "none-light," for
              instance, might simply set a light background, having no effect
              on other theme settings.
            - Non-keyword queries for scheme and style will always be matched
              exactly. However, if an exact match is not available, we also
              look for "none" in each component's place. For example, if we
              wanted to set "solarized-light" but only "none-light" was
              available, it would still be set because we can still satisfy the
              desire scheme (light). The same goes for the style specification,
              and if neither match, "none-none" will always be matched if
              available. Note that if "none" is specified exactly, it will be
              matched exactly, just like any other value.
            - During a query, "any" may also be specified for either component,
              indicating we're okay to match any file's text for that part. For
              example, if I have two config files ``"p1-dark"`` and
              ``"p2-dark"``, the query for ``("any", "dark")`` would suggest
              I'd like the dark scheme but am okay with either style.

            It's under the "any" keyword where possibly counter-intuitive
            results may come about. Specifying "any" does not change the
            mechanism that seeks to optionally match "none" if no specific
            match is available. For example, suppose we have the config file
            ``red-none`` (setting red colors regardless of a light/dark mode).
            If I query for ``("any", "dark")``, ``red-none`` will be matched
            (supposing there are no more direct matches available). Because we
            don't a match specifically for the scheme "dark," it gets relaxed
            to "none." But we indicated we're okay to match any style. So
            despite asking for a config that sets a dark scheme and not caring
            about the style, we end up with a config that explicitly does
            nothing about the scheme but sets a particular style. This matching
            process is still consistent with what we expect the keywords to do,
            it just slightly muddies the waters with regard to what can be
            matched (mostly due to the amount that's happening under the hood
            here).

            This example is the primary driver behind the optional ``strict``
            setting, which in this case would force the dark scheme to be
            matched (and ultimately find no matches).

            Also: when "any" is used for a component, options with "none" are
            prioritized, allowing "any" to be as flexible and unassuming as
            possible (only matching a random specific config among the options
            if there is no "none" available).

        Returns:
            Dictionary
        """

        user_app_dir = Path(self.apps_dir, app_name, "user")

        paths = []
        if user_app_dir.is_dir():
            paths = user_app_dir.iterdir()

        # 1) establish prefix order
        prefix_order = self.matcher.prefix_order(
            self._resolve_group("scheme", scheme),
            self._resolve_group("style", style),
            strict=strict,
        )

        # 2) match enumeration
        ordered_matches = self.matcher.match_paths(paths, prefix_order)

        # 3) make unique (by pathname)
        matching_file_map = {
            file_part.conf: file_part for file_part in ordered_matches
        }

        return matching_file_map

    def get_matching_templates(
        self,
        app_name: str,
        scheme: str = "auto",
        style: str = "auto",
        **kw_groups: dict,
    ) -> tuple[dict[str, Path], dict, list[FilePart], int]:
        template_dict, theme_matches = self._matching_template_groups(
            scheme=scheme,
            style=style,
            **kw_groups,
        )

        max_idx = 0
        if theme_matches:
            max_idx = max([fp.index for fp in theme_matches])

        template_map = {}
        template_dir = Path(self.apps_dir, app_name, "templates")
        if template_dir.is_dir():
            for template_file in template_dir.iterdir():
                template_map[template_file.name] = template_file

        return template_map, template_dict, theme_matches, max_idx

    def get_matching_scripts(
        self,
        app_name: str,
        scheme: str = "any",
        style: str = "any",
    ) -> list[FilePart]:
        """
        Execute matching scripts in the app's ``call/`` directory.

        Scripts need to be placed in

        .. code-block:: sh

            <config_dir>/apps/<app_name>/call/<style>-<scheme>.sh

        and are matched using the same heuristic employed by config file
        symlinking procedure (see ``get_matching_configs()``), albeit with a
        forced ``prefix_order``, ordered by increasing specificity. The order
        is then reversed, and the final list orders the scripts by the first
        time they appear (intention being to reload specific settings first).

        TODO: consider running just the most specific script? Users might want
        to design their scripts to be stackable, or they may just be
        independent.
        """

        app_dir = Path(self.apps_dir, app_name)
        call_dir = Path(app_dir, "call")

        if not call_dir.is_dir():
            return []

        prefix_order = [
            ("none", "none"),
            ("none", scheme),
            (style, "none"),
            (style, scheme),
        ]

        script_matches = self.matcher.match_paths(
            call_dir.iterdir(), prefix_order=prefix_order
        )
        relaxed_matches = self.matcher.relaxed_match(script_matches)

        # flip list to execute by decreasing specificity
        return relaxed_matches[::-1]

    def update_app_config(
        self,
        app_name: str,
        app_settings: dict = None,
        scheme: str = "any",
        style: str = "any",
        strict: bool = False,
        **kw_groups: dict,
    ) -> None:
        """
        Perform full app config update process, applying symlinks and running
        scripts.

        Note that this explicitly accepts app settings to override or act in
        place of missing app details in the app registry file. This is mostly
        to provide more programmatic control and test settings without needing
        them present in the registry file. The ``update_apps()`` method,
        however, **will** more strictly filter out those apps not in the
        registry, accepting a list of app keys that ultimately call this
        method.

        Note: symlinks point **from** the target location **to** the known
        internal config file; can be a little confusing.

        .. admonition:: Logic overview

            This method is the center point of the ConfigManager class. It
            unifies the user and template matching, file generation, setting of
            symlinks, and running of scripts. At a high level,

            1. An app name (e.g., kitty), app settings (e.g., a ``config_dir``
               or ``config_map``), scheme (e.g., "dark"), and style (e.g.,
               "soft-gruvbox")
            2. Get matching user config files via ``get_matching_configs()``
            3. Get matching template config files and the aggregate template
               dict via ``get_matching_templates()``
            4. Interleave the two result sets by pathname and match quality.
               Template matches are preferred in the case of tied scores. This
               resolves any pathname clashes across matching files.

               This is a particularly important step. It compares concrete
               config names explicitly provided by the user (e.g.,
               ``soft-gruvbox-dark.kitty.conf``) with named TOML files in a
               group directory (e.g,. ``theme/soft-gruvbox-dark.toml``). We
               have to determine whether the available templates constitute a
               better match than the best user option, which is done by
               comparing the level in the prefix order (the index) where the
               match takes place.

               Templates are generally more flexible, and other keywords may
               also provide a matching template group (e.g., ``-T font=mono``
               to match some font-specific settings). When the match is
               otherwise equally good (e.g., both style and scheme match
               directly), we prefer the template due to its general portability
               and likelihood of being more up-to-date. We also don't
               explicitly use the fact auxiliary template groups might be
               matched by the user's input: we only compare the user and
               template configs on the basis of the quality of the style-scheme
               match. This effectively means additional template groups (e.g.,
               font) don't "count" if the basis style-scheme doesn't win over a
               user config file. There could be an arbitrary number of other
               template group matches, but they don't contribute to the match
               quality. For instance, a concrete user config
               ``solarized-dark.kitty.conf`` will be selected over
               ``solarized-none.toml`` plus 10 other matching theme elements if
               the user asked for ``-s dark -t solarized``.
            5. For those template matches, fill/generate the template file and
               place it in the app's ``generated/`` directory.

        Parameters:
            app_name: name of the app whose config files should be updated
            app_settings: dict of app settings (i.e., ``config_dir`` or
                ``config_map``)
            scheme: scheme spec
            style: style spec
            strict: whether to match ``scheme`` and ``style`` strictly
        """

        if app_settings is None:
            app_settings = self.app_registry.get(app_name, {})

        if "config_dir" in app_settings and "config_map" in app_settings:
            print(f'App "{app_name}" incorrectly configured, skipping')
            return

        # get possibly specified user
        user = app_settings.get("user")

        # match both user configs and templates
        # -> "*_map" are dicts from config pathnames to FilePart / Paths
        config_map = self.get_matching_configs(
            app_name,
            scheme=scheme,
            style=style,
            strict=strict,
        )
        template_map, template_dict, theme_matches, tidx = (
            self.get_matching_templates(
                app_name, scheme=scheme, style=style, **kw_groups
            )
        )

        # create "generated" directory for the app
        generated_path = Path(self.apps_dir, app_name, "generated")
        generated_path.mkdir(parents=True, exist_ok=True)

        # track selected configs with a pathname -> fullpath map
        final_config_map = {}
        # tracker for template configs that were generated
        generated_config = []

        # interleave user and template matches
        for pathname, full_path in template_map.items():
            if pathname in config_map and config_map[pathname].index > tidx:
                final_config_map[pathname] = config_map[pathname].path
            else:
                config_path = Path(generated_path, pathname)
                config_path.write_text(
                    FileTemplate(full_path).fill(template_dict)
                )
                final_config_map[pathname] = config_path
                generated_config.append(pathname)

        # fill in any config matches not added to final_config_map above
        for pathname, file_part in config_map.items():
            if pathname not in final_config_map:
                final_config_map[pathname] = file_part.path

        # prepare symlinks (inverse loop and conditional order is sloppier)
        to_symlink: list[tuple[Path, Path]] = []
        if "config_dir" in app_settings:
            config_dir = util.absolute_path(app_settings["config_dir"])
            for ext_pathname, int_fullpath in final_config_map.items():
                ext_fullpath = Path(config_dir, ext_pathname)
                to_symlink.append(
                    (
                        ext_fullpath,  # point from external config dir
                        int_fullpath,  # to internal config location
                    )
                )
        elif "config_map" in app_settings:
            for ext_pathname, int_fullpath in final_config_map.items():
                # app's config map points config pathnames to absolute paths
                if ext_pathname in app_settings["config_map"]:
                    ext_fullpath = util.absolute_path(
                        app_settings["config_map"][ext_pathname]
                    )
                    to_symlink.append(
                        (
                            ext_fullpath,  # point from external config path
                            int_fullpath,  # to internal config location
                        )
                    )

        # run matching scripts for app-specific reload
        script_list = self.get_matching_scripts(
            app_name,
            scheme=scheme,
            style=style,
        )
        script_list = [f.path for f in script_list]

        # print match messages
        num_links = len(to_symlink)
        num_scripts = len(script_list)

        if user is None:
            print(
                color_text("├─", Fore.BLUE),
                f"{app_name} :: matched {num_links} config files, "
                f"{num_scripts} scripts",
            )
        else:
            print(
                color_text("├─", Fore.BLUE),
                f"{app_name}@user:{user} :: matched {num_links} config files, "
                f"{num_scripts} scripts",
            )

        rel_theme_matches = " < ".join(
            [str(fp.path.relative_to(self.group_dir)) for fp in theme_matches]
        )
        for pathname in generated_config:
            print(
                color_text("│", Fore.BLUE),
                color_text(
                    f' > generating config "{pathname}" from '
                    f"[{rel_theme_matches}]",
                    Style.DIM,
                ),
            )

        self._symlink_paths(to_symlink, user)
        self.runner.run_many(script_list)

    def configure_apps(
        self,
        apps: str | list[str] = "*",
        scheme: str = "any",
        style: str = "any",
        strict: bool = False,
        **kw_groups: dict,
    ) -> None:
        if apps == "*":
            # get all registered apps
            app_list = list(self.app_registry.keys())
        else:
            # get requested apps that overlap with registry
            app_list = [a for a in apps if a in self.app_registry]

        if not app_list:
            print(f'None of the apps "{apps}" are registered, exiting')
            return

        print("> symconf parameters: ")
        print(f"  > registered apps :: {color_text(app_list, Fore.YELLOW)}")
        print(f"  > style           :: {color_text(style, Fore.YELLOW)}")
        print(f"  > scheme          :: {color_text(scheme, Fore.YELLOW)}\n")

        for app_name in app_list:
            app_dir = Path(self.apps_dir, app_name)
            if not app_dir.exists():
                # app has no directory, skip it
                continue

            self.update_app_config(
                app_name,
                app_settings=self.app_registry[app_name],
                scheme=scheme,
                style=style,
                strict=False,
                **kw_groups,
            )

    def _app_action(
        self,
        script_pathname: str,
        apps: str | list[str] = "*",
    ) -> None:
        """
        Execute a static script-based action for a provided set of apps.

        Mostly a helper method for install and update actions, calling a static
        script name under each app's directory.
        """

        if apps == "*":
            # get all registered apps
            app_list = list(self.app_registry.keys())
        else:
            # get requested apps that overlap with registry
            app_list = [a for a in apps if a in self.app_registry]

        if not app_list:
            print(f'None of the apps "{apps}" are registered, exiting')
            return

        print(
            f"> symconf parameters: "
            f"  > registered apps :: {color_text(app_list, Fore.YELLOW)}"
        )

        for app_name in app_list:
            target_script = Path(self.apps_dir, app_name, script_pathname)
            if not target_script.exists():
                continue

            self.runner.run_script(target_script)

    def install_apps(
        self,
        apps: str | list[str] = "*",
    ) -> None:
        self._app_action("install.sh", apps)

    def update_apps(
        self,
        apps: str | list[str] = "*",
    ) -> None:
        self._app_action("update.sh", apps)

    def generate_app_templates(
        self,
        gen_dir: str | Path,
        apps: str | list[str] = "*",
        scheme: str = "any",
        style: str = "any",
        **kw_groups: dict,
    ) -> None:
        if apps == "*":
            app_list = list(self.app_registry.keys())
        else:
            app_list = [a for a in apps if a in self.app_registry]

        if not app_list:
            print(f'None of the apps "{apps}" are registered, exiting')
            return

        print("> symconf parameters: ")
        print(f"  > registered apps :: {color_text(app_list, Fore.YELLOW)}")
        print("> Writing templates...")

        gen_dir = util.absolute_path(gen_dir)
        theme_map = self._prepare_all_templates(scheme, style)

        for app_name in app_list:
            app_template_dir = Path(self.apps_dir, app_name, "templates")
            if not app_template_dir.exists():
                continue

            app_template_files = list(app_template_dir.iterdir())
            self.get_matching_templates(
                app_name, scheme=scheme, style=style, **kw_groups
            )

            num_temps = len(app_template_files)
            num_themes = len(theme_map)
            print(
                color_text("├─", Fore.BLUE),
                f"{app_name} :: generating ({num_temps}) "
                f"templates from ({num_themes}) themes",
            )

            for template_file in app_template_files:
                app_template = FileTemplate(template_file)

                for theme_stem, theme_dict in theme_map.items():
                    tgt_template_dir = Path(gen_dir, app_name)
                    tgt_template_dir.mkdir(parents=True, exist_ok=True)

                    tgt_template_path = Path(
                        tgt_template_dir, f"{theme_stem}.{template_file.name}"
                    )
                    filled_template = app_template.fill(theme_dict)
                    tgt_template_path.write_text(filled_template)

                    print(
                        color_text("│", Fore.BLUE),
                        f'>  generating "{tgt_template_path.name}"',
                    )

    def symlink(
        self,
        from_path: Path,
        to_path: Path,
        user: str | None = None,
    ) -> None:
        # attempt in-built pathlib symlink
        if user is None:
            # create parent directory if doesn't exist
            from_path.parent.mkdir(parents=True, exist_ok=True)

            # if path doesn't exist, or exists and is a symlink, remove the
            # symlink in preparation for the new symlink setting
            from_path.unlink(missing_ok=True)

            # attempt to set symlink
            Path(from_path).symlink_to(Path(to_path))

            return

        # otherwise bottle up and run as specified user w/ permissions
        # this looks sorta silly but I frankly think it's the easiest way to
        # compactly set up a symlink procedure under an elevated subprocess (we
        # *have* to wrap this up; can't do it in the current process)
        compact_symlink_py = (
            "import os,sys,pathlib;"
            "p=pathlib.Path(sys.argv[1]).parent;"
            "p.mkdir(parents=True,exist_ok=True);"
            "pathlib.Path(sys.argv[1]).unlink(missing_ok=True);"
            "pathlib.Path(sys.argv[1]).symlink_to(sys.argv[2])"
        )

        sudo_prompt = (
            color_text("│  > ", Fore.BLUE)
            + color_text(
                f"[symlinks require {user} permissions]",
                Fore.RED + Style.BRIGHT,
            )
            + color_text(" password for %p: ", Fore.RED)
        )

        subprocess.run(
            [
                "sudo",
                "-u",
                user,
                "-p",
                sudo_prompt,
                sys.executable,
                "-c",
                compact_symlink_py,
                str(from_path),
                str(to_path),
            ],
            check=True,
        )
