# Saral — the simplest automation language (v0.3.0)

> **Publication status: NOT PUBLISHED YET.** This folder is a release
> preparation copy. The GitHub repo `Die-Another-Day/Saral` has not
> been created or pushed yet, so the one-command download in
> INSTALL.md ("After push") does not work today and will return a
> 404 until the push is verified. To install today, use LOCAL mode:
> `./install.sh --local .` — see INSTALL.md for exact commands,
> destinations, and uninstall steps. No PyPI, apt, or Windows
> installer exists yet.

Saral (Hindi for "simple") is a brand-new scripting language for automation.
Files end in `.srl`, the command is `saral`, and a script reads like plain
words — no semicolons, no braces, no `=` assignment, no functions or
classes. v0.2 adds data structures and algorithms in that same style,
plus a SOC rule library (`log.rules`). v0.3 adds time-window and regex
rules with a timeline, more data structures (heap, linked list, trie,
graph DFS/cycle/topological sort), arithmetic, comparisons, `else`,
`while`, and a small CLI (`check`, `list`, `version`).

```saral
took net
took report

hosts is scan net "127.0.0.1" ports : "22,80,8000"
open is filter hosts where open is true
show open
save hosts to "scan.json" format : json
```

Run it:

```bash
python3 saral.py examples/hello.srl
# or, from this folder:
./saral examples/hello.srl
```

It runs on any system with Python 3 (Linux, macOS, Windows) — the
interpreter uses only the Python standard library. A later step can
package it as a single binary installer, like Python; that installer
does not exist yet.

## What Saral is — and is not

**It is:** a real interpreter (lexer, parser, executor) plus real core
libraries, a plugin system, and a cross-language bridge. Every example
in `examples/` runs and produces real output (see PROOF.md).

**It is not yet:** a huge library catalogue, a general-purpose language,
or a finished product used by everyone. The catalogue in this MVP is
small on purpose: every verb listed below is implemented and tested.
Nothing is claimed that is not in the code.

## Libraries and verbs (all implemented and tested)

| Library | Verbs |
|---|---|
| `file` | `read file "path"`, `write file "path" text : "..."`, `list file "folder"`, `exists file "path"` |
| `system` | `run "command" timeout : 5`, `info system`, `env system "HOME"` |
| `net` | `scan net "127.0.0.1" ports : "22,80"`, `ping net "127.0.0.1"`, `get net "http://127.0.0.1/"` |
| `logs` | `find logs "app.log" pattern : "ERROR"`, `count logs "app.log" pattern : "ERROR"` |
| `report` | `save data to "out.json" format : json` (also `csv`, `text`) |
| `greet_bridge` (Node bridge) | `greet greet_bridge "name"`, `shout greet_bridge "name"` |
| `data` (v0.2, containers) | `stack is new data "stack"`, `push data "x" to stack`, `pop data stack`, `peek data stack`, `queue is new data "queue"`, `enqueue data "x" to queue`, `dequeue data queue`, `myset is new data "set"`, `add data "a" to myset`, `has data myset "a"`, `remove data "a" from myset`, `mymap is new data "map"`, `put data mymap key : "a" value : 1`, `get data mymap key : "a"`, `tree is new data "tree"`, `insert data tree value : 5`, `search data tree value : 5`, `walk data tree`, `graph is new data "graph"`, `link data graph from "a" to "b" weight : 3`, `neighbours data graph node : "a"`, `path data graph from "a" to "b"`, `shortest data graph from "a" to "b"` |
| `data` (v0.2, sorting/searching/tables) | `sort data items using : merge` or `using : quick`, `sort data rows by : "count" using : quick`, `search data items value : 42 using : binary` or `using : linear`, `unique data items`, `group data rows by : "severity"`, `top data items count : 5`, `count data items`, `first data items`, `last data items`, `reverse data items`, `join data items separator : ","`, `split data "a,b" separator : ","` |
| `data` (v0.3, more containers) | `heap is new data "heap"`, `push data "task" to heap priority : 3` (lowest first), `pop data heap`, `peek data heap`, `list is new data "linked"`, `append data "x" to list`, `walk data list`, `remove data "x" from list`, `trie is new data "trie"`, `insert data trie value : "cat"`, `search data trie value : "cat"`, `words is prefix data trie "ca"`, `walked is walk data graph from "a"` (DFS), `cyc is cycle data graph`, `order is topological data graph` (error on a cyclic graph, never a partial order) |
| `log.rules` (v0.2, SOC) | `took log.rules` (dotted name loads `libs/log_rules.py`), `alerts is apply log.rules "rules.txt" to "auth.log"`, `alerts is apply rules "rules.txt" to "auth.log"` (alias), `matched is filter log.rules "auth.log" using rules "rules.txt"`, `matched is filter logs "auth.log" using rules "rules.txt"` (needs both `logs` and `log.rules` loaded), `ips is extract log.rules "auth.log"`, `topips is top log.rules "auth.log" count : 5`, `chain is graph log.rules "auth.log"` |
| `log.rules` (v0.3, SOC) | `rule "ssh burst" pattern : "Failed password" severity : high at least : 5 within : 60`, `rule "bad user" pattern : "Failed.*user root" severity : medium match : regex` (default `match : text`), `tl is timeline log.rules "auth.log" using rules "rules.txt"` (sorted by parsed timestamp; unparseable lines last, in original order) |
| built-in (no `took` needed) | `show value`, `find "pattern" in value`, `filter list where field is value`, `filter list where count > 5` |
| language (v0.3) | `x is 2 + 3 * 4` (arithmetic with `+ - * /`, `*`/`/` bind tighter; division by zero is an error), `if count > 5` (also `<`, `>=`, `<=`), `else` at the same indent as its `if`, `while n > 0` (capped at 1000 iterations — a loop that never stops errors instead of hanging) |

