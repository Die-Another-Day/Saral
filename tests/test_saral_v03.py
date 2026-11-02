"""Saral v0.3 test suite: time-window/regex/timeline log.rules, heap,
linked list, trie, graph DFS/cycle/topo, else, arithmetic, while, CLI.

Run:  python3 -m unittest discover -s tests -v
from the saral-lang folder. Old suites (test_saral.py, test_saral_v02.py)
are untouched and must stay green alongside this file.
"""
import os
import subprocess
import sys
import tempfile
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SARAL = os.path.join(BASE, "saral.py")


def run_script(script, cwd):
    path = os.path.join(cwd, "test.srl")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(script)
    return subprocess.run([sys.executable, SARAL, path], cwd=cwd,
                          capture_output=True, text=True, timeout=60)


def write_file(cwd, name, text):
    path = os.path.join(cwd, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


BURST_LOG = "".join(
    f"2026-11-02 09:10:{10 * i:02d} Failed password from 10.0.0.5\n"
    for i in range(5))
SPACED_LOG = "".join(
    f"2026-11-02 09:{10 + 5 * i:02d}:00 Failed password from 10.0.0.9\n"
    for i in range(5))
WINDOW_RULE = ('rule "burst" pattern : "Failed password" severity : high '
               'at least : 5 within : 60\n')


class LogRulesV03Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_window_fires_on_burst(self):
        write_file(self.cwd, "r.txt", WINDOW_RULE)
        write_file(self.cwd, "a.log", BURST_LOG)
        proc = run_script(
            'took log.rules\n'
            'alerts is apply log.rules "r.txt" to "a.log"\n'
            'show alerts\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertIn('"rule": "burst"', proc.stdout)
        self.assertIn('"count": 5', proc.stdout)
        self.assertIn('"within": 60', proc.stdout)

    def test_window_does_not_fire_when_spaced(self):
        write_file(self.cwd, "r.txt", WINDOW_RULE)
        write_file(self.cwd, "a.log", SPACED_LOG)
        proc = run_script(
            'took log.rules\n'
            'alerts is apply log.rules "r.txt" to "a.log"\n'
            'show alerts\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertIn("(empty list)", proc.stdout)

    def test_window_skips_unparseable_lines_and_reports_them(self):
        write_file(self.cwd, "r.txt", WINDOW_RULE)
        log = BURST_LOG + "Failed password with no timestamp\n" * 2
        write_file(self.cwd, "a.log", log)
        proc = run_script(
            'took log.rules\n'
            'alerts is apply log.rules "r.txt" to "a.log"\n'
            'show alerts\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        # Burst still fires (5 timed matches), but the 2 unparseable
        # matched lines are skipped and reported, not counted.
        self.assertIn('"count": 5', proc.stdout)
        self.assertIn('"skipped": 2', proc.stdout)

    def test_syslog_timestamp_parses(self):
        write_file(self.cwd, "r.txt", WINDOW_RULE)
        log = "".join(
            f"Nov  2 09:10:{10 * i:02d} Failed password from 10.0.0.5\n"
            for i in range(5))
        write_file(self.cwd, "a.log", log)
        proc = run_script(
            'took log.rules\n'
            'alerts is apply log.rules "r.txt" to "a.log"\n'
            'show alerts\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertIn('"count": 5', proc.stdout)

    def test_regex_rule_and_bad_regex_error(self):
        write_file(self.cwd, "r.txt",
                   'rule "bad user" pattern : "Failed.*user root" '
                   'severity : medium match : regex\n')
        write_file(self.cwd, "a.log",
                   "2026-11-02 09:41:00 Failed login for user root\n"
                   "2026-11-02 09:42:00 Failed login for user bob\n")
        proc = run_script(
            'took log.rules\n'
            'alerts is apply log.rules "r.txt" to "a.log"\n'
            'show alerts\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertIn('"count": 1', proc.stdout)
        # Bad regex: clear error, never a silent substring fallback.
        write_file(self.cwd, "bad.txt",
                   'rule "bad" pattern : "[a-" severity : low match : regex\n')
        proc = run_script(
            'took log.rules\n'
            'alerts is apply log.rules "bad.txt" to "a.log"\n', self.cwd)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("bad regex", proc.stdout + proc.stderr)

    def test_timeline_sorts_out_of_order_log(self):
        write_file(self.cwd, "r.txt",
                   'rule "any" pattern : "event" severity : low\n')
        write_file(self.cwd, "a.log",
                   "2026-11-02 09:30:00 event c\n"
                   "2026-11-02 09:10:00 event a\n"
                   "2026-11-02 09:20:00 event b\n"
                   "event with no time\n")
        proc = run_script(
            'took log.rules\n'
            'tl is timeline log.rules "a.log" using rules "r.txt"\n'
            'show tl\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        out = proc.stdout
        self.assertLess(out.index("event a"), out.index("event b"))
        self.assertLess(out.index("event b"), out.index("event c"))
        # Unparseable line goes last.
        self.assertLess(out.index("event c"), out.index("event with no time"))


class DsaV03Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_heap_lowest_priority_first(self):
        proc = run_script(
            'took data\n'
            'heap is new data "heap"\n'
            'push data "low" to heap priority : 3\n'
            'push data "urgent" to heap priority : 1\n'
            'push data "normal" to heap priority : 2\n'
            'a is pop data heap\n'
            'b is pop data heap\n'
            'c is pop data heap\n'
            'show a\nshow b\nshow c\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertEqual(proc.stdout.strip().splitlines(),
                         ["urgent", "normal", "low"])

    def test_heap_push_without_priority_is_error(self):
        proc = run_script(
            'took data\n'
            'heap is new data "heap"\n'
            'push data "x" to heap\n', self.cwd)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("priority", proc.stdout + proc.stderr)

    def test_linked_list(self):
        proc = run_script(
            'took data\n'
            'list is new data "linked"\n'
            'append data "a" to list\n'
            'append data "b" to list\n'
            'append data "c" to list\n'
            'yes is search data list value : "b"\n'
            'show yes\n'
            'remove data "b" from list\n'
            'walked is walk data list\n'
            'show walked\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertIn("True", proc.stdout)
        self.assertEqual(proc.stdout.strip().splitlines()[-2:], ["a", "c"])

    def test_trie_exact_and_prefix(self):
        proc = run_script(
            'took data\n'
            'trie is new data "trie"\n'
            'insert data trie value : "cat"\n'
            'insert data trie value : "car"\n'
            'insert data trie value : "dog"\n'
            'yes is search data trie value : "cat"\n'
            'no is search data trie value : "ca"\n'
            'show yes\nshow no\n'
            'words is prefix data trie "ca"\n'
            'show words\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        lines = proc.stdout.strip().splitlines()
        self.assertEqual(lines[0], "True")
        self.assertEqual(lines[1], "False")
        self.assertEqual(lines[2:], ["car", "cat"])

    def _graph_script(self, extra_links):
        base = ('took data\n'
                'graph is new data "graph"\n'
                'link data graph from "a" to "b"\n'
                'link data graph from "a" to "c"\n'
                'link data graph from "b" to "d"\n'
                'link data graph from "c" to "d"\n')
        return base + extra_links

    def test_graph_dfs_cycle_and_topo(self):
        proc = run_script(
            self._graph_script(
                'walked is walk data graph from "a"\n'
                'show walked\n'
                'cyc is cycle data graph\n'
                'show cyc\n'
                'order is topological data graph\n'
                'show order\n'), self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        lines = proc.stdout.strip().splitlines()
        # DFS in link order: a, b, d, c
        self.assertEqual(lines[0:4], ["a", "b", "d", "c"])
        self.assertEqual(lines[4], "False")
        order = lines[5:]
        self.assertEqual(order[0], "a")
        self.assertEqual(order[-1], "d")
        self.assertLess(order.index("b"), order.index("d"))
        self.assertLess(order.index("c"), order.index("d"))

    def test_graph_cycle_true_and_topo_error(self):
        proc = run_script(
            self._graph_script(
                'link data graph from "d" to "a"\n'
                'cyc is cycle data graph\n'
                'show cyc\n'), self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertIn("True", proc.stdout)
        proc = run_script(
            self._graph_script(
                'link data graph from "d" to "a"\n'
                'order is topological data graph\n'), self.cwd)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("cycle", proc.stdout + proc.stderr)


class LanguageV03Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_else_branch(self):
        proc = run_script(
            'x is 3\n'
            'if x > 10\n'
            '    show "big"\n'
            'else\n'
            '    show "small"\n'
            'if x is 3\n'
            '    show "three"\n'
            'else\n'
            '    show "not three"\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertEqual(proc.stdout.strip().splitlines(),
                         ["small", "three"])

    def test_multi_statement_block(self):
        # Regression test for the v0.3 parser bug: a block with two
        # statements used to run only its first one.
        proc = run_script(
            'n is 3\n'
            'while n > 0\n'
            '    show n\n'
            '    n is n - 1\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertEqual(proc.stdout.strip().splitlines(), ["3", "2", "1"])

    def test_arithmetic_and_precedence(self):
        proc = run_script(
            'a is 2 + 3 * 4\n'
            'show a\n'
            'b is a - 4\n'
            'show b\n'
            'c is b / 2\n'
            'show c\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertEqual(proc.stdout.strip().splitlines(), ["14", "10", "5"])

    def test_division_by_zero_is_error(self):
        proc = run_script('x is 1 / 0\nshow x\n', self.cwd)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("division by zero", proc.stdout + proc.stderr)

    def test_while_loop_and_cap(self):
        proc = run_script(
            'n is 3\n'
            'while n > 0\n'
            '    n is n - 1\n'
            'show "done"\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertIn("done", proc.stdout)
        # A loop that never changes its condition errors at the cap,
        # instead of hanging.
        proc = run_script(
            'x is 0\n'
            'while true\n'
            '    x is x + 1\n', self.cwd)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("1000 times", proc.stdout + proc.stderr)


class CliTests(unittest.TestCase):
    def test_version_list_check(self):
        proc = subprocess.run([sys.executable, SARAL, "version"],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("0.3.0", proc.stdout)
        proc = subprocess.run([sys.executable, SARAL, "list"],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("data:", proc.stdout)
        self.assertIn("log.rules:", proc.stdout)
        self.assertIn("timeline", proc.stdout)
        good = os.path.join(BASE, "examples", "hello.srl")
        proc = subprocess.run([sys.executable, SARAL, "check", good],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("parses", proc.stdout)
        # check does not execute: a script that would fail at runtime
        # still passes check, and a syntax-broken script fails check.
        with tempfile.TemporaryDirectory() as tmp:
            ok_path = os.path.join(tmp, "ok.srl")
            with open(ok_path, "w") as fh:
                fh.write('took nosuchlib\nshow "hi"\n')
            # 'took nosuchlib' is a runtime error, not a parse error.
            proc = subprocess.run([sys.executable, SARAL, "check", ok_path],
                                  capture_output=True, text=True, timeout=60)
            self.assertEqual(proc.returncode, 0)
            bad_path = os.path.join(tmp, "bad.srl")
            with open(bad_path, "w") as fh:
                fh.write('x is "unclosed\n')
            proc = subprocess.run([sys.executable, SARAL, "check", bad_path],
                                  capture_output=True, text=True, timeout=60)
            self.assertNotEqual(proc.returncode, 0)

    def test_launcher_version(self):
        proc = subprocess.run(["./saral", "version"], cwd=BASE,
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("0.3.0", proc.stdout)


if __name__ == "__main__":
    unittest.main()
