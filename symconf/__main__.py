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
        default  = '*',
        type     = lambda s: s.split(',') if s != '*' else s,
        help     = 'Application target for theme. App must be present in the registry. ' \
                 + 'Use "*" to apply to all registered apps'
    )
    parser.set_defaults(func=update_apps)

def add_config_subparser(subparsers):
    def configure_apps(args):
        cm = ConfigManager(args.config_dir)
        cm.configure_apps(
            apps=args.apps,
            scheme=args.mode,
            style=args.style,
        )

    parser = subparsers.add_parser(
        'config',
        description='Set config files for registered applications.'
    )
    parser.add_argument(
        '-s', '--style',
        required = False,
        default  = 'any',
        help     = 'Style indicator (often a color palette) capturing thematic details in '
                   'a config file'
    )
    parser.add_argument(
        '-m', '--mode',
        required = False,
        default  = "any",
        help     = 'Preferred lightness mode/scheme, either "light," "dark," "any," or "none."'
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
    parser.set_defaults(func=configure_apps)


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
