# Matching
This file describes the naming and matching scheme employed by `symconf`.

```
~/.config/symconf/
├── app_registry.toml
└── apps/
    └── <app>/
        ├── user/                      # user managed
        │   └── none-none.<config-name>
        ├── generated/                 # automatically populated
        │   └── none-none.<config-name>
        ├── templates/                 # config templates
        │   └── none-none.template
        └── call/                      # reload scripts
            └── none-none.sh
```
