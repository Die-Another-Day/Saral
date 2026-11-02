"""Saral library: log.rules — SOC rule files for log analysis.

Load it with the dotted name, which maps to this file:
    took log.rules

A rule file is plain Saral-style text, one rule per line. A rule needs
a pattern and a severity; 'at least' is optional and defaults to 1:
    rule "ssh brute force" pattern : "Failed password" severity : high at least : 5
    rule "disk full" pattern : "disk full" severity : medium

Severity must be low, medium, high, or critical. A bad or missing
severity is a clear error, never a silent default. A rule only
creates an alert when its match count reaches 'at least' — that
threshold applies to alerts (apply), not to line filtering (filter),
which returns every line matching any rule pattern.

Verbs (library token is log.rules, or the alias 'rules'):
    alerts is apply log.rules "rules.txt" to "auth.log"
    alerts is apply rules "rules.txt" to "auth.log"   (same thing)
    matched is filter log.rules "auth.log" using rules "rules.txt"
    matched is filter logs "auth.log" using rules "rules.txt"
               (only when both 'logs' and 'log.rules' are loaded)
    ips is extract log.rules "auth.log" kind : ips
    topips is top log.rules "auth.log" count : 5
    chain is graph log.rules "auth.log"
        (nodes are IPs; a line holding two IPs links the first to
         the second, so the result is a data Graph you can run
         path/shortest on. Lines with one IP add that node only.)

Patterns are plain substrings (case-sensitive, like logs find)
by default; v0.3 adds match : regex (a bad regex is a clear error)
and within : N seconds (a windowed rule only alerts when at least
N matches fall inside one window; lines with no parseable
timestamp are skipped and reported as 'skipped', never counted
as inside a window). timeline returns matched lines sorted by
parsed timestamp.
"""
import datetime
import importlib.util
import os
import re

try:
    from saral import SaralError
except Exception:
    class SaralError(Exception):
        def __init__(self, message, line=0):
            super().__init__(message)
            self.line = line


SEVERITIES = ("low", "medium", "high", "critical")
_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_ISO_RE = re.compile(r"(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})")
_SYSLOG_RE = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
                         r"\s+(\d{1,2}) (\d{2}:\d{2}:\d{2})\b")
_MONTHS = {name: i + 1 for i, name in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}


