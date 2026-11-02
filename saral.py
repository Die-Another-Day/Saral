#!/usr/bin/env python3
"""Saral — a simple automation language. Interpreter, Python 3 stdlib only.

Syntax (see SPEC.md):
  took file                    # load a library
  took net as web              # load with an alias
  text is read file "notes.txt"
  scan net "127.0.0.1" -> hosts
  save data to "out.json" format : json
  show data
  find "ERROR" in text
  filter hosts where port is 80
  for each host in hosts
      show host
  if count is 0
      show "none found"
  # comments start with #
No semicolons, no braces, no '=' assignment, no functions/classes in MVP.
"""
import json
import os
import re
import subprocess
import sys

VERSION = "0.3.0"
# Libraries do `from saral import SaralError`. When this file runs as a
# script its module is __main__, so alias it: otherwise libraries would
# load a second copy of this file with a different SaralError class and
# the error handler below would miss their errors.
sys.modules.setdefault("saral", sys.modules[__name__])
BASE = os.path.dirname(os.path.abspath(__file__))


def _resolve_lib_dir():
    """Where Saral libraries live, in priority order.

    Release/SecureOS install layouts split the interpreter from its
    libraries, so the original BASE/libs layout alone is not enough:
    1. $SARAL_LIB_DIR, if set (explicit, used by installers/tests)
    2. <interpreter dir>/libs (repo checkout / ~/.local/lib/saral layout)
    3. <interpreter dir>/../lib/saral/libs (e.g. /usr/local/bin/saral
       with libraries in /usr/local/lib/saral/libs)
    4. /usr/local/lib/saral/libs and ~/.local/lib/saral/libs
    5. /usr/local/lib/saral and ~/.local/lib/saral (flat copy of libs/)
    Falls back to <interpreter dir>/libs if nothing exists yet, so
    error messages still name the familiar location.
    """
    candidates = []
    env_dir = os.environ.get("SARAL_LIB_DIR")
    if env_dir:
        candidates.append(env_dir)
    candidates.append(os.path.join(BASE, "libs"))
    candidates.append(os.path.join(BASE, "..", "lib", "saral", "libs"))
    candidates.append("/usr/local/lib/saral/libs")
    candidates.append(
        os.path.join(os.path.expanduser("~"), ".local", "lib", "saral", "libs")
    )
    candidates.append("/usr/local/lib/saral")
    candidates.append(
        os.path.join(os.path.expanduser("~"), ".local", "lib", "saral")
    )
    for cand in candidates:
        if os.path.isdir(cand):
            return os.path.normpath(cand)
    return os.path.join(BASE, "libs")


LIB_DIR = _resolve_lib_dir()


class SaralError(Exception):
    def __init__(self, message, line=0):
        super().__init__(message)
        self.line = line
        self.message = message

    def __str__(self):
        if self.line:
            return f"Saral error on line {self.line}: {self.message}"
        return f"Saral error: {self.message}"


