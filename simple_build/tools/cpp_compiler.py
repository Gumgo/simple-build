from simple_build import graph_objects
from simple_build.simple_build_error import SimpleBuildError

class CppCompilerSettings(graph_objects.OperationSettings):
    def __init__(self):
        super().__init__()

class CppCompilerOperation(graph_objects.Operation):
    @staticmethod
    def get_default_settings():
        settings = CppCompilerSettings()
        # TODO fill out some defaults based on things like platform
        return settings

    def validate_input(self, input):
        raise NotImplementedError()

    def validate_output(self, output):
        raise NotImplementedError()

    def get_operation_implementation(self):
        return None

    def get_include_directories(self):
        if self.active_implementation is None:
            raise SimpleBuildError("An implementation for '{}' has not yet been assigned".format(type(self)))
        return self.active_implementation.get_include_directories()
