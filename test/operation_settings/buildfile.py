from simple_build import simple_build as sb

class MySettings(sb.OperationSettings):
	def __init__(self):
		self.a = 1
		self.b = 2
		self.c = 3

class MyOperation(sb.Operation):
	@staticmethod
	def get_default_settings():
		return MySettings()

buildfile_settings = MyOperation.get_buildfile_settings()
buildfile_settings.a = 10
