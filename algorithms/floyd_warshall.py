"""
floyd_warshall.py — Floyd–Warshall (All-Pairs Shortest Paths)
===============================================================
The signature "matrix algorithm".  The overlay exposes the full NxN
distance matrix at every step so the UI can render it as a live grid —
the single most important visual for understanding Floyd-Warshall.

Structure:
  for k in nodes:          ← "intermediate" node
      for i in nodes:
          for j in nodes:
              if dist[i][k] + dist[k][j] < dist[i][j]:
                  dist[i][j] = dist[i][k] + dist[k][j]

Yields a Step for:
  1. Initialisation (adjacency → matrix)
  2. Each (i, j) relaxation that actually changes the matrix
  3. End of each k-round (summary)
  4. Final: extract path for the user's chosen source→target pair

Because Floyd-Warshall is O(V³) and generates a LOT of steps, we
offer a "condensed" mode that only yields on actual updates + round
boundaries, keeping the step count manageable for the UI.
"""

from typing import Generator, List, Dict, Optional

from graph import Graph
from algorithms.step import Step, StepBuilder


# ---------------------------------------------------------------------------
# Pseudocode
# ---------------------------------------------------------------------------
PSEUDOCODE: List[str] = [
    "def FloydWarshall(graph):",                   # 0
    "    dist ← adjacency matrix",                 # 1
    "    next ← initialise next-hop matrix",       # 2
    "    for k in 0 … n-1:",                       # 3
    "        for i in 0 … n-1:",                   # 4
    "            for j in 0 … n-1:",               # 5
    "                if dist[i][k]+dist[k][j]",    # 6
    "                      < dist[i][j]:",         # 7
    "                    dist[i][j] = …",          # 8
    "                    next[i][j] = next[i][k]", # 9
    "    return dist, next",                       # 10
]


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------
def floyd_warshall(
    graph: Graph,
    source: str,
    target: str,
) -> Generator[Step, None, None]:
    """
    source / target are only used at the END to extract the specific
    path the user cares about.  The algorithm itself computes ALL pairs.
    """

    INF     = float("inf")
    step_no = 0

    # ordered list of node ids (stable iteration order)
    nodes   = sorted(graph.nodes.keys())
    n       = len(nodes)
    idx     = {nid: i for i, nid in enumerate(nodes)}   # id → matrix index

    # --- initialise dist & next matrices ---
    dist: List[List[float]] = [[INF] * n for _ in range(n)]
    nxt:  List[List[Optional[int]]] = [[None] * n for _ in range(n)]

    for i in range(n):
        dist[i][i] = 0
        nxt[i][i]  = i

    for edge in graph.edges.values():
        u = idx.get(edge.source)
        v = idx.get(edge.target)
        if u is None or v is None:
            continue
        # skip blocked
        u_node = graph.get_node(edge.source)
        v_node = graph.get_node(edge.target)
        if (u_node and u_node.blocked) or (v_node and v_node.blocked):
            continue

        if edge.weight < dist[u][v]:
            dist[u][v] = edge.weight
            nxt[u][v]  = v
        if not edge.directed:
            if edge.weight < dist[v][u]:
                dist[v][u] = edge.weight
                nxt[v][u]  = u

    # -- init step --
    sb = StepBuilder()
    sb.pseudocode_line = 1
    sb.explanation = (
        f"Floyd-Warshall: initialise {n}×{n} distance matrix from adjacency. "
        f"Diagonal = 0, direct edges = weight, rest = ∞."
    )
    sb.overlay["matrix"]      = _matrix_snapshot(dist, nodes)
    sb.overlay["k"]           = -1
    sb.overlay["nodes"]       = nodes
    yield sb.build(step_number=step_no)
    step_no += 1

    # ==============================================================
    # MAIN TRIPLE LOOP
    # ==============================================================
    for k in range(n):
        updates_this_round = 0

        # -- k-round start --
        sb_ks = StepBuilder()
        sb_ks.pseudocode_line = 3
        sb_ks.set_current(nodes[k])
        sb_ks.explanation = (
            f"── k = {nodes[k]} ── Allow paths through '{nodes[k]}' as intermediate."
        )
        sb_ks.overlay["matrix"] = _matrix_snapshot(dist, nodes)
        sb_ks.overlay["k"]      = nodes[k]
        sb_ks.overlay["nodes"]  = nodes
        yield sb_ks.build(step_number=step_no)
        step_no += 1

        for i in range(n):
            if dist[i][k] == INF:
                continue          # optimisation: skip entire row
            for j in range(n):
                if i == j:
                    continue
                if dist[k][j] == INF:
                    continue

                new_dist = dist[i][k] + dist[k][j]

                if new_dist < dist[i][j]:
                    old_dist    = dist[i][j]
                    dist[i][j]  = new_dist
                    nxt[i][j]   = nxt[i][k]
                    updates_this_round += 1

                    # -- relaxation step (only on actual updates) --
                    sb_r = StepBuilder()
                    sb_r.set_current(nodes[k])
                    sb_r.pseudocode_line = 8
                    sb_r.explanation = (
                        f"Update dist[{nodes[i]}][{nodes[j]}]: "
                        f"via {nodes[k]}: {dist[i][k]} + {dist[k][j]} = {new_dist} "
                        f"< {old_dist if old_dist != INF else '∞'}"
                    )
                    # highlight the two nodes involved
                    sb_r.node_states[nodes[i]] = "frontier"
                    sb_r.node_states[nodes[j]] = "frontier"
                    sb_r.node_states[nodes[k]] = "current"
                    # highlight edges i→k and k→j if they exist
                    e1 = graph.get_edge_between(nodes[i], nodes[k])
                    e2 = graph.get_edge_between(nodes[k], nodes[j])
                    if e1:
                        sb_r.relax_edge(e1.id)
                    if e2:
                        sb_r.relax_edge(e2.id)
                    sb_r.overlay["matrix"]       = _matrix_snapshot(dist, nodes)
                    sb_r.overlay["k"]            = nodes[k]
                    sb_r.overlay["nodes"]        = nodes
                    sb_r.overlay["highlight_cell"] = (nodes[i], nodes[j])
                    yield sb_r.build(step_number=step_no)
                    step_no += 1

        # -- k-round end --
        sb_ke = StepBuilder()
        sb_ke.pseudocode_line = 3
        sb_ke.explanation = (
            f"Round k={nodes[k]} complete: {updates_this_round} update(s)."
        )
        sb_ke.overlay["matrix"] = _matrix_snapshot(dist, nodes)
        sb_ke.overlay["k"]      = nodes[k]
        sb_ke.overlay["nodes"]  = nodes
        yield sb_ke.build(step_number=step_no)
        step_no += 1

    # ==============================================================
    # EXTRACT PATH for source → target
    # ==============================================================
    si = idx.get(source)
    ti = idx.get(target)

    if si is None or ti is None or dist[si][ti] == INF:
        sb_nf = StepBuilder()
        sb_nf.pseudocode_line = 10
        sb_nf.explanation     = f"All pairs computed. '{target}' not reachable from '{source}'."
        sb_nf.overlay["matrix"] = _matrix_snapshot(dist, nodes)
        sb_nf.overlay["nodes"]  = nodes
        yield sb_nf.build(step_number=step_no, is_final=True)
        return

    # reconstruct via next-hop matrix
    path = _reconstruct_path(nxt, si, ti, nodes)

    sb_fin = StepBuilder()
    sb_fin.pseudocode_line = 10
    sb_fin.set_path(path)
    sb_fin.explanation = (
        f"✅ All-pairs done. Shortest {source}→{target}: "
        f"{' → '.join(path)}, cost = {dist[si][ti]}."
    )
    for i in range(len(path) - 1):
        e = graph.get_edge_between(path[i], path[i + 1])
        if e:
            sb_fin.choose_edge(e.id)
    sb_fin.overlay["matrix"] = _matrix_snapshot(dist, nodes)
    sb_fin.overlay["nodes"]  = nodes
    yield sb_fin.build(step_number=step_no, is_final=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _matrix_snapshot(dist: List[List[float]], nodes: List[str]) -> List[Dict]:
    """Serialise the matrix for the overlay in a renderer-friendly format."""
    rows = []
    for i, row in enumerate(dist):
        rows.append({
            "label": nodes[i],
            "values": [v if v != float("inf") else "∞" for v in row],
        })
    return rows


def _reconstruct_path(
    nxt: List[List[Optional[int]]],
    si: int,
    ti: int,
    nodes: List[str],
) -> List[str]:
    if nxt[si][ti] is None:
        return []
    path = [nodes[si]]
    cur  = si
    safety = len(nodes) + 1   # prevent infinite loop on bad data
    while cur != ti and safety > 0:
        cur = nxt[cur][ti]
        if cur is None:
            break
        path.append(nodes[cur])
        safety -= 1
    return path
