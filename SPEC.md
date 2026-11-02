# Saral Language Specification — v0.3.0

## 1. Why Saral is not a renamed Python

Python, Bash, and PowerShell are general-purpose: they make you glue
text together (subprocess output, grep, JSON parsing) before you get a
result. Saral is an automation language: verbs return **structured
values** (lists, tables, counts) that the next verb can filter, show,
or save without parsing text. Its syntax is also its own:

| Saral | Python / Bash equivalent |
|---|---|
| `took file` | `import` / sourcing a library — but Saral loads by library name, not by file path |
| `text is read file "notes.txt"` | `text = open(...).read()` — Saral uses the word `is`, never `=` |
| `scan net "127.0.0.1" -> hosts` | a pipeline arrow that **names** its result, not stdout piping |
| `save data to "out.json" format : json` | named arguments with `key : value`, no parentheses, no commas |
| `filter hosts where open is true` | a filter sentence, not a list comprehension or `jq` |
| blocks by indentation, no braces, no colon after the header | like Python's indentation, but headers carry no trailing colon |

There are no semicolons, no brackets for calls, no `=` assignment,
no functions, and no classes in the MVP. That is a deliberate limit:
scripts are task lists, not programs.

## 2. Lexical rules

- Lines, `#` comments (to end of line, outside strings).
- Strings in double quotes, with `\n`, `\t`, `\\`, `\"` escapes.
- Numbers (integers, decimals), `true`, `false`.
- `->` (flow) and `:` (named argument) are separate tokens.
- Indentation (spaces) defines blocks. Tabs are expanded to 4 spaces.

## 3. Statements

```
took <library>
took <library> as <alias>
took log.rules                     # dotted name, loads libs/log_rules.py
<var> is <verb call>
<var> is <literal or variable>
<verb call> -> <var>
<verb call>
for each <var> in <list>
    <indented statements>
if <condition>
    <indented statements>
else
    <indented statements>
while <condition>
    <indented statements>
<var> is <expr>                    # v0.3 arithmetic, e.g. x is 2 + 3 * 4
```

v0.2 adds two separators, both analogous to the existing `to`/`in`:
`from <x>` (e.g. `remove data "a" from myset`,
`link data graph from "a" to "b"`) and `using <label> <file>`
(e.g. `filter log.rules "a.log" using rules "r.txt"`, where
`named["using"]` is the file). `from : "a"` and `using : merge`
still parse as ordinary named arguments, because the separator form
only triggers when the next token is not `:`.

## 4. Verb calls

A verb call is plain words: verb, optional library, positional
arguments, then named arguments (`key : value`), then special words:

```
read file "notes.txt"
scan net "127.0.0.1" ports : "22,80"
run "echo hi" timeout : 5
save data to "out.json" format : json
find "ERROR" in text
filter hosts where port is 80
filter hosts where name contains "web"
filter hosts where port is not 22
```

Library disambiguation: if the word after the verb is a loaded
library (or its alias), it names the library. Otherwise it is a
positional argument — so `show message` shows the variable `message`,
it does not try to load a library called `message`.

## 5. Conditions and arithmetic (v0.3)

```
if count is 0
if host is not "down"
if text contains "ERROR"
if open
if count > 5
if total >= 10
x is 2 + 3 * 4          # 14: * and / bind tighter than + and -
total is a + b
n is n - 1
```

Operators: `is`, `is not`, `contains`, `>`, `<`, `>=`, `<=`.
A bare variable (or expression) tests truthiness. Left and right
sides of a condition are full arithmetic expressions. Arithmetic
needs spaces around operators (`2 + 3`, not `2+3`), because a
`-` next to a word is part of that word in the lexer. Division by
zero is a clear error. `while` loops are capped at 1000 iterations:
a loop that never changes its condition errors instead of hanging.
`else` must sit at the same indent as its `if`.

## 6. Values

Values are returned by verbs: strings, numbers, booleans, lists,
and tables (lists of dictionaries, e.g. scan results
`{"host": "127.0.0.1", "port": 22, "open": false}`).
Dotted access reads a field: `result.status`, `host.port`.
There is no list-literal syntax in the MVP; lists come from verbs.

## 7. Errors

Every error is printed in plain words with its line number, e.g.:

```
Saral error on line 2: no such file: does-not-exist.txt
Saral error on line 2: net verbs refuse public IPs: 8.8.8.8 is not localhost or private
```

A failed command, missing file, or refused target exits non-zero.
It never prints an empty success.

