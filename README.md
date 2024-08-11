# Symconf
`symconf` is a CLI tool for managing local application configuration. It implements a
general model that supports dynamically switching/reloading themes for any application,
and makes it easy to templatize your config files.

## Quick example
The single command `symconf config -m dark -s gruvbox` indicates a dark mode preference and
that the `gruvbox` palette should be used. In this example, invoking this command kicks
off several app-specific process to update the system state:

- **GTK**: reacts to the mode setting and sets `prefer-dark` system-wide, changing general
  GTK-responsive applications like Firefox (and subsequently websites that are responsive to
  `prefers-color-scheme`)
- **kitty**: theme template is re-generated using the dark `gruvbox` palette, and `kitty`
  processes are sent a message to live reload the new config
- **neovim**: a `vim` theme file is generated from the `gruvbox` palette, and running
  instances of `neovim` are sent a message to re-source this theme
- **waybar**: bar styles are updated to match the mode setting
- **sway**: the background color and window borders are dynamically set to base `gruvbox`
  colors, and `swaymsg reload` is called
- **fzf**: a palette-dependent theme is re-generated for `gruvbox` colors and re-exported
- **rofi**: launcher text and highlight colors are set according to mode

# Behavior
It uses a simple operational model that symlinks centralized config files to their
expected locations across one's system. This central config directory can then be version
controlled, and app config files can be updated in one place.

`symconf` also facilitates dynamically setting system and application themes. You can
create themed variants of your config files, and `symconf` will "swap out" the matching
theme config files for registered apps and running config reloading scripts. 

# Usage
See more in [USAGE](/USAGE.md)
