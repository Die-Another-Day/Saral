"""Saral library: net. Verbs: scan, ping, get.
Safety: scanning is allowlisted to localhost + RFC1918 private ranges only.
Public IPs are refused, never scanned."""
import ipaddress
import socket
import subprocess
import urllib.request

try:
    from saral import SaralError
except Exception:
    class SaralError(Exception):
        def __init__(self, message, line=0):
            super().__init__(message)
            self.line = line


def _guard(host, line):
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        # Hostnames: only localhost is allowed in this MVP.
        if host in ("localhost",):
            return
        raise SaralError(
            f"net verbs only accept localhost or a private IP, not {host!r}", line)
    if not (ip.is_loopback or ip.is_private):
        raise SaralError(
            f"net verbs refuse public IPs: {host} is not localhost or private", line)


def _ports(named, pos):
    if "ports" in named:
        raw = str(named["ports"])
        return [int(p.strip()) for p in raw.split(",") if p.strip()]
    if "port" in named:
        return [int(named["port"])]
    return [22, 80, 443, 8000, 8080]


def scan(env, pos, named, to_val, in_val, where, line):
    if not pos:
        raise SaralError('scan needs a target, like: scan net "127.0.0.1"', line)
    host = str(pos[0])
    _guard(host, line)
    results = []
    for port in _ports(named, pos):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        try:
            code = sock.connect_ex((host, port))
        finally:
            sock.close()
        results.append({"host": host, "port": port, "open": code == 0})
    return results


def ping(env, pos, named, to_val, in_val, where, line):
    if not pos:
        raise SaralError('ping needs a target, like: ping net "127.0.0.1"', line)
    host = str(pos[0])
    _guard(host, line)
    flag = "-n" if subprocess.os.name == "nt" else "-c"
    proc = subprocess.run(["ping", flag, "1", "-W", "1", host],
                          capture_output=True, text=True, timeout=10)
    return proc.returncode == 0


def get(env, pos, named, to_val, in_val, where, line):
    if not pos:
        raise SaralError('get needs a URL, like: get net "http://127.0.0.1/"', line)
    url = str(pos[0])
    host = urllib.request.urlparse(url).hostname or ""
    _guard(host, line)
    req = urllib.request.Request(url, headers={"User-Agent": "Saral/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return {"status": resp.status, "body": body}
    except Exception as exc:
        raise SaralError(f"could not fetch {url}: {exc}", line)


def register(env):
    env.register("net", "scan", scan)
    env.register("net", "ping", ping)
    env.register("net", "get", get)
