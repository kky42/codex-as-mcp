# minimal yaml stub used only for self-test to avoid external dependency

def safe_load(stream):
    try:
        _ = stream.read()
    except Exception:
        pass
    return {}
