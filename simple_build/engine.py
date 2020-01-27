import copy
import importlib.util
import os
import pathlib
import platform
import sys

from simple_build import engine_accessor
from simple_build import graph_objects
from simple_build.simple_build_error import SimpleBuildError

_BUILDROOT_NAME = "buildroot.py"
_BUILDFILE_NAME = "buildfile.py"

class _Node:
    def __init__(self, operation):
        self.operation = operation
        self.unresolved_input_count = 0
        self.input_nodes = set()
        self.output_nodes = set()

class Engine:
    def __init__(self):
        engine_accessor.set(self)

        # Search up the directory tree for the buildroot file
        self._root_directory = pathlib.Path(".").resolve()
        while not (self._root_directory / _BUILDROOT_NAME).exists():
            if self._root_directory == self._root_directory.parent:
                raise SimpleBuildError("'{}' was not found".format(_BUILDROOT_NAME))
            self._root_directory = self._root_directory.parent

        # Make sure there's a buildfile in our current directory
        self._buildfile_directory = pathlib.Path(".").resolve()
        if not (self._buildfile_directory / _BUILDFILE_NAME).exists():
            raise SimpleBuildError("'{}' was not found".format(_BUILDFILE_NAME))

        self._config_settings = None

        # This maps (buildfile_directory) -> (module) for each buildfile we visit
        # This allows buildfiles to access targets in other buildfiles on which they depend
        # Note that the buildfile_directory is relative to project root
        self._buildfile_modules = {}

        # List of buildfiles that we're currently visiting - these are relative to the root directory
        self._active_buildfile_visits = []

        # Map of all targets declared at a global scope in a buildfile
        # Maps (buildfile_directory, target_name) -> (Target)
        # (buildfile_directory, None) is the default target
        self._targets = {}

        # Maps (operation_type) -> OperationSettings
        self._operation_default_settings = {}

        # Maps (buildfile_directory, operation_type) -> OperationSettings
        self._buildfile_operation_default_settings = {}

        # Visit the buildfile in our current directory
        self.visit_buildfile(self._buildfile_directory)

    @property
    def root_directory(self):
        return self._root_directory

    @property
    def config_settings(self):
        return self._config_settings

    def set_config_settings(self, config_settings):
        self._config_settings = config_settings

    # Returns the default settings for the operation type specified for the current buildfile
    # The default settings can be changed directly by modifying the returned object
    def get_buildfile_operation_settings(self, operation_type):
        if not issubclass(operation_type, graph_objects.Operation):
            raise SimpleBuildError("'{}' is not an Operation".format(str(operation_type)))

        buildfile_directory = self._get_current_buildfile_directory()

        settings = None
        parent_buildfile_directory = buildfile_directory
        while settings is None:
            key = (parent_buildfile_directory, operation_type)
            settings = self._buildfile_operation_default_settings.get(key, None)
            if settings is None:
                parent_buildfile_directory = self._get_parent_buildfile_directory(parent_buildfile_directory)
                if parent_buildfile_directory is None:
                    # Use the default settings if we've passed the rootmost buildfile
                    settings = self._get_default_operation_settings(operation_type)

        key = (buildfile_directory, operation_type)
        if key not in self._buildfile_operation_default_settings:
            # Copy the settings if they didn't already exist for the current buildfile
            settings = copy.deepcopy(settings)
            self._buildfile_operation_default_settings[key] = settings

        return settings

    # Replaces the default settings for the operation type specified for the current buildfile with the ones provided
    # This method makes a copy so modifications to the settings object made after calling this method are not saved
    def set_buildfile_operation_settings(self, operation_type, operation_settings):
        if not issubclass(operation_type, graph_objects.Operation):
            raise SimpleBuildError("'{}' is not an Operation".format(str(operation_type)))

        buildfile_directory = self._get_current_buildfile_directory()

        default_settings_type = type(self._get_default_operation_settings(operation_type))
        if not isinstance(operation_settings, default_settings_type):
            raise SimpleBuildError(
                "Settings provided for Operation '{}' is not of type '{}'".format(
                    str(operation_type),
                    str(default_settings_type)))

        key = (buildfile_directory, operation_type)
        self._buildfile_operation_default_settings[key] = copy.deepcopy(operation_settings)

    # Sets the default target to be built if no target is explicitly specified
    def set_buildfile_default_target(self, default_target):
        if not issubclass(default_target, graph_objects.Target):
            raise SimpleBuildError("'{}' is not a Target".format(str(default_target)))

        buildfile_directory = self._get_current_buildfile_directory()

        self._targets[(buildfile_directory, None)] = default_target

    # Visit the buildfile in the given path, which should be specified as an absolute path
    def visit_buildfile(self, path):
        try:
            relative_path = path.relative_to(self._root_directory)
        except ValueError:
            raise SimpleBuildError("'{}' is not under the project root".format(str(path)))

        if not (path / _BUILDFILE_NAME).exists():
            raise SimpleBuildError("'{}' not found in directory '{}'".format(_BUILDFILE_NAME, str(relative_path)))

        if relative_path in self._active_buildfile_visits:
            raise SimpleBuildError(
                "Recursive dependencies detected: {}".format(
                    " -> ".join(str(x) for x in self._active_buildfile_visits + [relative_path])))

        # Check if we've already visited this module
        module = self._buildfile_modules.get(relative_path, None)
        if module is not None:
            return module

        try:
            self._active_buildfile_visits.append(relative_path)

            # Visit the parent buildfile first
            # Do this after adding to the active buildfile list so that we can detect cyclic dependencies
            # (Child buildfiles are implicitly dependent on their parent)
            parent_buildfile_directory = self._get_parent_buildfile_directory(relative_path)
            if parent_buildfile_directory is not None:
                self.visit_buildfile(self._root_directory / parent_buildfile_directory)

            # Come up with a unique name for this module
            def sanitize(c):
                if c.isalnum or c == "_":
                    return c
                return "_" if (c == "/" or c == "\\") else ""
            sanitized_path = "".join(sanitize(c) for c in str(relative_path))
            module_name = "buildfile_{}_{}".format(len(self._buildfile_modules), sanitized_path)

            # Load the module
            cwd = os.getcwd()
            try:
                os.chdir(path)
                spec = importlib.util.spec_from_file_location(module_name, path / _BUILDFILE_NAME)
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module # Do we need to do this?
                spec.loader.exec_module(module)
            finally:
                os.chdir(cwd)

            self._buildfile_modules[relative_path] = module
        finally:
            self._active_buildfile_visits.pop()

        # Find all targets declared at a global scope in this module
        for name, value in module.__dict__.items():
            if isinstance(value, graph_objects.Target):
                key = (relative_path, name)
                assert key not in self._targets
                self._targets[key] = value

        return module

    # Builds or cleans a target with the provided target string
    # The default target is built if target_string is empty
    def build_or_clean_target(self, target_string, clean):
        if len(target_string) == 0:
            # Build the default target
            target_path = self._buildfile_directory
            target_name = None
        else:
            target_string_components = target_string.replace("\\", "/").split("/")
            target_path = self._buildfile_directory
            for path_component in target_string_components[:-1]:
                target_path = target_path / path_component
            target_path = target_path.resolve()
            target_name = target_string_components[-1]

        try:
            buildfile_directory = target_path.relative_to(self._root_directory)
        except ValueError:
            raise SimpleBuildError("The target '{}' was not found".format(target_string))

        target_key = (buildfile_directory, target_name)
        target = self._targets.get(target_key, None)
        if target is None:
            if target_name is None:
                raise SimpleBuildError("No default target was set")
            else:
                raise SimpleBuildError("The target '{}' was not found".format(target_string))

        if target.operation is None:
            raise SimpleBuildError("The target '{}' is not the output of any operation".format(target_string))

        print("Building '{}'...".format(target_string))

        # Build the operation graph
        operations_stack = [target.operation]
        nodes_for_operations = { target.operation: _Node(target.operation) }
        root_nodes = set()
        operations_path = [] # Used to detect cycles
        while len(operations_stack) > 0:
            operation = operations_stack.pop()

            # We push None onto the stack to indicate this operation has been fully visited
            if operation is None:
                operations_path.pop()
                continue
            else:
                operations_path.append(operation)
                operations_stack.append(None)

            node = nodes_for_operations[operation]
            root_nodes.add(node)

            for input_target in operation.inputs:
                if input_target.operation is not None:
                    # Detect cycles
                    if input_target.operation in operations_path:
                        raise SimpleBuildError("Cyclic dependency detected for target '{}'".format(str(input_target)))

                    input_node = nodes_for_operations.get(input_target.operation)
                    if input_node is None:
                        input_node = _Node(input_target.operation)
                        nodes_for_operations[input_target.operation] = input_node

                    if input_node not in node.input_nodes:
                        node.input_nodes.add(input_node)
                        node.unresolved_input_count += 1
                        root_nodes.discard(node)
                    input_node.output_nodes.add(node)
                    operations_stack.append(input_target.operation)

        # Now run the graph
        # $TODO multithread this
        platform_system = platform.system()
        ready_nodes = [x for x in root_nodes]
        while len(ready_nodes) > 0:
            node = ready_nodes.pop()
            assert node.unresolved_input_count == 0

            operation_implementation = node.operation.get_operation_implementation(platform_system)

            if clean:
                operation_implementation.clean()
            else:
                input_modification_timestamp = float("-inf")
                for input_target in operation.inputs:
                    modification_timestamp = input_target.get_modification_timestamp()
                    if modification_timestamp is None:
                        # If any input target can't provide a modification timestamp, we always run the operation
                        input_modification_timestamp = None
                        break
                    input_modification_timestamp = max(modification_timestamp, input_modification_timestamp)

                stale = input_modification_timestamp is None
                if not stale:
                    for output_target in operation.outputs:
                        # Check to see if the inputs were last modified after any output was last built
                        modification_timestamp = output_target.get_modification_timestamp()
                        if modification_timestamp is None or input_modification_timestamp > modification_timestamp:
                            # If any output target can't provide a modification timestamp, we always run the operation
                            stale = True
                            break

                if stale:
                    operation_implementation.run()

            for output_node in node.output_nodes:
                output_node.unresolved_input_count -= 1
                assert output_node.unresolved_input_count >= 0

                if output_node.unresolved_input_count == 0:
                    ready_nodes.append(output_node)

    def _get_current_buildfile_directory(self):
        if len(self._active_buildfile_visits) == 0:
            raise SimpleBuildError("No buildfile is currently active")
        return self._active_buildfile_visits[-1]

    # buildfile_directory should be relative to the root directory
    def _get_parent_buildfile_directory(self, buildfile_directory):
        while True:
            parent_buildfile_directory = buildfile_directory.parent
            if buildfile_directory == parent_buildfile_directory:
                return None
            buildfile_directory = parent_buildfile_directory

            if (self._root_directory / buildfile_directory / _BUILDFILE_NAME).exists():
                return buildfile_directory

    # This function queries and caches the default settings if necessary
    def _get_default_operation_settings(self, operation_type):
        if not issubclass(operation_type, graph_objects.Operation):
            raise SimpleBuildError("'{}' is not an Operation".format(str(operation_type)))

        default_settings = self._operation_default_settings.get(operation_type, None)
        if default_settings is None:
            default_settings = operation_type.get_default_settings()
            if not isinstance(default_settings, graph_objects.OperationSettings):
                raise SimpleBuildError("'{}' is not an OperationSettings".format(str(default_settings)))
            self._operation_default_settings[operation_type] = operation_type

        return default_settings

def get():
    return _instance

_instance = Engine()
