"""Saral library: data. Containers and algorithms, in Saral's own style.

Containers are created with a quoted kind, because bare words in Saral
are variable names, not labels:
    stack is new data "stack"
    queue is new data "queue"
    myset is new data "set"
    mymap is new data "map"
    tree  is new data "tree"
    graph is new data "graph"

Algorithms are implemented here by hand, not by delegating to a
built-in sort: merge sort and quick sort are written out below,
binary search is a manual loop that first checks the list really is
sorted (an unsorted list is an error, not a silent wrong answer),
BFS and Dijkstra are manual traversals. Set/map storage uses
Python's set/dict internally — that is storage, not the algorithm
being demonstrated — and this is stated in SPEC.md, not hidden.
"""
import json

try:
    from saral import SaralError
except Exception:
    class SaralError(Exception):
        def __init__(self, message, line=0):
            super().__init__(message)
            self.line = line


# ------------------------------------------------------------ containers
class Stack:
    def __init__(self):
        self.items = []

    def __str__(self):
        return "stack: " + json.dumps(self.items, ensure_ascii=False)


class Queue:
    def __init__(self):
        self.items = []

    def __str__(self):
        return "queue: " + json.dumps(self.items, ensure_ascii=False)


class SetObj:
    def __init__(self):
        self.items = set()

    def __str__(self):
        return "set: " + json.dumps(sorted(self.items, key=str), ensure_ascii=False)


class MapObj:
    def __init__(self):
        self.items = {}

    def __str__(self):
        return "map: " + json.dumps(self.items, ensure_ascii=False)


class TreeNode:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None


class Tree:
    """Binary search tree, built by hand: insert/search/in-order walk."""

    def __init__(self):
        self.root = None

    def insert(self, value):
        if self.root is None:
            self.root = TreeNode(value)
            return
        node = self.root
        while True:
            if value == node.value:
                return  # duplicates are ignored, documented in SPEC.md
            if value < node.value:
                if node.left is None:
                    node.left = TreeNode(value)
                    return
                node = node.left
            else:
                if node.right is None:
                    node.right = TreeNode(value)
                    return
                node = node.right

    def search(self, value):
        node = self.root
        while node is not None:
            if value == node.value:
                return True
            node = node.left if value < node.value else node.right
        return False

    def walk(self):
        out = []

        def inorder(node):
            if node is None:
                return
            inorder(node.left)
            out.append(node.value)
            inorder(node.right)

        inorder(self.root)
        return out

    def __str__(self):
        return "tree (in order): " + json.dumps(self.walk(), ensure_ascii=False)


class Heap:
    """Min-heap, built by hand (array + sift up/down, no heapq).

    Lower priority comes out first: push with priority : 1 beats
    priority : 3. Equal priorities come out in push order, because
    each entry also carries a counter. Pop/peek return the value,
    not the (priority, value) pair."""

    def __init__(self):
        self.items = []  # (priority, counter, value)
        self.counter = 0

    def push(self, priority, value):
        self.items.append((priority, self.counter, value))
        self.counter += 1
        i = len(self.items) - 1
        while i > 0:
            parent = (i - 1) // 2
            if self.items[i][:2] < self.items[parent][:2]:
                self.items[i], self.items[parent] = \
                    self.items[parent], self.items[i]
                i = parent
            else:
                break

    def pop(self):
        if not self.items:
            raise ValueError("cannot pop an empty heap")
        top = self.items[0][2]
        last = self.items.pop()
        if self.items:
            self.items[0] = last
            i = 0
            while True:
                left, right = 2 * i + 1, 2 * i + 2
                smallest = i
                if left < len(self.items) \
                        and self.items[left][:2] < self.items[smallest][:2]:
                    smallest = left
                if right < len(self.items) \
                        and self.items[right][:2] < self.items[smallest][:2]:
                    smallest = right
                if smallest == i:
                    break
                self.items[i], self.items[smallest] = \
                    self.items[smallest], self.items[i]
                i = smallest
        return top

    def peek(self):
        if not self.items:
            raise ValueError("cannot peek an empty heap")
        return self.items[0][2]

    def __str__(self):
        return "heap: " + json.dumps(
            [v for _p, _c, v in sorted(self.items)], ensure_ascii=False)