## 8. Libraries and the bridge

A library is either:

- a Python module `libs/<name>.py` with `register(env)`, or
- a folder `libs/<name>/lib.json` with
  `{"name": ..., "language": "node"|"shell"|"python",
    "entry": "file", "verbs": ["..."]}`.

The bridge protocol is JSON over stdin/stdout:

```
in:  {"verb": "greet", "args": ["Saral"], "named": {}}
out: {"result": "Hello from Node, Saral!"}
     or {"error": "unknown verb ..."}
```

The bridge is how Saral supports libraries written in other
languages without rewriting them: the library stays in its own
language, Saral calls it over JSON. `libs/greet_bridge/` (Node.js)
is the working example in this MVP.

## 9. Data structures and algorithms (v0.2, library `data`)

Containers are values: create one, then act on it with verbs. The
kind is quoted (`new data "stack"`) because a bare word in Saral is
a variable name, not a label — writing `new data stack` would be
read as "the variable called stack", which does not exist yet.

```
stack is new data "stack"
push data "a" to stack
top is pop data stack            # LIFO; pop/peek on empty = error
top is peek data stack
queue is new data "queue"
enqueue data "a" to queue
first is dequeue data queue      # FIFO; dequeue on empty = error
myset is new data "set"
add data "a" to myset            # duplicates kept once
yes is has data myset "a"        # true/false
remove data "a" from myset       # also: remove data myset "a"
mymap is new data "map"
put data mymap key : "a" value : 1
v is get data mymap key : "a"    # missing key = error
tree is new data "tree"
insert data tree value : 5
yes is search data tree value : 5
sorted is walk data tree         # in-order, so already sorted
graph is new data "graph"
link data graph from "a" to "b" weight : 3   # weight default 1
friends is neighbours data graph node : "a"
route is path data graph from "a" to "b"     # BFS, fewest hops; [] if none
best is shortest data graph from "a" to "b"  # Dijkstra: {"path": [...], "distance": n}
                                                # distance -1 and [] if unreachable
```

Sorting and searching are implemented by hand in `libs/data.py`
(merge sort, quick sort, binary search loop, BFS, Dijkstra with a
manual minimum scan). They are not calls to a built-in sort:
`sort` returns a new list and never mutates its input.

```
sorted is sort data items using : merge        # or using : quick (default merge)
sorted is sort data rows by : "count" using : quick
idx is search data items value : 42 using : binary   # index, or -1
idx is search data items value : 42 using : linear   # default linear
```

Binary search first checks the list really is sorted (by the same
field, if `by` is given); an unsorted list is a clear error, not a
silent wrong index. Linear search needs no sorted input.

Tables (lists of rows) and list/text utilities, all in `data`:

```
uniq is unique data items          # order preserved, duplicates removed
grouped is group data rows by : "severity"   # field -> list of rows
top5 is top data items count : 5   # first 5 items (frequency ranking
                                    # lives in log.rules top, not here)
n is count data items              # lists, tables, sets, maps, stacks, queues
f is first data items
l is last data items
rev is reverse data items
joined is join data items separator : ","
parts is split data "a,b" separator : ","
```

Ambiguous verb names (`count`, `filter`, `top`, `search`) are
resolved by the library word: `count data items` vs
`count logs "a.log" ...` are different verbs in different libraries.
Writing the verb without a library word when two loaded libraries
both have it is an error telling you to name the library.

v0.3 additions, all in `libs/data.py`:

```
heap is new data "heap"
push data "task" to heap priority : 3   # lowest priority first;
                                         # missing priority is an error
urgent is pop data heap                # pop/peek on empty = error
top is peek data heap
list is new data "linked"
append data "x" to list
walked is walk data list               # in insertion order
remove data "x" from list              # also: remove data list "x"
trie is new data "trie"
insert data trie value : "cat"
yes is search data trie value : "cat"  # exact word only; "ca" is false
words is prefix data trie "ca"         # ["car", "cat"], alphabetical
walked is walk data graph from "a"     # DFS, neighbours in link order
cyc is cycle data graph                # true/false, three-colour DFS
order is topological data graph        # Kahn's algorithm; a cyclic
                                         # graph is an error, never a
                                         # partial order
```

The heap is a hand-rolled array binary heap (sift up/down, no
`heapq`); equal priorities come out in push order. The linked list
and trie are hand-rolled node structures.

