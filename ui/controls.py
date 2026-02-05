"""
controls.py — UI Control Panels
=================================
Every UI panel is a pure function that takes state and returns HTML.

Panels:
  • playback_controls       – play/pause/next/prev/rewind/speed
  • algorithm_selector      – dropdown + heuristic picker
  • graph_generator         – random/grid/scale-free/import tabs
  • source_target_picker    – click-to-set or dropdown
  • analytics_panel         – nodes visited, edges relaxed, path cost, …
  • comparison_panel        – side-by-side metrics of two runs
  • pseudocode_viewer       – with live line highlighting
  • explanation_panel       – Learning Mode "why this step happened"
  • heuristic_playground    – A* admissibility teaching tool

Design:
  - All panels are stateless render functions.
  - State is passed in as kwargs.
  - Output is raw HTML strings (no templating engine).
  - The main app stitches them together.
"""

from typing import Optional, List, Dict, Any
from algorithms import AlgoInfo, list_algorithms
from engine import RunMetrics, ComparisonResult


# ---------------------------------------------------------------------------
# Playback Controls
# ---------------------------------------------------------------------------
def playback_controls(
    is_playing: bool = False,
    current_step: int = 0,
    total_steps: int = 0,
    speed: str = "medium",
    is_finished: bool = False,
) -> str:
    play_icon = "⏸" if is_playing else "▶"
    play_label = "Pause" if is_playing else "Play"

    return f"""
    <div class="panel playback-controls">
      <h3>⏯ Playback</h3>
      <div class="button-row">
        <button id="btn-rewind" title="Rewind to start">⏮</button>
        <button id="btn-prev" title="Previous step">◀</button>
        <button id="btn-play" title="{play_label}">{play_icon}</button>
        <button id="btn-next" title="Next step">▶</button>
        <button id="btn-end" title="Jump to end">⏭</button>
      </div>
      <div class="step-info">
        Step <span id="current-step">{current_step}</span> / <span id="total-steps">{total_steps}</span>
        {' <span class="finished-badge">FINISHED</span>' if is_finished else ''}
      </div>
      <div class="speed-control">
        <label>Speed:</label>
        <select id="speed-selector">
          <option value="slow" {'selected' if speed == 'slow' else ''}>Slow (teaching)</option>
          <option value="medium" {'selected' if speed == 'medium' else ''}>Medium</option>
          <option value="fast" {'selected' if speed == 'fast' else ''}>Fast (demo)</option>
          <option value="turbo" {'selected' if speed == 'turbo' else ''}>Turbo</option>
        </select>
      </div>
    </div>
    """


# ---------------------------------------------------------------------------
# Algorithm Selector
# ---------------------------------------------------------------------------
def algorithm_selector(
    algorithms: List[AlgoInfo],
    selected_key: str = "bfs",
    show_heuristic: bool = False,
    selected_heuristic: str = "euclidean",
) -> str:
    options = []
    for algo in algorithms:
        sel = 'selected' if algo.key == selected_key else ''
        options.append(
            f'<option value="{algo.key}" {sel}>{algo.label} — {algo.complexity_time}</option>'
        )

    heuristic_block = ""
    if show_heuristic:
        heuristic_block = f"""
        <div class="heuristic-picker">
          <label>Heuristic:</label>
          <select id="heuristic-selector">
            <option value="euclidean" {'selected' if selected_heuristic == 'euclidean' else ''}>Euclidean</option>
            <option value="manhattan" {'selected' if selected_heuristic == 'manhattan' else ''}>Manhattan</option>
            <option value="octile" {'selected' if selected_heuristic == 'octile' else ''}>Octile</option>
            <option value="zero" {'selected' if selected_heuristic == 'zero' else ''}>Zero (= Dijkstra)</option>
          </select>
        </div>
        """

    return f"""
    <div class="panel algorithm-selector">
      <h3>🧠 Algorithm</h3>
      <select id="algo-selector">
        {''.join(options)}
      </select>
      {heuristic_block}
      <button id="btn-run" class="btn-primary">▶ Run Algorithm</button>
    </div>
    """


