"""
astar.py — A* Search
=====================
Generator-based A* with a pluggable heuristic function.

Ships three built-in heuristics:
  • manhattan   – |Δx| + |Δy|          (admissible on 4-connected grids)
  • euclidean   – √(Δx² + Δy²)        (admissible everywhere)
  • octile      – max(|Δx|,|Δy|) + (√2-1)·min(|Δx|,|Δy|)
  • custom      – caller supplies a callable(node, target) → float

The overlay exposes g, h, f for every node that has been touched,
which the Heuristic Playground panel uses to teach admissibility.

Yields same event types as Dijkstra, plus heuristic-specific explanations.
"""

import heapq, math
from typing import Generator, Optional, List, Dict, Callable

from graph import Graph, Node
from algorithms.step import Step, StepBuilder


# ---------------------------------------------------------------------------
# Built-in heuristics  (all take two Node objects, return float)
# ---------------------------------------------------------------------------
def manhattan(a: Node, b: Node) -> float:
    return abs(a.x - b.x) + abs(a.y - b.y)

def euclidean(a: Node, b: Node) -> float:
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)

def octile(a: Node, b: Node) -> float:
    dx = abs(a.x - b.x)
    dy = abs(a.y - b.y)
    return max(dx, dy) + (math.sqrt(2) - 1) * min(dx, dy)

def zero(a: Node, b: Node) -> float:
    """h=0 → A* degrades to Dijkstra.  Useful for teaching."""
    return 0.0

HEURISTICS: Dict[str, Callable[[Node, Node], float]] = {
    "manhattan": manhattan,
    "euclidean": euclidean,
    "octile":    octile,
    "zero":      zero,            # "what if h = 0?" → becomes Dijkstra
}