def parse_timestamp(line_text):
    """First timestamp in a line, or None.

    Formats: ISO-like 2026-11-02 09:10:05 / 2026-11-02T09:10:05, and
    syslog-style Nov  2 09:10:05 (year assumed to be the current year,
    because syslog lines carry no year). Anything else is unparseable.
    """
    m = _ISO_RE.search(line_text)
    if m:
        try:
            return datetime.datetime.strptime(
                m.group(1) + " " + m.group(2), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    m = _SYSLOG_RE.search(line_text)
    if m:
        try:
            return datetime.datetime(
                datetime.datetime.now().year, _MONTHS[m.group(1)],
                int(m.group(2)), *map(int, m.group(3).split(":")))
        except ValueError:
            return None
    return None


def _read_lines(path, line, what="file"):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read().splitlines()
    except FileNotFoundError:
        raise SaralError(f"no such {what}: {path}", line)


def parse_rules(text, line):
    """Parse rule-file text into a list of rule dicts. Raises SaralError
    with the rule-file line number in the message for any bad rule."""
    rules = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not stripped.startswith("rule"):
            raise SaralError(
                f"rule file line {lineno}: a rule line must start with rule", line)
        name_match = re.search(r'"([^"]*)"', stripped)
        if not name_match:
            raise SaralError(
                f"rule file line {lineno}: a rule needs a quoted name", line)
        name = name_match.group(1)
        rest = stripped[name_match.end():]
        # key : value pairs; value is a quoted string, a number, or a word.
        pairs = {}
        for m in re.finditer(r"(\w+)\s*:\s*(\"[^\"]*\"|\d+|[A-Za-z]+)", rest):
            raw_val = m.group(2)
            if raw_val.startswith('"'):
                pairs[m.group(1)] = raw_val[1:-1]
            elif raw_val.isdigit():
                pairs[m.group(1)] = int(raw_val)
            else:
                pairs[m.group(1)] = raw_val
        if "pattern" not in pairs:
            raise SaralError(
                f"rule file line {lineno}: rule {name!r} needs pattern : \"text\"", line)
        if "severity" not in pairs:
            raise SaralError(
                f"rule file line {lineno}: rule {name!r} needs severity : low|medium|high|critical",
                line)
        severity = str(pairs["severity"]).lower()
        if severity not in SEVERITIES:
            raise SaralError(
                f"rule file line {lineno}: rule {name!r} has severity "
                f"{pairs['severity']!r}, which is not low, medium, high, or critical",
                line)
        at_least = pairs.get("at", pairs.get("atleast", pairs.get("at_least", 1)))
        # The documented spelling is 'at least : N' — the tokenizer
        # above sees 'at' as a key only when followed by ':', so handle
        # the spaced form explicitly: 'at least : 5'.
        spaced = re.search(r"\bat\s+least\s*:\s*(\d+)", rest)
        if spaced:
            at_least = int(spaced.group(1))
        try:
            at_least = int(at_least)
        except (TypeError, ValueError):
            raise SaralError(
                f"rule file line {lineno}: rule {name!r} needs at least : a whole number",
                line)
        if at_least < 1:
            raise SaralError(
                f"rule file line {lineno}: rule {name!r} needs at least : 1 or more",
                line)
        # v0.3: match : text (default, substring) or match : regex.
        # A bad regex is a clear error naming the rule line, never a
        # silent fallback to substring matching.
        match = str(pairs.get("match", "text")).lower()
        if match not in ("text", "regex"):
            raise SaralError(
                f"rule file line {lineno}: rule {name!r} has match "
                f"{pairs['match']!r}, which is not text or regex", line)
        compiled = None
        if match == "regex":
            try:
                compiled = re.compile(str(pairs["pattern"]))
            except re.error as exc:
                raise SaralError(
                    f"rule file line {lineno}: rule {name!r} has a bad "
                    f"regex pattern {pairs['pattern']!r}: {exc}", line)
        # v0.3: within : N seconds (integer). A windowed rule only
        # alerts when at least N matches fall inside one window.
        within = pairs.get("within")
        if within is not None:
            try:
                within = int(within)
            except (TypeError, ValueError):
                raise SaralError(
                    f"rule file line {lineno}: rule {name!r} needs "
                    f"within : a whole number of seconds", line)
            if within < 1:
                raise SaralError(
                    f"rule file line {lineno}: rule {name!r} needs "
                    f"within : 1 or more seconds", line)
        rules.append({"name": name, "pattern": str(pairs["pattern"]),
                      "severity": severity, "at_least": at_least,
                      "match": match, "compiled": compiled,
                      "within": within})
    return rules


def _rule_matches(rule, line_text):
    if rule["match"] == "regex":
        return rule["compiled"].search(line_text) is not None
    return rule["pattern"] in line_text


def _window_burst(timed_lines, within, at_least):
    """Largest burst inside one window.

    timed_lines: [(datetime, line), ...] sorted by time. Returns
    (burst_count, burst_lines) for the first window reaching the
    largest count, using a two-pointer sliding window (interval
    <= within seconds, inclusive)."""
    best_count, best_lines = 0, []
    start = 0
    for end in range(len(timed_lines)):
        while (timed_lines[end][0] - timed_lines[start][0]).total_seconds() \
                > within:
            start += 1
        count = end - start + 1
        if count > best_count:
            best_count = count
            best_lines = [ln for _t, ln in timed_lines[start:end + 1]]
    return best_count, best_lines


def _load_rules(path, line):
    return parse_rules("\n".join(_read_lines(path, line, "rule file")), line)


def _ips_in(line_text):
    out = []
    for m in _IP_RE.finditer(line_text):
        parts = m.group(0).split(".")
        if all(0 <= int(p) <= 255 for p in parts) and m.group(0) not in out:
            out.append(m.group(0))
    return out


def _data_graph():
    """Load the Graph class from libs/data.py without going through
    the Saral loader (data.py has no import side effects)."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.py")
    spec = importlib.util.spec_from_file_location("saral_data_lib", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.Graph


def apply_rules(env, pos, named, to_val, in_val, where, line):
    if not pos or to_val is None:
        raise SaralError(
            'apply looks like: apply log.rules "rules.txt" to "auth.log"', line)
    rules = _load_rules(pos[0], line)
    log_lines = _read_lines(str(to_val), line, "log file")
    alerts = []
    for rule in rules:
        matched = [ln for ln in log_lines if _rule_matches(rule, ln)]
        if rule["within"] is None:
            if len(matched) >= rule["at_least"]:
                alerts.append({"rule": rule["name"], "pattern": rule["pattern"],
                               "severity": rule["severity"],
                               "count": len(matched), "lines": matched})
            continue
        # Windowed rule: unparseable lines are SKIPPED (never counted
        # as inside a window), and the alert says how many were
        # skipped. This is the documented v0.3 behaviour, tested.
        timed, skipped = [], 0
        for ln in matched:
            ts = parse_timestamp(ln)
            if ts is None:
                skipped += 1
            else:
                timed.append((ts, ln))
        timed.sort(key=lambda item: item[0])
        burst_count, burst_lines = _window_burst(
            timed, rule["within"], rule["at_least"])
        if burst_count >= rule["at_least"]:
            alerts.append({"rule": rule["name"], "pattern": rule["pattern"],
                           "severity": rule["severity"],
                           "count": burst_count, "lines": burst_lines,
                           "within": rule["within"], "skipped": skipped})
    return alerts


def filter_rules(env, pos, named, to_val, in_val, where, line):
    if not pos or "using" not in named:
        raise SaralError(
            'filter looks like: filter log.rules "auth.log" using rules "rules.txt"',
            line)
    rules = _load_rules(str(named["using"]), line)
    log_lines = _read_lines(str(pos[0]), line, "log file")
    # Each line once, in log order, even if several rules match it.
    # Window thresholds do not apply to filtering (it is per line);
    # regex rules do apply, through _rule_matches.
    return [ln for ln in log_lines
            if any(_rule_matches(r, ln) for r in rules)]


def timeline(env, pos, named, to_val, in_val, where, line):
    """Matched lines sorted by parsed timestamp.

    timeline log.rules "auth.log" using rules "rules.txt"  -> matched
    lines only, sorted. Without 'using', every line is returned,
    sorted. Lines with no parseable timestamp go last, in their
    original order (stable sort), and carry time "".
    Returns [{"time": "2026-11-02T09:10:05", "line": ...}, ...].
    """
    if not pos:
        raise SaralError(
            'timeline looks like: timeline log.rules "auth.log" '
            'using rules "rules.txt"', line)
    log_lines = _read_lines(str(pos[0]), line, "log file")
    if "using" in named:
        rules = _load_rules(str(named["using"]), line)
        log_lines = [ln for ln in log_lines
                     if any(_rule_matches(r, ln) for r in rules)]
    stamped = [(parse_timestamp(ln), ln) for ln in log_lines]
    # datetime.max sorts unparseable lines last; Python's sort is
    # stable, so their original order is preserved.
    stamped.sort(key=lambda item: item[0] or datetime.datetime.max)
    return [{"time": ts.isoformat() if ts is not None else "", "line": ln}
            for ts, ln in stamped]


def extract(env, pos, named, to_val, in_val, where, line):
    if not pos:
        raise SaralError('extract looks like: extract log.rules "auth.log"', line)
    kind = str(named.get("kind", "ips")).lower()
    if kind != "ips":
        raise SaralError(f"extract kind is ips, not {kind!r}", line)
    log_lines = _read_lines(str(pos[0]), line, "log file")
    out = []
    for ln in log_lines:
        for ip in _ips_in(ln):
            if ip not in out:
                out.append(ip)
    return out


def top(env, pos, named, to_val, in_val, where, line):
    if not pos:
        raise SaralError('top looks like: top log.rules "auth.log" count : 5', line)
    log_lines = _read_lines(str(pos[0]), line, "log file")
    counts = {}
    for ln in log_lines:
        for ip in _ips_in(ln):
            counts[ip] = counts.get(ip, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    try:
        n = int(named.get("count", 5))
    except (TypeError, ValueError):
        raise SaralError("top needs count : a whole number", line)
    return [{"ip": ip, "count": c} for ip, c in ranked[:n]]


def graph(env, pos, named, to_val, in_val, where, line):
    if not pos:
        raise SaralError('graph looks like: graph log.rules "auth.log"', line)
    Graph = _data_graph()
    g = Graph()
    for ln in _read_lines(str(pos[0]), line, "log file"):
        ips = _ips_in(ln)
        for ip in ips:
            g.add_node(ip)
        if len(ips) >= 2:
            g.link(ips[0], ips[1], 1)
    return g


def register(env):
    # Primary name, plus the 'rules' alias the task examples use, so
    # 'apply rules ...' resolves without a separate library.
    for verb, fn in [("apply", apply_rules), ("filter", filter_rules),
                     ("extract", extract), ("top", top), ("graph", graph),
                     ("timeline", timeline)]:
        env.register("log.rules", verb, fn)
    # The 'filter logs ... using rules ...' shorthand: register filter
    # under 'logs' too, without overwriting env.libs['logs'] (so logs
    # find/count keep working when both libraries are loaded).
    env.register("logs", "filter", filter_rules)
    env.libs.setdefault("rules", "log.rules")
