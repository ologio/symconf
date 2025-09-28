from importlib.metadata import version

from symconf import util, config, reader, matching, template
from symconf.config import ConfigManager
from symconf.reader import DictReader
from symconf.runner import Runner
from symconf.matching import Matcher, FilePart
from symconf.template import Template, FileTemplate, TOMLTemplate

__version__ = version("symconf")
