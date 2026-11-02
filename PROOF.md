# Saral MVP — Proof of Run (2026-11-02)

Environment: Python 3.12.3, Node v24.22.1, bash 5.2.21, Linux.
All commands were run from `~/workspace/saral-lang/`.
No failure was hidden; the two failures found during development
(the `show message` library-name bug and the duplicated `SaralError`
class) were fixed in code and the suite re-run, not edited out of
this file.

## Test suite — 12/12 passing

```
$ python3 -m unittest discover -s tests -v
test_bridge_node_library (test_saral.SaralTests.test_bridge_node_library) ... ok
test_file_round_trip (test_saral.SaralTests.test_file_round_trip) ... ok
test_filter_where (test_saral.SaralTests.test_filter_where) ... ok
test_for_loop_and_filter (test_saral.SaralTests.test_for_loop_and_filter) ... ok
test_log_find_and_count (test_saral.SaralTests.test_log_find_and_count) ... ok
test_missing_file_is_an_error_not_empty_success (test_saral.SaralTests.test_missing_file_is_an_error_not_empty_success) ... ok
test_net_alias (test_saral.SaralTests.test_net_alias) ... ok
test_net_scan_real_local_server (test_saral.SaralTests.test_net_scan_real_local_server) ... ok
test_private_ip_guard_refuses_public (test_saral.SaralTests.test_private_ip_guard_refuses_public) ... ok
test_report_save_and_reread (test_saral.SaralTests.test_report_save_and_reread) ... ok
test_syntax_error_reports_line_number (test_saral.SaralTests.test_syntax_error_reports_line_number) ... ok
test_system_run_echo (test_saral.SaralTests.test_system_run_echo) ... ok

----------------------------------------------------------------------
Ran 12 tests in 0.921s

OK
```

What the tests actually prove: file read/write round-trip in a temp
dir; `run "echo ..."` output; a net scan of a real local TCP server
(the open port reported open, a neighbouring port reported closed —
both measured, not assumed); log find/count on a real sample log;
report save + JSON re-read; a Node bridge call; a public IP
(8.8.8.8) refused; a missing file reported as an error; a syntax
error reported with its line number.

## Examples — all run, exit 0

```
$ ./saral examples/bridge_demo.srl
Hello from Node, Saral!
SARAL!

$ ./saral examples/log_check.srl
ERROR disk full
ERROR timeout
2
errors found

$ ./saral examples/hello.srl
Hello, Saral
Hello, Saral
{
  "os": "Linux",
  "release": "7.0.0-39-generic",
  "machine": "x86_64",
  "python": "3.12.3"
}
done

$ ./saral examples/scan_localhost.srl
{"host": "127.0.0.1", "port": 22, "open": false}
{"host": "127.0.0.1", "port": 80, "open": false}
{"host": "127.0.0.1", "port": 8000, "open": false}
{"host": "127.0.0.1", "port": 8080, "open": false}
(empty list)
```

Note on the scan output: on this machine none of 22/80/8000/8080
was listening, so the filter for open ports correctly returned an
empty list. That is a real result, not a staged one — the test
suite's local-server test is the one that proves an open port is
detected.

## Not proven / not in this MVP

- Windows/macOS running (interpreter is stdlib-only Python, so it
  should run, but it was only run on Linux here).
- A packaged installer (no .exe/.deb yet).
- A large library catalogue (only the libraries in README.md exist).
- VAPT, login, or CAPTCHA features — deliberately absent.


---

# Saral v0.2 — Proof of Run (2026-11-02)

All commands run from `~/workspace/saral-lang/`. No failure was hidden:
two real failures were found and fixed in code during v0.2 — (1) a
Graph built by log.rules failed `path` because it loaded data.py as
a second module, fixed by duck-typing graph checks in data.py; (2)
`using : merge` was hijacked by the new `using` separator, fixed so
the separator only triggers when the next token is not `:`. The
suite was re-run after each fix, not edited to hide them.

## Test suite — 28/28 passing (original 12 still green)

