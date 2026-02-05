"""
dfs.py — Depth-First Search
=============================
Generator-based DFS using an explicit stack (no Python recursion limit issues).

Yields a Step at:
  1. Push source onto stack
  2. Pop a node  →  CURRENT
  3. Examine each neighbour  →  edge RELAXED / IGNORED
  4. Push unseen neighbour  →  FRONTIER
  5. Path found  →  reconstruct via parent map
  6. Stack empty  →  NOT FOUND

The overlay exposes the full stack at every step so the UI can render
the "recursion stack" panel.
"""

from typing import Generator, Optional, List, Dict

from graph import Graph
from algorithms.step import Step, StepBuilder


# ---------------------------------------------------------------------------
# Pseudocode
# ---------------------------------------------------------------------------
PSEUDOCODE: List[str] = [
    "def DFS(graph, source, target):",          # 0
    "    stack ← [source]",                     # 1
    "    visited ← {}",                         # 2
    "    parent ← {}",                          # 3
    "    while stack is not empty:",             # 4
    "        node ← stack.pop()",               # 5
    "        if node in visited: continue",     # 6
    "        visited.add(node)",                # 7
    "        if node == target: return path",   # 8
    "        for neighbour in adj(node):",      # 9
    "            if neighbour not visited:",     # 10
    "                parent[neighbour] = node", # 11
    "                stack.push(neighbour)",    # 12
    "    return NOT FOUND",                     # 13
]


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------
def dfs(
    graph: Graph,
    source: str,
    target: str,
) -> Generator[Step, None, None]:
    """
    Iterative DFS with parent tracking for path reconstruction.

    Note: iterative DFS with a simple stack can visit nodes in a different
    order than recursive DFS when a node is pushed multiple times before
    being popped.  We use the standard "mark on pop" strategy here because
    it keeps the generator simple and still finds a valid path.
    """

    sb      = StepBuilder()
    step_no = 0
    stack   = [source]
    visited: set  = set()
    parent:  Dict[str, Optional[str]] = {source: None}

    # --- init step ---
    sb.set_current(source)
    sb.set_frontier([source])
    sb.pseudocode_line = 1
    sb.explanation = (
        f"Initialise: push source '{source}' onto the stack. "
        f"DFS dives as deep as possible before backtracking."
    )
    sb.overlay["stack"] = list(stack)
    yield sb.build(step_number=step_no)
    step_no += 1

    # --- main loop ---
    while stack:
        node = stack.pop()

        # already visited (can happen because we mark-on-pop)
        if node in visited:
            sb2 = StepBuilder()
            sb2.visited_set     = list(visited)
            sb2.set_frontier([n for n in stack if n not in visited])
            sb2.pseudocode_line = 6
            sb2.explanation     = f"Pop '{node}' — already visited, skip."
            sb2.overlay["stack"] = list(stack)
            yield sb2.build(step_number=step_no)
            step_no += 1
            continue

        # -- pop & visit --
        visited.add(node)

        sb3 = StepBuilder()
        sb3.visited_set     = list(visited)
        sb3.set_current(node)
        sb3.visit(node)
        sb3.set_frontier([n for n in stack if n not in visited])
        sb3.pseudocode_line = 7
        sb3.explanation     = (
            f"Pop '{node}' from stack and mark VISITED. "
            f"DFS will now explore its neighbours before returning here."
        )
        sb3.overlay["stack"] = list(stack)
        yield sb3.build(step_number=step_no)
        step_no += 1

        # -- target check --
        if node == target:
            path = _reconstruct(parent, target)
            sb4 = StepBuilder()
            sb4.visited_set     = list(visited)
            sb4.pseudocode_line = 8
            sb4.set_path(path)
            sb4.explanation     = (
                f"🎯 Target '{target}' found! Path: {' → '.join(path)} "
                f"({len(path)-1} edge(s))."
            )
            for i in range(len(path) - 1):
                e = graph.get_edge_between(path[i], path[i + 1])
                if e:
                    sb4.choose_edge(e.id)
            sb4.overlay["stack"] = list(stack)
            yield sb4.build(step_number=step_no, is_final=True)
            return

        # -- explore neighbours --
        for nbr, edge in graph.neighbours(node):
            nbr_node = graph.get_node(nbr)
            if nbr_node and nbr_node.blocked:
                continue

            sb_e = StepBuilder()
            sb_e.visited_set     = list(visited)
            sb_e.set_current(node)
            sb_e.set_frontier([n for n in stack if n not in visited])
            sb_e.relax_edge(edge.id)
            sb_e.pseudocode_line = 9

            if nbr in visited:
                sb_e.edge_states[edge.id] = "ignored"
                sb_e.explanation = f"Edge {node}→{nbr}: '{nbr}' already visited — ignore."
            else:
                sb_e.explanation = f"Edge {node}→{nbr}: '{nbr}' unseen — push onto stack."
            sb_e.overlay["stack"] = list(stack)
            yield sb_e.build(step_number=step_no)
            step_no += 1

            if nbr not in visited:
                if nbr not in parent:
                    parent[nbr] = node
                stack.append(nbr)

                sb_p = StepBuilder()
                sb_p.visited_set     = list(visited)
                sb_p.set_current(node)
                sb_p.set_frontier([n for n in stack if n not in visited])
                sb_p.node_states[nbr] = "frontier"
                sb_p.pseudocode_line = 12
                sb_p.explanation     = f"Push '{nbr}' onto stack (parent = '{node}')."
                sb_p.overlay["stack"] = list(stack)
                yield sb_p.build(step_number=step_no)
                step_no += 1

    # --- not found ---
    sb_fin = StepBuilder()
    sb_fin.visited_set     = list(visited)
    sb_fin.pseudocode_line = 13
    sb_fin.explanation     = f"Stack empty. '{target}' not reachable from '{source}'."
    sb_fin.overlay["stack"] = []
    yield sb_fin.build(step_number=step_no, is_final=True)


# ---------------------------------------------------------------------------
def _reconstruct(parent: Dict[str, Optional[str]], target: str) -> List[str]:
    path, cur = [], target
    while cur is not None:
        path.append(cur)
        cur = parent.get(cur)
    path.reverse()
    return path