## log.rules — rule files

One rule per line, plain Saral-style text. A rule needs a pattern
and a severity; `at least` is optional (default 1) and gates alerts
only, not line filtering. v0.3 adds `within : N` (seconds) and
`match : regex` (default `match : text`):

```
rule "ssh burst" pattern : "Failed password" severity : high at least : 5 within : 60
rule "bad user" pattern : "Failed.*user root" severity : medium match : regex
```

A windowed rule only alerts when at least `at least` matches fall
inside any `within`-second window (sliding window, inclusive).
Timestamps are parsed from ISO-like `2026-11-02 09:10:05` /
`2026-11-02T09:10:05` and syslog-style `Nov  2 09:10:05` (current
year assumed, because syslog carries no year). **Windowed rules
skip lines with no parseable timestamp — they are never counted
as inside a window — and the alert reports them as `skipped`.**
A bad regex is a clear error naming the rule line, never a silent
fallback to substring matching. `timeline` returns matched lines
as `{"time": "2026-11-02T09:10:05", "line": ...}`, sorted by
timestamp, with unparseable lines last in original order.

```
rule "ssh brute force" pattern : "Failed password" severity : high at least : 5
rule "disk full" pattern : "disk full" severity : medium
```

Severity must be `low`, `medium`, `high`, or `critical` — a bad or
missing severity is a clear error, never a silent default. Patterns
are plain substrings (case-sensitive), not regular expressions.
`apply` returns an alerts table (`rule`, `pattern`, `severity`,
`count`, `lines`) only for rules whose match count reaches `at
least`. `filter` returns every line matching any rule pattern, once,
in log order. `extract` returns unique IPs in order of first
appearance (octets validated 0–255). `graph` builds a data Graph:
a line holding two IPs links the first to the second, so you can
run `path`/`shortest` on the result for an attack chain.

Note on names, for parser honesty: containers are created with a
quoted kind (`new data "stack"`) because a bare word in Saral is a
variable name, not a label. `remove` also works as `remove data
myset "a"` (container first). `link`/`path`/`shortest` use the
`from "a" to "b"` separators, not `from : "a"`, because `to` is
already Saral's separator word. See SPEC.md §9–10 for the exact
forms and the reasons.

## Safety rules built into the MVP

- **Network guard:** `net` verbs only accept localhost and RFC1918
  private IPs. A public IP is refused with a clear error — it is never
  scanned. This follows the SecureOS rule: only systems you own or have
  permission to test.
- **No VAPT verbs in this MVP.** Attack automation belongs in the
  SecureOS lab later, gated to lab mode and a private LAN — not in a
  general scripting language.
