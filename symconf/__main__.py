import argparse

from symconf import util
from symconf.config import ConfigManager


def add_set_subparser(subparsers):
    def update_app_settings(args):
        cm = ConfigManager(args.config_dir)
        cm.update_apps(
            apps=args.apps,
            scheme=args.scheme,
            palette=args.palette,
        )

    parser = subparsers.add_parser(
        'set',
        description='Generate theme files for various applications. Uses a template (in TOML ' \
                  + 'format) to map application-specific config keywords to colors (in JSON '  \
                  + 'format).' 
    )
    parser.add_argument(
        '-p', '--palette',
        required = False,
        default  = "any",
        help     = 'Palette name, must match a folder in themes/'
    )
    parser.add_argument(
        '-s', '--scheme',
        required = False,
        default  = "any",
        help     = 'Preferred lightness scheme, either "light" or "dark".'
    )
    parser.add_argument(
        '-a', '--apps',
        required = False,
        default  = "*",
        type     = lambda s: s.split(',') if s != '*' else s,
        help     = 'Application target for theme. App must be present in the registry. ' \
                 + 'Use "*" to apply to all registered apps'
    )
    parser.set_defaults(func=update_app_settings)

def add_gen_subparser(subparsers):
    parser = subparsers.add_parser(
        'gen',
        description='Generate theme files for various applications. Uses a template (in TOML ' \
                  + 'format) to map application-specific config keywords to colors (in JSON '  \
                  + 'format).' 
    )
    parser.add_argument(
        '-a', '--app',
        required=True,
        help='Application target for theme. Supported: ["kitty"]'
    )
    parser.add_argument(
        '-p', '--palette',
        required=True,
        help='Palette to use for template mappings. Uses local "theme/<palette>/colors.json".'
    )
    parser.add_argument(
        '-t', '--template',
        default=None,
        help='Path to TOML template file. If omitted, app\'s default template path is used.' \
           + 'If a directory is provided, all TOML files in the folder will be used.'
    )
    parser.add_argument(
        '-o', '--output',
        default=None,
        help='Output file path for theme. If omitted, app\'s default theme output path is used.'
    )
    parser.set_defaults(func=generate_theme_files)


# central argparse entry point
parser = argparse.ArgumentParser(
    'symconf',
    description='Generate theme files for various applications. Uses a template (in TOML ' \
              + 'format) to map application-specific config keywords to colors (in JSON '  \
              + 'format).' 
)
parser.add_argument(
    '-c', '--config-dir',
    default = util.xdg_config_path(),
    type    = util.absolute_path,
    help    = 'Path to config directory'
)

# add subparsers
subparsers = parser.add_subparsers(title='subcommand actions')
#add_gen_subparser(subparsers)
add_set_subparser(subparsers)


if __name__ == '__main__':
    args = parser.parse_args()

    if 'func' in args:
        args.func(args)
    else:
        parser.print_help()