# ---------------------------------------------------------------- lexer
# A line is tokenised into words, quoted strings, numbers, -> and :
def tokenize(line, lineno):
    tokens = []
    i, n = 0, len(line)
    while i < n:
        c = line[i]
        if c in " \t":
            i += 1
            continue
        if c == "#":  # comment to end of line (outside strings)
            break
        if c == '"':
            j = i + 1
            out = []
            while j < n and line[j] != '"':
                if line[j] == "\\" and j + 1 < n:
                    nxt = line[j + 1]
                    out.append({"n": "\n", "t": "\t", "\\": "\\", '"': '"'}.get(nxt, nxt))
                    j += 2
                else:
                    out.append(line[j])
                    j += 1
            if j >= n:
                raise SaralError("string is missing its closing quote", lineno)
            tokens.append(("str", "".join(out)))
            i = j + 1
            continue
        if line.startswith("->", i):
            tokens.append(("arrow", "->"))
            i += 2
            continue
        if c == ":":
            tokens.append(("colon", ":"))
            i += 1
            continue
        # Arithmetic / comparison operators (v0.3). A '-' followed by a
        # digit is a negative number (handled below); a spaced '-' is
        # subtraction. Words like "a-b" stay one word, as before, so
        # arithmetic needs spaces:  x is 2 + 3, not  x is 2+3.
        if c in "+*/":
            tokens.append(("op", c))
            i += 1
            continue
        if c in "><":
            if i + 1 < n and line[i + 1] == "=":
                tokens.append(("op", c + "="))
                i += 2
            else:
                tokens.append(("op", c))
                i += 1
            continue
        if c == "-" and not (i + 1 < n and line[i + 1].isdigit()
                              and (i == 0 or not (line[i - 1].isalnum()
                                                  or line[i - 1] == "_"))):
            tokens.append(("op", "-"))
            i += 1
            continue
        m = re.match(r"-?\d+\.\d+|-?\d+", line[i:])
        if m and (i == 0 or not (line[i - 1].isalnum() or line[i - 1] == "_")):
            # A number, unless its digits belong to a word (e.g. "h1").
            tokens.append(("num", m.group(0)))
            i += len(m.group(0))
            continue
        m = re.match(r"[A-Za-z_][A-Za-z0-9_.\-/]*", line[i:])
        if m:
            tokens.append(("word", m.group(0)))
            i += len(m.group(0))
            continue
        raise SaralError(f"I do not understand the character {c!r}", lineno)
    return tokens


def tok_word(tokens, idx):
    if idx < len(tokens) and tokens[idx][0] == "word":
        return tokens[idx][1]
    return None


# ---------------------------------------------------------------- parser
# Nodes are dicts: {kind, line, ...}. Blocks are nested by indentation.
class Node:
    def __init__(self, kind, line, **kw):
        self.kind = kind
        self.line = line
        self.__dict__.update(kw)


def parse(lines):
    """lines: list of (lineno, indent, tokens). Returns list of Nodes."""
    pos = [0]

    def parse_block(min_indent):
        # v0.3 bug fix: the old code called a body with min_indent =
        # header indent + 1, then broke on any later line whose indent
        # was greater than that — so a body with two statements only
        # ever ran its first one, and the rest were silently dropped.
        # Now a block's indent is the indent of its first line, and
        # every line at exactly that indent belongs to the block.
        # A dedent ends the block; a deeper indent is not consumed
        # here (a header consumes its own body by recursion).
        nodes = []
        block_indent = None
        while pos[0] < len(lines):
            lineno, indent, toks = lines[pos[0]]
            if indent < min_indent:
                break
            if not toks:
                pos[0] += 1
                continue
            if block_indent is None:
                block_indent = indent
            elif indent != block_indent:
                break
            first = tok_word(toks, 0)
            if first == "for":
                # for each <var> in <expr tokens>
                if tok_word(toks, 1) != "each" or tok_word(toks, 3) != "in":
                    raise SaralError(
                        "for loops look like: for each host in hosts", lineno)
                var = tok_word(toks, 2)
                expr = toks[4:]
                if not var or not expr:
                    raise SaralError(
                        "for loops look like: for each host in hosts", lineno)
                pos[0] += 1
                body = parse_block(indent + 1)
                nodes.append(Node("for", lineno, var=var, expr=expr,
                                  body=body))
                continue
            if first == "if":
                cond = parse_condition(toks[1:], lineno)
                pos[0] += 1
                body = parse_block(indent + 1)
                else_body = []
                if pos[0] < len(lines):
                    l2, ind2, t2 = lines[pos[0]]
                    if ind2 == indent and tok_word(t2, 0) == "else":
                        pos[0] += 1
                        else_body = parse_block(indent + 1)
                nodes.append(Node("if", lineno, cond=cond, body=body,
                                  else_body=else_body))
                continue
            if first == "while":
                # while <condition>  (v0.3, capped at 1000 iterations
                # in the executor so a runaway loop errors, not hangs)
                cond = parse_condition(toks[1:], lineno)
                pos[0] += 1
                body = parse_block(indent + 1)
                nodes.append(Node("while", lineno, cond=cond, body=body))
                continue
            if first == "else":
                raise SaralError("'else' must follow an 'if' block", lineno)
            nodes.append(parse_statement(toks, lineno))
            pos[0] += 1
        return nodes

    nodes = parse_block(0)
    if pos[0] < len(lines):
        lineno = lines[pos[0]][0]
        raise SaralError(
            "unexpected indentation: this line does not belong to any "
            "block above it", lineno)
    return nodes


