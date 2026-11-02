"""Saral library: system. Verbs: run, info, env."""
import os
import platform
import subprocess

try:
    from saral import SaralError
except Exception:
    class SaralError(Exception):
        def __init__(self, message, line=0):
            super().__init__(message)
            self.line = line


def run(env, pos, named, to_val, in_val, where, line):
    if not pos:
        raise SaralError('run needs a command, like: run "echo hi"', line)
    cmd = pos[0]
    timeout = named.get("timeout", 30)
    try:
        timeout = int(timeout)
    except (TypeError, ValueError):
        raise SaralError("timeout must be a whole number of seconds", line)
    try:
        proc = subprocess.run(cmd, shell=True, text=True, capture_output=True,
                              timeout=timeout)
    except subprocess.TimeoutExpired:
        raise SaralError(f"command timed out after {timeout} seconds: {cmd}", line)
    out = (proc.stdout or "").strip()
    if proc.returncode != 0:
        # Honest failure, not an empty success: include stderr.
        err = (proc.stderr or "").strip()
        raise SaralError(
            f"command failed (exit {proc.returncode}): {cmd}"
            + (f" — {err[:300]}" if err else ""), line)
    return out


def info(env, pos, named, to_val, in_val, where, line):
    return {"os": platform.system(), "release": platform.release(),
            "machine": platform.machine(), "python": platform.python_version()}


def env_var(env, pos, named, to_val, in_val, where, line):
    if not pos:
        raise SaralError('env needs a name, like: env system "HOME"', line)
    return os.environ.get(pos[0], "")


def register(env):
    env.register("system", "run", run)
    env.register("system", "info", info)
    env.register("system", "env", env_var)
