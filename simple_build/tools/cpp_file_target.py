import os
import pathlib
import re

from simple_build.tools import file_target

class CppFileTarget(file_target.FileTarget):
    def get_modification_timestamp(self, operation):
        include_directories = operation.get_include_directories()

        # Crawl #include statements to find the most recently modified file
        most_recent_modification_timestamp = float("-inf")
        encountered_paths = set([self._path])
        path_stack = [self._path]
        while len(path_stack) > 0:
            path = path_stack.pop()
            modification_timestamp = _file_modification_timestamp_cache.get_modification_timestamp_for_file(path)
            if modification_timestamp is None:
                # We failed to obtain the timestamp, return None to be safe
                return None
            most_recent_modification_timestamp = max(modification_timestamp, most_recent_modification_timestamp)

            includes = _include_cache.get_includes_for_file(path)
            if includes is None:
                # We failed to parse includes, return None to be safe
                return None

            for include, is_quoted in includes:
                # Attempt to resolve the #include
                if is_quoted:
                    include_directories_for_file = [path.parent] + include_directories
                else:
                    include_directories_for_file = include_directories
                include_path = None
                for include_directory in include_directories_for_file:
                    possible_include_path = include_directory / include
                    try:
                        if possible_include_path.exists():
                            include_path = possible_include_path
                            break
                    except OSError:
                        # The #include path was invalid, return None to be safe
                        return None

                if include_path not in encountered_paths:
                    encountered_paths.add(include_path)
                    path_stack.append(include_path)

        return most_recent_modification_timestamp

class _IncludeCache:
    def __init__(self):
        # Maps (file_path) -> (list_of_include_strings, is_quoted)
        # is_quoted distinguishes between #include "file.h" vs #include <file.h>
        self._file_includes = {}

    def get_includes_for_file(self, path):
        if path not in self._file_includes:
            includes = self._parse_file_includes(path)
            self._file_includes[path] = includes

        return self._file_includes[path]

    def _parse_file_includes(self, path):
        includes = []

        try:
            with open(path) as file:
                for line in file:
                    for match in re.finditer(r'#[ \t]*include[ \t]+((\"(?P<quoted_value>[^"]*)\")|(<(?P<tagged_value>[^>]*)>))', line):
                        quoted_value = match.group("quoted_value")
                        tagged_value = match.group("tagged_value")
                        assert (quoted_value is None) != (tagged_value is None)
                        is_quoted = quoted_value is not None
                        value = quoted_value if is_quoted else tagged_value
                        includes.append((value, is_quoted))
        except Exception as e:
            # nocheckin Warn the user?
            return None

        return includes

class _FileModificationTimestampCache:
    def __init__(self):
        # Maps (file_path) -> (modification_timestamp)
        self._file_modification_timestamps = {}

    def get_modification_timestamp_for_file(self, path):
        if path not in self._file_modification_timestamps:
            try:
                modification_timestamp = os.path.getmtime(path)
            except OSError:
                modification_timestamp = None
            self._file_modification_timestamps[path] = modification_timestamp

        return self._file_modification_timestamps[path]

_include_cache = _IncludeCache()
_file_modification_timestamp_cache = _FileModificationTimestampCache()