def parse_condition(toks, lineno):
    """Returns (left_tokens, op, right_tokens_or_None).

    v0.3: left/right are full arithmetic expressions (see eval_expr),
    and operators are is / is not / contains / > / < / >= / <=.
    A condition with no operator tests the truthiness of its expression.
    """
    if not toks:
        raise SaralError("an 'if' line needs a condition", lineno)
    for idx in range(len(toks)):
        if toks[idx] == ("word", "is"):
            if idx + 1 < len(toks) and toks[idx + 1] == ("word", "not"):
                return (toks[:idx], "is not", toks[idx + 2:])
            return (toks[:idx], "is", toks[idx + 1:])
        if toks[idx] == ("word", "contains"):
            return (toks[:idx], "contains", toks[idx + 1:])
        if toks[idx][0] == "op" and toks[idx][1] in (">", "<", ">=", "<="):
            return (toks[:idx], toks[idx][1], toks[idx + 1:])
    return (toks, None, None)


def parse_statement(toks, lineno):
    first = tok_word(toks, 0)
    if first == "took":
        lib = tok_word(toks, 1)
        alias = None
        if not lib:
            raise SaralError("took needs a library name, like: took file", lineno)
        if tok_word(toks, 2) == "as":
            alias = tok_word(toks, 3)
            if not alias:
                raise SaralError("took ... as needs a name", lineno)
        if len(toks) > (4 if alias else 2):
            raise SaralError("took lines look like: took file  or  took net as web", lineno)
        return Node("took", lineno, lib=lib, alias=alias)
    # flow: <verb call> -> <var>
    arrow = [i for i, t in enumerate(toks) if t[0] == "arrow"]
    if arrow:
        if len(arrow) != 1:
            raise SaralError("a line can have only one ->", lineno)
        call = parse_call(toks[:arrow[0]], lineno)
        target = tok_word(toks, arrow[0] + 1)
        if not target or len(toks) != arrow[0] + 2:
            raise SaralError("after -> put one variable name", lineno)
        return Node("flow", lineno, call=call, target=target)
    # assignment: <var> is <call or value or arithmetic expression>
    if len(toks) >= 3 and toks[1] == ("word", "is"):
        var = tok_word(toks, 0)
        rhs = toks[2:]
        if len(rhs) == 1:
            return Node("assign_value", lineno, var=var, token=rhs[0])
        if any(t[0] == "op" for t in rhs):
            # Arithmetic (v0.3): x is 2 + 3, total is a + b.
            # Verb calls never contain operator tokens, so this is
            # unambiguous. Comparisons in an assignment are not
            # supported and error in eval_expr.
            return Node("assign_expr", lineno, var=var, expr=rhs)
        return Node("assign_call", lineno, var=var, call=parse_call(rhs, lineno))
    # plain verb call
    return Node("call", lineno, call=parse_call(toks, lineno))


