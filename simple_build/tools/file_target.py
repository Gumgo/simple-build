import os
import pathlib

from simple_build import graph_objects
from simple_build.simple_build_error import SimpleBuildError

class FileTarget(graph_objects.Target):
    def __init__(self, path):
        super().__init__()
        self._path = pathlib.Path(path).absolute()

    def get_modification_timestamp(self, operation):
        try:
            return os.path.getmtime(self._path)
        except OSError:
            return None

    def validate(self):
        if not self._path.exists():
            raise SimpleBuildError("The file '{}' does not exist".format(str(self._path)))
