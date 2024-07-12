import argparse

from symconf import util
from symconf.config import ConfigManager


def add_install_subparser(subparsers):
    def install_apps(args):
        cm = ConfigManager(args.config_dir)
        cm.install_apps(apps=args.apps)

    parser = subparsers.add_parser(
        'install',
        description='Run install scripts for registered applications.'
    )
    parser.add_argument(
        '-a', '--apps',
        required = False,
        default  = "*",
        type     = lambda s: s.split(',') if s != '*' else s,
        help     = 'Application target for theme. App must be present in the registry. ' \
                 + 'Use "*" to apply to all registered apps'
    )
    parser.set_defaults(func=install_apps)

def add_update_subparser(subparsers):
    def update_apps(args):
        cm = ConfigManager(args.config_dir)
        cm.update_apps(apps=args.apps)

    parser = subparsers.add_parser(
        'update',
        description='Run update scripts for registered applications.'
    )
    parser.add_argument(
        '-a', '--apps',
        required = False,
        default  = "*",
        type     = lambda s: s.split(',') if s != '*' else s,
        help     = 'Application target for theme. App must be present in the registry. ' \
                 + 'Use "*" to apply to all registered apps'
    )
    parser.set_defaults(func=update_apps)

def add_config_subparser(subparsers):
    def config_apps(args):
        cm = ConfigManager(args.config_dir)
        cm.config_apps(
            apps=args.apps,
            scheme=args.scheme,
            palette=args.palette,
        )

    parser = subparsers.add_parser(
        'config',
        description='Set config files for registered applications.'
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
    parser.add_argument(
        '-T', '--template-vars',
        required = False,
        nargs='+',
        action=util.KVPair,
        help='Groups to use when populating templates, in the form group=value'
    )
    parser.set_defaults(func=config_apps)


# central argparse entry point
parser = argparse.ArgumentParser(
    'symconf',
    description='Manage application configuration with symlinks.'
)
parser.add_argument(
    '-c', '--config-dir',
    default = util.xdg_config_path(),
    type    = util.absolute_path,
    help    = 'Path to config directory'
)

# add subparsers
subparsers = parser.add_subparsers(title='subcommand actions')
add_install_subparser(subparsers)
add_update_subparser(subparsers)
add_config_subparser(subparsers)


def main():
    args = parser.parse_args()

    if 'func' in args:
        args.func(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
