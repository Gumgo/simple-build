from simple_build import simple_build as sb

parent = sb.depends("..")

buildfile_settings = parent.MyOperation.get_buildfile_settings()
print(buildfile_settings.a)
