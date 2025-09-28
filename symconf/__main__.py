from argparse import Namespace, ArgumentParser

from symconf import util, __version__
from symconf.config import ConfigManager


def add_install_subparser(subparsers: ArgumentParser) -> None:
    def install_apps(args: Namespace) -> None:
        cm = ConfigManager(args.config_dir)
        cm.install_apps(apps=args.apps)

    parser = subparsers.add_parser(
        "install",
        description="Run install scripts for registered applications.",
    )
    parser.add_argument(
        "-a",
        "--apps",
        required=False,
        default="*",
        type=lambda s: s.split(",") if s != "*" else s,
        help=(
            "Application target for theme. App must be present in the "
            'registry. Use "*" to apply to all registered apps'
        ),
    )
    parser.set_defaults(func=install_apps)


def add_update_subparser(subparsers: ArgumentParser) -> None:
    def update_apps(args: Namespace) -> None:
        cm = ConfigManager(args.config_dir)
        cm.update_apps(apps=args.apps)

    parser = subparsers.add_parser(
        "update", description="Run update scripts for registered applications."
    )
    parser.add_argument(
        "-a",
        "--apps",
        required=False,
        default="*",
        type=lambda s: s.split(",") if s != "*" else s,
        help=(
            "Application target for theme. App must be present in the "
            'registry. Use "*" to apply to all registered apps'
        ),
    )
    parser.set_defaults(func=update_apps)


def add_config_subparser(subparsers: ArgumentParser) -> None:
    def configure_apps(args: Namespace) -> None:
        cm = ConfigManager(args.config_dir)
        cm.configure_apps(
            apps=args.apps,
            scheme=args.mode,
            style=args.style,
            **args.template_vars,
        )

    parser = subparsers.add_parser(
        "config", description="Set config files for registered applications."
    )
    parser.add_argument(
        "-s",
        "--style",
        required=False,
        default="any",
        help=(
            "Style indicator (often a color palette) capturing "
            "thematic details in a config file"
        ),
    )
    parser.add_argument(
        "-m",
        "--mode",
        required=False,
        default="any",
        help=(
            'Preferred lightness mode/scheme, either "light," "dark," '
            '"any," or "none."'
        ),
    )
    parser.add_argument(
        "-a",
        "--apps",
        required=False,
        default="*",
        type=lambda s: s.split(",") if s != "*" else s,
        help=(
            "Application target for theme. App must be present in the "
            'registry. Use "*" to apply to all registered apps'
        ),
    )
    parser.add_argument(
        "-T",
        "--template-vars",
        required=False,
        nargs="+",
        default={},
        action=util.KVPair,
        help=(
            "Groups to use when populating templates, in the form group=value"
        ),
    )
    parser.set_defaults(func=configure_apps)


def add_generate_subparser(subparsers: ArgumentParser) -> None:
    def generate_apps(args: Namespace) -> None:
        cm = ConfigManager(args.config_dir)
        cm.generate_app_templates(
            gen_dir=args.output_dir,
            apps=args.apps,
            scheme=args.mode,
            style=args.style,
            **args.template_vars,
        )

    parser = subparsers.add_parser(
        "generate",
        description="Generate all template config files for specified apps",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        required=True,
        type=util.absolute_path,
        help="Path to write generated template files",
    )
    parser.add_argument(
        "-s",
        "--style",
        required=False,
        default="any",
        help=(
            "Style indicator (often a color palette) capturing "
            "thematic details in a config file"
        ),
    )
    parser.add_argument(
        "-m",
        "--mode",
        required=False,
        default="any",
        help=(
            'Preferred lightness mode/scheme, either "light," "dark," '
            '"any," or "none."'
        ),
    )
    parser.add_argument(
        "-a",
        "--apps",
        required=False,
        default="*",
        type=lambda s: s.split(",") if s != "*" else s,
        help=(
            "Application target for theme. App must be present in the "
            'registry. Use "*" to apply to all registered apps'
        ),
    )
    parser.add_argument(
        "-T",
        "--template-vars",
        required=False,
        nargs="+",
        default={},
        action=util.KVPair,
        help=(
            "Groups to use when populating templates, in the form group=value"
        ),
    )
    parser.set_defaults(func=generate_apps)


# central argparse entry point
parser = ArgumentParser(
    "symconf", description="Manage application configuration with symlinks."
)
parser.add_argument(
    "-c",
    "--config-dir",
    default=util.xdg_config_path(),
    type=util.absolute_path,
    help="Path to config directory",
)
parser.add_argument(
    "-v",
    "--version",
    action="version",
    version=__version__,
    help="Print symconf version",
)

# add subparsers
subparsers = parser.add_subparsers(title="subcommand actions")
add_config_subparser(subparsers)
add_generate_subparser(subparsers)
add_install_subparser(subparsers)
add_update_subparser(subparsers)


def main() -> None:
    args = parser.parse_args()

    if "func" in args:
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