class _LinkNode:
    def __init__(self, value):
        self.value = value
        self.next = None


class LinkedList:
    """Singly linked list, built by hand: append, search, remove, walk."""

    def __init__(self):
        self.head = None

    def append(self, value):
        node = _LinkNode(value)
        if self.head is None:
            self.head = node
            return
        cur = self.head
        while cur.next is not None:
            cur = cur.next
        cur.next = node

    def search(self, value):
        cur = self.head
        while cur is not None:
            if cur.value == value:
                return True
            cur = cur.next
        return False

    def remove(self, value):
        if self.head is None:
            return False
        if self.head.value == value:
            self.head = self.head.next
            return True
        cur = self.head
        while cur.next is not None:
            if cur.next.value == value:
                cur.next = cur.next.next
                return True
            cur = cur.next
        return False

    def walk(self):
        out, cur = [], self.head
        while cur is not None:
            out.append(cur.value)
            cur = cur.next
        return out

    def __str__(self):
        return "linked: " + json.dumps(self.walk(), ensure_ascii=False)


class _TrieNode:
    def __init__(self):
        self.children = {}
        self.is_word = False


class Trie:
    """Trie (prefix tree), built by hand: insert, exact search, prefix."""

    def __init__(self):
        self.root = _TrieNode()
        self.words = 0

    def insert(self, word):
        node = self.root
        for ch in str(word):
            node = node.children.setdefault(ch, _TrieNode())
        if not node.is_word:
            node.is_word = True
            self.words += 1

    def search(self, word):
        node = self.root
        for ch in str(word):
            if ch not in node.children:
                return False
            node = node.children[ch]
        return node.is_word

    def prefix(self, prefix):
        node = self.root
        for ch in str(prefix):
            if ch not in node.children:
                return []
            node = node.children[ch]
        out = []

        def collect(n, word):
            if n.is_word:
                out.append(word)
            for ch in sorted(n.children):
                collect(n.children[ch], word + ch)

        collect(node, str(prefix))
        return out

    def __str__(self):
        return "trie: " + json.dumps(self.prefix(""), ensure_ascii=False)


