"""Saral test suite: runs the real interpreter on real scripts.

Run:  python3 -m unittest discover -s tests -v
from the saral-lang folder. Every test uses temp dirs and a real local
TCP server where a network result is asserted — nothing is mocked as real.
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import unittest

SARAL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "saral.py")


def run_script(script, cwd):
    path = os.path.join(cwd, "test.srl")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(script)
    proc = subprocess.run([sys.executable, SARAL, path], cwd=cwd,
                          capture_output=True, text=True, timeout=60)
    return proc


class SaralTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_file_round_trip(self):
        proc = run_script(
            'took file\n'
            'write file "note.txt" text : "hello saral"\n'
            'back is read file "note.txt"\n'
            'show back\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("hello saral", proc.stdout)
        with open(os.path.join(self.cwd, "note.txt"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "hello saral")

    def test_system_run_echo(self):
        proc = run_script(
            'took system\n'
            'out is run "echo hello-saral"\n'
            'show out\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("hello-saral", proc.stdout)

    def test_net_scan_real_local_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        open_port = server.getsockname()[1]
        server.listen(1)
        closed_port = open_port + 1 if open_port < 65534 else open_port - 1
        try:
            proc = run_script(
                'took net\n'
                f'results is scan net "127.0.0.1" ports : "{open_port},{closed_port}"\n'
                'show results\n', self.cwd)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn(f'"port": {open_port}, "open": true', proc.stdout)
            self.assertIn(f'"port": {closed_port}, "open": false', proc.stdout)
        finally:
            server.close()

    def test_net_alias(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 0))
        port = server.getsockname()[1]
        server.listen(1)
        try:
            proc = run_script(
                'took net as web\n'
                f'results is scan web "127.0.0.1" port : {port}\n'
                'show results\n', self.cwd)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn('"open": true', proc.stdout)
        finally:
            server.close()

    def test_log_find_and_count(self):
        with open(os.path.join(self.cwd, "app.log"), "w", encoding="utf-8") as fh:
            fh.write("INFO start\nERROR disk full\nINFO ok\nERROR timeout\n")
        proc = run_script(
            'took logs\n'
            'took file\n'
            'text is read file "app.log"\n'
            'found is find "ERROR" in text\n'
            'show found\n'
            'errors is count logs "app.log" pattern : "ERROR"\n'
            'show errors\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("ERROR disk full", proc.stdout)
        self.assertIn("ERROR timeout", proc.stdout)
        self.assertIn("\n2\n", proc.stdout)

    def test_report_save_and_reread(self):
        proc = run_script(
            'took net\n'
            'took report\n'
            'hosts is scan net "127.0.0.1" port : 9\n'
            'save hosts to "out.json" format : json\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        with open(os.path.join(self.cwd, "out.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertIsInstance(data, list)
        self.assertEqual(data[0]["host"], "127.0.0.1")
        self.assertEqual(data[0]["port"], 9)

    def test_for_loop_and_filter(self):
        with open(os.path.join(self.cwd, "a.txt"), "w") as fh:
            fh.write("a")
        proc = run_script(
            'took file\n'
            'names is list file "."\n'
            'for each name in names\n'
            '    show name\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("a.txt", proc.stdout)

    def test_filter_where(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 0))
        port = server.getsockname()[1]
        server.listen(1)
        try:
            proc = run_script(
                'took net\n'
                f'results is scan net "127.0.0.1" ports : "{port},{port + 1}"\n'
                'open is filter results where open is true\n'
                'show open\n', self.cwd)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn(f'"port": {port}, "open": true', proc.stdout)
            self.assertNotIn(f'"port": {port + 1}', proc.stdout)
        finally:
            server.close()

    def test_bridge_node_library(self):
        proc = run_script(
            'took greet_bridge\n'
            'hello is greet greet_bridge "Saral"\n'
            'show hello\n', self.cwd)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("Hello from Node, Saral!", proc.stdout)

    def test_private_ip_guard_refuses_public(self):
        proc = run_script(
            'took net\n'
            'scan net "8.8.8.8" port : 53\n', self.cwd)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("refuse", proc.stdout.lower())

    def test_missing_file_is_an_error_not_empty_success(self):
        proc = run_script(
            'took file\n'
            'text is read file "does-not-exist.txt"\n'
            'show text\n', self.cwd)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("no such file", proc.stdout)

    def test_syntax_error_reports_line_number(self):
        proc = run_script('took file\nshow "unclosed\n', self.cwd)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("line 2", proc.stdout)


if __name__ == "__main__":
    unittest.main()
