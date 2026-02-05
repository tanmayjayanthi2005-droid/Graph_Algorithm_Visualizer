"""
bellman_ford.py — Bellman–Ford Algorithm
=========================================
The only single-source shortest-path algorithm that handles NEGATIVE edge
weights (but not negative cycles).

Structure:
  • V-1 rounds of relaxing every edge in the graph.
  • A V-th "detector" round that flags negative cycles.

Yields a Step for:
  1. Each successful relaxation (dist improved)
  2. Each failed relaxation (no improvement — shown as IGNORED)
  3. End-of-round summary
  4. Negative-cycle detection (if found)
  5. Final path reconstruction

Overlay:
  • "round"            – current round number (1-indexed)
  • "distances"        – full distance map
  • "negative_cycle"   – True/False after detector round
"""

from typing import Generator, Optional, List, Dict

from graph import Graph
from algorithms.step import Step, StepBuilder


# ---------------------------------------------------------------------------
# Pseudocode
# ---------------------------------------------------------------------------
PSEUDOCODE: List[str] = [
    "def BellmanFord(graph, source):",             # 0
    "    dist ← {v: ∞ for v in V}",                # 1
    "    dist[source] ← 0",                        # 2
    "    parent ← {}",                             # 3
    "    for i in 1 … |V|-1:",                     # 4
    "        for each edge (u, v, w):",            # 5
    "            if dist[u] + w < dist[v]:",       # 6
    "                dist[v] ← dist[u] + w",       # 7
    "                parent[v] = u",               # 8
    "    // negative-cycle check:",                # 9
    "    for each edge (u, v, w):",                # 10
    "        if dist[u] + w < dist[v]:",           # 11
    "            return NEGATIVE CYCLE",           # 12
    "    return dist, parent",                     # 13
]


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------
def bellman_ford(
    graph: Graph,
    source: str,
    target: str,
) -> Generator[Step, None, None]:

    INF     = float("inf")
    step_no = 0
    V       = graph.node_count()

    dist:   Dict[str, float]          = {nid: INF for nid in graph.nodes}
    parent: Dict[str, Optional[str]]  = {}
    dist[source] = 0.0

    # collect all edges as (src, tgt, weight, edge_obj) — include reverse for undirected
    all_edges: List = []
    for edge in graph.edges.values():
        all_edges.append((edge.source, edge.target, edge.weight, edge))
        if not edge.directed:
            all_edges.append((edge.target, edge.source, edge.weight, edge))

    # -- init step --
    sb = StepBuilder()
    sb.set_current(source)
    sb.distances        = dict(dist)
    sb.pseudocode_line  = 2
    sb.explanation      = (
        f"Bellman-Ford init: dist['{source}'] = 0, all others = ∞. "
        f"Will run {V-1} relaxation rounds over all {len(all_edges)} directed edges."
    )
    sb.overlay["round"]     = 0
    sb.overlay["distances"] = dict(dist)
    yield sb.build(step_number=step_no)
    step_no += 1

    # ==============================================================
    # MAIN ROUNDS
    # ==============================================================
    for round_idx in range(1, V):                  # rounds 1 … V-1

        any_relaxed = False

        # -- round-start step --
        sb_rs = StepBuilder()
        sb_rs.distances        = dict(dist)
        sb_rs.pseudocode_line  = 4
        sb_rs.explanation      = f"── Round {round_idx} of {V-1}: scan all edges ──"
        sb_rs.overlay["round"]     = round_idx
        sb_rs.overlay["distances"] = dict(dist)
        yield sb_rs.build(step_number=step_no)
        step_no += 1

        for u, v, w, edge_obj in all_edges:
            # skip blocked
            u_node = graph.get_node(u)
            v_node = graph.get_node(v)
            if (u_node and u_node.blocked) or (v_node and v_node.blocked):
                continue

            if dist[u] == INF:
                continue   # can't relax from an unreachable node

            new_dist = dist[u] + w

            sb_e = StepBuilder()
            sb_e.set_current(u)
            sb_e.relax_edge(edge_obj.id)
            sb_e.distances        = dict(dist)
            sb_e.pseudocode_line  = 6
            sb_e.overlay["round"]     = round_idx
            sb_e.overlay["distances"] = dict(dist)

            if new_dist < dist[v]:
                dist[v]   = new_dist
                parent[v] = u
                any_relaxed = True
                sb_e.distances = dict(dist)     # update snapshot
                sb_e.node_states[v] = "frontier"
                sb_e.explanation = (
                    f"Relax {u}→{v} (w={w}): {dist[u]} + {w} = {new_dist} "
                    f"< old {dist[v] if dist[v] != new_dist else '∞'} → UPDATE dist[{v}] = {new_dist}"
                )
                sb_e.overlay["distances"] = dict(dist)
            else:
                sb_e.edge_states[edge_obj.id] = "ignored"
                sb_e.explanation = (
                    f"Edge {u}→{v} (w={w}): {dist[u]} + {w} = {new_dist} "
                    f"≥ {dist[v]} — no change."
                )

            yield sb_e.build(step_number=step_no)
            step_no += 1

        # -- round-end summary --
        sb_re = StepBuilder()
        sb_re.distances        = dict(dist)
        sb_re.pseudocode_line  = 4
        sb_re.overlay["round"]     = round_idx
        sb_re.overlay["distances"] = dict(dist)
        if not any_relaxed:
            sb_re.explanation = (
                f"Round {round_idx}: no relaxation occurred → distances converged early! "
                f"Remaining rounds can be skipped."
            )
            # early termination
            yield sb_re.build(step_number=step_no)
            step_no += 1
            break
        else:
            sb_re.explanation = f"Round {round_idx} complete."
            yield sb_re.build(step_number=step_no)
            step_no += 1

    # ==============================================================
    # NEGATIVE-CYCLE DETECTOR (round V)
    # ==============================================================
    sb_det = StepBuilder()
    sb_det.distances        = dict(dist)
    sb_det.pseudocode_line  = 10
    sb_det.explanation      = "Negative-cycle detector round: one more pass over all edges…"
    sb_det.overlay["round"]     = V
    sb_det.overlay["distances"] = dict(dist)
    yield sb_det.build(step_number=step_no)
    step_no += 1

    negative_cycle = False
    for u, v, w, edge_obj in all_edges:
        u_node = graph.get_node(u)
        v_node = graph.get_node(v)
        if (u_node and u_node.blocked) or (v_node and v_node.blocked):
            continue
        if dist[u] == INF:
            continue
        if dist[u] + w < dist[v]:
            negative_cycle = True
            sb_nc = StepBuilder()
            sb_nc.distances        = dict(dist)
            sb_nc.pseudocode_line  = 12
            sb_nc.explanation      = (
                f"⚠️ NEGATIVE CYCLE detected via edge {u}→{v} (w={w}): "
                f"dist[{u}]+{w} = {dist[u]+w} < dist[{v}]={dist[v]}. "
                f"Shortest paths are undefined!"
            )
            sb_nc.overlay["negative_cycle"] = True
            sb_nc.overlay["distances"]      = dict(dist)
            yield sb_nc.build(step_number=step_no, is_final=True)
            return

    # ==============================================================
    # PATH RECONSTRUCTION
    # ==============================================================
    if dist[target] == INF:
        sb_nf = StepBuilder()
        sb_nf.distances        = dict(dist)
        sb_nf.pseudocode_line  = 13
        sb_nf.explanation      = f"No negative cycle, but '{target}' is unreachable (dist = ∞)."
        sb_nf.overlay["negative_cycle"] = False
        sb_nf.overlay["distances"]      = dict(dist)
        yield sb_nf.build(step_number=step_no, is_final=True)
        return

    path = _reconstruct(parent, target)
    sb_fin = StepBuilder()
    sb_fin.distances        = dict(dist)
    sb_fin.pseudocode_line  = 13
    sb_fin.set_path(path)
    sb_fin.explanation      = (
        f"✅ No negative cycle. Shortest path to '{target}': "
        f"{' → '.join(path)}, cost = {dist[target]}."
    )
    for i in range(len(path) - 1):
        e = graph.get_edge_between(path[i], path[i + 1])
        if e:
            sb_fin.choose_edge(e.id)
    sb_fin.overlay["negative_cycle"] = False
    sb_fin.overlay["distances"]      = dict(dist)
    yield sb_fin.build(step_number=step_no, is_final=True)


# ---------------------------------------------------------------------------
def _reconstruct(parent: Dict[str, Optional[str]], target: str) -> List[str]:
    path, cur = [], target
    while cur is not None:
        path.append(cur)
        cur = parent.get(cur)
    path.reverse()
    return path