# ---------------------------------------------------------------------------
# Graph Generator
# ---------------------------------------------------------------------------
def graph_generator(active_tab: str = "random") -> str:
    tabs = ["random", "grid", "scale-free", "import"]
    tab_buttons = []
    for t in tabs:
        active = 'active' if t == active_tab else ''
        tab_buttons.append(f'<button class="tab-btn {active}" data-tab="{t}">{t.capitalize()}</button>')

    return f"""
    <div class="panel graph-generator">
      <h3>🌐 Graph Generator</h3>
      <div class="tabs">
        {''.join(tab_buttons)}
      </div>

      <div class="tab-content" data-tab="random" style="display: {'block' if active_tab == 'random' else 'none'};">
        <label>Nodes: <input type="number" id="rand-nodes" value="10" min="3" max="30"></label>
        <label>Edge Prob: <input type="range" id="rand-prob" min="0" max="1" step="0.05" value="0.3">
               <span id="rand-prob-val">0.3</span></label>
        <label><input type="checkbox" id="rand-directed"> Directed</label>
        <label><input type="checkbox" id="rand-weighted" checked> Weighted</label>
        <button id="btn-gen-random" class="btn-secondary">Generate Random</button>
      </div>

      <div class="tab-content" data-tab="grid" style="display: {'block' if active_tab == 'grid' else 'none'};">
        <label>Rows: <input type="number" id="grid-rows" value="6" min="3" max="15"></label>
        <label>Cols: <input type="number" id="grid-cols" value="8" min="3" max="15"></label>
        <label>Wall %: <input type="range" id="grid-walls" min="0" max="0.5" step="0.05" value="0.2">
               <span id="grid-walls-val">0.2</span></label>
        <button id="btn-gen-grid" class="btn-secondary">Generate Grid/Maze</button>
      </div>

      <div class="tab-content" data-tab="scale-free" style="display: {'block' if active_tab == 'scale-free' else 'none'};">
        <label>Nodes: <input type="number" id="sf-nodes" value="15" min="5" max="30"></label>
        <label>Edges/node: <input type="number" id="sf-m" value="2" min="1" max="5"></label>
        <label><input type="checkbox" id="sf-weighted" checked> Weighted</label>
        <button id="btn-gen-sf" class="btn-secondary">Generate Scale-Free</button>
      </div>

      <div class="tab-content" data-tab="import" style="display: {'block' if active_tab == 'import' else 'none'};">
        <label>Import Format:</label>
        <select id="import-format">
          <option value="adj-list">Adjacency List</option>
          <option value="adj-matrix">Adjacency Matrix</option>
        </select>
        <textarea id="import-text" rows="8" placeholder="A: B(3) C(5)
B: D(2)
C: D(1)
..."></textarea>
        <button id="btn-import" class="btn-secondary">Import Graph</button>
      </div>
    </div>
    """


# ---------------------------------------------------------------------------
# Source / Target Picker
# ---------------------------------------------------------------------------
def source_target_picker(
    node_ids: List[str],
    source: Optional[str] = None,
    target: Optional[str] = None,
) -> str:
    src_options = ['<option value="">-- Click on canvas --</option>']
    tgt_options = ['<option value="">-- Click on canvas --</option>']

    for nid in node_ids:
        src_sel = 'selected' if nid == source else ''
        tgt_sel = 'selected' if nid == target else ''
        src_options.append(f'<option value="{nid}" {src_sel}>{nid}</option>')
        tgt_options.append(f'<option value="{nid}" {tgt_sel}>{nid}</option>')

    return f"""
    <div class="panel source-target-picker">
      <h3>🎯 Source & Target</h3>
      <label>Source:
        <select id="source-selector">
          {''.join(src_options)}
        </select>
      </label>
      <label>Target:
        <select id="target-selector">
          {''.join(tgt_options)}
        </select>
      </label>
      <p class="hint">Or click nodes on the canvas to set them.</p>
    </div>
    """


# ---------------------------------------------------------------------------
# Analytics Panel
# ---------------------------------------------------------------------------
def analytics_panel(metrics: Optional[RunMetrics] = None) -> str:
    if not metrics:
        return """
        <div class="panel analytics-panel">
          <h3>📊 Analytics</h3>
          <p class="placeholder">Run an algorithm to see metrics.</p>
        </div>
        """

    path_status = "✅ Found" if metrics.path_found else "❌ Not Found"
    if metrics.negative_cycle:
        path_status = "⚠️ Negative Cycle"

    return f"""
    <div class="panel analytics-panel">
      <h3>📊 Analytics — {metrics.algo_label}</h3>
      <table>
        <tr><td>Nodes Visited:</td><td><strong>{metrics.nodes_visited}</strong></td></tr>
        <tr><td>Edges Relaxed:</td><td><strong>{metrics.edges_relaxed}</strong></td></tr>
        <tr><td>Path Length:</td><td><strong>{metrics.path_length} edges</strong></td></tr>
        <tr><td>Path Cost:</td><td><strong>{metrics.path_cost:.2f}</strong></td></tr>
        <tr><td>Total Steps:</td><td><strong>{metrics.total_steps}</strong></td></tr>
        <tr><td>Wall Time:</td><td><strong>{metrics.wall_time_ms:.2f} ms</strong></td></tr>
        <tr><td>Memory:</td><td><strong>{metrics.memory_bytes // 1024} KB</strong></td></tr>
        <tr><td>Path:</td><td><strong>{path_status}</strong></td></tr>
      </table>
    </div>
    """


