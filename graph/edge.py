"""
edge.py — Graph Edge
====================
Connects two nodes. Carries an optional weight and its own visual state
so the renderer can colour-code edges as Relaxed / Chosen / Ignored
exactly as the algorithm touches them.

Design decisions:
  - `source` and `target` are node-id strings, NOT Node references.
    This keeps edges serialisable and avoids circular references.
  - Weight defaults to 1 for unweighted graphs — algorithms that ignore
    weights simply never read it.
  - `directed` is stored per-edge so a single Graph can technically mix,
    though in practice the Graph-level flag controls generation.
  - `meta` mirrors the Node pattern: algorithms can stash whatever they need.
"""

from enum import Enum
from typing import Optional, Dict, Any
import uuid


# ---------------------------------------------------------------------------
# Edge State Enum — visual encoding for the renderer
# ---------------------------------------------------------------------------
class EdgeState(Enum):
    DEFAULT  = "default"   # thin, neutral grey
    RELAXED  = "relaxed"   # amber pulse — "this edge was considered / relaxed"
    CHOSEN   = "chosen"    # bright green, thick — "this edge is on the best path"
    IGNORED  = "ignored"   # faded / dashed — "algorithm explicitly skipped this"
    ACTIVE   = "active"    # current-step highlight — the edge being traversed RIGHT NOW


# ---------------------------------------------------------------------------
# Edge
# ---------------------------------------------------------------------------
class Edge:
    """
    Attributes:
        id       : Unique identifier.
        source   : ID of the tail node.
        target   : ID of the head node.
        weight   : Numeric cost (default 1). Can be negative for Bellman-Ford demos.
        directed : If False, traversal works in both directions.
        state    : EdgeState for visual encoding.
        meta     : Free-form dict for algorithm data.
    """

    __slots__ = ("id", "source", "target", "weight", "directed", "state", "meta")

    def __init__(
        self,
        source: str,
        target: str,
        weight: float = 1.0,
        directed: bool = False,
        edge_id: Optional[str] = None,
    ):
        self.id:       str       = edge_id or str(uuid.uuid4())[:8]
        self.source:   str       = source
        self.target:   str       = target
        self.weight:   float     = weight
        self.directed: bool      = directed
        self.state:    EdgeState = EdgeState.DEFAULT
        self.meta:     Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def reset(self) -> None:
        """Wipe visual state between algorithm runs."""
        self.state = EdgeState.DEFAULT
        self.meta.clear()

    def connects(self, node_a: str, node_b: str) -> bool:
        """True if this edge links node_a ↔ node_b (respects directedness)."""
        if self.directed:
            return self.source == node_a and self.target == node_b
        return {self.source, self.target} == {node_a, node_b}

    def other_end(self, node_id: str) -> Optional[str]:
        """Given one endpoint, return the other. None if node_id isn't an endpoint."""
        if node_id == self.source:
            return self.target
        if node_id == self.target and not self.directed:
            return self.source
        if node_id == self.target and self.directed:
            return None          # can't traverse backwards on a directed edge
        return None

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "id":       self.id,
            "source":   self.source,
            "target":   self.target,
            "weight":   self.weight,
            "directed": self.directed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Edge":
        return cls(
            source=data["source"],
            target=data["target"],
            weight=data.get("weight", 1.0),
            directed=data.get("directed", False),
            edge_id=data.get("id"),
        )

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        arrow = " → " if self.directed else " ↔ "
        return f"Edge({self.source}{arrow}{self.target}, w={self.weight}, state={self.state.value})"

    def __eq__(self, other) -> bool:
        return isinstance(other, Edge) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)