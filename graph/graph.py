"""
graph.py — Graph Container & Generator
=======================================
Single source of truth for the graph.  Algorithms and the renderer
both talk to this object.

Responsibilities:
  1. CRUD on nodes & edges                  (add / remove / get)
  2. Adjacency queries                      (neighbours, edges_from, …)
  3. Graph-generation factory methods       (random, grid, maze, scale-free)
  4. Import from adjacency-list / matrix    (text → graph)
  5. Serialisation round-trip               (to_dict / from_dict)
  6. Reset helpers                          (wipe algo state, keep structure)

Design decisions:
  - Nodes & edges stored in plain dicts keyed by id for O(1) lookup.
  - A separate adjacency dict  `_adj[node_id] → [(neighbour_id, edge_id)]`
    is maintained incrementally so neighbour queries are O(degree), not O(E).
  - `directed` is a graph-level flag; individual Edge objects also carry it
    so serialisation is self-contained.
"""

import random
import math
from typing import (
    Dict, List, Tuple, Optional, Set, Iterator
)
from graph.node import Node, NodeState
from graph.edge import Edge, EdgeState


class Graph:
    """
    Attributes:
        nodes      : {node_id: Node}
        edges      : {edge_id: Edge}
        directed   : bool – graph-level directedness
        weighted   : bool – whether weights are meaningful
        _adj       : {node_id: [(neighbour_id, edge_id), …]}
    """

    def __init__(self, directed: bool = False, weighted: bool = True):
        self.nodes:    Dict[str, Node] = {}
        self.edges:    Dict[str, Edge] = {}
        self.directed: bool           = directed
        self.weighted: bool           = weighted
        self._adj:     Dict[str, List[Tuple[str, str]]] = {}   # node_id → [(nbr, edge_id)]

    # ==================================================================
    # NODE CRUD
    # ==================================================================
    def add_node(self, node: Node) -> Node:
        self.nodes[node.id] = node
        self._adj.setdefault(node.id, [])
        return node

    def create_node(self, x: float, y: float, label: Optional[str] = None, node_id: Optional[str] = None) -> Node:
        """Convenience: create + add in one call."""
        return self.add_node(Node(x=x, y=y, label=label, node_id=node_id))

    def remove_node(self, node_id: str) -> None:
        if node_id not in self.nodes:
            return
        # remove every edge touching this node
        edge_ids_to_remove = [eid for eid in self.edges if self.edges[eid].source == node_id or self.edges[eid].target == node_id]
        for eid in edge_ids_to_remove:
            self.remove_edge(eid)
        del self.nodes[node_id]
        self._adj.pop(node_id, None)

    def get_node(self, node_id: str) -> Optional[Node]:
        return self.nodes.get(node_id)

    # ==================================================================
    # EDGE CRUD
    # ==================================================================
    def add_edge(self, edge: Edge) -> Edge:
        self.edges[edge.id] = edge
        # maintain adjacency
        self._adj.setdefault(edge.source, []).append((edge.target, edge.id))
        if not edge.directed:
            self._adj.setdefault(edge.target, []).append((edge.source, edge.id))
        return edge

    def create_edge(self, source: str, target: str, weight: float = 1.0, edge_id: Optional[str] = None) -> Edge:
        return self.add_edge(Edge(source=source, target=target, weight=weight, directed=self.directed, edge_id=edge_id))

    def remove_edge(self, edge_id: str) -> None:
        if edge_id not in self.edges:
            return
        e = self.edges[edge_id]
        self._adj.get(e.source, [])[:] = [(n, eid) for n, eid in self._adj.get(e.source, []) if eid != edge_id]
        if not e.directed:
            self._adj.get(e.target, [])[:] = [(n, eid) for n, eid in self._adj.get(e.target, []) if eid != edge_id]
        del self.edges[edge_id]

    def get_edge(self, edge_id: str) -> Optional[Edge]:
        return self.edges.get(edge_id)

    def get_edge_between(self, a: str, b: str) -> Optional[Edge]:
        """First edge connecting a and b (direction-aware)."""
        for _, eid in self._adj.get(a, []):
            e = self.edges[eid]
            if e.target == b or (not e.directed and e.source == b):
                return e
        return None

    # ==================================================================
    # ADJACENCY QUERIES
    # ==================================================================
    def neighbours(self, node_id: str) -> List[Tuple[str, Edge]]:
        """Return [(neighbour_id, edge)] for every reachable neighbour."""
        result = []
        for nbr_id, eid in self._adj.get(node_id, []):
            result.append((nbr_id, self.edges[eid]))
        return result

    def edges_from(self, node_id: str) -> List[Edge]:
        return [self.edges[eid] for _, eid in self._adj.get(node_id, [])]

    def degree(self, node_id: str) -> int:
        return len(self._adj.get(node_id, []))

    # ==================================================================
    # RESET (keep structure, wipe algo state)
    # ==================================================================
    def reset_algo_state(self) -> None:
        for node in self.nodes.values():
            node.reset_algo_state()
        for edge in self.edges.values():
            edge.reset()

    def clear(self) -> None:
        self.nodes.clear()
        self.edges.clear()
        self._adj.clear()

    # ==================================================================
    # SERIALISATION
    # ==================================================================
    def to_dict(self) -> dict:
        return {
            "directed": self.directed,
            "weighted": self.weighted,
            "nodes":    [n.to_dict() for n in self.nodes.values()],
            "edges":    [e.to_dict() for e in self.edges.values()],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Graph":
        g = cls(directed=data.get("directed", False), weighted=data.get("weighted", True))
        for nd in data.get("nodes", []):
            g.add_node(Node.from_dict(nd))
        for ed in data.get("edges", []):
            g.add_edge(Edge.from_dict(ed))
        return g

    # ==================================================================
    # GENERATORS — Factory class-methods
    # ==================================================================

    # ---------- Random Graph ----------
    @classmethod
    def generate_random(
        cls,
        num_nodes: int = 10,
        edge_probability: float = 0.3,
        directed: bool = False,
        weighted: bool = True,
        weight_range: Tuple[int, int] = (1, 10),
        seed: Optional[int] = None,
        canvas_w: float = 800,
        canvas_h: float = 500,
    ) -> "Graph":
        """
        Erdős–Rényi style random graph.
        Each possible edge is included with probability `edge_probability`.
        """
        if seed is not None:
            random.seed(seed)

        g = cls(directed=directed, weighted=weighted)
        margin = 40

        # place nodes in a circle with jitter so it looks natural
        ids = []
        for i in range(num_nodes):
            angle  = 2 * math.pi * i / num_nodes
            radius = min(canvas_w, canvas_h) * 0.35
            cx, cy = canvas_w / 2, canvas_h / 2
            x = cx + radius * math.cos(angle) + random.uniform(-30, 30)
            y = cy + radius * math.sin(angle) + random.uniform(-30, 30)
            x = max(margin, min(canvas_w - margin, x))
            y = max(margin, min(canvas_h - margin, y))
            nid = str(i)
            g.create_node(x, y, label=nid, node_id=nid)
            ids.append(nid)

        # add edges
        for i in range(num_nodes):
            start = i + 1 if not directed else 0
            for j in (range(start, num_nodes) if not directed else range(num_nodes)):
                if i == j:
                    continue
                if random.random() < edge_probability:
                    w = random.randint(*weight_range) if weighted else 1
                    g.create_edge(ids[i], ids[j], weight=w)

        # guarantee connectivity: add a spanning-tree backbone
        shuffled = list(ids)
        random.shuffle(shuffled)
        for k in range(1, len(shuffled)):
            if not g.get_edge_between(shuffled[k - 1], shuffled[k]):
                w = random.randint(*weight_range) if weighted else 1
                g.create_edge(shuffled[k - 1], shuffled[k], weight=w)

        return g

    # ---------- Grid / Maze Graph ----------
    @classmethod
    def generate_grid(
        cls,
        rows: int = 6,
        cols: int = 8,
        directed: bool = False,
        weighted: bool = False,
        wall_prob: float = 0.25,
        seed: Optional[int] = None,
        canvas_w: float = 800,
        canvas_h: float = 500,
    ) -> "Graph":
        """
        2-D grid graph.  If wall_prob > 0 some nodes are pre-blocked → maze feel.
        Edges connect 4-neighbours (up / down / left / right).
        """
        if seed is not None:
            random.seed(seed)

        g = cls(directed=directed, weighted=weighted)

        pad_x = 50
        pad_y = 50
        cell_w = (canvas_w - 2 * pad_x) / max(cols - 1, 1)
        cell_h = (canvas_h - 2 * pad_y) / max(rows - 1, 1)

        # helper: (row, col) → node-id string
        def nid(r, c):
            return f"{r}_{c}"

        # create nodes
        for r in range(rows):
            for c in range(cols):
                x = pad_x + c * cell_w
                y = pad_y + r * cell_h
                node = g.create_node(x, y, label=nid(r, c), node_id=nid(r, c))
                # randomly block some interior nodes
                if r != 0 and r != rows - 1 and c != 0 and c != cols - 1:
                    if random.random() < wall_prob:
                        node.toggle_blocked()

        # create edges (4-connected)
        directions = [(0, 1), (1, 0)]   # right, down  (undirected covers both)
        if directed:
            directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]

        for r in range(rows):
            for c in range(cols):
                for dr, dc in directions:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        g.create_edge(nid(r, c), nid(nr, nc), weight=1)

        return g

    # ---------- Scale-Free (Barabási–Albert-ish) ----------
    @classmethod
    def generate_scale_free(
        cls,
        num_nodes: int = 15,
        m: int = 2,                     # edges added per new node
        directed: bool = False,
        weighted: bool = True,
        weight_range: Tuple[int, int] = (1, 10),
        seed: Optional[int] = None,
        canvas_w: float = 800,
        canvas_h: float = 500,
    ) -> "Graph":
        """
        Preferential-attachment model: new nodes connect to existing nodes
        proportional to their current degree → produces hub-and-spoke topology
        that mimics real-world networks (social, web, …).
        """
        if seed is not None:
            random.seed(seed)

        g = cls(directed=directed, weighted=weighted)
        margin = 50

        # seed with a small clique of m+1 nodes
        initial = min(m + 1, num_nodes)
        ids = []
        for i in range(initial):
            angle  = 2 * math.pi * i / initial
            r      = 60
            x      = canvas_w / 2 + r * math.cos(angle)
            y      = canvas_h / 2 + r * math.sin(angle)
            nid    = str(i)
            g.create_node(x, y, label=nid, node_id=nid)
            ids.append(nid)
        # clique edges
        for i in range(initial):
            for j in range(i + 1, initial):
                w = random.randint(*weight_range) if weighted else 1
                g.create_edge(ids[i], ids[j], weight=w)

        # degree list for preferential attachment sampling
        degrees = {nid: initial - 1 for nid in ids}   # clique → each has (initial-1) edges

        # grow
        for i in range(initial, num_nodes):
            # random position – slight spiral to spread things out
            angle = 2 * math.pi * i / 7
            rad   = 40 + i * 15
            x     = canvas_w / 2 + rad * math.cos(angle) + random.uniform(-20, 20)
            y     = canvas_h / 2 + rad * math.sin(angle) + random.uniform(-20, 20)
            x     = max(margin, min(canvas_w - margin, x))
            y     = max(margin, min(canvas_h - margin, y))
            nid   = str(i)
            g.create_node(x, y, label=nid, node_id=nid)
            ids.append(nid)
            degrees[nid] = 0

            # pick m targets via preferential attachment
            total_deg = sum(degrees.values()) or 1
            targets: Set[str] = set()
            attempts = 0
            while len(targets) < m and attempts < m * 20:
                r = random.random() * total_deg
                cumul = 0
                for cand, deg in degrees.items():
                    cumul += max(deg, 1)   # floor at 1 so isolated nodes can be picked
                    if cumul >= r:
                        if cand != nid:
                            targets.add(cand)
                        break
                attempts += 1

            for t in targets:
                w = random.randint(*weight_range) if weighted else 1
                g.create_edge(nid, t, weight=w)
                degrees[nid]  = degrees.get(nid, 0) + 1
                degrees[t]    = degrees.get(t, 0) + 1

        return g

    # ---------- Import from Adjacency List (text) ----------
    @classmethod
    def from_adjacency_list(
        cls,
        text: str,
        directed: bool = False,
        weighted: bool = True,
        canvas_w: float = 800,
        canvas_h: float = 500,
    ) -> "Graph":
        """
        Parse a simple text adjacency list.

        Supported formats (one node per line):
            A: B C D            → A connects to B, C, D  (weight 1)
            A: B(3) C(7)        → A→B weight 3, A→C weight 7
            0 → 1,2,3           → alternate arrow syntax
            0: 1(5), 2(3)       → comma-separated with weights

        Nodes are auto-laid-out in a circle.
        """
        g = cls(directed=directed, weighted=weighted)
        adjacency: Dict[str, List[Tuple[str, float]]] = {}

        for line in text.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # split on ':' or '→'
            if ":" in line:
                parts = line.split(":", 1)
            elif "→" in line:
                parts = line.split("→", 1)
            elif "->" in line:
                parts = line.split("->", 1)
            else:
                continue

            src = parts[0].strip()
            adjacency.setdefault(src, [])

            if len(parts) < 2 or not parts[1].strip():
                continue

            targets_raw = parts[1].strip().replace(",", " ").split()
            for token in targets_raw:
                token = token.strip()
                if not token:
                    continue
                # parse optional weight: "B(3)" or "B"
                if "(" in token and token.endswith(")"):
                    tgt, w_str = token[:-1].split("(", 1)
                    try:
                        w = float(w_str)
                    except ValueError:
                        w = 1.0
                else:
                    tgt = token
                    w   = 1.0
                adjacency.setdefault(tgt, [])
                adjacency[src].append((tgt, w))

        # collect all node labels
        all_labels = list(adjacency.keys())
        n = len(all_labels)
        if n == 0:
            return g

        # layout in a circle
        margin = 50
        cx, cy = canvas_w / 2, canvas_h / 2
        radius = min(canvas_w, canvas_h) * 0.35
        for i, label in enumerate(all_labels):
            angle = 2 * math.pi * i / n
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            g.create_node(x, y, label=label, node_id=label)

        # add edges (deduplicate for undirected)
        seen_edges: Set[frozenset] = set()
        for src, targets in adjacency.items():
            for tgt, w in targets:
                key = frozenset([src, tgt]) if not directed else (src, tgt)
                if key in seen_edges:
                    continue
                seen_edges.add(key)
                if not weighted:
                    w = 1.0
                g.create_edge(src, tgt, weight=w)

        return g

    # ---------- Import from Adjacency Matrix (text) ----------
    @classmethod
    def from_adjacency_matrix(
        cls,
        text: str,
        directed: bool = False,
        weighted: bool = True,
        labels: Optional[List[str]] = None,
        canvas_w: float = 800,
        canvas_h: float = 500,
    ) -> "Graph":
        """
        Parse a whitespace / comma-separated adjacency matrix.

        Example:
            0 4 0 0
            4 0 8 0
            0 8 0 7
            0 0 7 0

        0 / inf / -1 = no edge.  Any other value = weight.
        First row can optionally be node labels (if non-numeric).
        """
        g = cls(directed=directed, weighted=weighted)

        rows_raw = [r.strip() for r in text.strip().splitlines() if r.strip()]
        if not rows_raw:
            return g

        # detect if first row is labels
        first_tokens = rows_raw[0].replace(",", " ").split()
        try:
            [float(t) for t in first_tokens]
            has_label_row = False
        except ValueError:
            has_label_row = True

        if has_label_row:
            labels = first_tokens
            rows_raw = rows_raw[1:]

        # parse matrix
        matrix: List[List[float]] = []
        for row in rows_raw:
            vals = row.replace(",", " ").split()
            matrix.append([float(v) for v in vals])

        n = len(matrix)
        if labels is None:
            labels = [str(i) for i in range(n)]

        # layout circle
        cx, cy = canvas_w / 2, canvas_h / 2
        radius = min(canvas_w, canvas_h) * 0.35
        for i in range(n):
            angle = 2 * math.pi * i / n
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            g.create_node(x, y, label=labels[i], node_id=labels[i])

        # edges
        seen: Set = set()
        for i in range(n):
            for j in range(len(matrix[i])):
                val = matrix[i][j]
                if val == 0 or val == float("inf") or val == -1:
                    continue
                key = frozenset([i, j]) if not directed else (i, j)
                if key in seen:
                    continue
                seen.add(key)
                w = val if weighted else 1.0
                g.create_edge(labels[i], labels[j], weight=w)

        return g

    # ==================================================================
    # UTILITY
    # ==================================================================
    def node_count(self) -> int:
        return len(self.nodes)

    def edge_count(self) -> int:
        return len(self.edges)

    def has_negative_edges(self) -> bool:
        return any(e.weight < 0 for e in self.edges.values())

    def node_ids(self) -> List[str]:
        return list(self.nodes.keys())

    def __repr__(self) -> str:
        return f"Graph(nodes={self.node_count()}, edges={self.edge_count()}, directed={self.directed})"