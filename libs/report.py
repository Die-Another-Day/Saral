"""Saral library: report. Verb: save (value -> file, json/csv/text)."""
import csv
import io
import json
import os

try:
    from saral import SaralError
except Exception:
    class SaralError(Exception):
        def __init__(self, message, line=0):
            super().__init__(message)
            self.line = line


def save(env, pos, named, to_val, in_val, where, line):
    if not pos or to_val is None:
        raise SaralError(
            'save looks like: save data to "out.json" format : json', line)
    value, path = pos[0], str(to_val)
    fmt = str(named.get("format", "json")).lower()
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    if fmt == "json":
        text = json.dumps(value, indent=2, ensure_ascii=False)
    elif fmt == "text":
        if isinstance(value, (list, tuple)):
            text = "\n".join(str(item) for item in value)
        elif isinstance(value, dict):
            text = json.dumps(value, indent=2, ensure_ascii=False)
        else:
            text = str(value)
    elif fmt == "csv":
        if not isinstance(value, (list, tuple)) or not value:
            raise SaralError("csv save needs a non-empty list", line)
        buf = io.StringIO()
        if isinstance(value[0], dict):
            writer = csv.DictWriter(buf, fieldnames=list(value[0].keys()))
            writer.writeheader()
            writer.writerows(value)
        else:
            writer = csv.writer(buf)
            for item in value:
                writer.writerow([item])
        text = buf.getvalue()
    else:
        raise SaralError(f"unknown report format {fmt!r} (use json, csv or text)", line)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def register(env):
    env.register("report", "save", save)
