"""
dijkstra.py — Dijkstra's Shortest-Path Algorithm
==================================================
Generator-based Dijkstra using a min-heap (heapq).

Yields a Step at:
  1. Initialise distances / push source
  2. Pop minimum-distance node  →  CURRENT
  3. Each neighbour relaxation attempt  →  edge RELAXED or IGNORED
  4. Successful relaxation  →  update distance, enqueue
  5. Target popped  →  path found, reconstruct
  6. Heap empty  →  NOT REACHABLE

Overlay exposes:
  • "queue"  – [(node_id, dist)] priority queue snapshot
  • "distances" – full current distance map

Correctness note: Dijkstra requires non-negative weights.
The caller (or the UI) should warn / block if negative edges exist.
"""

import heapq
from typing import Generator, Optional, List, Dict

from graph import Graph
from algorithms.step import Step, StepBuilder


# ---------------------------------------------------------------------------
# Pseudocode
# ---------------------------------------------------------------------------
PSEUDOCODE: List[str] = [
    "def Dijkstra(graph, source, target):",        # 0
    "    dist ← {v: ∞ for v in V}",                # 1
    "    dist[source] ← 0",                        # 2
    "    pq ← [(0, source)]",                      # 3
    "    parent ← {}",                             # 4
    "    while pq is not empty:",                   # 5
    "        (d, node) ← pq.pop_min()",            # 6
    "        if d > dist[node]: continue",         # 7
    "        if node == target: return path",      # 8
    "        for (neighbour, w) in adj(node):",    # 9
    "            new_dist ← dist[node] + w",       # 10
    "            if new_dist < dist[neighbour]:",  # 11
    "                dist[neighbour] ← new_dist",  # 12
    "                parent[neighbour] = node",    # 13
    "                pq.push((new_dist, nbr))",    # 14
    "    return NOT FOUND",                        # 15
]


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------
def dijkstra(
    graph: Graph,
    source: str,
    target: str,
) -> Generator[Step, None, None]:

    INF     = float("inf")
    step_no = 0

    # initialise
    dist:   Dict[str, float]            = {nid: INF for nid in graph.nodes}
    parent: Dict[str, Optional[str]]    = {}
    dist[source] = 0.0
    pq = [(0.0, source)]                # min-heap: (distance, node_id)
    visited: set = set()

    # --- init step ---
    sb = StepBuilder()
    sb.set_current(source)
    sb.distances        = dict(dist)
    sb.pseudocode_line  = 2
    sb.explanation      = (
        f"Initialise: all distances = ∞ except source '{source}' = 0. "
        f"Push source into the priority queue."
    )
    sb.overlay["queue"]     = [(d, n) for d, n in pq]
    sb.overlay["distances"] = dict(dist)
    yield sb.build(step_number=step_no)
    step_no += 1

    # --- main loop ---
    while pq:
        d, node = heapq.heappop(pq)

        # stale entry
        if d > dist[node]:
            sb_stale = StepBuilder()
            sb_stale.visited_set     = list(visited)
            sb_stale.distances       = dict(dist)
            sb_stale.pseudocode_line = 7
            sb_stale.explanation     = (
                f"Pop (dist={d}, '{node}') — stale entry (current best = {dist[node]}). Skip."
            )
            sb_stale.overlay["queue"]     = [(dd, n) for dd, n in pq]
            sb_stale.overlay["distances"] = dict(dist)
            yield sb_stale.build(step_number=step_no)
            step_no += 1
            continue

        visited.add(node)

        # -- pop event --
        sb2 = StepBuilder()
        sb2.visited_set     = list(visited)
        sb2.set_current(node)
        sb2.visit(node)
        sb2.set_frontier([n for _, n in pq if n not in visited])
        sb2.distances       = dict(dist)
        sb2.pseudocode_line = 6
        sb2.explanation     = (
            f"Pop '{node}' with distance {d} — smallest in the priority queue. "
            f"This distance is now FINAL (Dijkstra guarantee)."
        )
        sb2.overlay["queue"]     = [(dd, n) for dd, n in pq]
        sb2.overlay["distances"] = dict(dist)
        yield sb2.build(step_number=step_no)
        step_no += 1

        # -- target check --
        if node == target:
            path = _reconstruct(parent, target)
            sb3 = StepBuilder()
            sb3.visited_set     = list(visited)
            sb3.distances       = dict(dist)
            sb3.pseudocode_line = 8
            sb3.set_path(path)
            sb3.explanation     = (
                f"🎯 Target '{target}' popped! Shortest distance = {dist[target]}. "
                f"Path: {' → '.join(path)}"
            )
            for i in range(len(path) - 1):
                e = graph.get_edge_between(path[i], path[i + 1])
                if e:
                    sb3.choose_edge(e.id)
            sb3.overlay["queue"]     = [(dd, n) for dd, n in pq]
            sb3.overlay["distances"] = dict(dist)
            yield sb3.build(step_number=step_no, is_final=True)
            return

        # -- relax neighbours --
        for nbr, edge in graph.neighbours(node):
            nbr_node = graph.get_node(nbr)
            if nbr_node and nbr_node.blocked:
                continue
            if nbr in visited:
                # already finalised — show as ignored
                sb_ig = StepBuilder()
                sb_ig.visited_set     = list(visited)
                sb_ig.set_current(node)
                sb_ig.distances       = dict(dist)
                sb_ig.edge_states[edge.id] = "ignored"
                sb_ig.pseudocode_line = 9
                sb_ig.explanation     = f"Edge {node}→{nbr} (w={edge.weight}): '{nbr}' already finalised — skip."
                sb_ig.overlay["queue"]     = [(dd, n) for dd, n in pq]
                sb_ig.overlay["distances"] = dict(dist)
                yield sb_ig.build(step_number=step_no)
                step_no += 1
                continue

            new_dist = dist[node] + edge.weight

            # -- relaxation attempt step --
            sb_r = StepBuilder()
            sb_r.visited_set     = list(visited)
            sb_r.set_current(node)
            sb_r.set_frontier([n for _, n in pq if n not in visited])
            sb_r.relax_edge(edge.id)
            sb_r.distances       = dict(dist)
            sb_r.pseudocode_line = 10

            if new_dist < dist[nbr]:
                sb_r.explanation = (
                    f"Relax {node}→{nbr}: {dist[node]} + {edge.weight} = {new_dist} "
                    f"< current {dist[nbr]} → UPDATE!"
                )
                dist[nbr]   = new_dist
                parent[nbr] = node
                heapq.heappush(pq, (new_dist, nbr))
                sb_r.distances = dict(dist)
                sb_r.node_states[nbr] = "frontier"
            else:
                sb_r.explanation = (
                    f"Edge {node}→{nbr}: {dist[node]} + {edge.weight} = {new_dist} "
                    f"≥ current {dist[nbr]} → no improvement."
                )
                sb_r.edge_states[edge.id] = "ignored"

            sb_r.overlay["queue"]     = [(dd, n) for dd, n in pq]
            sb_r.overlay["distances"] = dict(dist)
            yield sb_r.build(step_number=step_no)
            step_no += 1

    # --- not found ---
    sb_fin = StepBuilder()
    sb_fin.visited_set     = list(visited)
    sb_fin.distances       = dict(dist)
    sb_fin.pseudocode_line = 15
    sb_fin.explanation     = f"Priority queue empty. '{target}' is not reachable."
    sb_fin.overlay["queue"]     = []
    sb_fin.overlay["distances"] = dict(dist)
    yield sb_fin.build(step_number=step_no, is_final=True)


# ---------------------------------------------------------------------------
def _reconstruct(parent: Dict[str, Optional[str]], target: str) -> List[str]:
    path, cur = [], target
    while cur is not None:
        path.append(cur)
        cur = parent.get(cur)
    path.reverse()
    return path