class Graph:
    """Directed graph. Edges carry a weight (default 1)."""

    def __init__(self):
        self.nodes = set()
        self.order = []  # first-seen order, for deterministic topo sort
        self.edges = {}  # node -> list of (neighbour, weight), in link order

    def add_node(self, node):
        if node not in self.nodes:
            self.nodes.add(node)
            self.order.append(node)
        self.edges.setdefault(node, [])

    def link(self, src, dst, weight=1):
        self.add_node(src)
        self.add_node(dst)
        for i, (n, _w) in enumerate(self.edges[src]):
            if n == dst:
                self.edges[src][i] = (dst, weight)
                return
        self.edges[src].append((dst, weight))

    def neighbours(self, node):
        if node not in self.nodes:
            return None
        return [n for n, _w in self.edges.get(node, [])]

    def bfs_path(self, start, goal):
        if start not in self.nodes or goal not in self.nodes:
            return []
        if start == goal:
            return [start]
        visited = {start}
        parent = {start: None}
        queue = [start]
        while queue:
            cur = queue.pop(0)
            for nxt, _w in self.edges.get(cur, []):
                if nxt not in visited:
                    visited.add(nxt)
                    parent[nxt] = cur
                    if nxt == goal:
                        path = [goal]
                        while parent[path[0]] is not None:
                            path.insert(0, parent[path[0]])
                        return path
                    queue.append(nxt)
        return []

    def dijkstra(self, start, goal):
        """Shortest weighted path, with a manual linear scan for the
        smallest unvisited distance (no heap library)."""
        if start not in self.nodes or goal not in self.nodes:
            return {"path": [], "distance": -1}
        dist = {n: None for n in self.nodes}
        parent = {n: None for n in self.nodes}
        dist[start] = 0
        done = set()
        while True:
            cur, best = None, None
            for node, d in dist.items():
                if node not in done and d is not None and (best is None or d < best):
                    cur, best = node, d
            if cur is None:
                break
            done.add(cur)
            if cur == goal:
                break
            for nxt, w in self.edges.get(cur, []):
                nd = dist[cur] + w
                if dist[nxt] is None or nd < dist[nxt]:
                    dist[nxt] = nd
                    parent[nxt] = cur
        if dist[goal] is None:
            return {"path": [], "distance": -1}
        path = [goal]
        while parent[path[0]] is not None:
            path.insert(0, parent[path[0]])
        return {"path": path, "distance": dist[goal]}

    def dfs_walk(self, start):
        """Depth-first walk from start, neighbours in link order."""
        if start not in self.nodes:
            raise ValueError(f"graph has no node {start!r}")
        visited, out = set(), []

        def visit(node):
            visited.add(node)
            out.append(node)
            for nxt, _w in self.edges.get(node, []):
                if nxt not in visited:
                    visit(nxt)

        visit(start)
        return out

    def has_cycle(self):
        """Directed cycle check, three-colour DFS (white/grey/black)."""
        colour = {n: 0 for n in self.nodes}  # 0 unvisited, 1 in stack, 2 done

        def visit(node):
            colour[node] = 1
            for nxt, _w in self.edges.get(node, []):
                if colour[nxt] == 1:
                    return True
                if colour[nxt] == 0 and visit(nxt):
                    return True
            colour[node] = 2
            return False

        return any(colour[n] == 0 and visit(n) for n in list(self.nodes))

    def topological_sort(self):
        """Kahn's algorithm, nodes in first-seen order for ties.
        Raises ValueError on a cyclic graph — never a partial order."""
        indegree = {n: 0 for n in self.nodes}
        for src in self.edges:
            for dst, _w in self.edges[src]:
                indegree[dst] += 1
        queue = [n for n in self.order if indegree[n] == 0]
        out = []
        while queue:
            cur = queue.pop(0)
            out.append(cur)
            for nxt, _w in self.edges.get(cur, []):
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    queue.append(nxt)
        if len(out) != len(self.nodes):
            raise ValueError(
                "topological sort needs a graph with no cycle: "
                "this graph has a cycle, so no order exists")
        return out

    def __str__(self):
        edges = []
        for src in sorted(self.edges, key=str):
            for dst, w in self.edges[src]:
                edges.append(f"{src} -> {dst} ({w})")
        return "graph: " + (", ".join(edges) if edges else "(no edges)")


_KINDS = {"stack": Stack, "queue": Queue, "set": SetObj,
          "map": MapObj, "tree": Tree, "graph": Graph,
          "heap": Heap, "linked": LinkedList, "trie": Trie}


def _is_graph(obj):
    """Duck type, not isinstance: a Graph built by log.rules loads
    data.py as a second module, so its class object differs even
    though it is the same code. What matters is the shape."""
    return hasattr(obj, "nodes") and hasattr(obj, "edges") \
        and callable(getattr(obj, "bfs_path", None)) \
        and callable(getattr(obj, "dijkstra", None))


# ------------------------------------------------------------ sorting
def _key(item, field):
    if field is None:
        return item
    if isinstance(item, dict):
        if field not in item:
            raise ValueError(f"row has no field {field!r}")
        return item[field]
    raise ValueError("by field only works on tables (lists of rows)")


def _merge(left, right, field):
    out, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        if _key(left[i], field) <= _key(right[j], field):
            out.append(left[i])
            i += 1
        else:
            out.append(right[j])
            j += 1
    out.extend(left[i:])
    out.extend(right[j:])
    return out


def merge_sort(items, field):
    if len(items) <= 1:
        return list(items)
    mid = len(items) // 2
    return _merge(merge_sort(items[:mid], field),
                  merge_sort(items[mid:], field), field)


