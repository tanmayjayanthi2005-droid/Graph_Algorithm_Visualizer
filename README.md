# 🚀 Graph Algorithm Visualizer

**A production-grade, pedagogical graph algorithm visualizer** — not just for watching algorithms run, but for **understanding**, **comparing**, and **breaking** them.

---

## 🎯 What Makes This Different

This isn't another basic BFS/DFS visualizer. This is a **teaching platform** and **experimentation sandbox** with:

- **8 algorithms**: BFS, DFS, Dijkstra, A*, Bidirectional BFS, Bellman-Ford, Floyd-Warshall, Greedy Best-First
- **Step-by-step engine** with play/pause/next/prev/rewind
- **Live pseudocode sync** — every step highlights the executing line
- **Comparison mode** — run two algorithms side-by-side on the same graph
- **Heuristic playground** — A* admissibility teaching tool
- **5 graph generators**: random, grid/maze, scale-free, adjacency list, adjacency matrix
- **Learning mode** — step explanations in plain English
- **Expert mode** — clean, fast, no hints
- **Negative edges** — Bellman-Ford + cycle detection
- **All-pairs shortest paths** — Floyd-Warshall with live NxN matrix
- **Analytics panel** — nodes visited, edges relaxed, path cost, memory, wall time
- **Visual encoding** — color-coded node/edge states, overlays, distance tables

---

## 📦 Installation

### Requirements
- Python 3.8+
- Flask

### Quick Start

```bash
# 1. Install dependencies
pip install flask

# 2. Run the visualizer
python main.py

# 3. Open your browser
# Navigate to http://localhost:5000
```

That's it. The server starts, and you're visualizing algorithms in seconds.

---

## 🏗️ Architecture

```
graph_visualizer/
├── graph/                    # Data layer
│   ├── node.py               # Node + NodeState enum
│   ├── edge.py               # Edge + EdgeState enum
│   ├── graph.py              # Graph container + 5 generators
│   └── __init__.py
│
├── algorithms/               # Algorithm layer
│   ├── step.py               # Step snapshot dataclass
│   ├── bfs.py                # Breadth-First Search
│   ├── dfs.py                # Depth-First Search
│   ├── dijkstra.py           # Dijkstra's Algorithm
│   ├── astar.py              # A* (+ 4 heuristics)
│   ├── bidirectional_bfs.py  # Bidirectional BFS
│   ├── bellman_ford.py       # Bellman-Ford + cycle detector
│   ├── floyd_warshall.py     # Floyd-Warshall (all-pairs)
│   ├── greedy_bfs.py         # Greedy Best-First
│   └── __init__.py           # REGISTRY — plugin system
│
├── engine/                   # Playback engine
│   ├── stepper.py            # Play/Pause/Next/Prev/Rewind
│   ├── recorder.py           # Run recording + analytics
│   └── __init__.py
│
├── ui/                       # Presentation layer
│   ├── canvas.py             # SVG renderer
│   ├── controls.py           # All UI panels
│   └── __init__.py
│
└── main.py                   # Flask web app
```

### Design Principles

1. **Generator-based algorithms** — every algorithm is a generator that `yield`s a `Step` at each meaningful event. The stepper calls `next()`. Clean, testable, reusable.

2. **Stateless rendering** — `render_canvas(graph, step)` is a pure function. No mutations. State is passed in, SVG comes out.

3. **Plugin system** — adding a new algorithm is literally: write the generator, add one entry to `REGISTRY`. No changes to the UI or engine.

4. **Step snapshots** — a `Step` is a frozen-in-time picture of everything the visualizer needs: node states, edge states, queue contents, distances, pseudocode line, explanation.

5. **Separation of concerns** — graph layer doesn't know about algorithms. Algorithms don't know about rendering. Engine doesn't know about Flask. Clean imports top-to-bottom.

---

## 🎮 Feature Guide

### **1. Graph Generation**

- **Random (Erdős–Rényi)**: adjustable node count + edge probability
- **Grid / Maze**: 2D grid with random walls (4-connected)
- **Scale-Free (Barabási–Albert)**: hub-and-spoke topology
- **Import from text**: adjacency list or adjacency matrix

### **2. Algorithm Selection**

Pick any of 8 algorithms. The UI auto-adjusts:
- **A* / Greedy**: heuristic selector appears
- **Bellman-Ford**: negative-edge warning
- **Floyd-Warshall**: matrix panel

### **3. Playback Controls**

- ▶ **Play** — auto-advance at configurable speed
- ⏸ **Pause**
- ⏭ **Next** — step forward
- ⏮ **Prev** — rewind one step (full history buffered)
- ⏮ **Rewind** — jump to step 0
- ⏭ **Jump to End** — exhaust generator

**Speed**: Slow (1s/step) | Medium (0.4s) | Fast (0.15s) | Turbo (0.05s)

### **4. Visual Encoding**

**Node states** (color-coded):
- Grey — unvisited
- Blue — frontier (in queue)
- Green — visited (processed)
- Amber — current (being expanded right now)
- Purple — on the final path
- Red — blocked (obstacle)
- Cyan — source
- Magenta — target

**Edge states**:
- Grey — default
- Amber pulse — relaxed
- Purple thick — chosen (on path)
- Faded — ignored

**Overlays** (live panels):
- Priority queue contents (Dijkstra / A*)
- Stack contents (DFS)
- Distance array (Dijkstra / Bellman-Ford)
- g/h/f scores (A*)
- NxN matrix (Floyd-Warshall)

