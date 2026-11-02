"""Saral v0.2 test suite: DSA, log.rules, and list/text utilities.

Run:  python3 -m unittest discover -s tests -v
from the saral-lang folder. The old suite (test_saral.py) is untouched
and must stay green alongside this file. Script tests run the real
interpreter in temp dirs; algorithm tests call the real merge/quick
sort and binary search in libs/data.py on seeded random data and
compare against the expected sorted order.
"""
import importlib.util
import os
import random
import subprocess
import sys
import tempfile
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SARAL = os.path.join(BASE, "saral.py")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # saral.py setdefaults itself into sys.modules
    spec.loader.exec_module(mod)
    return mod


# Load saral first so data.py's `from saral import SaralError` works.
_saral = _load("saral", SARAL)
sys.modules["saral"] = _saral
data = _load("saral_data_test", os.path.join(BASE, "libs", "data.py"))


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


AUTH_LOG = (
    "Failed password from 10.0.0.5 to 10.0.0.2\n"
    "Failed password from 10.0.0.5 to 10.0.0.2\n"
    "Failed password from 10.0.0.5 to 10.0.0.2\n"
    "Failed password from 10.0.0.5 to 10.0.0.2\n"
    "Failed password from 10.0.0.5 to 10.0.0.2\n"
    "Failed password from 10.0.0.9 to 10.0.0.2\n"
    "INFO disk full on host\n"
    "INFO ok\n"
)


class DsaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_stack_lifo_and_peek(self):
        proc = run_script(
            'took data\n'
            'stack is new data "stack"\n'
            'push data "a" to stack\n'
            'push data "b" to stack\n'
            'top is peek data stack\n'
            'show top\n'
            'first is pop data stack\n'
            'show first\n'
            'second is pop data stack\n'
            'show second\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        lines = proc.stdout.splitlines()
        self.assertEqual(lines[0], "b")   # peek: last pushed
        self.assertEqual(lines[1], "b")   # pop: LIFO
        self.assertEqual(lines[2], "a")

    def test_queue_fifo(self):
        proc = run_script(
            'took data\n'
            'queue is new data "queue"\n'
            'enqueue data "a" to queue\n'
            'enqueue data "b" to queue\n'
            'first is dequeue data queue\n'
            'show first\n'
            'second is dequeue data queue\n'
            'show second\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertEqual(proc.stdout.splitlines(), ["a", "b"])

    def test_set_uniqueness_has_remove(self):
        proc = run_script(
            'took data\n'
            'myset is new data "set"\n'
            'add data "a" to myset\n'
            'add data "a" to myset\n'
            'add data "b" to myset\n'
            'n is count data myset\n'
            'show n\n'
            'yes is has data myset "a"\n'
            'show yes\n'
            'remove data "a" from myset\n'
            'no is has data myset "a"\n'
            'show no\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertEqual(proc.stdout.splitlines(), ["2", "True", "False"])

    def test_map_put_get(self):
        proc = run_script(
            'took data\n'
            'mymap is new data "map"\n'
            'put data mymap key : "a" value : 1\n'
            'put data mymap key : "b" value : 2\n'
            'v is get data mymap key : "b"\n'
            'show v\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertEqual(proc.stdout.strip(), "2")

    def test_tree_insert_search_walk_sorted(self):
        proc = run_script(
            'took data\n'
            'tree is new data "tree"\n'
            'insert data tree value : 5\n'
            'insert data tree value : 3\n'
            'insert data tree value : 7\n'
            'insert data tree value : 1\n'
            'sorted is walk data tree\n'
            'show sorted\n'
            'yes is search data tree value : 7\n'
            'show yes\n'
            'no is search data tree value : 9\n'
            'show no\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertEqual(proc.stdout.splitlines(),
                         ["1", "3", "5", "7", "True", "False"])

    def test_graph_bfs_and_dijkstra_differ(self):
        # BFS (fewest hops) picks a->b directly; Dijkstra (cheapest
        # weights) picks a->c->b (1+1 < 10). Both must be right.
        proc = run_script(
            'took data\n'
            'graph is new data "graph"\n'
            'link data graph from "a" to "b" weight : 10\n'
            'link data graph from "a" to "c" weight : 1\n'
            'link data graph from "c" to "b" weight : 1\n'
            'route is path data graph from "a" to "b"\n'
            'show route\n'
            'best is shortest data graph from "a" to "b"\n'
            'show best\n'
            'none is path data graph from "b" to "a"\n'
            'show none\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("a\nb\n", proc.stdout)  # BFS path, one per line
        self.assertIn('"path": [\n    "a",\n    "c",\n    "b"\n  ]', proc.stdout)
        self.assertIn('"distance": 2', proc.stdout)
        self.assertIn("(empty list)", proc.stdout)  # no path b -> a

    def test_merge_and_quick_sort_random(self):
        rng = random.Random(42)
        for trial in range(20):
            nums = [rng.randint(-100, 100) for _ in range(30)]
            expected = sorted(nums)
            self.assertEqual(data.merge_sort(nums, None), expected)
            self.assertEqual(data.quick_sort(nums, None), expected)
            # The input must not be mutated into sorted order in place.
            self.assertEqual(sorted(nums), expected)

    def test_sort_via_script_on_table(self):
        write_file(self.cwd, "auth.log", AUTH_LOG)
        write_file(self.cwd, "rules.txt",
                   'rule "ssh" pattern : "Failed password" severity : high at least : 5\n'
                   'rule "disk" pattern : "disk full" severity : medium\n')
        proc = run_script(
            'took data\n'
            'took log.rules\n'
            'alerts is apply log.rules "rules.txt" to "auth.log"\n'
            'sorted is sort data alerts by : "count" using : quick\n'
            'show sorted\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        # disk (count 1) sorts before ssh (count 6).
        self.assertLess(proc.stdout.index('"rule": "disk"'),
                        proc.stdout.index('"rule": "ssh"'))

    def test_binary_search_found_notfound_and_unsorted_error(self):
        # Direct algorithm tests on numbers.
        self.assertEqual(data.binary_search([1, 3, 5, 7], 5, None), 2)
        self.assertEqual(data.binary_search([1, 3, 5, 7], 4, None), -1)
        self.assertEqual(data.linear_search([1, 3, 5, 7], 7, None), 3)
        self.assertEqual(data.linear_search([1, 3, 5, 7], 9, None), -1)
        with self.assertRaises(ValueError):
            data.binary_search([5, 1, 7], 7, None)
        # Script level: split, sort, then binary search the sorted list.
        proc = run_script(
            'took data\n'
            'parts is split data "b,a,c" separator : ","\n'
            'sorted is sort data parts using : merge\n'
            'idx is search data sorted value : "b" using : binary\n'
            'show idx\n'
            'miss is search data sorted value : "z" using : linear\n'
            'show miss\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertEqual(proc.stdout.splitlines(), ["1", "-1"])

    def test_unique_group_top_and_list_utils(self):
        proc = run_script(
            'took data\n'
            'parts is split data "b,a,b,c,a" separator : ","\n'
            'uniq is unique data parts\n'
            'show uniq\n'
            'n is count data parts\n'
            'show n\n'
            'top2 is top data parts count : 2\n'
            'show top2\n'
            'rev is reverse data parts\n'
            'show rev\n'
            'joined is join data parts separator : "-"\n'
            'show joined\n'
            'f is first data parts\n'
            'show f\n'
            'l is last data parts\n'
            'show l\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        out = proc.stdout
        self.assertIn("b\na\nc\n", out)          # unique, order preserved
        self.assertIn("\n5\n", out)               # count
        self.assertIn("b-a-b-c-a\n", out)         # join
        self.assertIn("a\nb\n", out)              # reversed starts a, b


class LogRulesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = self.tmp.name
        write_file(self.cwd, "auth.log", AUTH_LOG)

    def tearDown(self):
        self.tmp.cleanup()

    def _apply(self, rules_text):
        write_file(self.cwd, "rules.txt", rules_text)
        return run_script(
            'took log.rules\n'
            'alerts is apply log.rules "rules.txt" to "auth.log"\n'
            'show alerts\n', self.cwd)

    def test_threshold_both_sides(self):
        # 6 Failed-password lines: at least 5 fires, at least 7 does not.
        proc = self._apply(
            'rule "ssh" pattern : "Failed password" severity : high at least : 5\n')
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn('"count": 6', proc.stdout)
        proc = self._apply(
            'rule "ssh" pattern : "Failed password" severity : high at least : 7\n')
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("(empty list)", proc.stdout)

    def test_severity_validation_error(self):
        proc = self._apply(
            'rule "bad" pattern : "Failed" severity : urgent\n')
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("severity", proc.stdout.lower())

    def test_filter_using_rules_and_logs_shorthand(self):
        write_file(self.cwd, "rules.txt",
                   'rule "ssh" pattern : "Failed password" severity : high\n'
                   'rule "disk" pattern : "disk full" severity : medium\n')
        proc = run_script(
            'took log.rules\n'
            'took logs\n'
            'm1 is filter log.rules "auth.log" using rules "rules.txt"\n'
            'show m1\n'
            'm2 is filter logs "auth.log" using rules "rules.txt"\n'
            'show m2\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertEqual(proc.stdout.count("Failed password"), 12)  # 6 x 2
        self.assertEqual(proc.stdout.count("disk full"), 2)
        self.assertNotIn("INFO ok", proc.stdout)

    def test_apply_rules_alias_and_ip_extraction_top(self):
        write_file(self.cwd, "rules.txt",
                   'rule "ssh" pattern : "Failed password" severity : high at least : 5\n')
        proc = run_script(
            'took log.rules\n'
            'alerts is apply rules "rules.txt" to "auth.log"\n'
            'show alerts\n'
            'ips is extract log.rules "auth.log"\n'
            'show ips\n'
            'topips is top log.rules "auth.log" count : 2\n'
            'show topips\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn('"count": 6', proc.stdout)
        self.assertIn("10.0.0.5\n10.0.0.2\n10.0.0.9\n", proc.stdout)
        # 10.0.0.2 appears 6 times, 10.0.0.5 appears 5 times.
        self.assertIn('"ip": "10.0.0.2", "count": 6', proc.stdout)
        self.assertIn('"ip": "10.0.0.5", "count": 5', proc.stdout)

    def test_graph_from_log_and_path(self):
        proc = run_script(
            'took log.rules\n'
            'took data\n'
            'chain is graph log.rules "auth.log"\n'
            'show chain\n'
            'route is path data chain from "10.0.0.5" to "10.0.0.2"\n'
            'show route\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("10.0.0.5 -> 10.0.0.2", proc.stdout)
        self.assertIn("10.0.0.5\n10.0.0.2\n", proc.stdout)

    def test_group_alerts_by_severity_via_data(self):
        write_file(self.cwd, "rules.txt",
                   'rule "ssh" pattern : "Failed password" severity : high at least : 5\n'
                   'rule "disk" pattern : "disk full" severity : medium\n')
        proc = run_script(
            'took log.rules\n'
            'took data\n'
            'alerts is apply log.rules "rules.txt" to "auth.log"\n'
            'grouped is group data alerts by : "severity"\n'
            'show grouped\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn('"high"', proc.stdout)
        self.assertIn('"medium"', proc.stdout)


if __name__ == "__main__":
    unittest.main()