def quick_sort(items, field):
    if len(items) <= 1:
        return list(items)
    pivot = _key(items[0], field)
    less = [x for x in items if _key(x, field) < pivot]
    same = [x for x in items if _key(x, field) == pivot]
    more = [x for x in items if _key(x, field) > pivot]
    return quick_sort(less, field) + same + quick_sort(more, field)


def _sorted_keys(items, field):
    try:
        return [_key(x, field) for x in items]
    except ValueError as exc:
        raise exc


def linear_search(items, value, field):
    for idx, item in enumerate(items):
        if _key(item, field) == value:
            return idx
    return -1


def binary_search(items, value, field):
    keys = _sorted_keys(items, field)
    for i in range(len(keys) - 1):
        if keys[i] > keys[i + 1]:
            raise ValueError(
                "binary search needs a sorted list: sort it first, "
                "like: sorted is sort data items using : merge")
    lo, hi = 0, len(keys) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if keys[mid] == value:
            return mid
        if keys[mid] < value:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


# ------------------------------------------------------------ verb helpers
def _need_container(pos, line, verb):
    if not pos:
        raise SaralError(f"{verb} needs a container, like: {verb} data stack", line)
    return pos[0]


def _as_list(value, verb, line):
    if not isinstance(value, (list, tuple)):
        raise SaralError(f"{verb} needs a list, not {type(value).__name__}", line)
    return list(value)


def _int_named(named, key, default, line, verb):
    raw = named.get(key, default)
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise SaralError(f"{verb} needs {key} : a whole number, not {raw!r}", line)


# ------------------------------------------------------------ verbs
def new(env, pos, named, to_val, in_val, where, line):
    if not pos:
        raise SaralError('new needs a kind, like: new data "stack"', line)
    kind = str(pos[0])
    if kind not in _KINDS:
        raise SaralError(
            f"new data kinds are: {', '.join(sorted(_KINDS))}, not {kind!r}", line)
    return _KINDS[kind]()


def push(env, pos, named, to_val, in_val, where, line):
    if to_val is None or not pos:
        raise SaralError('push looks like: push data "x" to stack', line)
    if isinstance(to_val, Heap):
        # push data "task" to heap priority : 3  (lowest first)
        if "priority" not in named:
            raise SaralError(
                'heap push needs priority : a number, like: '
                'push data "task" to heap priority : 3', line)
        try:
            priority = int(named["priority"])
        except (TypeError, ValueError):
            raise SaralError("heap priority must be a whole number", line)
        to_val.push(priority, pos[0])
        return to_val
    if not isinstance(to_val, Stack):
        raise SaralError(
            "push only works on a stack or a heap: "
            "stack is new data \"stack\", heap is new data \"heap\"", line)
    to_val.items.append(pos[0])
    return to_val


def pop(env, pos, named, to_val, in_val, where, line):
    container = _need_container(pos, line, "pop")
    if isinstance(container, Heap):
        try:
            return container.pop()
        except ValueError as exc:
            raise SaralError(str(exc), line)
    if not isinstance(container, Stack):
        raise SaralError("pop only works on a stack or a heap", line)
    if not container.items:
        raise SaralError("cannot pop an empty stack", line)
    return container.items.pop()


def peek(env, pos, named, to_val, in_val, where, line):
    container = _need_container(pos, line, "peek")
    if isinstance(container, Heap):
        try:
            return container.peek()
        except ValueError as exc:
            raise SaralError(str(exc), line)
    if not isinstance(container, Stack):
        raise SaralError("peek only works on a stack or a heap", line)
    if not container.items:
        raise SaralError("cannot peek an empty stack", line)
    return container.items[-1]


def append(env, pos, named, to_val, in_val, where, line):
    if to_val is None or not pos:
        raise SaralError('append looks like: append data "x" to list', line)
    if not isinstance(to_val, LinkedList):
        raise SaralError(
            "append only works on a linked list: list is new data \"linked\"",
            line)
    to_val.append(pos[0])
    return to_val