Not in v0.3, stated plainly: AVL/red-black trees, a from-scratch
hash table (set/map storage uses Python's set/dict), and graph
algorithms beyond BFS, DFS, Dijkstra, cycle detection, and
topological sort.

## 10. log.rules — SOC rules (v0.2, library `log.rules`)

`took log.rules` loads `libs/log_rules.py` (dotted name to
underscore file, in the loader). The library also registers the
alias `rules`, so `apply rules ...` works, and registers `filter`
under `logs` as well, so `filter logs ... using rules ...` works
when both libraries are loaded — without overwriting `logs`
find/count.

Rule file, one rule per line (`#` comments allowed):

```
rule "ssh brute force" pattern : "Failed password" severity : high at least : 5
rule "disk full" pattern : "disk full" severity : medium
```

Rules: `pattern` (substring, case-sensitive) and `severity` are
required; `severity` must be low/medium/high/critical, otherwise a
clear error naming the rule-file line. `at least` defaults to 1.

```
alerts is apply log.rules "rules.txt" to "auth.log"
# -> [{"rule": ..., "pattern": ..., "severity": ..., "count": N,
#      "lines": [...]}, ...] for rules with count >= at least only
matched is filter log.rules "auth.log" using rules "rules.txt"
# -> matched lines only, once each, in log order; 'at least' does
#    not apply here, because filtering is per line, not per alert
ips is extract log.rules "auth.log"
# -> unique IPv4 addresses, order of first appearance, octets 0-255
topips is top log.rules "auth.log" count : 5
# -> [{"ip": ..., "count": N}, ...], most frequent first, ties by IP
chain is graph log.rules "auth.log"
# -> a data Graph: a line with two IPs links first -> second;
#    a line with one IP adds that node only. Then, e.g.:
route is path data chain from "10.0.0.5" to "10.0.0.3"
```

v0.3 additions:

```
rule "ssh burst" pattern : "Failed password" severity : high at least : 5 within : 60
rule "bad user" pattern : "Failed.*user root" severity : medium match : regex
tl is timeline log.rules "auth.log" using rules "rules.txt"
```

`match` defaults to `text` (substring, case-sensitive); `match :
regex` compiles the pattern, and a bad regex is a clear error
naming the rule line, never a silent substring fallback. `within`
is seconds (integer, 1 or more). A windowed rule alerts only when
at least `at least` matches fall inside one sliding window
(interval <= `within` seconds, inclusive); the alert's `count`
is the largest burst count, its `lines` are that burst's lines,
and it carries `within` and `skipped`. Skipped lines are matched
lines with no parseable timestamp: they are never counted as
inside a window. Timestamps parse ISO-like
`2026-11-02 09:10:05` / `2026-11-02T09:10:05` and syslog-style
`Nov  2 09:10:05` (current year assumed). Window thresholds do
not apply to `filter` (filtering is per line); regex does.
`timeline` returns `{"time", "line"}` rows sorted by timestamp,
unparseable lines last in original order; without `using` it
returns every line, sorted.

Not in v0.3: correlation across rule files.

## 11. Safety

- `net` verbs: localhost + RFC1918 private only; public IPs refused.
- No VAPT verbs in this MVP.
- No login, CAPTCHA, or human-verification automation, ever.
  If a site shows a human check, stop and hand it to the human.
- `system` `run` uses a timeout (default 30s) and reports a failed
  command as an error, including its stderr, not as success.

## 12. CLI (v0.3) and local packages

```
saral script.srl          # run (existing)
saral check script.srl    # parse only, no execution; exit 0/1
saral list                # libraries actually in libs/, with verbs
saral version             # Saral 0.3.0
```

`check` catches parse errors (bad strings, stray indentation,
bad block structure) without running anything; runtime errors
(missing library, missing file) are not parse errors and do not
fail `check`. Packages are local only in v0.3: a library folder
with `lib.json` placed in `libs/` is listed and usable. There is
deliberately no download/install-from-internet command — remote
packages are a future, signed-packages-only step, because
downloading and running remote code unverified would be unsafe.

## 13. Parser bug fixed in v0.3 (honest note)

Before v0.3, a block with two statements only ran its first one:
the old block parser broke on any later line whose indent was
greater than header-indent + 1, and the rest of the block was
silently dropped. v0.3 fixes this: a block's indent is the indent
of its first line, every line at that indent belongs to the block,
a dedent ends it, and stray indentation after the top-level block
is now a clear error instead of a silent drop. No old test was
changed for this fix; all 28 old tests still pass, and a new
regression test (`test_multi_statement_block`) covers it.
