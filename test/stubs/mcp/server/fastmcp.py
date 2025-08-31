class Context:
    def __init__(self):
        class _C:
            def print(self, *a, **k):
                pass
        self.console = _C()

class FastMCP:
    def __init__(self, name: str):
        self.name = name
    def tool(self):
        def decorator(fn):
            return fn
        return decorator
    def run(self):
        print("[stub] FastMCP.run() called")
