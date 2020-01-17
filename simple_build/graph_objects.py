from simple_build.simple_build_error import SimpleBuildError

class Target:
    def __init__(self):
        self._operation = None

    @property
    def operation(self):
        return self._operation

    # Returns the last modification timestamp of the target
    # This should be a float representing the number of seconds since the epoch, as returned by os.path.getmtime()
    # None is returned if the target doesn't have a modification timestamp or if it isn't available (e.g. file doesn't exist)
    def get_modification_timestamp(self):
        raise NotImplementedError()

    # Raises an error if this target is in an invalid state - e.g. a file doesn't exist
    def validate(self):
        raise NotImplementedError()

class Operation:
    def __init__(self):
        self._inputs = []
        self._outputs = []

    @property
    def inputs(self):
        return (x for x in self._inputs)

    @property
    def outputs(self):
        return (x for x in self._outputs)

    def add_input(self, target):
        if not isinstance(target, Target):
            raise SimpleBuildError("'{}' is not a Target".format(str(target)))
        self._inputs.append(target)

    def add_output(self, target):
        if not isinstance(target, Target):
            raise SimpleBuildError("'{}' is not a Target".format(str(target)))
        if target.operation is not None:
            raise SimpleBuildError("'{}' is already an output of an operation".format(str(target)))
        self._outputs.append(target)
        target._operation = self

    # Raises an error if the input provided is not valid - e.g. providing a py file to a C++ compiler
    def validate_input(self, input):
        raise NotImplementedError()

    # Raises an error if the output provided is not valid - e.g. providing a cpp file to a linker
    def validate_output(self, output):
        raise NotImplementedError()

    # Returns the operation implementation appropriate for the given platform
    # platform is the string obtained by calling platform.system()
    def get_operation_implementation(self, platform):
        raise NotImplementedError()

class OperationImplementation:
    def __init__(self, operation):
        self._operation = operation

    @property
    def operation(self):
        return self._operation

    # Attempts to build, raising an error if something goes wrong
    def build(self):
        pass

    # Attempts to clean, raising an error if something goes wrong
    def clean(self):
        pass
