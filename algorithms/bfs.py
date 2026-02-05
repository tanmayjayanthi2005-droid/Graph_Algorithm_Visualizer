"""
bfs.py — Breadth-First Search
==============================
Generator-based BFS.  Yields a Step at every meaningful event:
  1. Dequeue a node  →  mark it CURRENT
  2. Examine each neighbour  →  mark edge RELAXED
  3. Enqueue unseen neighbour  →  mark it FRONTIER
  4. Final step  →  reconstruct & highlight the shortest (hop-count) path

Pseudocode lines are 0-indexed and match the PSEUDOCODE constant
exported alongside the generator so the UI can highlight them live.

Skips blocked nodes transparently.
"""

from typing import Generator, Optional, List, Dict
from collections import deque

from graph import Graph
from algorithms.step import Step, StepBuilder


# ---------------------------------------------------------------------------
# Pseudocode — each string is one displayed line; index = pseudocode_line
# ---------------------------------------------------------------------------
PSEUDOCODE: List[str] = [
    "def BFS(graph, source, target):",          # 0
    "    queue ← [source]",                     # 1
    "    visited ← {source}",                   # 2
    "    parent ← {}",                          # 3
    "    while queue is not empty:",             # 4
    "        node ← queue.dequeue()",           # 5
    "        if node == target: return path",   # 6
    "        for neighbour in adj(node):",      # 7
    "            if neighbour not visited:",     # 8
    "                visited.add(neighbour)",   # 9
    "                parent[neighbour] = node", # 10
    "                queue.enqueue(neighbour)", # 11
    "    return NOT FOUND",                     # 12
]


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------
def bfs(
    graph: Graph,
    source: str,
    target: str,
) -> Generator[Step, None, None]:
    """
    Yields Step snapshots for every event during BFS execution.

    Args:
        graph  : The graph to search.
        source : Starting node id.
        target : Goal node id.

    Yields:
        Step – one per event (dequeue, neighbour-check, enqueue, path-found).
    """

    sb      = StepBuilder()
    step_no = 0
    queue   = deque([source])
    visited: set  = {source}
    parent:  Dict[str, Optional[str]] = {source: None}

    # --- initialisation step ---
    sb.set_current(source)
    sb.set_frontier([source])
    sb.pseudocode_line = 1
    sb.explanation = (
        f"Initialise: source node '{source}' is placed into the queue "
        f"and marked as visited. BFS explores layer by layer from here."
    )
    sb.overlay["queue"] = list(queue)
    yield sb.build(step_number=step_no)
    step_no += 1

    # --- main loop ---
    while queue:
        node = queue.popleft()

        # -- dequeue event --
        sb.reset()
        sb.visited_set      = list(visited)
        sb.set_current(node)
        sb.set_frontier(list(queue))
        sb.pseudocode_line  = 5
        sb.explanation      = (
            f"Dequeue node '{node}' — it is now the CURRENT node being expanded. "
            f"BFS always dequeues the node that was discovered earliest (FIFO)."
        )
        sb.overlay["queue"] = list(queue)
        yield sb.build(step_number=step_no)
        step_no += 1

        # -- target check --
        if node == target:
            path = _reconstruct(parent, target)
            sb.reset()
            sb.visited_set     = list(visited)
            sb.pseudocode_line = 6
            sb.set_path(path)
            sb.explanation     = (
                f"🎯 Target '{target}' reached! "
                f"The shortest path (by hop count) has {len(path)-1} edge(s): "
                f"{' → '.join(path)}"
            )
            # mark path edges
            for i in range(len(path) - 1):
                e = graph.get_edge_between(path[i], path[i + 1])
                if e:
                    sb.choose_edge(e.id)
            sb.overlay["queue"] = list(queue)
            yield sb.build(step_number=step_no, is_final=True)
            return

        # -- explore neighbours --
        for nbr, edge in graph.neighbours(node):
            # skip blocked
            nbr_node = graph.get_node(nbr)
            if nbr_node and nbr_node.blocked:
                continue

            # -- edge-examination step --
            sb_edge = StepBuilder()
            sb_edge.visited_set     = list(visited)
            sb_edge.set_current(node)
            sb_edge.set_frontier(list(queue))
            sb_edge.relax_edge(edge.id)
            sb_edge.pseudocode_line = 7

            if nbr in visited:
                sb_edge.explanation = (
                    f"Examine edge {node}→{nbr}: neighbour '{nbr}' already visited — skip."
                )
                sb_edge.edge_states[edge.id] = "ignored"
            else:
                sb_edge.explanation = (
                    f"Examine edge {node}→{nbr}: neighbour '{nbr}' is NEW — "
                    f"enqueue it and mark visited."
                )
            sb_edge.overlay["queue"] = list(queue)
            yield sb_edge.build(step_number=step_no)
            step_no += 1

            if nbr not in visited:
                visited.add(nbr)
                parent[nbr] = node
                queue.append(nbr)

                # -- enqueue event --
                sb_enq = StepBuilder()
                sb_enq.visited_set     = list(visited)
                sb_enq.set_current(node)
                sb_enq.set_frontier(list(queue))
                sb_enq.node_states[nbr] = "frontier"
                sb_enq.pseudocode_line = 11
                sb_enq.explanation     = (
                    f"Enqueue '{nbr}' (parent = '{node}'). "
                    f"It will be expanded after all nodes at the current depth."
                )
                sb_enq.overlay["queue"] = list(queue)
                yield sb_enq.build(step_number=step_no)
                step_no += 1

    # --- exhausted without finding target ---
    sb.reset()
    sb.visited_set     = list(visited)
    sb.pseudocode_line = 12
    sb.explanation     = (
        f"Queue is empty. Target '{target}' is NOT reachable from '{source}'."
    )
    sb.overlay["queue"] = []
    yield sb.build(step_number=step_no, is_final=True)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _reconstruct(parent: Dict[str, Optional[str]], target: str) -> List[str]:
    path = []
    cur: Optional[str] = target
    while cur is not None:
        path.append(cur)
        cur = parent.get(cur)
    path.reverse()
    return path
