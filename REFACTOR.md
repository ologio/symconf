- Require all app names be set somewhere in the app registry, even if no variables need to
  be supplied (such as "gnome," which just calls a script based on scheme). This helps
  explicitly define the scope of "*" for applications, and can allow users to keep their
  config files without involving them in any `autoconf` call.
- `scheme: auto` is a valid specification, but it will always resolve to either `light` or
  `dark`. "auto" is not a valid scheme choice when it comes to naming, but it can be used
  when making `autoconf` calls to set palettes that reflect the scheme that is currently
  set (just think of the analogous setting in the browser: auto just means to infer and
  set the local scheme to whatever the system scheme is set to).
- Due `/call`, we no longer have explicit, hard-coded scheme commends in `set_theme.py`.
  Calls to GNOME's portal or to MacOS system settings can now just be seen as another
  "app" with a configurable script, reactive to the passed scheme option.
- Here's the palette/scheme spec model
  * If specific `scheme` and `palette` are provided, files prefixed with
    `<scheme>-<palette>`, `any-<palette>`, or `<scheme>-any` are matched, in that order,
    for each unique file tail, for each app.
  * If `palette` is provided by `scheme` is not, it defaults to `auto` and will attempt to
    infer a specific value, yielding the same case as above.
  * If `scheme` cannot be inferred when `auto`, or is explicitly set to `any`, only
    `any-<palette>` file prefixes are matched. The idea here is that `any` indicates that
    a theme file is explicitly indifferent to the specification of that option, and won't
    interfere in an unintended way. The term `none` would work exactly the same here;
    `any` seems like it might be misleading, indicating it will match with any specific
    palette. In any case (no pun intended), palettes should create files with an `any`
    scheme if want to be considered as a possible setting when the `scheme` is any option,
    i.e., `light/dark/any`.
  * The same goes for `palette`, although it will default to `any` when unspecified. Thus,
    only commands/files that change `scheme` will be considered when `palette` isn't
    given. (I suppose we could also consider an `auto` default here that attempts to
    determine app-specific palettes that are currently set, and switch to their opposite
    `scheme` counterparts if available. You could still explicitly provide `any` to ensure
    you just isolate the `scheme` switch, but `auto` could allow something like a dark to
    light switch that applies to gnome (only supports scheme), changes kitty to
    "tone4-light" (a light counterpart the currently set palette is available), and
    Discord remains the same (as a hypothetical app for which we've created a dark palette
    but no a light one)). I guess the main takeaway with `any`/`auto` is the following: if
    `auto` can resolve to the concrete option currently set for a given app, behave as if
    that option was given. When `any` is provided (or `auto` fails to infer a concrete
    setting), _isolate_ that property (either `scheme` or `palette`) and ensure it doesn't
    change (even when another might, and doing so by only matching theme files that have
    actually used `any`, indicating they actually deliver on the agreed upon behavior
    here).
  * If neither are given, (depending on what we decide), both would be `auto` and should
    do nothing (simply determine the `scheme` and `palette` currently set, requiring no
    updates). If both are `any`, this should also do nothing; `any` is meant to "freeze"
    that property, so we'd just be freezing both of the possible variables. One or both of
    these options could serve as a meaningful refresh, however, either re-symlinking the
    relevant/expected files and/or calling the refresh commands for each apps to ensure
    expected settings are freshly applied.
- Config TOML accepts either `config_dir` or `config_map`, nothing else and only one of
  the two.
- Refresh scripts should likely specify a shell shabang at the top of the file
- `apps` can serve as a dotfiles folder
- Support symlinking whole folders?
- `any` might prefer to match configs with none over specific options, but will match any
