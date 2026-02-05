from enum import Enum
from typing import Optional, Tuple, Dict, Any
import uuid


# ---------------------------------------------------------------------------
# Node State Enum — maps 1-to-1 with the visual encoding palette
# ---------------------------------------------------------------------------
class NodeState(Enum):
    UNVISITED  = "unvisited"   # default grey
    FRONTIER   = "frontier"    # blue / amber — "seen but not yet processed"
    VISITED    = "visited"     # green — "fully processed"
    CURRENT    = "current"     # bright highlight — the node being expanded RIGHT NOW
    PATH       = "path"        # gold — on the shortest / final reconstructed path
    BLOCKED    = "blocked"     # dark red — user-placed obstacle
    SOURCE     = "source"      # distinct teal — start node
    TARGET     = "target"      # distinct magenta — goal node


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------
class Node:
    """
    Immutable identity (id, label), mutable position and algorithm state.

    Attributes:
        id       : Unique identifier (uuid string by default, or user-supplied).
        label    : Human-readable name shown on the canvas.
        x, y     : Canvas coordinates (floats, 0-1 normalised OR pixel — caller decides).
        state    : Current NodeState for visual encoding.
        blocked  : Boolean obstacle flag (independent of state).
        meta     : Dict for algorithm-specific data:
                       • dist      – current shortest-known distance
                       • parent    – node-id of predecessor on best path
                       • g, h, f   – A* / greedy scores
                       • visited_order – integer, the order in which algo visited this node
    """

    __slots__ = ("id", "label", "x", "y", "state", "blocked", "meta", "_created_at")

    def __init__(
        self,
        x: float = 0.0,
        y: float = 0.0,
        label: Optional[str] = None,
        node_id: Optional[str] = None,
    ):
        self.id: str            = node_id or str(uuid.uuid4())[:8]
        self.label: str         = label or self.id
        self.x: float           = x
        self.y: float           = y
        self.state: NodeState   = NodeState.UNVISITED
        self.blocked: bool      = False
        self.meta: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # State helpers (used heavily by algorithms + renderer)
    # ------------------------------------------------------------------
    def reset(self) -> None:
        """Wipe algorithm state back to defaults — called between runs."""
        self.state = NodeState.UNVISITED
        self.blocked = False          # keep obstacles across reset? caller decides
        self.meta.clear()

    def reset_algo_state(self) -> None:
        """Softer reset: keep blocked flag, clear only algorithm metadata."""
        self.state = NodeState.UNVISITED
        self.meta.clear()

    def mark_visited(self, order: int) -> None:
        self.state = NodeState.VISITED
        self.meta["visited_order"] = order

    def mark_frontier(self) -> None:
        self.state = NodeState.FRONTIER

    def mark_current(self) -> None:
        self.state = NodeState.CURRENT

    def mark_path(self) -> None:
        self.state = NodeState.PATH

    def set_source(self) -> None:
        self.state = NodeState.SOURCE

    def set_target(self) -> None:
        self.state = NodeState.TARGET

    def toggle_blocked(self) -> None:
        self.blocked = not self.blocked
        if self.blocked:
            self.state = NodeState.BLOCKED

    # ------------------------------------------------------------------
    # Distance / A* helpers (read from meta, never crash on missing keys)
    # ------------------------------------------------------------------
    @property
    def dist(self) -> float:
        return self.meta.get("dist", float("inf"))

    @dist.setter
    def dist(self, value: float):
        self.meta["dist"] = value

    @property
    def parent(self) -> Optional[str]:
        return self.meta.get("parent")

    @parent.setter
    def parent(self, node_id: Optional[str]):
        self.meta["parent"] = node_id

    @property
    def g(self) -> float:         # cost from source
        return self.meta.get("g", float("inf"))

    @g.setter
    def g(self, value: float):
        self.meta["g"] = value

    @property
    def h(self) -> float:         # heuristic estimate to target
        return self.meta.get("h", float("inf"))

    @h.setter
    def h(self, value: float):
        self.meta["h"] = value

    @property
    def f(self) -> float:         # f = g + h
        return self.meta.get("f", float("inf"))

    @f.setter
    def f(self, value: float):
        self.meta["f"] = value

    # ------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------
    def distance_to(self, other: "Node") -> float:
        """Euclidean distance — used as default heuristic in A*."""
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

    # ------------------------------------------------------------------
    # Serialisation  (for save / export / import)
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "id":      self.id,
            "label":   self.label,
            "x":       self.x,
            "y":       self.y,
            "blocked": self.blocked,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Node":
        node = cls(x=data["x"], y=data["y"], label=data.get("label"), node_id=data["id"])
        node.blocked = data.get("blocked", False)
        if node.blocked:
            node.state = NodeState.BLOCKED
        return node

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return f"Node(id={self.id}, label={self.label}, state={self.state.value}, pos=({self.x:.2f},{self.y:.2f}))"

    def __eq__(self, other) -> bool:
        return isinstance(other, Node) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)