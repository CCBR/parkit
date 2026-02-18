import os

global __version__
current_path = os.path.dirname(os.path.abspath(__file__))
vfile = open(os.path.join(current_path, "VERSION"), "r")
__version__ = "v" + vfile.read()
__version__ = __version__.strip()
vfile.close()
