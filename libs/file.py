"""Saral library: file. Verbs: read, write, list, exists."""
import os

try:
    from saral import SaralError
except Exception:  # pragma: no cover - fallback when loaded standalone
    class SaralError(Exception):
        def __init__(self, message, line=0):
            super().__init__(message)
            self.line = line


def _need(pos, line, what="a path"):
    if not pos:
        raise SaralError(f"file verb needs {what}", line)
    return pos[0]


def read(env, pos, named, to_val, in_val, where, line):
    path = _need(pos, line)
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        raise SaralError(f"no such file: {path}", line)
    except IsADirectoryError:
        raise SaralError(f"that is a folder, not a file: {path}", line)


def write(env, pos, named, to_val, in_val, where, line):
    path = _need(pos, line)
    text = named.get("text", pos[1] if len(pos) > 1 else "")
    if not isinstance(text, str):
        text = str(text)
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def list_(env, pos, named, to_val, in_val, where, line):
    path = _need(pos, line, "a folder")
    try:
        return sorted(os.listdir(path))
    except FileNotFoundError:
        raise SaralError(f"no such folder: {path}", line)
    except NotADirectoryError:
        raise SaralError(f"that is a file, not a folder: {path}", line)


def exists(env, pos, named, to_val, in_val, where, line):
    return os.path.exists(_need(pos, line))


def register(env):
    env.register("file", "read", read)
    env.register("file", "write", write)
    env.register("file", "list", list_)
    env.register("file", "exists", exists)
