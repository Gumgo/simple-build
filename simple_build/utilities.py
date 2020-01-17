from simple_build import engine
from simple_build.simple_build_error import SimpleBuildError

def get_root_directory():
    return engine.get().root_directory

# Path is relative to the current directory
def depends(path):
    absolute_path = path.resolve()
    return engine.get().visit_buildfile(absolute_path)

# Returns a dict of the command-line NAME=VALUE config settings provided
def get_config_settings():
    return engine.get().config_settings
