# Symconf
`symconf` is a CLI tool for managing local application configuration. It
implements a general model that supports dynamically switching/reloading themes
for any application, and provides a basic means of templatizing your config
files.

## Simple example
Below is a simple example demonstrating two system-wide theme switches:

![Simple example](docs/_static/example.gif)

This GIF shows two `symconf` calls, the first of which applies a `gruvbox` dark
theme and the second a dark [`monobiome`][1] variant. Each call (of the form
`symconf config -m dark -s style`) indicates a dark mode preference and a
particular color palette that should be used when populating config file
templates. Specifically, in this example, invoking `symconf` results in the
following app-specific config updates:

- **GTK**: reacts to the mode setting and sets `prefer-dark` system-wide,
  changing general GTK-responsive applications like Nautilus and Firefox (and
  subsequently websites that are responsive to `prefers-color-scheme`)
- **kitty**: theme template is re-generated using the specified palette, and
  `kitty` processes are sent a message to live-reload the new config file
- **neovim**: a `vim` theme file (along with a statusline theme) is generated
  from the chosen palette, and running instances of `neovim` are sent a message
  to re-source this theme (via `nvim --remote-send`)
- **waybar**: bar styles are updated to match the mode setting
- **sway**: the background color and window borders are dynamically set to base
  palette colors, and `swaymsg reload` is called
- **fzf**: a palette-dependent theme is re-generated and re-exported
- **rofi**: launcher text and highlight colors are set according to the mode
  and palette, applying on next invocation

This example highlights the generality of `symconf`, and so long as an app's
config can be reloaded dynamically, you can use a single `symconf` call to
apply themes for an arbitrary number of apps at once.

# Behavior
`symconf` uses a simple operational model that symlinks centralized config
files to their expected locations across the system. This central config
directory can then be version controlled, and app config files can be updated
in one place.

App config files can either be concrete (fully-specified) or templates (to be
populated by values conditional on style, e.g., a palette). When `symconf` is
executed with a particular mode preference (dark or light) and a style (any
other indicator of thematic elements, often simply in the form of a palette
like `solarized` or `gruvbox`), it searches for both concrete and template
config files that match and symlinks them to registered locations. When
necessary, `symconf` will also match and execute scripts to reload apps after
updating their configuration.

You can find more details on how `symconf`'s matching scheme works in
[Matching](docs/reference/matching.md).

# Configuring
Before using, you must first set up your config directory to house your config
files and give `symconf` something to act on. See
[Configuring](docs/reference/configuring.md) for details.

# Installation
The recommended way to install `symconf` is via `uv`'s "tool" subsystem, which
is well-suited for managing Python packages meant to be used as CLI programs.
With `uv` on your system, you can install with

```sh
uv tool install symconf
```

Alternatively, you can use `pipx` to similar effect:

```sh
pipx install symconf
```

You can also install via `pip`, or clone and install locally.

# Usage
- `-h --help`: print help message
- `-c --config-dir`: set the location of the `symconf` config directory
- `symconf config` is the subcommand used to match and set available config
  files for registered applications
  * `-a --apps`: comma-separate list of registered apps, or `"*"` (default) to
    consider all registered apps.
  * `-m --mode`: preferred lightness mode/scheme, either `light`, `dark`,
    `any`, or `none`.
  * `-s --style`: style indicator, often the name of a color palette, capturing
    thematic details in a config file to be matched. `any` or `none` are
    reserved keywords (see below).
  * `-T --template-vars`: additional groups to use when populating templates,
    in the form `<group>=<value>`, where `<group>` is a template group with a
    folder `$CONFIG_HOME/groups/<group>/` and `<value>` should correspond to a
    TOML file in this folder (i.e., `<value>.toml`).
- `symconf generate` is a subcommand that can be used for batch generation of
  config files. It accepts the same arguments as `symconf config`, but rather
  than selecting the best match to be used for the system setting, all matching
  templates are generated. There is one additional required argument:
  * `-o --output-dir`: the directory under which generated config files should
    be written. App-specific subdirectories are created to house config files
    for each provided app.
- `symconf install`: runs install scripts for matching apps that specify one
  * `-a --apps`: comma-separate list of registered apps, or `"*"` (default) to
    consider all registered apps.
- `symconf update`: runs update scripts for matching apps that specify one
  * `-a --apps`: comma-separate list of registered apps, or `"*"` (default) to
    consider all registered apps.

The keywords `any` and `none` can be used when specifying `--mode`, `--style`,
or as a value in `--template-vars` (and we refer to each of these variables as
_factors_ that help determine a config match):

- `any` will match config files with _any_ value for this factor, preferring
  config files with a value `none`, indicating no dependence on the factor.
  This is the default value when a factor is left unspecified.
- `none` will match `"none"` directly for a given factor (so no special
  behavior), but used to indicate that a config file is independent of the
  factor. For instance,

  ```sh
  symconf config -m light -s none
  ```

  will match config files that capture the notion of a light mode, but do not
  depend on or provide further thematic components such as a color palette.

## Examples
- Set a dark mode for all registered apps, matching any available style/palette
  component:

  ```sh
  symconf config -m dark
  ```
- Set `solarized` theme for `kitty` and match any available mode (light or
  dark):

  ```sh
  symconf config -s solarized -a kitty
  ```
- Set a dark `gruvbox` theme for multiple apps (but not all):

  ```sh
  symconf config -m dark -s gruvbox -apps="kitty,nvim"
  ```
- Set a dark `gruvbox` theme for all apps, and attempt to match other template
  elements:

  ```sh
  symconf config -m dark -s gruvbox -T font=mono window=sharp
  ```

  which would attempt to find and load key-value pairs in the files
  `$CONFIG_HOME/groups/font/mono.toml` and
  `$CONFIG_HOME/groups/window/sharp.toml` to be used as values when filling
  templatized config files.


[1]: https://github.com/ologio/monobiome