def parse_call(toks, lineno):
    """Returns dict: verb, lib_token, positional tokens, named dict,
    to, in, from, where. v0.2 additions, both analogous to the existing
    'to'/'in' separators, so they are extensions, not a redesign:
      from <x>   -- e.g. remove data "a" from myset, link data g from "a" to "b"
                   (only when the next token is not ':', so 'from : "a"'
                   still parses as a named argument)
      using <label> <file> / using <file>
                 -- e.g. filter log.rules "a.log" using rules "r.txt"
                   -> named['using'] is the file token."""
    if not toks or toks[0][0] != "word":
        raise SaralError("a line must start with a verb, like: show ...", lineno)
    verb = toks[0][1]
    rest = toks[1:]
    lib_token = None
    # 'save' is special: its first argument is the value, never a library.
    if verb != "save" and rest and rest[0][0] == "word":
        lib_token = rest[0][1]
        rest = rest[1:]
    positional, named, to_tok, in_tok, from_tok, where = [], {}, None, None, None, None
    i = 0
    while i < len(rest):
        t = rest[i]
        if t == ("word", "to") and i + 1 < len(rest):
            to_tok = rest[i + 1]
            i += 2
            continue
        if t == ("word", "in") and i + 1 < len(rest):
            in_tok = rest[i + 1]
            i += 2
            continue
        if t == ("word", "from") and i + 1 < len(rest) \
                and rest[i + 1][0] != "colon":
            from_tok = rest[i + 1]
            i += 2
            continue
        if t == ("word", "using") and i + 1 < len(rest) \
                and rest[i + 1][0] != "colon":
            # using rules "r.txt" -> the file is two tokens on;
            # using "r.txt" -> the file is the next token.
            # (using : merge is a named argument, handled below.)
            if i + 2 < len(rest) and rest[i + 1][0] == "word" \
                    and rest[i + 2][0] != "colon":
                named["using"] = rest[i + 2]
                i += 3
            else:
                named["using"] = rest[i + 1]
                i += 2
            continue
        if t == ("word", "where"):
            where = rest[i + 1:]
            break
        if t[0] == "word" and i + 2 < len(rest) and rest[i + 1][0] == "colon":
            named[t[1]] = rest[i + 2]
            i += 3
            continue
        positional.append(t)
        i += 1
    return {"verb": verb, "lib": lib_token, "pos": positional,
            "named": named, "to": to_tok, "in": in_tok, "from": from_tok,
            "where": where, "line": lineno}


# ---------------------------------------------------------------- executor
class Env:
    def __init__(self):
        self.vars = {}
        self.libs = {}       # name/alias -> library object
        self.registry = {}   # verb -> list of (lib_name, function)
        self.builtins = {}

    def register(self, lib_name, verb, fn):
        self.registry.setdefault(verb, []).append((lib_name, fn))

    def resolve(self, token, line):
        kind, val = token
        if kind == "str":
            return val
        if kind == "num":
            return float(val) if "." in val else int(val)
        if kind == "word":
            if val == "true":
                return True
            if val == "false":
                return False
            # dotted access: host.port, result.status
            parts = val.split(".")
            base = parts[0]
            if base not in self.vars:
                raise SaralError(
                    f"I have not seen a variable named '{base}' yet. "
                    f"Give it a value first, like: {base} is ...", line)
            value = self.vars[base]
            for part in parts[1:]:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    raise SaralError(
                        f"'{base}' has no field named '{part}'", line)
            return value
        raise SaralError(f"cannot use {token!r} as a value", line)

    def truthy(self, value):
        return bool(value)


