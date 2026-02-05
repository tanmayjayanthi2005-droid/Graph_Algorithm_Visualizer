"""
step.py — Algorithm Step Snapshot
==================================
Every algorithm is a generator that yields Step objects.
A Step is a frozen-in-time picture of everything the visualizer
needs to render one frame:

    • Which nodes are visited / frontier / current / on-path
    • Which edges are relaxed / chosen / active
    • The current priority-queue or stack contents (for overlays)
    • The distance array (for the live distance panel)
    • Which line of pseudocode is executing right now
    • A plain-English explanation of *why* this step happened
      (Learning Mode reads this)

Design decisions:
  - Step is a plain dataclass (no methods that mutate the graph).
    It is a SNAPSHOT. The algorithm generator is the only writer;
    the stepper / renderer are pure readers.
  - `node_states` and `edge_states` are shallow dicts so the renderer
    can apply them in one pass without walking the whole graph.
  - `overlay` is a free-form dict so different algorithms can push
    whatever extra info they want (queue contents, relaxation detail, …).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass(frozen=True)
class Step:
    """
    Attributes:
        step_number     : 0-based index of this step in the run.
        current_node    : ID of the node being expanded / processed right now.
        current_edge    : ID of the edge being traversed right now (or None).
        node_states     : {node_id: state_string}  — only nodes that CHANGED.
        edge_states     : {edge_id: state_string}  — only edges that CHANGED.
        visited_set     : Set of node_ids fully processed so far.
        frontier        : List of node_ids currently in the queue / stack.
        path            : Ordered list of node_ids on the best path found so far (empty until done).
        distances       : {node_id: float} — current shortest-known distances (Dijkstra / A* / BF).
        pseudocode_line : 0-based index of the pseudocode line executing now.
        explanation     : Human-readable "why" text for Learning Mode.
        overlay         : Free-form dict for algo-specific overlay data:
                            • "queue"         – list of (node_id, priority) for PQ algos
                            • "stack"         – list of node_ids for DFS
                            • "relaxed_edge"  – (src, tgt, new_dist) just relaxed
                            • "matrix"        – current distance matrix for Floyd-Warshall
        metrics         : Running tally: nodes_visited, edges_relaxed, …
        is_final        : True on the very last step (path found or exhausted).
    """

    step_number:      int                          = 0
    current_node:     Optional[str]                = None
    current_edge:     Optional[str]                = None
    node_states:      Dict[str, str]               = field(default_factory=dict)
    edge_states:      Dict[str, str]               = field(default_factory=dict)
    visited_set:      List[str]                    = field(default_factory=list)
    frontier:         List[str]                    = field(default_factory=list)
    path:             List[str]                    = field(default_factory=list)
    distances:        Dict[str, float]             = field(default_factory=dict)
    pseudocode_line:  int                          = 0
    explanation:      str                          = ""
    overlay:          Dict[str, Any]               = field(default_factory=dict)
    metrics:          Dict[str, Any]               = field(default_factory=dict)
    is_final:         bool                         = False


# ---------------------------------------------------------------------------
# Convenience builder so algorithms don't have to spell out every kwarg
# ---------------------------------------------------------------------------
class StepBuilder:
    """
    Mutable scratch-pad that algorithms use to construct Steps cleanly.

    Usage inside an algorithm generator:
        sb = StepBuilder()
        sb.visit("A")
        sb.set_frontier(["B", "C"])
        sb.explanation = "Node A was dequeued because it had the smallest distance."
        yield sb.build(step_number=3)
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.current_node:     Optional[str]       = None
        self.current_edge:     Optional[str]       = None
        self.node_states:      Dict[str, str]      = {}
        self.edge_states:      Dict[str, str]      = {}
        self.visited_set:      List[str]           = []
        self.frontier:         List[str]           = []
        self.path:             List[str]           = []
        self.distances:        Dict[str, float]    = {}
        self.pseudocode_line:  int                 = 0
        self.explanation:      str                 = ""
        self.overlay:          Dict[str, Any]      = {}
        self.metrics:          Dict[str, Any]      = {"nodes_visited": 0, "edges_relaxed": 0, "path_length": 0}
        self.is_final:         bool                = False

    # -- helpers --
    def visit(self, node_id: str):
        self.node_states[node_id] = "visited"
        if node_id not in self.visited_set:
            self.visited_set.append(node_id)
        self.metrics["nodes_visited"] = len(self.visited_set)

    def set_current(self, node_id: str):
        self.current_node = node_id
        self.node_states[node_id] = "current"

    def set_frontier(self, nodes: List[str]):
        self.frontier = list(nodes)
        for n in nodes:
            if n not in self.node_states or self.node_states[n] == "unvisited":
                self.node_states[n] = "frontier"

    def relax_edge(self, edge_id: str):
        self.current_edge = edge_id
        self.edge_states[edge_id] = "relaxed"
        self.metrics["edges_relaxed"] = self.metrics.get("edges_relaxed", 0) + 1

    def choose_edge(self, edge_id: str):
        self.edge_states[edge_id] = "chosen"

    def set_path(self, path: List[str]):
        self.path = path
        self.metrics["path_length"] = len(path) - 1 if len(path) > 1 else 0
        for n in path:
            self.node_states[n] = "path"

    def build(self, step_number: int = 0, is_final: bool = False) -> Step:
        return Step(
            step_number=step_number,
            current_node=self.current_node,
            current_edge=self.current_edge,
            node_states=dict(self.node_states),
            edge_states=dict(self.edge_states),
            visited_set=list(self.visited_set),
            frontier=list(self.frontier),
            path=list(self.path),
            distances=dict(self.distances),
            pseudocode_line=self.pseudocode_line,
            explanation=self.explanation,
            overlay=dict(self.overlay),
            metrics=dict(self.metrics),
            is_final=is_final,
        )