```
test_bridge_node_library (test_saral.SaralTests.test_bridge_node_library) ... ok
test_file_round_trip (test_saral.SaralTests.test_file_round_trip) ... ok
test_filter_where (test_saral.SaralTests.test_filter_where) ... ok
test_for_loop_and_filter (test_saral.SaralTests.test_for_loop_and_filter) ... ok
test_log_find_and_count (test_saral.SaralTests.test_log_find_and_count) ... ok
test_missing_file_is_an_error_not_empty_success (test_saral.SaralTests.test_missing_file_is_an_error_not_empty_success) ... ok
test_net_alias (test_saral.SaralTests.test_net_alias) ... ok
test_net_scan_real_local_server (test_saral.SaralTests.test_net_scan_real_local_server) ... ok
test_private_ip_guard_refuses_public (test_saral.SaralTests.test_private_ip_guard_refuses_public) ... ok
test_report_save_and_reread (test_saral.SaralTests.test_report_save_and_reread) ... ok
test_syntax_error_reports_line_number (test_saral.SaralTests.test_syntax_error_reports_line_number) ... ok
test_system_run_echo (test_saral.SaralTests.test_system_run_echo) ... ok
test_binary_search_found_notfound_and_unsorted_error (test_saral_v02.DsaTests.test_binary_search_found_notfound_and_unsorted_error) ... ok
test_graph_bfs_and_dijkstra_differ (test_saral_v02.DsaTests.test_graph_bfs_and_dijkstra_differ) ... ok
test_map_put_get (test_saral_v02.DsaTests.test_map_put_get) ... ok
test_merge_and_quick_sort_random (test_saral_v02.DsaTests.test_merge_and_quick_sort_random) ... ok
test_queue_fifo (test_saral_v02.DsaTests.test_queue_fifo) ... ok
test_set_uniqueness_has_remove (test_saral_v02.DsaTests.test_set_uniqueness_has_remove) ... ok
test_sort_via_script_on_table (test_saral_v02.DsaTests.test_sort_via_script_on_table) ... ok
test_stack_lifo_and_peek (test_saral_v02.DsaTests.test_stack_lifo_and_peek) ... ok
test_tree_insert_search_walk_sorted (test_saral_v02.DsaTests.test_tree_insert_search_walk_sorted) ... ok
test_unique_group_top_and_list_utils (test_saral_v02.DsaTests.test_unique_group_top_and_list_utils) ... ok
test_apply_rules_alias_and_ip_extraction_top (test_saral_v02.LogRulesTests.test_apply_rules_alias_and_ip_extraction_top) ... ok
test_filter_using_rules_and_logs_shorthand (test_saral_v02.LogRulesTests.test_filter_using_rules_and_logs_shorthand) ... ok
test_graph_from_log_and_path (test_saral_v02.LogRulesTests.test_graph_from_log_and_path) ... ok
test_group_alerts_by_severity_via_data (test_saral_v02.LogRulesTests.test_group_alerts_by_severity_via_data) ... ok
test_severity_validation_error (test_saral_v02.LogRulesTests.test_severity_validation_error) ... ok
test_threshold_both_sides (test_saral_v02.LogRulesTests.test_threshold_both_sides) ... ok

----------------------------------------------------------------------
Ran 28 tests in 1.752s

OK
```

What the 16 new tests prove: stack LIFO + peek, queue FIFO, set
uniqueness + has/remove, map put/get, tree insert/search/in-order
sorted output, graph BFS vs Dijkstra on the same weighted graph
(BFS picks the direct hop, Dijkstra picks the cheaper 1+1 route),
merge and quick sort on 20 seeded random lists vs expected sorted
order, binary search found/not-found plus an unsorted-list error,
unique/group/top and first/last/reverse/join/split/count, log.rules
threshold both sides (6 matches: at least 5 fires, at least 7 does
not), severity validation error, filter using rules (both the
log.rules form and the logs shorthand), apply via the 'rules'
alias, IP extraction + top IPs, a log-built graph + path, and
grouping alerts by severity.

## Examples — all run, exit 0

```
--- examples/hello.srl
Hello, Saral
Hello, Saral
{
  "os": "Linux",
  "release": "7.0.0-39-generic",
  "machine": "x86_64",
  "python": "3.12.3"
}
done
exit:0
--- examples/scan_localhost.srl
{"host": "127.0.0.1", "port": 22, "open": false}
{"host": "127.0.0.1", "port": 80, "open": false}
{"host": "127.0.0.1", "port": 8000, "open": false}
{"host": "127.0.0.1", "port": 8080, "open": false}
(empty list)
exit:0
--- examples/log_check.srl
ERROR disk full
ERROR timeout
2
errors found
exit:0
--- examples/bridge_demo.srl
Hello from Node, Saral!
SARAL!
exit:0
--- examples/dsa_demo.srl
b
stack: ["a"]
queue: ["first", "second"]
first
set: ["a"]
map: {"web": 80}
80
3
5
7
a
b
{
  "path": [
    "a",
    "c",
    "b"
  ],
  "distance": 2
}
a
b
c
d
2
exit:0
--- examples/soc_rules.srl
{"rule": "ssh brute force", "pattern": "Failed password", "severity": "high", "count": 6, "lines": ["Failed password from 10.0.0.5 to 10.0.0.2", "Failed password from 10.0.0.5 to 10.0.0.2", "Failed password from 10.0.0.5 to 10.0.0.2", "Failed password from 10.0.0.5 to 10.0.0.2", "Failed password from 10.0.0.5 to 10.0.0.2", "Failed password from 10.0.0.9 to 10.0.0.2"]}
{"rule": "disk full", "pattern": "disk full", "severity": "medium", "count": 1, "lines": ["INFO disk full on host"]}
{
  "high": [
    {
      "rule": "ssh brute force",
      "pattern": "Failed password",
      "severity": "high",
      "count": 6,
      "lines": [
        "Failed password from 10.0.0.5 to 10.0.0.2",
        "Failed password from 10.0.0.5 to 10.0.0.2",
        "Failed password from 10.0.0.5 to 10.0.0.2",
        "Failed password from 10.0.0.5 to 10.0.0.2",
        "Failed password from 10.0.0.5 to 10.0.0.2",
        "Failed password from 10.0.0.9 to 10.0.0.2"
      ]
    }
  ],
  "medium": [
    {
      "rule": "disk full",
      "pattern": "disk full",
      "severity": "medium",
      "count": 1,
      "lines": [
        "INFO disk full on host"
      ]
    }
  ]
}
Failed password from 10.0.0.5 to 10.0.0.2
Failed password from 10.0.0.5 to 10.0.0.2
Failed password from 10.0.0.5 to 10.0.0.2
Failed password from 10.0.0.5 to 10.0.0.2
Failed password from 10.0.0.5 to 10.0.0.2
Failed password from 10.0.0.9 to 10.0.0.2
INFO disk full on host
10.0.0.5
10.0.0.2
10.0.0.9
10.0.0.3
{"ip": "10.0.0.2", "count": 7}
{"ip": "10.0.0.5", "count": 5}
graph: 10.0.0.2 -> 10.0.0.3 (1), 10.0.0.5 -> 10.0.0.2 (1), 10.0.0.9 -> 10.0.0.2 (1)
10.0.0.5
10.0.0.2
10.0.0.3
exit:0
```