def eval_expr(env, toks, line):
    """Evaluate an arithmetic expression: values joined by + - * /,
    with * and / binding tighter than + and -. No parentheses in
    v0.3. Division by zero is a clear error, not a crash."""
    if not toks:
        raise SaralError("an expression needs a value", line)
    pos = [0]

    def factor():
        if pos[0] >= len(toks):
            raise SaralError("an expression ends before its value", line)
        tok = toks[pos[0]]
        pos[0] += 1
        return env.resolve(tok, line)

    def term():
        value = factor()
        while pos[0] < len(toks) and toks[pos[0]] in (("op", "*"), ("op", "/")):
            op = toks[pos[0]][1]
            pos[0] += 1
            right = factor()
            if op == "*":
                value = value * right
            else:
                if right == 0:
                    raise SaralError("division by zero", line)
                if isinstance(value, int) and isinstance(right, int) \
                        and value % right == 0:
                    value = value // right
                else:
                    value = value / right
        return value

    value = term()
    while pos[0] < len(toks) and toks[pos[0]] in (("op", "+"), ("op", "-")):
        op = toks[pos[0]][1]
        pos[0] += 1
        right = term()
        value = value + right if op == "+" else value - right
    if pos[0] != len(toks):
        raise SaralError(
            f"I do not understand {toks[pos[0]][1]!r} in this expression", line)
    return value


def eval_condition(env, cond, line):
    left_toks, op, right_toks = cond
    left = eval_expr(env, left_toks, line)
    if op is None:
        return env.truthy(left)
    if not right_toks:
        raise SaralError("a condition needs a value after its operator", line)
    right = eval_expr(env, right_toks, line)
    if op == "is":
        return left == right
    if op == "is not":
        return left != right
    if op == "contains":
        if isinstance(left, (list, tuple, set)):
            return right in left
        if isinstance(left, dict):
            return right in left
        return str(right) in str(left)
    if op == ">":
        return left > right
    if op == "<":
        return left < right
    if op == ">=":
        return left >= right
    if op == "<=":
        return left <= right
    raise SaralError(f"unknown condition {op!r}", line)


def show_value(value):
    if isinstance(value, list):
        if not value:
            print("(empty list)")
        for item in value:
            print(format_value(item))
    elif isinstance(value, dict):
        print(json.dumps(value, indent=2, ensure_ascii=False))
    else:
        print(value)


def format_value(value):
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def exec_nodes(env, nodes):
    for node in nodes:
        if node.kind == "took":
            load_library(env, node.lib, node.alias, node.line)
        elif node.kind == "assign_expr":
            env.vars[node.var] = eval_expr(env, node.expr, node.line)
        elif node.kind == "assign_value":
            env.vars[node.var] = env.resolve(node.token, node.line)
        elif node.kind == "assign_call":
            env.vars[node.var] = exec_call(env, node.call)
        elif node.kind == "flow":
            env.vars[node.target] = exec_call(env, node.call)
        elif node.kind == "call":
            exec_call(env, node.call)
        elif node.kind == "for":
            iterable = env.resolve(node.expr[0], node.line) \
                if len(node.expr) == 1 else exec_call(env, parse_call(node.expr, node.line))
            if isinstance(iterable, dict):
                iterable = list(iterable.items())
            if not isinstance(iterable, (list, tuple)):
                raise SaralError(
                    f"for each needs a list to go through, not {type(iterable).__name__}",
                    node.line)
            for item in iterable:
                env.vars[node.var] = item
                exec_nodes(env, node.body)
        elif node.kind == "if":
            branch = node.body if eval_condition(env, node.cond, node.line) \
                else node.else_body
            exec_nodes(env, branch)
        elif node.kind == "while":
            # Capped at 1000 iterations: a loop that never stops is a
            # clear error, not a hang. The cap is documented in SPEC.md.
            count = 0
            while eval_condition(env, node.cond, node.line):
                if count >= 1000:
                    raise SaralError(
                        "while loop ran 1000 times without stopping. "
                        "Check that the loop changes its condition.",
                        node.line)
                exec_nodes(env, node.body)
                count += 1
        else:
            raise SaralError(f"unknown task {node.kind!r}", node.line)


def _known_library_names():
    names = set()
    try:
        for entry in os.listdir(LIB_DIR):
            if entry.endswith(".py"):
                names.add(entry[:-3])
            elif os.path.isdir(os.path.join(LIB_DIR, entry)):
                names.add(entry)
    except OSError:
        pass
    return names


