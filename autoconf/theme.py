import argparse
import inspect
import json
import tomllib as toml
from pathlib import Path


# separation sequences to use base on app
app_sep_map = {
    'kitty': ' ',
}

def generate_theme_files():
    basepath = get_running_path()

    # set arg conditional variables 
    palette_path  = Path(basepath, 'themes', args.palette)
    colors_path   = Path(palette_path, 'colors.json')
    theme_app     = args.app

    template_path = None
    output_path   = None

    if args.template is None:
        template_path = Path(palette_path, 'apps', theme_app, 'templates')
    else:
        template_path = Path(args.template).resolve()

    if args.output is None:
        output_path = Path(palette_path, 'apps', theme_app, 'generated')
    else:
        output_path = Path(args.output).resolve()

    # check paths
    if not colors_path.exists():
        print(f'Resolved colors path [{colors_path}] doesn\'t exist, exiting')
        return
    
    if not template_path.exists():
        print(f'Template path [{template_path}] doesn\'t exist, exiting')
        return

    if not output_path.exists() or not output_path.is_dir():
        print(f'Output path [{output_path}] doesn\'t exist or not a directory, exiting')
        return

    print(f'Using palette colors [{colors_path}]')
    print(f'-> with templates in [{template_path}]')
    print(f'-> to output path [{output_path}]\n')

    # load external files (JSON, TOML)
    colors_json = json.load(colors_path.open())

    # get all matching TOML files
    template_list = [template_path]
    if template_path.is_dir():
        template_list = template_path.rglob('*.toml')

    for template_path in template_list:
        template_toml = toml.load(template_path.open('rb'))

        # lookup app-specific config separator
        config_sep = app_sep_map.get(theme_app, ' ')
        output_lines = []
        for config_key, color_key in template_toml.items():
            color_value = colors_json
            for _key in color_key.split('.'):
                color_value = color_value.get(_key, {})
            output_lines.append(f'{config_key}{config_sep}{color_value}') 

        output_file = Path(output_path, template_path.stem).with_suffix('.conf')
        output_file.write_text('\n'.join(output_lines))
        print(f'[{len(output_lines)}] lines written to [{output_file}] for app [{theme_app}]')