def enqueue(env, pos, named, to_val, in_val, where, line):
    if to_val is None or not pos:
        raise SaralError('enqueue looks like: enqueue data "x" to queue', line)
    if not isinstance(to_val, Queue):
        raise SaralError("enqueue only works on a queue", line)
    to_val.items.append(pos[0])
    return to_val


def dequeue(env, pos, named, to_val, in_val, where, line):
    queue = _need_container(pos, line, "dequeue")
    if not isinstance(queue, Queue):
        raise SaralError("dequeue only works on a queue", line)
    if not queue.items:
        raise SaralError("cannot dequeue an empty queue", line)
    return queue.items.pop(0)


def add(env, pos, named, to_val, in_val, where, line):
    if to_val is None or not pos:
        raise SaralError('add looks like: add data "a" to myset', line)
    if not isinstance(to_val, SetObj):
        raise SaralError("add only works on a set: myset is new data \"set\"", line)
    try:
        to_val.items.add(pos[0])
    except TypeError:
        raise SaralError("a set only holds values that can be hashed", line)
    return to_val


def has(env, pos, named, to_val, in_val, where, line):
    if len(pos) < 2:
        raise SaralError('has looks like: has data myset "a"', line)
    container, value = pos[0], pos[1]
    if isinstance(container, SetObj):
        return value in container.items
    if isinstance(container, MapObj):
        return value in container.items
    if isinstance(container, (list, tuple)):
        return value in container
    raise SaralError("has works on a set, a map, or a list", line)


def remove(env, pos, named, to_val, in_val, where, line):
    # Two forms, both documented:
    #   remove data "a" from myset   (from separator)
    #   remove data myset "a"        (container first)
    if "from" in named:
        container, value = named["from"], pos[0] if pos else None
    elif len(pos) >= 2:
        container, value = pos[0], pos[1]
    else:
        raise SaralError(
            'remove looks like: remove data "a" from myset', line)
    if isinstance(container, SetObj):
        if value not in container.items:
            raise SaralError(f"set does not hold {value!r}, so it cannot be removed", line)
        container.items.discard(value)
        return container
    if isinstance(container, MapObj):
        if value not in container.items:
            raise SaralError(f"map has no key {value!r}, so it cannot be removed", line)
        del container.items[value]
        return container
    if isinstance(container, LinkedList):
        if not container.remove(value):
            raise SaralError(f"linked list does not hold {value!r}", line)
        return container
    raise SaralError("remove works on a set, a map, or a linked list", line)


def put(env, pos, named, to_val, in_val, where, line):
    container = _need_container(pos, line, "put")
    if not isinstance(container, MapObj):
        raise SaralError("put only works on a map: mymap is new data \"map\"", line)
    if "key" not in named or "value" not in named:
        raise SaralError('put looks like: put data mymap key : "a" value : 1', line)
    container.items[named["key"]] = named["value"]
    return container


def get(env, pos, named, to_val, in_val, where, line):
    container = _need_container(pos, line, "get")
    if not isinstance(container, MapObj):
        raise SaralError("get only works on a map", line)
    if "key" not in named:
        raise SaralError('get looks like: get data mymap key : "a"', line)
    key = named["key"]
    if key not in container.items:
        raise SaralError(f"map has no key {key!r}", line)
    return container.items[key]


def insert(env, pos, named, to_val, in_val, where, line):
    target = _need_container(pos, line, "insert")
    if "value" not in named:
        raise SaralError('insert looks like: insert data tree value : 5', line)
    if isinstance(target, Tree):
        target.insert(named["value"])
        return target
    if isinstance(target, Trie):
        target.insert(named["value"])
        return target
    raise SaralError("insert only works on a tree or a trie", line)


def search(env, pos, named, to_val, in_val, where, line):
    if not pos:
        raise SaralError('search needs something to search, like: search data tree value : 5', line)
    target = pos[0]
    if isinstance(target, (Tree, Trie, LinkedList)):
        if "value" not in named:
            raise SaralError('search a tree/trie/list like: search data tree value : 5', line)
        return target.search(named["value"])
    items = _as_list(target, "search", line)
    if "value" not in named:
        raise SaralError(
            'search a list like: search data items value : 42 using : binary', line)
    using = str(named.get("using", "linear")).lower()
    field = named.get("by")
    if using == "linear":
        return linear_search(items, named["value"], field)
    if using == "binary":
        try:
            return binary_search(items, named["value"], field)
        except ValueError as exc:
            raise SaralError(str(exc), line)
    raise SaralError(f"search using is linear or binary, not {using!r}", line)