def exec_call(env, call):
    verb, lib_token = call["verb"], call["lib"]
    line = call["line"]
    # If the word after the verb is not a loaded library and not a known
    # library name at all, it is a positional argument (a variable), not a
    # library — e.g. 'show message' must not try to load a library 'message'.
    # Dotted names map to underscore files (log.rules -> log_rules.py), so
    # the dotted form also counts as known.
    if lib_token is not None and lib_token not in env.libs \
            and lib_token not in _known_library_names() \
            and lib_token.replace(".", "_") not in _known_library_names():
        call = dict(call)
        call["lib"] = None
        call["pos"] = [("word", lib_token)] + list(call["pos"])
        lib_token = None
    # Built-in verbs first when no library is named (they are the plain words).
    if lib_token is None and verb in env.builtins:
        return env.builtins[verb](env, call)
    candidates = env.registry.get(verb, [])
    fn = None
    if lib_token is not None:
        lib_name = env.libs.get(lib_token)
        if lib_name is None:
            raise SaralError(
                f"I have not loaded '{lib_token}'. Load it first, like: took {lib_token}",
                line)
        for name, f in candidates:
            if name == lib_name:
                fn = f
                break
        if fn is None:
            raise SaralError(
                f"library '{lib_name}' has no verb '{verb}'", line)
    else:
        if len(candidates) == 1:
            fn = candidates[0][1]
        elif len(candidates) > 1:
            raise SaralError(
                f"verb '{verb}' exists in more than one loaded library. "
                f"Say which one, like: {verb} {candidates[0][0]} ...", line)
        elif verb in env.builtins:
            return env.builtins[verb](env, call)
    if fn is None:
        raise SaralError(
            f"I do not know the verb '{verb}'. Load a library with took, "
            f"or check the spelling.", line)
    pos = [env.resolve(t, line) for t in call["pos"]]
    # Named values: a variable if one exists, otherwise a plain keyword
    # (format : json, format : csv) — keywords are not variables.
    named = {}
    for k, v in call["named"].items():
        if v[0] == "word" and v[1] not in ("true", "false") \
                and v[1].split(".")[0] not in env.vars:
            named[k] = v[1]
        else:
            named[k] = env.resolve(v, line)
    to_val = env.resolve(call["to"], line) if call["to"] is not None else None
    in_val = env.resolve(call["in"], line) if call["in"] is not None else None
    # 'from' is handed to library functions as named['from'], so existing
    # 7-argument library functions keep working unchanged.
    if call.get("from") is not None:
        named["from"] = env.resolve(call["from"], line)
    where = None
    if call["where"] is not None:
        where = parse_where(env, call["where"], line)
    return fn(env, pos, named, to_val, in_val, where, line)


def parse_where(env, toks, line):
    """field op value  — op: is / is not / contains (v0.3: also
    > < >= <=, evaluated like a condition)."""
    if len(toks) < 3:
        raise SaralError(
            "filter needs: where <field> is <value>", line)
    field = toks[0][1] if toks[0][0] == "word" else None
    left_toks, op, right_toks = parse_condition(toks, line)
    if left_toks != toks[:1]:
        raise SaralError(
            "filter needs: where <field> is <value>", line)
    return (field, op, eval_expr(env, right_toks, line) if right_toks else None)


# ------------------------------------------------------- built-in verbs
def builtin_show(env, call):
    if not call["pos"]:
        raise SaralError("show needs something to show, like: show hosts", call["line"])
    value = env.resolve(call["pos"][0], call["line"])
    show_value(value)
    return value


def builtin_find(env, call):
    if not call["pos"] or call["in"] is None:
        raise SaralError(
            'find looks like: find "ERROR" in text', call["line"])
    pattern = env.resolve(call["pos"][0], call["line"])
    # Built-ins receive the raw call, so resolve the 'in' token here.
    hay = env.resolve(call["in"], call["line"])
    if isinstance(hay, str):
        return [ln for ln in hay.splitlines() if str(pattern) in ln]
    if isinstance(hay, (list, tuple)):
        return [item for item in hay if str(pattern) in format_value(item)]
    return []


