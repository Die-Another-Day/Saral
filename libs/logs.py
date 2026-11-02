"""Saral library: logs. Verbs: find, count (both need a log file)."""
import os

try:
    from saral import SaralError
except Exception:
    class SaralError(Exception):
        def __init__(self, message, line=0):
            super().__init__(message)
            self.line = line


def _read(path, line):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read().splitlines()
    except FileNotFoundError:
        raise SaralError(f"no such log file: {path}", line)


def find(env, pos, named, to_val, in_val, where, line):
    if not pos:
        raise SaralError('find needs a log file, like: find logs "app.log" pattern : "ERROR"', line)
    pattern = named.get("pattern", pos[1] if len(pos) > 1 else None)
    if pattern is None:
        raise SaralError('find logs needs pattern : "text"', line)
    return [ln for ln in _read(pos[0], line) if str(pattern) in ln]


def count(env, pos, named, to_val, in_val, where, line):
    if not pos:
        raise SaralError('count needs a log file, like: count logs "app.log" pattern : "ERROR"', line)
    pattern = named.get("pattern", pos[1] if len(pos) > 1 else None)
    if pattern is None:
        raise SaralError('count logs needs pattern : "text"', line)
    return sum(1 for ln in _read(pos[0], line) if str(pattern) in ln)


def register(env):
    env.register("logs", "find", find)
    env.register("logs", "count", count)