# ---------------------------------------------------------------------------
# Comparison Panel (side-by-side)
# ---------------------------------------------------------------------------
def comparison_panel(comp: Optional[ComparisonResult] = None) -> str:
    if not comp:
        return """
        <div class="panel comparison-panel">
          <h3>⚖️ Comparison Mode</h3>
          <p class="placeholder">Run two algorithms on the same graph to compare.</p>
          <button id="btn-compare-mode" class="btn-secondary">Enable Comparison Mode</button>
        </div>
        """

    left = comp.left
    right = comp.right

    def winner_badge(field, winner_label):
        if winner_label == "tie":
            return "🟰 Tie"
        return f"👑 {winner_label}"

    return f"""
    <div class="panel comparison-panel">
      <h3>⚖️ Comparison: {left.algo_label} vs {right.algo_label}</h3>
      <table class="comparison-table">
        <thead>
          <tr>
            <th>Metric</th>
            <th>{left.algo_label}</th>
            <th>{right.algo_label}</th>
            <th>Winner</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Nodes Visited</td>
            <td>{left.nodes_visited}</td>
            <td>{right.nodes_visited}</td>
            <td>{winner_badge('nodes', comp.winner_nodes)}</td>
          </tr>
          <tr>
            <td>Edges Relaxed</td>
            <td>{left.edges_relaxed}</td>
            <td>{right.edges_relaxed}</td>
            <td>{winner_badge('edges', comp.winner_edges)}</td>
          </tr>
          <tr>
            <td>Path Cost</td>
            <td>{left.path_cost:.2f}</td>
            <td>{right.path_cost:.2f}</td>
            <td>{winner_badge('path', comp.winner_path)}</td>
          </tr>
          <tr>
            <td>Wall Time</td>
            <td>{left.wall_time_ms:.2f} ms</td>
            <td>{right.wall_time_ms:.2f} ms</td>
            <td>—</td>
          </tr>
        </tbody>
      </table>
      <button id="btn-exit-compare" class="btn-secondary">Exit Comparison</button>
    </div>
    """


# ---------------------------------------------------------------------------
# Pseudocode Viewer
# ---------------------------------------------------------------------------
def pseudocode_viewer(
    pseudocode_lines: List[str],
    current_line: int = -1,
    algo_label: str = "",
) -> str:
    if not pseudocode_lines:
        return """
        <div class="code-block">
          <div style="color: #7d8590; padding: 20px; text-align: center;">
            Select an algorithm to view pseudocode
          </div>
        </div>
        """

    lines_html = []
    for i, line in enumerate(pseudocode_lines):
        highlight = 'highlight' if i == current_line else ''
        # Escape HTML entities
        line_escaped = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        lines_html.append(f'<div class="code-line {highlight}" data-line="{i}">{line_escaped}</div>')

    return f"""
    <div class="code-block">
      {''.join(lines_html)}
    </div>
    """


# ---------------------------------------------------------------------------
# Explanation Panel (Learning Mode)
# ---------------------------------------------------------------------------
def explanation_panel(explanation: str = "", show: bool = True) -> str:
    if not show:
        return """<div class="explanation-text" style="color: #7d8590; padding: 20px;">Learning mode disabled</div>"""
    
    if not explanation:
        explanation = "▶ Click <strong>Run Algorithm</strong> to see step-by-step explanations of what's happening at each stage."

    return f"""<div class="explanation-text">{explanation}</div>"""


# ---------------------------------------------------------------------------
# Heuristic Playground (A* teaching tool)
# ---------------------------------------------------------------------------
def heuristic_playground(
    scores: Optional[List[Dict]] = None,
    heuristic: str = "euclidean",
) -> str:
    if not scores:
        return """
        <div class="panel heuristic-playground">
          <h3>🧪 Heuristic Playground</h3>
          <p class="placeholder">Run A* or Greedy to explore heuristic behavior.</p>
        </div>
        """

    # show top nodes sorted by f
    sorted_scores = sorted(scores, key=lambda s: s.get("f", float("inf")))[:10]

    rows = []
    for item in sorted_scores:
        n = item.get("node", "?")
        g = item.get("g", float("inf"))
        h = item.get("h", 0)
        f = item.get("f", float("inf"))
        g_str = f"{g:.2f}" if g != float("inf") else "∞"
        h_str = f"{h:.2f}"
        f_str = f"{f:.2f}" if f != float("inf") else "∞"
        rows.append(f"<tr><td>{n}</td><td>{g_str}</td><td>{h_str}</td><td>{f_str}</td></tr>")

    return f"""
    <div class="panel heuristic-playground">
      <h3>🧪 Heuristic Playground — {heuristic}</h3>
      <p>A* = g (actual cost) + h (heuristic estimate). If h is <strong>admissible</strong> (never overestimates),
         A* guarantees optimal path.</p>
      <table class="scores-table">
        <thead>
          <tr><th>Node</th><th>g</th><th>h</th><th>f = g+h</th></tr>
        </thead>
        <tbody>
          {''.join(rows)}
        </tbody>
      </table>
    </div>
    """


# ---------------------------------------------------------------------------
# Mode Toggle (Learning vs Expert)
# ---------------------------------------------------------------------------
def mode_toggle(learning_mode: bool = True) -> str:
    return f"""
    <div class="panel mode-toggle">
      <h3>🎓 Mode</h3>
      <label>
        <input type="checkbox" id="learning-mode-toggle" {'checked' if learning_mode else ''}>
        Learning Mode (tooltips + explanations)
      </label>
    </div>
    """