def builtin_filter(env, call):
    if not call["pos"]:
        raise SaralError(
            "filter looks like: filter hosts where port is 80", call["line"])
    items = env.resolve(call["pos"][0], call["line"])
    if not isinstance(items, (list, tuple)):
        raise SaralError("filter needs a list", call["line"])
    if call["where"] is None:
        return list(items)
    # Built-ins receive the raw 'where' tokens; parse them here.
    field, op, wanted = parse_where(env, call["where"], call["line"])
    out = []
    for item in items:
        if isinstance(item, dict):
            got = item.get(field)
        else:
            got = item  # a plain list: the item itself is compared
        keep = False
        if op == "is":
            keep = got == wanted
        elif op == "is not":
            keep = got != wanted
        elif op == "contains":
            keep = str(wanted) in str(got)
        elif op == ">":
            keep = got > wanted
        elif op == "<":
            keep = got < wanted
        elif op == ">=":
            keep = got >= wanted
        elif op == "<=":
            keep = got <= wanted
        if keep:
            out.append(item)
    return out


# ------------------------------------------------------- library loading
def make_bridge_fn(lib_name, language, entry_path, verb=None):
    def bridge(env, pos, named, to_val, in_val, where, line):
        if language == "node":
            cmd = ["node", entry_path]
        elif language == "shell":
            cmd = ["bash", entry_path]
        elif language == "python":
            cmd = [sys.executable, entry_path]
        else:
            raise SaralError(
                f"bridge language '{language}' is not supported (node, shell, python)",
                line)
        payload = {"verb": bridge_verb, "args": pos, "named": named}
        try:
            proc = subprocess.run(cmd, input=json.dumps(payload), text=True,
                                  capture_output=True, timeout=30)
        except FileNotFoundError:
            raise SaralError(
                f"cannot run the '{lib_name}' bridge: '{cmd[0]}' is not installed",
                line)
        if proc.returncode != 0:
            raise SaralError(
                f"bridge library '{lib_name}' failed: {proc.stderr.strip()[:300]}",
                line)
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            raise SaralError(
                f"bridge library '{lib_name}' did not return JSON: "
                f"{proc.stdout.strip()[:200]}", line)
        if "error" in data:
            raise SaralError(f"bridge library '{lib_name}': {data['error']}", line)
        return data.get("result")
    bridge_verb = verb
    return bridge