- **No login, CAPTCHA, or human-verification automation.** Saral has
  no library for logging into any third-party account, and no library
  that passes an "I'm human" check or any other bot check. If a site
  shows a human check, the correct behaviour is to **stop and hand it
  to the human** — Saral must not automate past it. Examples and
  documentation use placeholders (`YOUR_ACCOUNT`) and environment
  variables only, never real credentials.
- **Honest errors:** a missing file, a failed command, or a refused
  public IP is an error with a line number and plain words — never an
  empty success.

## CLI (v0.3)

```bash
./saral examples/hello.srl   # run a script (existing behaviour)
./saral check examples/hello.srl  # parse only, no execution, exit 0/1
./saral list                 # libraries actually present in libs/, with verbs
./saral version              # Saral 0.3.0
```

Local packages only: a library folder with `lib.json` placed in
`libs/` is listed and usable. There is deliberately **no**
download/install-from-internet command in v0.3 — downloading and
running remote code unverified would be unsafe. Remote packages are
a future, signed-packages-only step.

## Examples

Run these from the saral-lang folder (fixture scripts use
`examples/...` paths; outputs go into the folder you run them from):

```bash
python3 saral.py examples/hello.srl        # files, system info, report
python3 saral.py examples/scan_localhost.srl # localhost scan + JSON report
python3 saral.py examples/log_check.srl    # write, find, count a log
python3 saral.py examples/bridge_demo.srl  # call a Node.js library
python3 saral.py examples/dsa_demo.srl     # v0.2: stack, queue, set, map, tree, graph, sort, search
python3 saral.py examples/soc_rules.srl    # v0.2: log.rules alerts, IPs, attack-chain graph
python3 saral.py examples/dsa_v03.srl      # v0.3: heap, linked list, trie, DFS/cycle/topo, arithmetic, else, while
python3 saral.py examples/soc_window.srl   # v0.3: time-window + regex rules, timeline
```

## Tests

```bash
python3 -m unittest discover -s tests -v
# 47 tests, all passing: the original 12, 16 v0.2 tests, and 19 new
# v0.3 tests (see PROOF.md). No old test was changed in v0.3.
```

## Adding a library

- **Python library:** add `libs/<name>.py` with a `register(env)` that
  calls `env.register("<name>", "<verb>", fn)`. A verb must have a real
  implementation — a verb with no implementation is not allowed.
- **Other-language library:** add `libs/<name>/lib.json` declaring
  `{name, language: node|shell|python, entry: file, verbs: [...]}`.
  The entry program reads `{"verb", "args", "named"}` as JSON on stdin
  and writes `{"result": ...}` (or `{"error": ...}`) as JSON on stdout.
  See `libs/greet_bridge/` (Node.js, actually run in tests) for a
  working example.

## Folder layout

```
saral.py            interpreter (lexer, parser, executor, loader)
saral               launcher (./saral script.srl)
libs/               one module per library + bridge folders
examples/           runnable .srl scripts (+ sample.log, soc_auth.log, soc_rules.txt fixtures)
tests/              unittest suite (real runs, real local server)
SPEC.md             full syntax specification
PROOF.md            commands run + actual output
```

## Limits (honest) — v0.3 not-yet list

- No functions, classes, or modules in scripts yet — tasks, verbs,
  variables, `for each`, `if`/`else`, and `while` only. No `else if`.
- No list literals, no parentheses in expressions — values come from
  verbs, and arithmetic needs spaces (`2 + 3`, not `2+3`).
- No Windows/macOS installer or single binary yet; you need Python 3
  installed. No remote package downloads (deliberately, see CLI above).
- **Not "all possible DSA":** in v0.3 are stack, queue, set, map,
  binary search tree, heap (hand-rolled min-heap), singly linked list,
  trie, directed graph (BFS, DFS, Dijkstra, cycle detection,
  topological sort), merge sort, quick sort, binary/linear search,
  unique, group, top, and the list/text utilities above.
  **Not in v0.3:** AVL/red-black trees, a from-scratch hash table
  (set/map storage uses Python's set/dict internally — stated, not
  hidden), hash maps with custom hashing, or graph algorithms beyond
  those listed.
- No VAPT, login, or CAPTCHA features — deliberately, see Safety above.
- `log.rules`: no correlation across rule files, and no rule that
  combines a window with a regex in a way beyond the documented
  fields (`within` and `match` are independent options on one rule).
