def test_imports():
    from symconf.runner import Runner
    from symconf.reader import DictReader
    from symconf.config import ConfigManager
    from symconf.matching import Matcher, FilePart
    from symconf.template import Template, FileTemplate, TOMLTemplate

    from symconf import config
    from symconf import reader
    from symconf import util