def walk(env, pos, named, to_val, in_val, where, line):
    target = _need_container(pos, line, "walk")
    if isinstance(target, Tree):
        return target.walk()
    if isinstance(target, LinkedList):
        return target.walk()
    if _is_graph(target):
        # walk data graph from "a"  (from separator) or node : "a"
        start = named.get("from", named.get("node"))
        if start is None:
            raise SaralError(
                'walk a graph like: walk data graph from "a"', line)
        try:
            return target.dfs_walk(start)
        except ValueError as exc:
            raise SaralError(str(exc), line)
    raise SaralError("walk only works on a tree, a linked list, or a graph", line)


def prefix(env, pos, named, to_val, in_val, where, line):
    if len(pos) < 2:
        raise SaralError('prefix looks like: prefix data trie "ca"', line)
    trie, text = pos[0], pos[1]
    if not isinstance(trie, Trie):
        raise SaralError("prefix only works on a trie", line)
    return trie.prefix(text)


def cycle(env, pos, named, to_val, in_val, where, line):
    graph = _need_container(pos, line, "cycle")
    if not _is_graph(graph):
        raise SaralError("cycle only works on a graph", line)
    return graph.has_cycle()


def topological(env, pos, named, to_val, in_val, where, line):
    graph = _need_container(pos, line, "topological")
    if not _is_graph(graph):
        raise SaralError("topological only works on a graph", line)
    try:
        return graph.topological_sort()
    except ValueError as exc:
        raise SaralError(str(exc), line)


def link(env, pos, named, to_val, in_val, where, line):
    graph = _need_container(pos, line, "link")
    if not _is_graph(graph):
        raise SaralError("link only works on a graph", line)
    if "from" not in named or to_val is None:
        raise SaralError('link looks like: link data graph from "a" to "b"', line)
    weight = named.get("weight", 1)
    try:
        weight = int(weight)
    except (TypeError, ValueError):
        raise SaralError("link weight must be a whole number", line)
    graph.link(named["from"], to_val, weight)
    return graph


def neighbours(env, pos, named, to_val, in_val, where, line):
    graph = _need_container(pos, line, "neighbours")
    if not _is_graph(graph):
        raise SaralError("neighbours only works on a graph", line)
    if "node" not in named:
        raise SaralError('neighbours looks like: neighbours data graph node : "a"', line)
    result = graph.neighbours(named["node"])
    if result is None:
        raise SaralError(f"graph has no node {named['node']!r}", line)
    return result


def path(env, pos, named, to_val, in_val, where, line):
    graph = _need_container(pos, line, "path")
    if not _is_graph(graph):
        raise SaralError("path only works on a graph", line)
    if "from" not in named or to_val is None:
        raise SaralError('path looks like: path data graph from "a" to "b"', line)
    return graph.bfs_path(named["from"], to_val)


def shortest(env, pos, named, to_val, in_val, where, line):
    graph = _need_container(pos, line, "shortest")
    if not _is_graph(graph):
        raise SaralError("shortest only works on a graph", line)
    if "from" not in named or to_val is None:
        raise SaralError('shortest looks like: shortest data graph from "a" to "b"', line)
    return graph.dijkstra(named["from"], to_val)


def sort(env, pos, named, to_val, in_val, where, line):
    if not pos:
        raise SaralError('sort looks like: sort data items using : merge', line)
    items = _as_list(pos[0], "sort", line)
    using = str(named.get("using", "merge")).lower()
    field = named.get("by")
    try:
        if using == "merge":
            return merge_sort(items, field)
        if using == "quick":
            return quick_sort(items, field)
    except ValueError as exc:
        raise SaralError(str(exc), line)
    raise SaralError(f"sort using is merge or quick, not {using!r}", line)


