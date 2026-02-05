"""
bidirectional_bfs.py — Bidirectional BFS
==========================================
Two BFS frontiers expand simultaneously — one from the source, one from
the target.  The search terminates the moment the two frontiers collide.

Visual encoding:
  • Forward-frontier nodes  →  "frontier"  (blue)
  • Backward-frontier nodes →  "frontier_b" (orange)  — renderer maps this
  • Meeting node            →  "path"

Overlay exposes:
  • "queue_forward"  – current forward queue
  • "queue_backward" – current backward queue

This is the canonical way to show WHY bidirectional search explores
far fewer nodes than single-source BFS on large graphs.
"""

from typing import Generator, Optional, List, Dict, Set
from collections import deque

from graph import Graph
from algorithms.step import Step, StepBuilder


# ---------------------------------------------------------------------------
# Pseudocode
# ---------------------------------------------------------------------------
PSEUDOCODE: List[str] = [
    "def BidiBFS(graph, source, target):",         # 0
    "    qF ← [source];  visitedF ← {source}",    # 1
    "    qB ← [target];  visitedB ← {target}",    # 2
    "    parentF, parentB ← {}, {}",               # 3
    "    while qF or qB:",                         # 4
    "        if qF:",                              # 5
    "            expand one layer of qF",          # 6
    "            if frontier intersects visitedB:", # 7
    "                reconstruct & return path",   # 8
    "        if qB:",                              # 9
    "            expand one layer of qB",          # 10
    "            if frontier intersects visitedF:", # 11
    "                reconstruct & return path",   # 12
    "    return NOT FOUND",                        # 13
]


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------
def bidirectional_bfs(
    graph: Graph,
    source: str,
    target: str,
) -> Generator[Step, None, None]:

    step_no = 0

    # forward state
    qF:       deque          = deque([source])
    visitedF: Set[str]       = {source}
    parentF:  Dict[str, Optional[str]] = {source: None}

    # backward state
    qB:       deque          = deque([target])
    visitedB: Set[str]       = {target}
    parentB:  Dict[str, Optional[str]] = {target: None}

    # -- init step --
    sb = StepBuilder()
    sb.node_states[source] = "source"
    sb.node_states[target] = "target"
    sb.pseudocode_line = 1
    sb.explanation = (
        f"Bidirectional BFS: launch two frontiers — "
        f"forward from '{source}' and backward from '{target}'."
    )
    sb.overlay["queue_forward"]  = list(qF)
    sb.overlay["queue_backward"] = list(qB)
    yield sb.build(step_number=step_no)
    step_no += 1

    # helper: check collision after expanding
    def find_meeting(expanded_set: Set[str], other_visited: Set[str]) -> Optional[str]:
        intersection = expanded_set & other_visited
        return next(iter(intersection)) if intersection else None

    # --- main loop (layer-by-layer) ---
    while qF or qB:

        # ============================================================
        # FORWARD EXPANSION — one full layer
        # ============================================================
        if qF:
            layer_size = len(qF)
            new_frontier_f: Set[str] = set()

            for _ in range(layer_size):
                node = qF.popleft()

                # -- dequeue step --
                sb2 = StepBuilder()
                sb2.visited_set = list(visitedF)
                sb2.set_current(node)
                sb2.visit(node)
                sb2.pseudocode_line = 6
                sb2.explanation = f"[Forward] Expand '{node}'."
                # colour backward frontier differently
                for n in visitedB:
                    if n not in visitedF:
                        sb2.node_states[n] = "frontier_b"
                sb2.overlay["queue_forward"]  = list(qF)
                sb2.overlay["queue_backward"] = list(qB)
                yield sb2.build(step_number=step_no)
                step_no += 1

                for nbr, edge in graph.neighbours(node):
                    nbr_node = graph.get_node(nbr)
                    if nbr_node and nbr_node.blocked:
                        continue

                    sb_e = StepBuilder()
                    sb_e.visited_set = list(visitedF)
                    sb_e.set_current(node)
                    sb_e.relax_edge(edge.id)
                    sb_e.pseudocode_line = 6
                    for n in visitedB:
                        if n not in visitedF:
                            sb_e.node_states[n] = "frontier_b"

                    if nbr not in visitedF:
                        visitedF.add(nbr)
                        parentF[nbr] = node
                        qF.append(nbr)
                        new_frontier_f.add(nbr)
                        sb_e.node_states[nbr] = "frontier"
                        sb_e.explanation = f"[Fwd] Edge {node}→{nbr}: enqueue '{nbr}'."
                    else:
                        sb_e.edge_states[edge.id] = "ignored"
                        sb_e.explanation = f"[Fwd] Edge {node}→{nbr}: already visited."

                    sb_e.overlay["queue_forward"]  = list(qF)
                    sb_e.overlay["queue_backward"] = list(qB)
                    yield sb_e.build(step_number=step_no)
                    step_no += 1

            # collision check
            meeting = find_meeting(new_frontier_f, visitedB)
            if meeting:
                path = _build_path(parentF, parentB, meeting)
                yield from _final_step(step_no, path, graph, visitedF, visitedB)
                return

        # ============================================================
        # BACKWARD EXPANSION — one full layer
        # ============================================================
        if qB:
            layer_size = len(qB)
            new_frontier_b: Set[str] = set()

            for _ in range(layer_size):
                node = qB.popleft()

                sb3 = StepBuilder()
                sb3.visited_set = list(visitedB)
                sb3.set_current(node)
                sb3.node_states[node] = "visited"
                sb3.pseudocode_line = 10
                sb3.explanation = f"[Backward] Expand '{node}'."
                for n in visitedF:
                    sb3.node_states[n] = "visited"
                sb3.overlay["queue_forward"]  = list(qF)
                sb3.overlay["queue_backward"] = list(qB)
                yield sb3.build(step_number=step_no)
                step_no += 1

                for nbr, edge in graph.neighbours(node):
                    nbr_node = graph.get_node(nbr)
                    if nbr_node and nbr_node.blocked:
                        continue

                    sb_e2 = StepBuilder()
                    sb_e2.visited_set = list(visitedB)
                    sb_e2.set_current(node)
                    sb_e2.relax_edge(edge.id)
                    sb_e2.pseudocode_line = 10
                    for n in visitedF:
                        sb_e2.node_states[n] = "visited"

                    if nbr not in visitedB:
                        visitedB.add(nbr)
                        parentB[nbr] = node
                        qB.append(nbr)
                        new_frontier_b.add(nbr)
                        sb_e2.node_states[nbr] = "frontier_b"
                        sb_e2.explanation = f"[Bwd] Edge {node}→{nbr}: enqueue '{nbr}'."
                    else:
                        sb_e2.edge_states[edge.id] = "ignored"
                        sb_e2.explanation = f"[Bwd] Edge {node}→{nbr}: already visited."

                    sb_e2.overlay["queue_forward"]  = list(qF)
                    sb_e2.overlay["queue_backward"] = list(qB)
                    yield sb_e2.build(step_number=step_no)
                    step_no += 1

            # collision check
            meeting = find_meeting(new_frontier_b, visitedF)
            if meeting:
                path = _build_path(parentF, parentB, meeting)
                yield from _final_step(step_no, path, graph, visitedF, visitedB)
                return

    # --- not found ---
    sb_fin = StepBuilder()
    sb_fin.visited_set     = list(visitedF | visitedB)
    sb_fin.pseudocode_line = 13
    sb_fin.explanation     = "Both frontiers exhausted — target not reachable."
    yield sb_fin.build(step_number=step_no, is_final=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _build_path(
    parentF: Dict[str, Optional[str]],
    parentB: Dict[str, Optional[str]],
    meeting: str,
) -> List[str]:
    # forward half: meeting → source (reversed)
    fwd, cur = [], meeting
    while cur is not None:
        fwd.append(cur)
        cur = parentF.get(cur)
    fwd.reverse()

    # backward half: meeting → target
    bwd, cur = [], parentB.get(meeting)   # skip meeting (already in fwd)
    while cur is not None:
        bwd.append(cur)
        cur = parentB.get(cur)

    return fwd + bwd


def _final_step(step_no, path, graph, visitedF, visitedB):
    sb = StepBuilder()
    sb.visited_set = list(visitedF | visitedB)
    sb.set_path(path)
    sb.pseudocode_line = 8
    sb.explanation = (
        f"🎯 Frontiers met at '{path[len(path)//2] if path else '?'}'! "
        f"Path: {' → '.join(path)} ({len(path)-1} edges). "
        f"Total nodes explored: {len(visitedF | visitedB)} "
        f"(vs potentially {len(visitedF | visitedB)*2} with single BFS)."
    )
    for i in range(len(path) - 1):
        e = graph.get_edge_between(path[i], path[i + 1])
        if e:
            sb.choose_edge(e.id)
    yield sb.build(step_number=step_no, is_final=True)
