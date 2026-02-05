"""
algorithms/__init__.py — Algorithm Registry
=============================================
Single source of truth for every algorithm the visualizer knows about.

    from algorithms import REGISTRY, get_algorithm

REGISTRY is a dict:
    {
        "bfs": AlgoInfo(name, label, fn, pseudocode, tags, supports_negative, …),
        …
    }

AlgoInfo is a lightweight dataclass.  The engine and UI both consume it
so adding a new algorithm is literally: write the generator, add one
entry here.  That's the plugin system.
"""

from dataclasses import dataclass, field
from typing import Callable, List, Dict, Optional

# ---------------------------------------------------------------------------
# Import all algorithm modules
# ---------------------------------------------------------------------------
from algorithms.bfs              import bfs              as _bfs,              PSEUDOCODE as _bfs_pc
from algorithms.dfs              import dfs              as _dfs,              PSEUDOCODE as _dfs_pc
from algorithms.dijkstra         import dijkstra         as _dijkstra,         PSEUDOCODE as _dij_pc
from algorithms.astar            import astar            as _astar,            PSEUDOCODE as _ast_pc
from algorithms.bidirectional_bfs import bidirectional_bfs as _bibfs,          PSEUDOCODE as _bibfs_pc
from algorithms.bellman_ford     import bellman_ford     as _bf,               PSEUDOCODE as _bf_pc
from algorithms.floyd_warshall   import floyd_warshall   as _fw,               PSEUDOCODE as _fw_pc
from algorithms.greedy_bfs       import greedy_bfs       as _gbfs,             PSEUDOCODE as _gbfs_pc


# ---------------------------------------------------------------------------
# AlgoInfo — metadata card for each algorithm
# ---------------------------------------------------------------------------
@dataclass
class AlgoInfo:
    key:               str                    # registry key, e.g. "bfs"
    label:             str                    # human label, e.g. "Breadth-First Search"
    fn:                Callable               # the generator function
    pseudocode:        List[str]              # lines for the side-panel
    tags:              List[str] = field(default_factory=list)   # e.g. ["unweighted", "shortest-path"]
    supports_negative: bool     = False       # can handle negative edges?
    is_all_pairs:      bool     = False       # Floyd-Warshall style?
    has_heuristic:     bool     = False       # A* / Greedy — expose heuristic selector?
    complexity_time:   str      = ""          # e.g. "O(V + E)"
    complexity_space:  str      = ""          # e.g. "O(V)"
    description:       str      = ""          # one-liner for the UI card


# ---------------------------------------------------------------------------
# THE REGISTRY
# ---------------------------------------------------------------------------
REGISTRY: Dict[str, AlgoInfo] = {

    "bfs": AlgoInfo(
        key="bfs", label="Breadth-First Search", fn=_bfs, pseudocode=_bfs_pc,
        tags=["unweighted", "shortest-path", "traversal"],
        complexity_time="O(V + E)", complexity_space="O(V)",
        description="Explores layer-by-layer. Finds shortest path by hop count.",
    ),

    "dfs": AlgoInfo(
        key="dfs", label="Depth-First Search", fn=_dfs, pseudocode=_dfs_pc,
        tags=["unweighted", "traversal"],
        complexity_time="O(V + E)", complexity_space="O(V)",
        description="Dives deep before backtracking. Does NOT guarantee shortest path.",
    ),

    "dijkstra": AlgoInfo(
        key="dijkstra", label="Dijkstra's Algorithm", fn=_dijkstra, pseudocode=_dij_pc,
        tags=["weighted", "shortest-path"],
        complexity_time="O((V + E) log V)", complexity_space="O(V)",
        description="Greedily expands the closest node. Optimal for non-negative weights.",
    ),

    "astar": AlgoInfo(
        key="astar", label="A* Search", fn=_astar, pseudocode=_ast_pc,
        tags=["weighted", "shortest-path", "heuristic"],
        has_heuristic=True,
        complexity_time="O((V + E) log V)", complexity_space="O(V)",
        description="Dijkstra + heuristic guidance. Optimal when h is admissible.",
    ),

    "bidirectional_bfs": AlgoInfo(
        key="bidirectional_bfs", label="Bidirectional BFS", fn=_bibfs, pseudocode=_bibfs_pc,
        tags=["unweighted", "shortest-path", "bidirectional"],
        complexity_time="O(b^(d/2))", complexity_space="O(b^(d/2))",
        description="Two frontiers from source & target. Meets in the middle — explores far fewer nodes.",
    ),

    "bellman_ford": AlgoInfo(
        key="bellman_ford", label="Bellman–Ford", fn=_bf, pseudocode=_bf_pc,
        tags=["weighted", "shortest-path", "negative-edges"],
        supports_negative=True,
        complexity_time="O(V · E)", complexity_space="O(V)",
        description="Handles negative edges. Detects negative cycles. Slower than Dijkstra.",
    ),

    "floyd_warshall": AlgoInfo(
        key="floyd_warshall", label="Floyd–Warshall", fn=_fw, pseudocode=_fw_pc,
        tags=["weighted", "all-pairs", "negative-edges"],
        supports_negative=True, is_all_pairs=True,
        complexity_time="O(V³)", complexity_space="O(V²)",
        description="All-pairs shortest paths via dynamic programming. Watch the matrix evolve!",
    ),

    "greedy_bfs": AlgoInfo(
        key="greedy_bfs", label="Greedy Best-First", fn=_gbfs, pseudocode=_gbfs_pc,
        tags=["heuristic", "suboptimal"],
        has_heuristic=True,
        complexity_time="O((V + E) log V)", complexity_space="O(V)",
        description="Pure heuristic — fast but NOT optimal. Compare with A* to see the difference!",
    ),
}


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------
def get_algorithm(key: str) -> Optional[AlgoInfo]:
    """Return AlgoInfo by key, or None."""
    return REGISTRY.get(key)


def list_algorithms() -> List[AlgoInfo]:
    """Return all registered algorithms in insertion order."""
    return list(REGISTRY.values())


def algorithms_by_tag(tag: str) -> List[AlgoInfo]:
    """Filter registry by tag."""
    return [a for a in REGISTRY.values() if tag in a.tags]


__all__ = [
    "AlgoInfo",
    "REGISTRY",
    "get_algorithm",
    "list_algorithms",
    "algorithms_by_tag",
]