# ---------------------------------------------------------------------------
# Pseudocode
# ---------------------------------------------------------------------------
PSEUDOCODE: List[str] = [
    "def AStar(graph, source, target, h):",        # 0
    "    g[source] ← 0",                           # 1
    "    f[source] ← h(source, target)",           # 2
    "    open_set ← [(f[source], source)]",        # 3
    "    parent ← {}",                             # 4
    "    while open_set:",                          # 5
    "        (_, node) ← open_set.pop_min()",      # 6
    "        if node == target: return path",      # 7
    "        closed.add(node)",                    # 8
    "        for (nbr, w) in adj(node):",          # 9
    "            tentative_g ← g[node] + w",       # 10
    "            if tentative_g < g[nbr]:",        # 11
    "                parent[nbr] = node",          # 12
    "                g[nbr] ← tentative_g",        # 13
    "                f[nbr] ← g[nbr] + h(nbr)",   # 14
    "                open_set.push((f[nbr], nbr))",# 15
    "    return NOT FOUND",                        # 16
]


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------
def astar(
    graph: Graph,
    source: str,
    target: str,
    heuristic: str = "euclidean",
) -> Generator[Step, None, None]:
    """
    Args:
        graph     : The graph.
        source    : Start node id.
        target    : Goal node id.
        heuristic : Key into HEURISTICS dict, or "euclidean" default.
    """

    h_fn = HEURISTICS.get(heuristic, euclidean)
    target_node = graph.get_node(target)

    INF     = float("inf")
    step_no = 0

    g_score: Dict[str, float]          = {nid: INF for nid in graph.nodes}
    f_score: Dict[str, float]          = {nid: INF for nid in graph.nodes}
    parent: Dict[str, Optional[str]]   = {}
    closed: set                        = set()

    src_node = graph.get_node(source)
    g_score[source] = 0.0
    h_val          = h_fn(src_node, target_node) if src_node and target_node else 0.0
    f_score[source] = h_val
    open_set       = [(f_score[source], source)]

    # --- init step ---
    sb = StepBuilder()
    sb.set_current(source)
    sb.distances        = {"g": dict(g_score), "h": {source: h_val}, "f": dict(f_score)}
    sb.pseudocode_line  = 2
    sb.explanation      = (
        f"A* init: g(source)=0, h(source)={h_val:.2f} (using {heuristic}), "
        f"f(source)={h_val:.2f}. Push into open set."
    )
    sb.overlay["queue"]     = [(f, n) for f, n in open_set]
    sb.overlay["heuristic"] = heuristic
    sb.overlay["scores"]    = _scores_snapshot(g_score, f_score, {source: h_val})
    yield sb.build(step_number=step_no)
    step_no += 1

    h_cache: Dict[str, float] = {source: h_val}   # cache h values

    # --- main loop ---
    while open_set:
        _, node = heapq.heappop(open_set)

        if node in closed:
            continue

        closed.add(node)

        # -- pop event --
        sb2 = StepBuilder()
        sb2.visited_set     = list(closed)
        sb2.set_current(node)
        sb2.visit(node)
        sb2.set_frontier([n for _, n in open_set if n not in closed])
        sb2.pseudocode_line = 6
        sb2.explanation     = (
            f"Pop '{node}': g={g_score[node]:.2f}, h={h_cache.get(node,0):.2f}, "
            f"f={f_score[node]:.2f}. Expand neighbours."
        )
        sb2.overlay["queue"]  = [(f, n) for f, n in open_set if n not in closed]
        sb2.overlay["scores"] = _scores_snapshot(g_score, f_score, h_cache)
        yield sb2.build(step_number=step_no)
        step_no += 1

        # -- target check --
        if node == target:
            path = _reconstruct(parent, target)
            sb3 = StepBuilder()
            sb3.visited_set     = list(closed)
            sb3.pseudocode_line = 7
            sb3.set_path(path)
            total_cost = g_score[target]
            sb3.explanation     = (
                f"🎯 Target '{target}' reached! Optimal cost = {total_cost:.2f}. "
                f"Path: {' → '.join(path)}"
            )
            for i in range(len(path) - 1):
                e = graph.get_edge_between(path[i], path[i + 1])
                if e:
                    sb3.choose_edge(e.id)
            sb3.overlay["scores"] = _scores_snapshot(g_score, f_score, h_cache)
            yield sb3.build(step_number=step_no, is_final=True)
            return

        # -- relax neighbours --
        node_obj = graph.get_node(node)
        for nbr, edge in graph.neighbours(node):
            nbr_node = graph.get_node(nbr)
            if nbr_node and nbr_node.blocked:
                continue
            if nbr in closed:
                continue

            tentative_g = g_score[node] + edge.weight

            # compute / cache h
            if nbr not in h_cache and nbr_node and target_node:
                h_cache[nbr] = h_fn(nbr_node, target_node)

            sb_r = StepBuilder()
            sb_r.visited_set     = list(closed)
            sb_r.set_current(node)
            sb_r.set_frontier([n for _, n in open_set if n not in closed])
            sb_r.relax_edge(edge.id)
            sb_r.pseudocode_line = 10

            if tentative_g < g_score[nbr]:
                g_score[nbr] = tentative_g
                f_score[nbr] = tentative_g + h_cache.get(nbr, 0.0)
                parent[nbr]  = node
                heapq.heappush(open_set, (f_score[nbr], nbr))
                sb_r.node_states[nbr] = "frontier"
                sb_r.explanation = (
                    f"Relax {node}→{nbr}: g={tentative_g:.2f}, "
                    f"h={h_cache.get(nbr,0):.2f}, f={f_score[nbr]:.2f} — UPDATE!"
                )
            else:
                sb_r.edge_states[edge.id] = "ignored"
                sb_r.explanation = (
                    f"Edge {node}→{nbr}: tentative g={tentative_g:.2f} ≥ "
                    f"current g={g_score[nbr]:.2f} — no improvement."
                )

            sb_r.overlay["queue"]  = [(f, n) for f, n in open_set if n not in closed]
            sb_r.overlay["scores"] = _scores_snapshot(g_score, f_score, h_cache)
            yield sb_r.build(step_number=step_no)
            step_no += 1

    # --- not found ---
    sb_fin = StepBuilder()
    sb_fin.visited_set     = list(closed)
    sb_fin.pseudocode_line = 16
    sb_fin.explanation     = f"Open set empty. '{target}' not reachable."
    sb_fin.overlay["scores"] = _scores_snapshot(g_score, f_score, h_cache)
    yield sb_fin.build(step_number=step_no, is_final=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _scores_snapshot(g: Dict, f: Dict, h: Dict) -> List[Dict]:
    """Return a list of {node, g, h, f} dicts for the overlay panel."""
    nodes = set(g.keys()) | set(f.keys()) | set(h.keys())
    return [
        {"node": n, "g": g.get(n, float("inf")), "h": h.get(n, 0), "f": f.get(n, float("inf"))}
        for n in sorted(nodes)
    ]

def _reconstruct(parent: Dict[str, Optional[str]], target: str) -> List[str]:
    path, cur = [], target
    while cur is not None:
        path.append(cur)
        cur = parent.get(cur)
    path.reverse()
    return path
