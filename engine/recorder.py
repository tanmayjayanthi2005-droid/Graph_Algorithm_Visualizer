"""
recorder.py — Run Recorder & Analytics
========================================
Records a complete algorithm run (all Steps), then computes the
analytics metrics the UI needs for the Analytics panel and Comparison
Mode.

Usage:
    rec = Recorder()
    rec.start(algo_key="dijkstra", source="A", target="F", graph=g)
    rec.run_to_completion()          # exhausts the generator
    metrics = rec.get_metrics()      # the analytics card
    rec.export()                     # serialisable snapshot for save/replay

Comparison Mode:
    The UI holds two Recorders (one per algo), runs both to completion
    on the SAME graph, then calls compare(rec1, rec2) → ComparisonResult.
"""

import time
import sys
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from graph import Graph
from algorithms import get_algorithm, AlgoInfo
from algorithms.step import Step
from engine.stepper import Stepper


# ---------------------------------------------------------------------------
# Metrics dataclass — what the Analytics panel renders
# ---------------------------------------------------------------------------
@dataclass
class RunMetrics:
    algo_key:        str   = ""
    algo_label:      str   = ""
    source:          str   = ""
    target:          str   = ""
    nodes_visited:   int   = 0
    edges_relaxed:   int   = 0
    path_length:     int   = 0          # number of edges on the final path
    path_cost:       float = 0.0        # total weight of the final path
    total_steps:     int   = 0          # number of Steps yielded
    wall_time_ms:    float = 0.0        # wall-clock time to run to completion
    memory_bytes:    int   = 0          # approx peak memory (via sys.getsizeof on step buffer)
    path_found:      bool  = False
    negative_cycle:  bool  = False
    heuristic:       str   = ""         # for A* / Greedy


# ---------------------------------------------------------------------------
# ComparisonResult — side-by-side analytics
# ---------------------------------------------------------------------------
@dataclass
class ComparisonResult:
    left:  RunMetrics = field(default_factory=RunMetrics)
    right: RunMetrics = field(default_factory=RunMetrics)
    # derived
    winner_nodes:  str = ""   # which algo visited fewer nodes
    winner_edges:  str = ""
    winner_path:   str = ""   # which algo found shorter / cheaper path


