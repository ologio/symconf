"""
Generic combinatorial name-matching subsystem

Config files are expected to have names matching the following spec:

.. code-block:: sh

    <style>-<scheme>.<config_pathname>

- ``config_pathname``: refers to a concrete filename, typically that which is
  expected by the target app (e.g., ``kitty.conf``). In the context of
  ``config_map`` in the registry, however, it merely serves as an identifier,
  as it can be mapped onto any path.
- ``scheme``: indicates the lightness mode ("light" or "dark")
- ``style``: general identifier capturing the stylizations applied to the
  config file. This is typically of the form ``<variant>-<palette>``, i.e.,
  including a reference to a particular color palette.

For example

.. code-block:: sh

    soft-gruvbox-dark.kitty.conf

gets mapped to

.. code-block:: sh

    style    -> "soft-gruvbox"
    scheme   -> "dark"
    pathname -> "kitty.conf"
"""

from pathlib import Path

from symconf import util


class FilePart:
    def __init__(self, path: str | Path) -> None:
        self.path = util.absolute_path(path)
        self.pathname = self.path.name

        parts = str(self.pathname).split(".")
        if len(parts) < 2:
            raise ValueError(
                f'Filename "{self.pathname}" incorrectly formatted, ignoring'
            )

        self.theme = parts[0]
        self.conf = ".".join(parts[1:])

        theme_split = self.theme.split("-")
        self.scheme = theme_split[-1]
        self.style = "-".join(theme_split[:-1])

        self.index = -1

    def set_index(self, idx: int) -> None:
        self.index = idx