def load_library(env, name, alias, line):  # noqa: F811 - intentional override
    if name in env.libs:
        if alias:
            env.libs[alias] = env.libs[name]
        return
    # Dotted library names map to underscore files/folders on disk:
    # took log.rules loads libs/log_rules.py, but verbs still resolve
    # under the name the script used ("log.rules").
    fs_name = name.replace(".", "_")
    py_path = os.path.join(LIB_DIR, fs_name + ".py")
    folder = os.path.join(LIB_DIR, fs_name)
    if os.path.isfile(py_path):
        import importlib.util
        spec = importlib.util.spec_from_file_location("saral_lib_" + fs_name, py_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.register(env)
        env.libs[name] = name
        if alias:
            env.libs[alias] = name
        return
    if os.path.isdir(folder):
        manifest_path = os.path.join(folder, "lib.json")
        if not os.path.isfile(manifest_path):
            raise SaralError(
                f"library '{name}' has no lib.json in libs/{name}/", line)
        with open(manifest_path, encoding="utf-8") as fh:
            manifest = json.load(fh)
        language, entry = manifest.get("language"), manifest.get("entry")
        verbs = manifest.get("verbs", [])
        if not language or not entry or not verbs:
            raise SaralError(
                f"lib.json for '{name}' must declare language, entry and verbs",
                line)
        entry_path = os.path.join(folder, entry)
        for verb in verbs:
            env.register(name, verb,
                         make_bridge_fn(name, language, entry_path, verb))
        env.libs[name] = name
        if alias:
            env.libs[alias] = name
        return
    raise SaralError(
        f"there is no library named '{name}'. Available libraries live in libs/.",
        line)


# ---------------------------------------------------------------- main
def parse_source(source):
    """Tokenise + parse only, no execution. Used by `saral check`."""
    raw_lines = []
    for lineno, raw in enumerate(source.splitlines(), 1):
        expanded = raw.replace("\t", "    ")
        indent = len(expanded) - len(expanded.lstrip(" "))
        stripped = expanded.strip()
        if not stripped or stripped.startswith("#"):
            continue
        tokens = tokenize(expanded, lineno)
        raw_lines.append((lineno, indent, tokens))
    return parse(raw_lines)


def run_source(source, filename="<script>"):
    nodes = parse_source(source)
    env = Env()
    env.builtins = {"show": builtin_show, "find": builtin_find,
                    "filter": builtin_filter}
    exec_nodes(env, nodes)
    return env


def list_libraries():
    """Libraries actually present in libs/, with their real verbs.

    Python libraries are imported and registered on a throwaway Env
    (they have no import side effects); bridge folders are read from
    lib.json. Only the library's primary name is shown, so
    log.rules does not also appear as a stray 'logs' entry.
    """
    entries = []
    try:
        names = sorted(os.listdir(LIB_DIR))
    except OSError:
        return entries
    for entry in names:
        if entry == "__pycache__":
            continue
        path = os.path.join(LIB_DIR, entry)
        if entry.endswith(".py"):
            primary = "log.rules" if entry == "log_rules.py" else entry[:-3]
            env = Env()
            env.builtins = {}
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    "saral_list_" + entry[:-3], path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                mod.register(env)
            except Exception:
                continue
            verbs = sorted({verb for verb, pairs in env.registry.items()
                            for lib_name, _fn in pairs if lib_name == primary})
            entries.append((primary, verbs))
        elif os.path.isdir(path):
            manifest_path = os.path.join(path, "lib.json")
            if not os.path.isfile(manifest_path):
                continue
            try:
                with open(manifest_path, encoding="utf-8") as fh:
                    manifest = json.load(fh)
            except (OSError, json.JSONDecodeError):
                continue
            entries.append((manifest.get("name", entry),
                            sorted(manifest.get("verbs", []))))
    return entries


def main(argv):
    if len(argv) >= 2 and argv[1] == "version":
        print("Saral " + VERSION)
        return 0
    if len(argv) >= 2 and argv[1] == "list":
        for name, verbs in list_libraries():
            print(f"{name}: {', '.join(verbs)}" if verbs else f"{name}: (no verbs)")
        return 0
    if len(argv) >= 2 and argv[1] == "check":
        if len(argv) != 3:
            print("Usage: saral check script.srl")
            return 2
        path = argv[2]
        if not os.path.isfile(path):
            print(f"Saral error: no such script: {path}")
            return 2
        try:
            with open(path, encoding="utf-8") as fh:
                parse_source(fh.read())
        except SaralError as exc:
            print(str(exc))
            return 1
        print(f"OK: {path} parses")
        return 0
    if len(argv) != 2 or argv[1] in ("-h", "--help"):
        print("Saral " + VERSION)
        print("Usage: saral script.srl | saral check script.srl | "
              "saral list | saral version")
        print("See README.md and SPEC.md for the syntax.")
        return 0 if len(argv) == 2 else 2
    path = argv[1]
    if not os.path.isfile(path):
        print(f"Saral error: no such script: {path}")
        return 2
    try:
        with open(path, encoding="utf-8") as fh:
            run_source(fh.read(), path)
    except SaralError as exc:
        print(str(exc))
        return 1
    except FileNotFoundError as exc:
        print(f"Saral error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