# ---------------------------------------------------------------------------
# Recorder
# ---------------------------------------------------------------------------
class Recorder:
    """
    Attributes:
        steps       : Full list of Steps from the run.
        metrics     : Computed RunMetrics (available after run_to_completion).
        stepper     : The underlying Stepper (if you want live step-by-step access).
    """

    def __init__(self):
        self.steps:     List[Step]        = []
        self.metrics:   Optional[RunMetrics] = None
        self.stepper:   Optional[Stepper] = None

        self._algo_info:  Optional[AlgoInfo] = None
        self._source:     str               = ""
        self._target:     str               = ""
        self._graph:      Optional[Graph]   = None
        self._heuristic:  str               = ""
        self._start_time: float             = 0.0

    # ------------------------------------------------------------------
    # Setup & run
    # ------------------------------------------------------------------
    def start(
        self,
        algo_key: str,
        source: str,
        target: str,
        graph: Graph,
        heuristic: str = "euclidean",
    ) -> None:
        """Initialise the generator and stepper for this run."""
        info = get_algorithm(algo_key)
        if info is None:
            raise ValueError(f"Unknown algorithm: {algo_key}")

        self._algo_info  = info
        self._source     = source
        self._target     = target
        self._graph      = graph
        self._heuristic  = heuristic
        self.steps       = []
        self.metrics     = None

        # build kwargs based on what the algo accepts
        kwargs: Dict[str, Any] = {"graph": graph, "source": source, "target": target}
        if info.has_heuristic:
            kwargs["heuristic"] = heuristic

        gen = info.fn(**kwargs)

        # wrap in a Stepper (but we'll drive it manually for recording)
        self.stepper = Stepper()
        self.stepper.start(gen)

    def run_to_completion(self) -> RunMetrics:
        """Exhaust the generator, record every step, compute metrics."""
        if self.stepper is None:
            raise RuntimeError("Call start() first.")

        self._start_time = time.monotonic()

        # pull every step
        self.stepper.jump_to_end()
        self.steps = list(self.stepper.steps)

        wall_ms = (time.monotonic() - self._start_time) * 1000

        # --- compute metrics ---
        self.metrics = self._compute_metrics(wall_ms)
        return self.metrics

    def get_metrics(self) -> Optional[RunMetrics]:
        return self.metrics

    # ------------------------------------------------------------------
    # Step access (for live playback recording)
    # ------------------------------------------------------------------
    def record_step(self, step: Step) -> None:
        self.steps.append(step)

    # ------------------------------------------------------------------
    # Export (serialisable snapshot)
    # ------------------------------------------------------------------
    def export(self) -> Dict[str, Any]:
        return {
            "algo_key":  self._algo_info.key if self._algo_info else "",
            "source":    self._source,
            "target":    self._target,
            "heuristic": self._heuristic,
            "graph":     self._graph.to_dict() if self._graph else {},
            "metrics":   self.metrics.__dict__ if self.metrics else {},
            "steps": [
                {
                    "step_number":     s.step_number,
                    "current_node":    s.current_node,
                    "node_states":     s.node_states,
                    "edge_states":     s.edge_states,
                    "visited_set":     s.visited_set,
                    "frontier":        s.frontier,
                    "path":            s.path,
                    "distances":       s.distances,
                    "pseudocode_line": s.pseudocode_line,
                    "explanation":     s.explanation,
                    "is_final":        s.is_final,
                }
                for s in self.steps
            ],
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _compute_metrics(self, wall_ms: float) -> RunMetrics:
        info = self._algo_info
        last = self.steps[-1] if self.steps else None

        nodes_visited = len(last.visited_set)  if last else 0
        edges_relaxed = last.metrics.get("edges_relaxed", 0) if last else 0
        path          = last.path              if last else []
        path_found    = bool(path)

        # path cost: sum edge weights along the path
        path_cost = 0.0
        if self._graph and len(path) > 1:
            for i in range(len(path) - 1):
                e = self._graph.get_edge_between(path[i], path[i + 1])
                if e:
                    path_cost += e.weight

        # approximate memory: sizeof the steps buffer
        mem = sys.getsizeof(self.steps)
        for s in self.steps:
            mem += sys.getsizeof(s)

        neg_cycle = False
        if last and last.overlay.get("negative_cycle"):
            neg_cycle = True

        return RunMetrics(
            algo_key=info.key if info else "",
            algo_label=info.label if info else "",
            source=self._source,
            target=self._target,
            nodes_visited=nodes_visited,
            edges_relaxed=edges_relaxed,
            path_length=len(path) - 1 if len(path) > 1 else 0,
            path_cost=path_cost,
            total_steps=len(self.steps),
            wall_time_ms=round(wall_ms, 2),
            memory_bytes=mem,
            path_found=path_found,
            negative_cycle=neg_cycle,
            heuristic=self._heuristic,
        )


# ---------------------------------------------------------------------------
# Comparison helper
# ---------------------------------------------------------------------------
def compare(left: Recorder, right: Recorder) -> ComparisonResult:
    """Given two completed Recorders, produce a ComparisonResult."""
    l = left.metrics  or RunMetrics()
    r = right.metrics or RunMetrics()

    def winner(l_val, r_val, l_key, r_key, lower_is_better=True):
        if l_val == r_val:
            return "tie"
        if lower_is_better:
            return l_key if l_val < r_val else r_key
        return l_key if l_val > r_val else r_key

    return ComparisonResult(
        left=l,
        right=r,
        winner_nodes=winner(l.nodes_visited, r.nodes_visited, l.algo_label, r.algo_label),
        winner_edges=winner(l.edges_relaxed, r.edges_relaxed, l.algo_label, r.algo_label),
        winner_path =winner(l.path_cost, r.path_cost, l.algo_label, r.algo_label),
    )