class Matcher:
    def get_file_parts(
        self,
        paths: list[str | Path],
    ) -> list[FilePart]:
        """
        Split pathnames into parts for matching.

        Pathnames should be of the format

        .. code-block:: sh

            <style>-<scheme>.<config_pathname>

        where ``style`` is typically itself of the form
        ``<variant>-<palette>``.
        """

        file_parts = []
        for path in paths:
            try:
                config_file = FilePart(path)
                file_parts.append(config_file)
            except ValueError:
                print(f'Filename "{path}" incorrectly formatted, ignoring')

        return file_parts

    def prefix_order(
        self,
        scheme: str,
        style: str,
        strict: bool = False,
    ) -> list[tuple[str, str]]:
        """
        Determine the order of concrete config pathname parts to match, given
        the ``scheme`` and ``style`` inputs.

        There is a unique preferred match order when ``style``, ``scheme``,
        both, or none are ``any``. In general, when ``any`` is provided for a
        given factor, it is best matched by a config file that expresses
        indifference under that factor.
        """

        # explicit cases are the most easily managed here, even if a little
        # redundant
        if strict:
            theme_order = [
                (style, scheme),
            ]
        else:
            # inverse order of match relaxation; intention being to overwrite
            # with results from increasingly relevant groups given the
            # conditions
            if style == "any" and scheme == "any":
                # prefer both be "none", with preference for specific scheme
                theme_order = [
                    (style, scheme),
                    (style, "none"),
                    ("none", scheme),
                    ("none", "none"),
                ]
            elif style == "any":
                # prefer style to be "none", then specific, then relax specific
                # scheme to "none"
                theme_order = [
                    (style, "none"),
                    ("none", "none"),
                    (style, scheme),
                    ("none", scheme),
                ]
            elif scheme == "any":
                # prefer scheme to be "none", then specific, then relax
                # specific style to "none"
                theme_order = [
                    ("none", scheme),
                    ("none", "none"),
                    (style, scheme),
                    (style, "none"),
                ]
            else:
                # neither component is any; prefer most specific
                theme_order = [
                    ("none", "none"),
                    ("none", scheme),
                    (style, "none"),
                    (style, scheme),
                ]

        return theme_order

    def match_paths(
        self,
        paths: list[str | Path],
        prefix_order: list[tuple[str, str]],
    ) -> list[FilePart]:
        """
        Find and return FilePart matches according to the provided prefix
        order.

        The prefix order specifies all valid style-scheme combos that can be
        considered as "consistent" with some user input (and is computed
        external to this method). For example, it could be

        .. code-block:: python

            [("none", "none")("none", "dark")]

        indicating that either ``none-none.<config>`` or ``none-dark.<config>``
        would be considered matching pathnames, with the latter being
        preferred.

        This method exists because we need a way to allow any of the combos in
        the prefix order to match the candidate files. We don't know a priori
        how good of a match will be available, so we consider each file for
        each of the prefixes, and take the latest/best match for each unique
        config pathname (allowing for a "soft" match).

        .. admonition:: Checking for matches

            When thinking about how best to structure this method, it initially
            felt like indexing factors of the FileParts would make the most
            sense, preventing the inner loop that needs to inspect each
            FilePart for each element of the prefix order. But indexing the
            file parts and checking against prefixes isn't so straightforward,
            as we'd still need to check matches by factor. For instance, if we
            index by style-scheme, either are allowed to be "any," so we'd need
            to check for the 4 valid combos and join the matching lists. If we
            index by both factors individually, we may have several files
            associated with a given key, and then need to coordinate the checks
            across both to ensure they belong to the same file.

            In any case, you should be able to do this in a way that's a bit
            more efficient, but the loop and the simple conditionals is just
            much simpler to follow. We're also talking about at most 10s of
            files, so it really doesn't matter.

        Parameters:
            pathnames:
            scheme:
            style:
            prefix_order:
            strict:
        """

        file_parts = self.get_file_parts(paths)

        ordered_matches = []
        for i, (style_prefix, scheme_prefix) in enumerate(prefix_order):
            for fp in file_parts:
                style_match = style_prefix == fp.style or style_prefix == "any"
                scheme_match = (
                    scheme_prefix == fp.scheme or scheme_prefix == "any"
                )

                if style_match and scheme_match:
                    fp.set_index(i + 1)
                    ordered_matches.append(fp)

        return ordered_matches

    def relaxed_match(self, match_list: list[FilePart]) -> list[FilePart]:
        """
        Isolate the best match in a match list and find its relaxed variants.

        This method allows us to use the ``match_paths()`` method for matching
        templates rather than direct user config files. In the latter case, we
        want to symlink the single best config file match for each stem, across
        all stems with matching prefixes (e.g., ``none-dark.config.a`` and
        ``solarized-dark.config.b`` have two separate stems with prefixes that
        could match ``scheme=dark, style=any`` query). We can find these files
        by just indexing the ``match_path`` outputs (i.e., all matches) by
        config pathname and taking the one that appears latest (under the
        prefix order) for each unique value.

        In the template matching case, we want only a single best file match,
        period (there's really no notion of "config stems," it's just the
        prefixes). Once that match has been found, we can then "relax" either
        the scheme or style (or both) to ``none``, and if the corresponding
        files exist, we use those as parts of the template keys. For example,
        if we match ``solarized-dark.toml``, we would also consider the values
        in ``none-dark.toml`` if available. The TOML values that are defined in
        the most specific (i.e., better under the prefix order) match are
        loaded "on top of" those less specific matches, overwriting keys when
        there's a conflict. ``none-dark.toml``, for instance, might define a
        general dark scheme background color, but a more specific definition in
        ``solarized-dark.toml`` would take precedent. These TOML files would be
        stacked before using the resulting dictionary to populate config
        templates.
        """

        if not match_list:
            return []

        relaxed_map = {}
        match = match_list[-1]

        for fp in match_list:
            style_match = fp.style == match.style or fp.style == "none"
            scheme_match = fp.scheme == match.scheme or fp.scheme == "none"

            if style_match and scheme_match:
                relaxed_map[fp.pathname] = fp

        return list(relaxed_map.values())
