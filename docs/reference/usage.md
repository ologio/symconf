# Usage

```sh
usage: symconf [-h] [-c CONFIG_DIR] [-v] {config,generate,install,update} ...

Manage application configuration with symlinks.

options:
  -h, --help            show this help message and exit
  -c CONFIG_DIR, --config-dir CONFIG_DIR
                        Path to config directory
  -v, --version         Print symconf version

subcommand actions:
  {config,generate,install,update}
```

Additional argument details:

- `-h --help`: print help message
- `-c --config-dir`: the location of the `symconf` config directory. Assumes
  `$XDG_CONFIG_HOME` (e.g., `~/.config/symconf/`) by default.

## `config` subcommand
The config subcommand applies symlinks for registered application routes that
meet specified constraints.

```sh
usage: symconf config [-h] [-s STYLE] [-m MODE] [-a APPS] [-T TEMPLATE_VARS [TEMPLATE_VARS ...]]

Set config files for registered applications.

options:
  -h, --help            show this help message and exit
  -s STYLE, --style STYLE
                        Style indicator (often a color palette) capturing thematic details in a config file
  -m MODE, --mode MODE  Preferred lightness mode/scheme, either "light," "dark," "any," or "none."
  -a APPS, --apps APPS  Application target for theme. App must be present in the registry. Use "*" to apply to all registered apps
  -T TEMPLATE_VARS [TEMPLATE_VARS ...], --template-vars TEMPLATE_VARS [TEMPLATE_VARS ...]
                        Groups to use when populating templates, in the form group=value
```

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


## `generate` subcommand
The generate subcommand fills in templates with theme values matched under
provided constraints,

```sh
usage: symconf generate [-h] -o OUTPUT_DIR [-s STYLE] [-m MODE] [-a APPS] [-T TEMPLATE_VARS [TEMPLATE_VARS ...]]

Generate all template config files for specified apps

options:
  -h, --help            show this help message and exit
  -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                        Path to write generated template files
  -s STYLE, --style STYLE
                        Style indicator (often a color palette) capturing thematic details in a config file
  -m MODE, --mode MODE  Preferred lightness mode/scheme, either "light," "dark," "any," or "none."
  -a APPS, --apps APPS  Application target for theme. App must be present in the registry. Use "*" to apply to all registered apps
  -T TEMPLATE_VARS [TEMPLATE_VARS ...], --template-vars TEMPLATE_VARS [TEMPLATE_VARS ...]
                        Groups to use when populating templates, in the form group=value
```

- `symconf generate` is a subcommand that can be used for batch generation of
  config files. It accepts the same arguments as `symconf config`, but rather
  than selecting the best match to be used for the system setting, all matching
  templates are generated. There is one additional required argument:
  * `-o --output-dir`: the directory under which generated config files should
    be written. App-specific subdirectories are created to house config files
    for each provided app.

## `install` subcommand
The install subcommand runs the `install.sh` scripts for registered apps.

```sh
usage: symconf install [-h] [-a APPS]

Run install scripts for registered applications.

options:
  -h, --help            show this help message and exit
  -a APPS, --apps APPS  Application target for theme. App must be present in the registry. Use "*" to apply to all registered apps
```

- `symconf install`: runs install scripts for matching apps
  * `-a --apps`: comma-separate list of registered apps, or `"*"` (default) to
    consider all registered apps.

## `update` subcommand
The update subcommand runs the `update.sh` scripts for registered apps. This
action expects the install process for each matched app to have been run
beforehand. 

```sh
usage: symconf update [-h] [-a APPS]

Run update scripts for registered applications.

options:
  -h, --help            show this help message and exit
  -a APPS, --apps APPS  Application target for theme. App must be present in the registry. Use "*" to apply to all registered apps
```

- `symconf update`: runs update scripts for matching apps that specify one
  * `-a --apps`: comma-separate list of registered apps, or `"*"` (default) to
    consider all registered apps.

## Matching factors
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