### **5. Pseudocode Sync**

The pseudocode panel highlights the line executing at each step. Every algorithm ships its own pseudocode in `algorithms/<algo>.py` as `PSEUDOCODE: List[str]`.

### **6. Learning Mode vs Expert Mode**

**Learning Mode** (default):
- Step explanations in plain English
- "Why did the algorithm choose this node?"
- Tooltips on every panel

**Expert Mode**:
- Clean UI
- No hints
- Fast execution

Toggle via checkbox in the sidebar.

### **7. Comparison Mode**

Run two algorithms on the **same graph** and see side-by-side metrics:
- Nodes visited
- Edges relaxed
- Path cost
- Wall time

**Example**: "Is A* really faster than Dijkstra on this graph?"

Winner badges show which algorithm performed better on each metric.

### **8. Heuristic Playground (A* / Greedy)**

When running A* or Greedy BFS, the playground shows:
- g (actual cost from source)
- h (heuristic estimate to target)
- f = g + h

**Teaching moment**: "What happens if h overestimates?" → A* becomes suboptimal. "What if h = 0?" → A* degrades to Dijkstra.

Built-in heuristics:
- **Euclidean** — √(Δx² + Δy²)
- **Manhattan** — |Δx| + |Δy|
- **Octile** — diagonal-aware
- **Zero** — h=0 (becomes Dijkstra)

### **9. Analytics Panel**

After every run, see:
- **Nodes visited** — how many nodes the algorithm explored
- **Edges relaxed** — how many edge-weight updates happened
- **Path length** — number of edges on the final path
- **Path cost** — total weight of the final path
- **Total steps** — number of Step objects yielded
- **Wall time** — milliseconds to run to completion
- **Memory** — approximate peak memory (step buffer size)

---

## 🧪 Testing the Full Stack

Every module has been smoke-tested end-to-end:

```bash
cd graph_visualizer
python3 -c "
from graph import Graph
from algorithms import get_algorithm
from engine import Recorder, compare

# generate a graph
g = Graph.generate_random(num_nodes=10, seed=42)

# run BFS
rec1 = Recorder()
rec1.start('bfs', '0', '9', g)
rec1.run_to_completion()

# run Dijkstra
rec2 = Recorder()
rec2.start('dijkstra', '0', '9', g)
rec2.run_to_completion()

# compare
result = compare(rec1, rec2)
print(f'BFS: {rec1.metrics.nodes_visited} nodes')
print(f'Dijkstra: {rec2.metrics.nodes_visited} nodes')
print(f'Winner: {result.winner_nodes}')
"
```

Output:
```
BFS: 10 nodes
Dijkstra: 10 nodes
Winner: tie
```

All 8 algorithms, both generators, grid/scale-free/import graph modes, Recorder, compare, and serialisation round-trip — **all green**.

---

## 🔧 Extending the Visualizer

### Add a New Algorithm

1. **Write the generator** in `algorithms/your_algo.py`:
   ```python
   def your_algo(graph, source, target):
       sb = StepBuilder()
       # ... your logic ...
       yield sb.build(step_number=0)
   ```

2. **Add to REGISTRY** in `algorithms/__init__.py`:
   ```python
   REGISTRY["your_algo"] = AlgoInfo(
       key="your_algo",
       label="Your Algorithm",
       fn=your_algo,
       pseudocode=PSEUDOCODE,
       tags=["shortest-path"],
       complexity_time="O(E log V)",
   )
   ```

3. **Done**. The UI auto-discovers it. No other changes needed.

### Add a New Graph Generator

Add a `@classmethod` to `Graph` in `graph/graph.py`:

```python
@classmethod
def generate_your_graph(cls, **kwargs) -> "Graph":
    g = cls()
    # ... generate nodes and edges ...
    return g
```

Wire it into the Flask API in `main.py` under `/api/graph/generate`.

### Add a New Visual Overlay

In `ui/canvas.py`, add a new helper to `_render_overlays()`:

```python
def _render_your_overlay(data, config, x, y):
    # ... return SVG string ...
```

The overlay data comes from `step.overlay["your_key"]`, which the algorithm populates.

---

## 📊 Feature Comparison

| Feature | This Visualizer | Typical Student Project |
|---------|----------------|------------------------|
| Algorithms | 8 (BFS, DFS, Dijkstra, A*, Bi-BFS, BF, FW, Greedy) | 2-3 (BFS, DFS) |
| Step-by-step | ✅ Full rewind + play/pause | ❌ Or forward-only |
| Comparison mode | ✅ Side-by-side metrics | ❌ |
| Pseudocode sync | ✅ Live line highlighting | ❌ |
| Heuristic playground | ✅ A* admissibility teaching | ❌ |
| Negative edges | ✅ Bellman-Ford + cycle detector | ❌ |
| All-pairs | ✅ Floyd-Warshall + live matrix | ❌ |
| Graph generators | 5 (random, grid, scale-free, import) | 1 (random) |
| Analytics | ✅ 8 metrics per run | ❌ |
| Architecture | Clean plugin system | ❌ Monolithic |

---

## 🙏 Acknowledgments

Built with:
- **Flask** — web framework
- **Python** — language
- **SVG** — rendering
- **Lots of coffee** — fuel

---

**Ready to start? Run `python main.py` and open http://localhost:5000**
