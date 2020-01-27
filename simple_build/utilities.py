import pathlib

from simple_build import engine_accessor
from simple_build.simple_build_error import SimpleBuildError

def get_root_directory():
    return engine_accessor.get().root_directory

# Path is relative to the current directory
def depends(path):
    absolute_path = pathlib.Path(path).resolve()
    return engine_accessor.get().visit_buildfile(absolute_path)

# Returns a dict of the command-line NAME=VALUE config settings provided
def get_config_settings():
    return engine_accessor.get().config_settings

def set_default_target(target):
    engine_accessor.get().set_buildfile_default_target(target)
