import argparse

from gen_theme import add_gen_subparser
from set_theme import add_set_subparser


parser = argparse.ArgumentParser(
    'autoconf',
    description='Generate theme files for various applications. Uses a template (in TOML ' \
              + 'format) to map application-specific config keywords to colors (in JSON '  \
              + 'format).' 
)
subparsers = parser.get_subparsers()
add_gen_subparser(subparsers)
add_set_subparser(subparsers)

args = parser.parse_args()

if __name__ == '__main__':
    if 'func' in args:
        args.func(args)
    else:
        parser.print_help()
