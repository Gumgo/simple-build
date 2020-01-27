def get():
    return _engine_instance

def set(engine_instance):
    global _engine_instance
    _engine_instance = engine_instance

_engine_instance = None