def unique(env, pos, named, to_val, in_val, where, line):
    if not pos:
        raise SaralError('unique looks like: unique data items', line)
    items = _as_list(pos[0], "unique", line)
    seen, out = set(), []
    for item in items:
        key = json.dumps(item, sort_keys=True) if isinstance(item, dict) else item
        try:
            if key not in seen:
                seen.add(key)
                out.append(item)
        except TypeError:
            if item not in out:
                out.append(item)
    return out


def group(env, pos, named, to_val, in_val, where, line):
    if not pos:
        raise SaralError('group looks like: group data rows by : "severity"', line)
    items = _as_list(pos[0], "group", line)
    if "by" not in named:
        raise SaralError('group needs by : a field, like: group data rows by : "severity"', line)
    field = named["by"]
    out = {}
    for item in items:
        if not isinstance(item, dict) or field not in item:
            raise SaralError(f"group needs rows with a field {field!r}", line)
        out.setdefault(item[field], []).append(item)
    return out


def top(env, pos, named, to_val, in_val, where, line):
    if not pos:
        raise SaralError('top looks like: top data items count : 5', line)
    items = _as_list(pos[0], "top", line)
    return items[:_int_named(named, "count", 5, line, "top")]


def count(env, pos, named, to_val, in_val, where, line):
    if not pos:
        raise SaralError('count looks like: count data items', line)
    value = pos[0]
    if isinstance(value, (list, tuple)):
        return len(value)
    if isinstance(value, dict):
        return len(value)
    if isinstance(value, (SetObj, MapObj)):
        return len(value.items)
    if isinstance(value, (Stack, Queue, Heap)):
        return len(value.items)
    if isinstance(value, LinkedList):
        return len(value.walk())
    if isinstance(value, Trie):
        return value.words
    raise SaralError(
        "count works on a list, table, set, map, stack, queue, heap, "
        "linked list, or trie", line)


def first(env, pos, named, to_val, in_val, where, line):
    if not pos:
        raise SaralError('first looks like: first data items', line)
    items = _as_list(pos[0], "first", line)
    if not items:
        raise SaralError("first needs a non-empty list", line)
    return items[0]


def last(env, pos, named, to_val, in_val, where, line):
    if not pos:
        raise SaralError('last looks like: last data items', line)
    items = _as_list(pos[0], "last", line)
    if not items:
        raise SaralError("last needs a non-empty list", line)
    return items[-1]


def reverse(env, pos, named, to_val, in_val, where, line):
    if not pos:
        raise SaralError('reverse looks like: reverse data items', line)
    items = _as_list(pos[0], "reverse", line)
    out = []
    for i in range(len(items) - 1, -1, -1):
        out.append(items[i])
    return out


def join(env, pos, named, to_val, in_val, where, line):
    if not pos:
        raise SaralError('join looks like: join data items separator : ","', line)
    items = _as_list(pos[0], "join", line)
    return str(named.get("separator", ",")).join(str(x) for x in items)


def split(env, pos, named, to_val, in_val, where, line):
    if not pos:
        raise SaralError('split looks like: split data "a,b" separator : ","', line)
    return str(pos[0]).split(str(named.get("separator", ",")))


def register(env):
    for verb, fn in [
            ("new", new), ("push", push), ("pop", pop), ("peek", peek),
            ("enqueue", enqueue), ("dequeue", dequeue),
            ("add", add), ("has", has), ("remove", remove),
            ("put", put), ("get", get),
            ("insert", insert), ("search", search), ("walk", walk),
            ("append", append), ("prefix", prefix),
            ("cycle", cycle), ("topological", topological),
            ("link", link), ("neighbours", neighbours), ("path", path),
            ("shortest", shortest),
            ("sort", sort), ("unique", unique), ("group", group),
            ("top", top), ("count", count), ("first", first),
            ("last", last), ("reverse", reverse), ("join", join),
            ("split", split)]:
        env.register("data", verb, fn)
