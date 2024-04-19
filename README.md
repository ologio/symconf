# autoconf
The `autoconf` project is an attempt at wrangling the complexity of configuring many
applications across one's Linux system. It provides a simple operational model for pulling
many application config files into one place, as well as generating/setting color schemes
across apps.

Quick terminology rundown for theme-related items:

- **Theme**: loose term referring generally to the overall aesthetic of a visual setting.
  Ignoring stylistic changes (only applicable to some apps; example here might be a
  a particular setting of the `waybar` layout), a theme is often just the wrapper term for
  a choice of color _palette_ and _scheme_. For example, "tone4-light" could be a _theme_
  setting for an app like `kitty`, referring to both a palette and scheme.
- **Palette**: a set of base colors used to style text or other aspects of an app's
  displayed assets
- **Scheme**: an indication of lightness, typically either "light" or "dark.

As far as managing settings across apps, there are current two useful classifications
here:

1. **Inseparable from theme**: some apps (e.g., `sway`, `waybar`) have color scheme
   components effectively built in to their canonical configuration file. This can make it
   hard to set themes dynamically, as it would likely require some involved
   matching/substitution rules. This is not a level of complexity I'm willing to embrace,
   so we simply split the config files according to theme and/or scheme.
2. **Can load an external theme file**: some apps (e.g., `kitty`) have a clear mechanism
   for loading themes. This typically implies some distinct color format, although usually
   somewhat easy to generate (don't have to navigate non-color settings, for instance).
   Such apps allow for an even less "invasive" config swapping process when setting a new
   theme, as one can just swap out the external theme file.

To be clear on operation implications here: apps of type (1) must have _manually
maintained_ config variations according the desired themes. General theme settings must
follow the naming scheme `<app-name>-<palette>-<scheme>.<ext>`. For example, if I wanted to set
`sway` to a light variation (which, at the time of writing, would just entail changing a
single background color), I must have explicitly created a `sway-tone4-light.conf` file
that captures this setting. The canonical config file will then be symlinked to the
theme-specific file when the theme is set. (Note that the palette in this example is pretty much
irrelevant, but it needs to be present in order to match the overarching setting; here you
can just think of the format being `<app-name>-<theme>.<ext>`, where `tone4-light` is the
provided theme name.)

For apps of type (2), the canonical config file can remain untouched so long as it refers
to a fixed, generic theme file. For example, with `kitty`, my config file can point to a
`current-theme.conf` file, which will be symlinked to a specific theme file here in
`autoconf` when a change is requested. This enables a couple of conveniences:

- The true config directory on disk remains unpolluted with theme variants.
- If the set theme is regenerated, there is no intervention necessary to propagate its
  changes to the target app. The symlinked file itself will be updated when the theme
  does, ensuring the latest theme version is always immediately available and pointed to
  by the app.

Keep in mind that some apps may fall into some grey area here, allowing some external
customization but locking down other settings internally. In such instances, there's no
need to overcomplicate things; just stick to explicit config variants under the type (1)
umbrella. Type (2) only works for generated themes anyhow; even if the target app can load
an external theme, type (1) should be used if preset themes are fixed.

## Naming standards
To keep things simple, we use a few fixed naming standards for setting app config files
and their themed counterparts. The app registry requires each theme-eligible app to
provide a config directory (`config_dir`), containing some canonical config file
(`config_file`) and to serve as a place for theme-specific config variations. The
following naming schemes must be used in order for theme switching to behave
appropriately: 

- When setting a theme for a particular app, the following variables will be available:
    * `<app-name>`
    * `<palette>`
    * `<scheme>`
- For apps with `external_theme = False`, config variants must named as
  `<app-name>-<palette>-<scheme>.<ext>`, where `<ext>` is the app's default config file
  extension.
- For apps with `external_theme = True`, the file `<config-dir>/current-theme.conf` will
  be used when symlinking the requested theme. The config file thus must point to this
  file in order to change with the set theme.

  Additionally, the theme symlink will be created from the file

  ```
  <autoconf-root>/autoconf/themes/<palette>/apps/<app-name>/generated/<scheme>.conf
  ```

  to `<config-dir>/current-theme.conf`. 

## Directory structure

- `autoconf/`: main repo directory
    * `config/`: app-specific configuration files. Each folder inside this directory is
      app-specific, and the target of associated copy operations when a config sync is
      performed. Nothing in this directory should pertain to any repo functionality; it
      should only contain config files that originated elsewhere on the system.
    * `themes/`: app-independent theme data files. Each folder in this directory should
      correspond to a specific color palette and house any relevant color spec files
      (currently likely be a `colors.json`). Also servers the output location for
      generated theme files
        * `<palette>/colors.json`: JSON formatted color key-value pairings for palette
          colors. There's no standard here aside from the filename and format; downstream
          app-specific TOML templates can be dependent on any key naming scheme within the
          JSON.
        + `<palette>/apps/<app-name>/templates/`: houses the TOML maps for the color
          palette `<palette>` under app `<app-name>`. Files `<fname>.toml` will be mapped to
          `<fname>.conf` in the theme output folder (below), so ensure the naming
          standards align with those outlined above.
        + `<palette>/apps/<app-name>/generated/`: output directory for generated scheme
          variants. These are the symlink targets for dynamically set external themes.
    * `app_registry.toml`: global application "registry" used by sync and theme-setting
      scripts. This lets apps be dynamically added or removed from being eligible for
      config-related operations.

## Scripts

`set_theme.py`: sets a theme across select apps.

- Applies to specific app with `-a <app>` , or to all apps in the `app_registry.toml` with
  `-a "*"`.
- Uses symlinks to set canonical config files to theme-based variations. Which files get
  set depends on the _app type_ (see above), which really just boils down to whether
  theming (1) can be specified with an external format, and (2) if it depends on
  auto-generated theme files from within `autoconf`.
- Palette and scheme are specified as expected. They are used to infer proper paths
  according to naming and structure standards.
- Real config files will never be overwritten. To begin setting themes with the script,
  you must delete the canonical config file expected by the app (and specified in the app
  registry) to allow the first symlink to be set. From there on out, symlinks will be
  automatically flushed.
- A report will be provided on which apps were successfully set to the requested theme,
  along with the file stems. A number of checks are in place for the existence of involved
  files and directories. Overall, the risk of overwritting a real config file is low; we
  only flush existing symlinks, and if the would-be target for the requested theme (be it
  from an auto-generated theme file, or from a manually manage config variant) doesn't
  exist, that app's config will be completed skipped. Essentially, everything must be in
  perfect shape before the symlink trigger is officially pulled.


`gen_theme.py`: generates theme files for palettes by mapping their color definitions
through app-specific templates. These templates specific how to relate an app's theme
variables to the color names provided by the template.

- An app and palette are the two required parameters. If no template or output paths are
  provided, they will be inferred according to the theme path standards seen above.
- The `--template` argument can be a directory or a file, depending on what theme files
  you'd like to render.
- The `--output` path, if specified, must be a directory. Generated theme files take on
  a name with the same stem as their source template, but using the `.conf` extension.
- The TOML templates should make config variable names to JSON dot-notation accessors. If
  color definitions are nested, the dot notation should be properly expanded by the script
  when mapping the colors to keyword values.
- There are a number of checks for existing paths, even those inferred (e.g., template and
  output) from the palette and app. If the appropriate setup hasn't been followed, the
  script will fail. Make sure the `theme` folder in question and it's nested `app`
  directory are correctly setup before running the script. (Perhaps down the line there
  are some easy auto-setup steps to take here, but I'm not making that jump now.)
- TODO: open up different app "writers," or make it easy to extend output syntax based on
  the app in question. This would like be as simple as mapping app names to
  line-generating functions, which accept the keyword and color (among other items). This
  can be fleshed out as needed.

`sync.sh`: copies relevant configuration files from local paths into the `autoconf`
subpath. Markdown files in the docs directory then reference the local copies of these
files, meaning the documentation updates dynamically when the configuration files do. That
is, the (possibly extracted) config snippets will change with the current state of my
system config without any manual intervention of the documentation files.

### Specific theme-setting example
To make clear how the theme setting script works on my system, the following breaks down
exactly what steps are taken to exert as much scheme control as possible. Everything at this
point is wrapped up in a single `make set-<palette>-<scheme>` call; suppose we're
currently running the dark scheme (see first image) and I run `make set-tone4-light`:

![
  Starting point; have a GTK app (GNOME files), `kitty`, and Firefox (with the
  system-dependent default theme set). In Firefox, I have open `localsys` with its
  scheme-mode to set to "auto," which should reflect the theme setting picked up by the
  browser (and note the white tab icon).
](_static/set-theme-1.png)

_(Starting point; have a GTK app (GNOME files), `kitty`, and Firefox (with the
system-dependent default theme set). In Firefox, I have open `localsys` with its
scheme-mode to set to "auto," which should reflect the theme setting picked up by the
browser (and note the white tab icon).)_

1. `set_theme.py` is invoked. Global settings are applied first, based on my OS (`Linux`),
   which calls

   ```
   gsettings set org.gnome.desktop.interface color-scheme 'prefer-light'
   ```

   controlling settings for GTK apps and other `desktop-portal`-aware programs. This
   yields the following:

   ![Portal-aware apps changed, config apps not yet set](_static/set-theme-2.png)

   _(Portal-aware apps changed, config apps not yet set. Scheme-aware sites are updated
   without page refresh.)_
2. Specific application styles are set. For now the list is small, including `kitty`,
   `waybar`, and `sway`. `kitty` is the only type (2) application here, whereas the other
   two are type (1).

   a. For the type (1) apps, the canonical config files as specified in the app registry
      are symlinked to their light variants. For `sway`, this is `~/.config/sway/config`,
      and if we look at the `file`:

      ```sh
      .config/sway/config: symbolic link to ~/.config/sway/sway-tone4-light
      ```
   b. For the type (2) apps, just the `current-theme.conf` file is symlinked to the
      relevant palette-scheme file. `kitty` is such an app, with a supported theme file
      for `tone4`, and those files have been auto-generated via `gen_theme.py`. Looking at
      this file under the `kitty` config directory:

      ```sh
      .config/kitty/current-theme.conf: symbolic link to ~/Documents/projects/autoconf/autoconf/themes/tone4/apps/kitty/generated/light.conf
      ```

      The `kitty.conf` file isn't changed, as all palette-related items are specified in
      the theme file. (Note that the general notion of a "theme" could include changes to
      other stylistic aspects, like the font family; this would likely require some hybrid
      type 1-2 approach not yet implemented).
3. Live application instances are reloaded, according to the registered `refresh_cmd`s.
   Here the apps with style/config files set in step (2) are reloaded to reflect those
   changes. Again, in this example, this is `kitty`, `sway`, and the `waybar`.

   ![Final light setting: portal-dependent apps _and_ config-based apps changed](_static/set-theme-3.png)

   _(Final light setting: portal-dependent apps _and_ config-based apps changed)_
4. `set_theme.py` provides a report for the actions taken; in this case, the following was
   printed:

   ![`set_theme.py` output](_static/set-theme-4.png)
   _(`set_theme.py` output)_