## Not proven / not in v0.2

- Windows/macOS running (stdlib-only Python, so it should run, but
  only run on Linux here). No packaged installer yet.
- 'All possible DSA' is not claimed: see README.md for the exact
  in/out lists (no AVL/red-black, heaps, tries, DFS, etc.).
- No VAPT, login, or CAPTCHA features — deliberately absent.
- log.rules patterns are substrings, not regex; no time windows.

## v0.3.0 — time-window/regex rules, more DSA, arithmetic, CLI

Commands run (from the saral-lang folder), actual output:

```
$ python3 -m unittest discover -s tests -v
Ran 47 tests in 3.200s
OK
```
47 = the original 12 + 16 v0.2 + 19 new v0.3 tests. No old test was
changed in v0.3; all 28 old tests still pass.

```
$ ./saral version
Saral 0.3.0
$ ./saral list
data: add, append, count, cycle, dequeue, enqueue, first, get, group, has, insert, join, last, link, neighbours, new, path, peek, pop, prefix, push, put, remove, reverse, search, shortest, sort, split, top, topological, unique, walk
file: exists, list, read, write
greet_bridge: greet, shout
log.rules: apply, extract, filter, graph, timeline, top
logs: count, find
net: get, ping, scan
report: save
system: env, info, run
$ ./saral check examples/dsa_v03.srl
OK: examples/dsa_v03.srl parses
```

```
$ ./saral examples/dsa_v03.srl
urgent
linked: ["a", "c"]
car
cat
a
b
d
c
False
a
b
c
d
14
big
3
2
1
```
Heap pops "urgent" (priority 1) first; the linked list lost "b";
the trie prefix "ca" gives car, cat; DFS from "a" is a, b, d, c;
the graph has no cycle; topological order is a, b, c, d;
2 + 3 * 4 = 14 (precedence, not 20); the while loop counts 3, 2, 1.

```
$ ./saral examples/soc_window.srl   (first alert lines only)
{"rule": "ssh burst", "pattern": "Failed password", "severity": "high", "count": 5, "lines": ["2026-11-02 09:10:00 Failed password from 10.0.0.5 to 10.0.0.2", "2026-11-02 09:10:10 ...", "2026-11-02 09:10:20 ...", "2026-11-02 09:10:30 ...", "2026-11-02 09:10:40 ..."], "within": 60, "skipped": 0}
{"rule": "bad user", "pattern": "Failed.*user root", "severity": "medium", "count": 1, "lines": ["2026-11-02 09:41:00 Failed login for user root from 10.0.0.7"]}
```
The burst (5 failures in 40 seconds) fires the windowed rule;
the 5 spaced-out failures (5 minutes apart) do not fire it, even
though there are 5 of them in the file. The timeline in the same
run returns the matched lines in timestamp order, including the
syslog-style `Nov  2 09:42:00` line last in time order.

All 8 examples run with exit 0 from the saral-lang folder:
bridge_demo, dsa_demo, dsa_v03, hello, log_check,
scan_localhost, soc_rules, soc_window. (An earlier v0.3 run
showed soc_rules failing only because the new soc_window example
was first written to run from inside examples/ while soc_rules
runs from the saral-lang folder; soc_window was fixed to the
established convention — examples/... paths, run from the
saral-lang folder — and all 8 now pass from there.)

Failures found and fixed in code during v0.3, not hidden:
- Multi-statement indented blocks only ran their first statement
  (see SPEC.md §13). Fixed in the parser; regression test added.
- The new soc_window example's paths, fixed as above.

## Not proven / not in v0.3

- Windows/macOS running (stdlib-only Python, so it should run, but
  only run on Linux here). No packaged installer, no remote
  package downloads — deliberately, see README.md CLI section.
- Functions/classes in scripts are not in v0.3 (a bigger parser
  change, kept on the not-yet list).
- 'All possible DSA' is not claimed: see README.md for the exact
  in/out lists (no AVL/red-black, no from-scratch hash table).
- No VAPT, login, or CAPTCHA features — deliberately absent.
