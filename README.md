# Overview
`symconf` is a CLI tool for managing local application configuration. It uses a simple
operational model that symlinks centralized config files to their expected locations across
the system. This central config directory can then be version controlled.

`symconf` also facilitates dynamically setting system and application "themes," symlinking
matching theme config files for registered apps and running config reloading scripts. 

For
example, the following `symconf` call coordinates a light to dark mode switch

