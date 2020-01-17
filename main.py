import sys

from simple_build import engine
from simple_build.simple_build_error import SimpleBuildError

# $TODO improve this
config_settings = {}
targets = []
clean = False
for arg in sys.argv[1:]:
    if arg == "--clean":
        clean = True
    elif "=" in arg:
        name = arg[:arg.index()]
        value = arg[arg.index() + 1:]
        config_settings[name] = value
    else:
        targets.append(arg)

if len(targets) == 0:
    print("No target specified")

try:
    for target in targets:
        engine.get().build_or_clean_target(target, clean)
except SimpleBuildError as e:
    print(e)
