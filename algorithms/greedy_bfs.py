"""
greedy_bfs.py — Greedy Best-First Search
==========================================
Expands the node with the smallest h(n) — pure heuristic, zero regard
for the actual cost incurred so far.

This is intentionally SUBOPTIMAL.  The teaching value is showing the
user exactly how and when greedy fails vs A*.  Every explanation
explicitly flags "greedy doesn't care about g" moments.

Shares the same heuristic catalogue as A* (manhattan / euclidean / …).

Overlay:
  • "queue"  – [(h, node_id)] priority queue
  • "scores" – [{node, h, note}]  (note flags suboptimality)
"""

import heapq, math
from typing import Generator, Optional, List, Dict, Callable

from graph import Graph, Node
from algorithms.step import Step, StepBuilder
from algorithms.astar import HEURISTICS, euclidean


# ---------------------------------------------------------------------------
# Pseudocode
# ---------------------------------------------------------------------------
PSEUDOCODE: List[str] = [
    "def GreedyBFS(graph, source, target, h):",    # 0
    "    open_set ← [(h(source), source)]",        # 1
    "    visited ← {}",                            # 2
    "    parent ← {}",                             # 3
    "    while open_set:",                          # 4
    "        (_, node) ← open_set.pop_min()",      # 5
    "        if node in visited: continue",        # 6
    "        visited.add(node)",                   # 7
    "        if node == target: return path",      # 8
    "        for (nbr, _) in adj(node):",          # 9
    "            if nbr not in visited:",           # 10
    "                parent[nbr] = node",          # 11
    "                open_set.push((h(nbr), nbr))",# 12
    "    return NOT FOUND",                        # 13
]


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------
def greedy_bfs(
    graph: Graph,
    source: str,
    target: str,
    heuristic: str = "euclidean",
) -> Generator[Step, None, None]:

    h_fn      = HEURISTICS.get(heuristic, euclidean)
    tgt_node  = graph.get_node(target)
    src_node  = graph.get_node(source)

    step_no   = 0
    visited:  set                        = set()
    parent:   Dict[str, Optional[str]]   = {source: None}
    h_cache:  Dict[str, float]           = {}

    def _h(nid: str) -> float:
        if nid not in h_cache:
            n = graph.get_node(nid)
            h_cache[nid] = h_fn(n, tgt_node) if n and tgt_node else 0.0
        return h_cache[nid]

    open_set = [(_h(source), source)]

    # -- init --
    sb = StepBuilder()
    sb.set_current(source)
    sb.pseudocode_line = 1
    sb.explanation = (
        f"Greedy Best-First: only h matters — no g cost at all! "
        f"h('{source}') = {_h(source):.2f} using {heuristic}."
    )
    sb.overlay["queue"]  = [(h, n) for h, n in open_set]
    sb.overlay["scores"] = [{"node": source, "h": _h(source)}]
    yield sb.build(step_number=step_no)
    step_no += 1

    # --- main loop ---
    while open_set:
        _, node = heapq.heappop(open_set)

        if node in visited:
            continue

        visited.add(node)

        # -- pop event --
        sb2 = StepBuilder()
        sb2.visited_set     = list(visited)
        sb2.set_current(node)
        sb2.visit(node)
        sb2.set_frontier([n for _, n in open_set if n not in visited])
        sb2.pseudocode_line = 7
        sb2.explanation     = (
            f"Pop '{node}' (h={_h(node):.2f}). "
            f"⚠️ Greedy chose this purely because h is smallest — "
            f"actual path cost is IGNORED."
        )
        sb2.overlay["queue"]  = [(h, n) for h, n in open_set if n not in visited]
        sb2.overlay["scores"] = [{"node": n, "h": _h(n)} for n in visited]
        yield sb2.build(step_number=step_no)
        step_no += 1

        # -- target check --
        if node == target:
            path = _reconstruct(parent, target)
            sb3 = StepBuilder()
            sb3.visited_set     = list(visited)
            sb3.pseudocode_line = 8
            sb3.set_path(path)
            sb3.explanation     = (
                f"🎯 Target found! Path: {' → '.join(path)} ({len(path)-1} edges). "
                f"⚠️ Note: this path may NOT be optimal — greedy ignores edge costs."
            )
            for i in range(len(path) - 1):
                e = graph.get_edge_between(path[i], path[i + 1])
                if e:
                    sb3.choose_edge(e.id)
            yield sb3.build(step_number=step_no, is_final=True)
            return

        # -- neighbours --
        for nbr, edge in graph.neighbours(node):
            nbr_node = graph.get_node(nbr)
            if nbr_node and nbr_node.blocked:
                continue
            if nbr in visited:
                continue

            heapq.heappush(open_set, (_h(nbr), nbr))
            if nbr not in parent:
                parent[nbr] = node

            sb_e = StepBuilder()
            sb_e.visited_set     = list(visited)
            sb_e.set_current(node)
            sb_e.relax_edge(edge.id)
            sb_e.node_states[nbr] = "frontier"
            sb_e.pseudocode_line = 12
            sb_e.explanation     = (
                f"Push '{nbr}' (h={_h(nbr):.2f}). "
                f"Greedy will pick whichever neighbour has lowest h next — "
                f"edge weight {edge.weight} is irrelevant here."
            )
            sb_e.overlay["queue"] = [(h, n) for h, n in open_set if n not in visited]
            yield sb_e.build(step_number=step_no)
            step_no += 1

    # --- not found ---
    sb_fin = StepBuilder()
    sb_fin.visited_set     = list(visited)
    sb_fin.pseudocode_line = 13
    sb_fin.explanation     = "Open set empty — target not reachable."
    yield sb_fin.build(step_number=step_no, is_final=True)


# ---------------------------------------------------------------------------
def _reconstruct(parent: Dict[str, Optional[str]], target: str) -> List[str]:
    path, cur = [], target
    while cur is not None:
        path.append(cur)
        cur = parent.get(cur)
    path.reverse()
    return path
