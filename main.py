"""
main.py — Graph Algorithm Visualizer Flask App
================================================
The web server that powers the visualizer.

Routes:
  GET  /                       – main UI
  POST /api/graph/generate     – generate a new graph
  POST /api/graph/import       – import from text
  POST /api/run                – start algorithm run
  POST /api/step/next          – advance one step
  POST /api/step/prev          – rewind one step
  POST /api/step/goto          – jump to step N
  POST /api/step/play          – toggle play/pause
  GET  /api/state              – current app state (for polling / SSE)
  POST /api/compare/start      – enter comparison mode
  POST /api/compare/add_run    – record second algo run
  GET  /api/compare/result     – get comparison result

State management:
  All state is stored in Flask session (in-memory for now; could move
  to Redis for production).  Each user's session holds:
    • graph           – serialised Graph
    • recorder        – current Recorder
    • stepper         – current Stepper
    • source / target
    • selected_algo
    • learning_mode
    • comparison_mode data
"""

from flask import Flask, render_template_string, request, jsonify, session
import secrets
import sys
import os

# add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from graph import Graph
from algorithms import get_algorithm, list_algorithms
from engine import Stepper, Recorder, compare
from ui import (
    render_canvas,
    playback_controls,
    algorithm_selector,
    graph_generator,
    source_target_picker,
    analytics_panel,
    comparison_panel,
    pseudocode_viewer,
    explanation_panel,
    heuristic_playground,
    mode_toggle,
)


app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# ---------------------------------------------------------------------------
# Session State Helpers
# ---------------------------------------------------------------------------
def get_graph() -> Graph:
    """Deserialise graph from session, or create default."""
    if "graph" not in session:
        session["graph"] = Graph.generate_random(num_nodes=8, edge_probability=0.4, seed=42).to_dict()
    return Graph.from_dict(session["graph"])


def save_graph(graph: Graph):
    session["graph"] = graph.to_dict()


def get_state():
    """Return current app state as a dict."""
    return {
        "source":         session.get("source"),
        "target":         session.get("target"),
        "selected_algo":  session.get("selected_algo", "bfs"),
        "heuristic":      session.get("heuristic", "euclidean"),
        "learning_mode":  session.get("learning_mode", True),
        "current_step":   session.get("current_step", 0),
        "total_steps":    session.get("total_steps", 0),
        "is_playing":     session.get("is_playing", False),
        "speed":          session.get("speed", "medium"),
        "comparison_mode": session.get("comparison_mode", False),
    }


def set_state(**kwargs):
    for k, v in kwargs.items():
        session[k] = v


# ---------------------------------------------------------------------------
# Main UI Route
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    graph = get_graph()
    state = get_state()

    # if no source/target, pick first and last
    if not state["source"] or not state["target"]:
        ids = graph.node_ids()
        if len(ids) >= 2:
            state["source"] = ids[0]
            state["target"] = ids[-1]
            set_state(source=state["source"], target=state["target"])

    algos = list_algorithms()
    algo_info = get_algorithm(state["selected_algo"])
    show_heuristic = algo_info.has_heuristic if algo_info else False

    # render initial canvas (no step)
    svg = render_canvas(graph, step=None, show_overlays=False)

    # build control panels
    playback_html   = playback_controls(
        is_playing=state["is_playing"],
        current_step=state["current_step"],
        total_steps=state["total_steps"],
        speed=state["speed"],
    )
    algo_html       = algorithm_selector(
        algorithms=algos,
        selected_key=state["selected_algo"],
        show_heuristic=show_heuristic,
        selected_heuristic=state["heuristic"],
    )
    graph_gen_html  = graph_generator()
    picker_html     = source_target_picker(
        node_ids=graph.node_ids(),
        source=state["source"],
        target=state["target"],
    )
    analytics_html  = analytics_panel()
    pseudocode_html = pseudocode_viewer(
        pseudocode_lines=algo_info.pseudocode if algo_info else [],
        current_line=-1,
        algo_label=algo_info.label if algo_info else "",
    )
    explanation_html = explanation_panel(show=state["learning_mode"])
    mode_html       = mode_toggle(learning_mode=state["learning_mode"])

    # assemble full page
    html = render_template_string(INDEX_TEMPLATE,
        svg=svg,
        playback=playback_html,
        algo_selector=algo_html,
        graph_gen=graph_gen_html,
        picker=picker_html,
        analytics=analytics_html,
        pseudocode=pseudocode_html,
        explanation=explanation_html,
        mode_toggle=mode_html,
    )
    return html


# ---------------------------------------------------------------------------
# API: Graph Generation
# ---------------------------------------------------------------------------
@app.route("/api/graph/generate", methods=["POST"])
def api_graph_generate():
    data = request.json
    mode = data.get("mode", "random")

    if mode == "random":
        g = Graph.generate_random(
            num_nodes=data.get("nodes", 10),
            edge_probability=data.get("prob", 0.3),
            directed=data.get("directed", False),
            weighted=data.get("weighted", True),
            seed=data.get("seed"),
        )
    elif mode == "grid":
        g = Graph.generate_grid(
            rows=data.get("rows", 6),
            cols=data.get("cols", 8),
            wall_prob=data.get("wall_prob", 0.2),
            directed=data.get("directed", False),
            seed=data.get("seed"),
        )
    elif mode == "scale-free":
        g = Graph.generate_scale_free(
            num_nodes=data.get("nodes", 15),
            m=data.get("m", 2),
            weighted=data.get("weighted", True),
            seed=data.get("seed"),
        )
    else:
        return jsonify({"error": "Unknown mode"}), 400

    save_graph(g)
    # pick new source/target
    ids = g.node_ids()
    if len(ids) >= 2:
        set_state(source=ids[0], target=ids[-1])

    svg = render_canvas(g, step=None, show_overlays=False)
    return jsonify({"svg": svg, "node_ids": ids})


@app.route("/api/graph/import", methods=["POST"])
def api_graph_import():
    data = request.json
    text = data.get("text", "")
    fmt  = data.get("format", "adj-list")

    try:
        if fmt == "adj-list":
            g = Graph.from_adjacency_list(text, weighted=data.get("weighted", True))
        elif fmt == "adj-matrix":
            g = Graph.from_adjacency_matrix(text, weighted=data.get("weighted", True))
        else:
            return jsonify({"error": "Unknown format"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    save_graph(g)
    ids = g.node_ids()
    if len(ids) >= 2:
        set_state(source=ids[0], target=ids[-1])

    svg = render_canvas(g, step=None, show_overlays=False)
    return jsonify({"svg": svg, "node_ids": ids})


# ---------------------------------------------------------------------------
# API: Run Algorithm
# ---------------------------------------------------------------------------
@app.route("/api/run", methods=["POST"])
def api_run():
    graph = get_graph()
    state = get_state()

    source = state["source"]
    target = state["target"]
    if not source or not target:
        return jsonify({"error": "Set source and target first"}), 400

    algo_key   = state["selected_algo"]
    heuristic  = state["heuristic"]

    rec = Recorder()
    rec.start(algo_key, source, target, graph, heuristic)
    rec.run_to_completion()

    # store steps in session (serialised)
    session["steps"] = [
        {
            "step_number":     s.step_number,
            "current_node":    s.current_node,
            "current_edge":    s.current_edge,
            "node_states":     s.node_states,
            "edge_states":     s.edge_states,
            "visited_set":     s.visited_set,
            "frontier":        s.frontier,
            "path":            s.path,
            "distances":       s.distances,
            "pseudocode_line": s.pseudocode_line,
            "explanation":     s.explanation,
            "overlay":         s.overlay,
            "is_final":        s.is_final,
        }
        for s in rec.steps
    ]
    session["metrics"] = rec.metrics.__dict__ if rec.metrics else {}
    set_state(current_step=0, total_steps=len(rec.steps), is_playing=False)

    # render first step
    from algorithms.step import Step
    step0 = Step(**session["steps"][0])
    svg = render_canvas(graph, step0, show_overlays=True)

    algo_info = get_algorithm(algo_key)
    pseudocode_html = pseudocode_viewer(
        pseudocode_lines=algo_info.pseudocode if algo_info else [],
        current_line=step0.pseudocode_line,
        algo_label=algo_info.label if algo_info else "",
    )
    explanation_html = explanation_panel(step0.explanation, show=state["learning_mode"])
    analytics_html   = analytics_panel(rec.metrics)

    return jsonify({
        "svg": svg,
        "pseudocode": pseudocode_html,
        "explanation": explanation_html,
        "analytics": analytics_html,
        "current_step": 0,
        "total_steps": len(rec.steps),
    })


# ---------------------------------------------------------------------------
# API: Step Navigation
# ---------------------------------------------------------------------------
@app.route("/api/step/next", methods=["POST"])
def api_step_next():
    graph = get_graph()
    state = get_state()
    steps = session.get("steps", [])

    if state["current_step"] >= len(steps) - 1:
        return jsonify({"error": "Already at last step"}), 400

    new_idx = state["current_step"] + 1
    set_state(current_step=new_idx)

    from algorithms.step import Step
    step = Step(**steps[new_idx])
    svg = render_canvas(graph, step, show_overlays=True)

    algo_info = get_algorithm(state["selected_algo"])
    pseudocode_html = pseudocode_viewer(
        pseudocode_lines=algo_info.pseudocode if algo_info else [],
        current_line=step.pseudocode_line,
        algo_label=algo_info.label if algo_info else "",
    )
    explanation_html = explanation_panel(step.explanation, show=state["learning_mode"])

    return jsonify({
        "svg": svg,
        "pseudocode": pseudocode_html,
        "explanation": explanation_html,
        "current_step": new_idx,
    })


@app.route("/api/step/prev", methods=["POST"])
def api_step_prev():
    graph = get_graph()
    state = get_state()
    steps = session.get("steps", [])

    if state["current_step"] <= 0:
        return jsonify({"error": "Already at first step"}), 400

    new_idx = state["current_step"] - 1
    set_state(current_step=new_idx)

    from algorithms.step import Step
    step = Step(**steps[new_idx])
    svg = render_canvas(graph, step, show_overlays=True)

    algo_info = get_algorithm(state["selected_algo"])
    pseudocode_html = pseudocode_viewer(
        pseudocode_lines=algo_info.pseudocode if algo_info else [],
        current_line=step.pseudocode_line,
        algo_label=algo_info.label if algo_info else "",
    )
    explanation_html = explanation_panel(step.explanation, show=state["learning_mode"])

    return jsonify({
        "svg": svg,
        "pseudocode": pseudocode_html,
        "explanation": explanation_html,
        "current_step": new_idx,
    })


@app.route("/api/step/goto", methods=["POST"])
def api_step_goto():
    graph = get_graph()
    state = get_state()
    steps = session.get("steps", [])
    idx   = request.json.get("index", 0)

    if not (0 <= idx < len(steps)):
        return jsonify({"error": "Invalid step index"}), 400

    set_state(current_step=idx)

    from algorithms.step import Step
    step = Step(**steps[idx])
    svg = render_canvas(graph, step, show_overlays=True)

    algo_info = get_algorithm(state["selected_algo"])
    pseudocode_html = pseudocode_viewer(
        pseudocode_lines=algo_info.pseudocode if algo_info else [],
        current_line=step.pseudocode_line,
        algo_label=algo_info.label if algo_info else "",
    )
    explanation_html = explanation_panel(step.explanation, show=state["learning_mode"])

    return jsonify({
        "svg": svg,
        "pseudocode": pseudocode_html,
        "explanation": explanation_html,
        "current_step": idx,
    })


@app.route("/api/step/play", methods=["POST"])
def api_step_play():
    state = get_state()
    set_state(is_playing=not state["is_playing"])
    return jsonify({"is_playing": not state["is_playing"]})


# ---------------------------------------------------------------------------
# API: Config Changes
# ---------------------------------------------------------------------------
@app.route("/api/config/algo", methods=["POST"])
def api_config_algo():
    algo_key = request.json.get("algo_key", "bfs")
    set_state(selected_algo=algo_key)

    algo_info = get_algorithm(algo_key)
    algos = list_algorithms()
    algo_html = algorithm_selector(
        algorithms=algos,
        selected_key=algo_key,
        show_heuristic=algo_info.has_heuristic if algo_info else False,
        selected_heuristic=get_state()["heuristic"],
    )
    pseudocode_html = pseudocode_viewer(
        pseudocode_lines=algo_info.pseudocode if algo_info else [],
        current_line=-1,
        algo_label=algo_info.label if algo_info else "",
    )
    return jsonify({"algo_selector": algo_html, "pseudocode": pseudocode_html})


@app.route("/api/config/heuristic", methods=["POST"])
def api_config_heuristic():
    h = request.json.get("heuristic", "euclidean")
    set_state(heuristic=h)
    return jsonify({"heuristic": h})


@app.route("/api/config/speed", methods=["POST"])
def api_config_speed():
    speed = request.json.get("speed", "medium")
    set_state(speed=speed)
    return jsonify({"speed": speed})


@app.route("/api/config/source_target", methods=["POST"])
def api_config_source_target():
    src = request.json.get("source")
    tgt = request.json.get("target")
    if src:
        set_state(source=src)
    if tgt:
        set_state(target=tgt)
    return jsonify({"source": src, "target": tgt})


# ---------------------------------------------------------------------------
# HTML Template
# ---------------------------------------------------------------------------
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Graph Algorithm Visualizer</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=DM+Sans:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    
    :root {
      --bg-dark: #0d1117;
      --bg-darker: #010409;
      --bg-panel: #161b22;
      --bg-panel-hover: #1c2128;
      --border: #30363d;
      --border-bright: #484f58;
      --text-primary: #e6edf3;
      --text-secondary: #7d8590;
      --text-muted: #484f58;
      --accent-cyan: #0ea5e9;
      --accent-teal: #06b6d4;
      --accent-emerald: #10b981;
      --accent-amber: #f59e0b;
      --accent-rose: #f43f5e;
      --accent-purple: #a855f7;
      --glow-cyan: rgba(14, 165, 233, 0.4);
      --glow-teal: rgba(6, 182, 212, 0.4);
    }
    
    body {
      font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      background: var(--bg-darker);
      color: var(--text-primary);
      display: flex;
      height: 100vh;
      overflow: hidden;
    }
    
    /* Sidebar */
    #sidebar {
      width: 340px;
      background: linear-gradient(180deg, var(--bg-dark) 0%, var(--bg-darker) 100%);
      border-right: 1px solid var(--border);
      overflow-y: auto;
      padding: 24px 16px;
      box-shadow: 4px 0 24px rgba(0,0,0,0.4);
    }
    
    #sidebar::-webkit-scrollbar { width: 6px; }
    #sidebar::-webkit-scrollbar-track { background: transparent; }
    #sidebar::-webkit-scrollbar-thumb { 
      background: var(--border); 
      border-radius: 3px; 
    }
    #sidebar::-webkit-scrollbar-thumb:hover { background: var(--border-bright); }
    
    /* Main area */
    #main {
      flex: 1;
      display: flex;
      flex-direction: column;
      background: var(--bg-darker);
    }
    
    /* Canvas */
    #canvas-container {
      flex: 1;
      background: radial-gradient(ellipse at top, rgba(6, 182, 212, 0.05) 0%, transparent 50%),
                  var(--bg-darker);
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      border-bottom: 1px solid var(--border);
    }
    
    #canvas-svg { 
      max-width: 100%; 
      max-height: 100%;
      filter: drop-shadow(0 0 30px rgba(6, 182, 212, 0.15));
    }
    
    /* Bottom panel - FIXED LAYOUT */
    #bottom-panel {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      padding: 20px;
      background: var(--bg-dark);
      border-top: 1px solid var(--border);
      min-height: 320px;
      max-height: 400px;
      overflow: hidden;
    }
    
    #pseudocode-container,
    #explanation-container {
      display: flex;
      flex-direction: column;
      background: var(--bg-panel);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px;
      overflow: hidden;
    }
    
    #pseudocode-container h3,
    #explanation-container h3 {
      font-family: 'DM Sans', sans-serif;
      font-size: 14px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 16px;
      color: var(--accent-cyan);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    
    #pseudocode-container h3::before {
      content: "⟨/⟩";
      font-size: 16px;
    }
    
    #explanation-container h3::before {
      content: "💡";
      font-size: 16px;
    }
    
    .code-block {
      background: var(--bg-darker);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
      overflow-y: auto;
      flex: 1;
      font-family: 'JetBrains Mono', 'Courier New', monospace;
      font-size: 13px;
      line-height: 1.6;
    }
    
    .code-block::-webkit-scrollbar { width: 6px; }
    .code-block::-webkit-scrollbar-track { background: transparent; }
    .code-block::-webkit-scrollbar-thumb { 
      background: var(--border); 
      border-radius: 3px; 
    }
    
    .code-line {
      padding: 6px 12px;
      margin: 2px 0;
      border-radius: 6px;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .code-line.highlight {
      background: linear-gradient(90deg, rgba(6, 182, 212, 0.15) 0%, transparent 100%);
      border-left: 3px solid var(--accent-cyan);
      padding-left: 9px;
      box-shadow: 0 0 20px var(--glow-cyan);
      animation: pulse-glow 2s ease-in-out infinite;
    }
    
    @keyframes pulse-glow {
      0%, 100% { box-shadow: 0 0 20px var(--glow-cyan); }
      50% { box-shadow: 0 0 30px var(--glow-cyan); }
    }
    
    .explanation-text {
      color: var(--text-secondary);
      line-height: 1.8;
      font-size: 14px;
    }
    
    .explanation-text strong {
      color: var(--text-primary);
      font-weight: 600;
    }
    
    /* Panels */
    .panel {
      background: var(--bg-panel);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 18px;
      margin-bottom: 16px;
      transition: all 0.3s ease;
      position: relative;
      overflow: hidden;
    }
    
    .panel::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 2px;
      background: linear-gradient(90deg, var(--accent-cyan), var(--accent-teal));
      opacity: 0;
      transition: opacity 0.3s ease;
    }
    
    .panel:hover::before { opacity: 1; }
    
    .panel h3 {
      font-size: 13px;
      font-weight: 700;
      margin-bottom: 14px;
      color: var(--text-primary);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    
    /* Buttons */
    .button-row {
      display: flex;
      gap: 8px;
      margin-bottom: 12px;
    }
    
    button {
      background: linear-gradient(135deg, var(--accent-cyan), var(--accent-teal));
      color: #fff;
      border: none;
      padding: 10px 16px;
      border-radius: 8px;
      cursor: pointer;
      font-size: 13px;
      font-weight: 600;
      font-family: 'DM Sans', sans-serif;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      box-shadow: 0 2px 8px rgba(6, 182, 212, 0.3);
      position: relative;
      overflow: hidden;
    }
    
    button::before {
      content: '';
      position: absolute;
      top: 50%;
      left: 50%;
      width: 0;
      height: 0;
      border-radius: 50%;
      background: rgba(255,255,255,0.3);
      transform: translate(-50%, -50%);
      transition: width 0.6s, height 0.6s;
    }
    
    button:hover::before {
      width: 300px;
      height: 300px;
    }
    
    button:hover { 
      transform: translateY(-2px);
      box-shadow: 0 4px 16px rgba(6, 182, 212, 0.5);
    }
    
    button:active {
      transform: translateY(0);
    }
    
    .btn-primary {
      background: linear-gradient(135deg, var(--accent-emerald), #059669);
      box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
    }
    
    .btn-primary:hover {
      box-shadow: 0 4px 16px rgba(16, 185, 129, 0.5);
    }
    
    .btn-secondary {
      background: var(--bg-panel-hover);
      border: 1px solid var(--border);
      box-shadow: none;
    }
    
    .btn-secondary:hover {
      background: var(--border);
      box-shadow: 0 2px 8px rgba(72, 79, 88, 0.4);
    }
    
    /* Inputs */
    select, input[type="number"], input[type="range"], textarea {
      width: 100%;
      padding: 10px 12px;
      margin: 6px 0;
      background: var(--bg-darker);
      border: 1px solid var(--border);
      border-radius: 8px;
      color: var(--text-primary);
      font-size: 13px;
      font-family: 'DM Sans', sans-serif;
      transition: all 0.2s ease;
    }
    
    select:focus, input:focus, textarea:focus {
      outline: none;
      border-color: var(--accent-cyan);
      box-shadow: 0 0 0 3px var(--glow-cyan);
    }
    
    textarea { 
      font-family: 'JetBrains Mono', monospace; 
      resize: vertical;
      min-height: 120px;
    }
    
    label {
      display: block;
      margin: 10px 0 4px;
      font-size: 12px;
      color: var(--text-secondary);
      font-weight: 500;
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }
    
    /* Tabs */
    .tabs {
      display: flex;
      gap: 6px;
      margin-bottom: 14px;
      background: var(--bg-darker);
      padding: 4px;
      border-radius: 8px;
    }
    
    .tab-btn {
      flex: 1;
      padding: 8px 12px;
      background: transparent;
      font-size: 12px;
      font-weight: 600;
      border-radius: 6px;
      transition: all 0.2s ease;
      box-shadow: none;
    }
    
    .tab-btn.active {
      background: linear-gradient(135deg, var(--accent-cyan), var(--accent-teal));
      box-shadow: 0 2px 8px rgba(6, 182, 212, 0.3);
    }
    
    .tab-content { display: none; }
    
    /* Step info */
    .step-info {
      font-size: 13px;
      margin: 10px 0;
      color: var(--text-secondary);
      font-family: 'JetBrains Mono', monospace;
      padding: 8px 12px;
      background: var(--bg-darker);
      border-radius: 6px;
      border-left: 3px solid var(--accent-cyan);
    }
    
    .finished-badge {
      background: linear-gradient(135deg, var(--accent-emerald), #059669);
      color: #fff;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      box-shadow: 0 2px 8px rgba(16, 185, 129, 0.4);
    }
    
    /* Table */
    table {
      width: 100%;
      font-size: 13px;
      border-collapse: separate;
      border-spacing: 0 4px;
      margin-top: 8px;
    }
    
    table td {
      padding: 8px 4px;
      border-radius: 4px;
    }
    
    table tr:hover td {
      background: var(--bg-darker);
    }
    
    table td:first-child {
      color: var(--text-secondary);
      font-weight: 500;
    }
    
    table td:last-child {
      text-align: right;
      color: var(--accent-cyan);
      font-family: 'JetBrains Mono', monospace;
      font-weight: 600;
    }
    
    .hint {
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 8px;
      font-style: italic;
    }
    
    /* Animations */
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
    
    .panel {
      animation: fadeIn 0.4s ease-out;
    }
    
    /* Scrollbar styling */
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: var(--bg-darker); }
    ::-webkit-scrollbar-thumb { 
      background: var(--border); 
      border-radius: 4px;
      transition: background 0.2s;
    }
    ::-webkit-scrollbar-thumb:hover { background: var(--border-bright); }
  </style>
</head>
<body>
  <div id="sidebar">
    <div id="mode-toggle">{{ mode_toggle|safe }}</div>
    <div id="algo-selector">{{ algo_selector|safe }}</div>
    <div id="picker">{{ picker|safe }}</div>
    <div id="playback">{{ playback|safe }}</div>
    <div id="graph-gen">{{ graph_gen|safe }}</div>
    <div id="analytics">{{ analytics|safe }}</div>
  </div>
  
  <div id="main">
    <div id="canvas-container">
      <div id="canvas-svg">{{ svg|safe }}</div>
    </div>
    
    <div id="bottom-panel">
      <div id="pseudocode-container">
        <h3>Pseudocode</h3>
        <div id="pseudocode">{{ pseudocode|safe }}</div>
      </div>
      <div id="explanation-container">
        <h3>Step Explanation</h3>
        <div id="explanation">{{ explanation|safe }}</div>
      </div>
    </div>
  </div>

  <script>
    // Tab switching for graph generator
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
        document.querySelector(\`.tab-content[data-tab="\${tab}"]\`).style.display = 'block';
      });
    });

    // API helpers
    async function post(url, data) {
      const res = await fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data),
      });
      return await res.json();
    }

    // Playback controls
    document.getElementById('btn-next')?.addEventListener('click', async () => {
      const data = await post('/api/step/next', {});
      if (data.svg) document.getElementById('canvas-svg').innerHTML = data.svg;
      if (data.pseudocode) document.getElementById('pseudocode').innerHTML = data.pseudocode;
      if (data.explanation) document.getElementById('explanation').innerHTML = data.explanation;
      document.getElementById('current-step').textContent = data.current_step;
    });

    document.getElementById('btn-prev')?.addEventListener('click', async () => {
      const data = await post('/api/step/prev', {});
      if (data.svg) document.getElementById('canvas-svg').innerHTML = data.svg;
      if (data.pseudocode) document.getElementById('pseudocode').innerHTML = data.pseudocode;
      if (data.explanation) document.getElementById('explanation').innerHTML = data.explanation;
      document.getElementById('current-step').textContent = data.current_step;
    });

    document.getElementById('btn-rewind')?.addEventListener('click', async () => {
      const data = await post('/api/step/goto', {index: 0});
      if (data.svg) document.getElementById('canvas-svg').innerHTML = data.svg;
      if (data.pseudocode) document.getElementById('pseudocode').innerHTML = data.pseudocode;
      if (data.explanation) document.getElementById('explanation').innerHTML = data.explanation;
      document.getElementById('current-step').textContent = 0;
    });

    document.getElementById('btn-run')?.addEventListener('click', async () => {
      const data = await post('/api/run', {});
      if (data.svg) document.getElementById('canvas-svg').innerHTML = data.svg;
      if (data.pseudocode) document.getElementById('pseudocode').innerHTML = data.pseudocode;
      if (data.explanation) document.getElementById('explanation').innerHTML = data.explanation;
      if (data.analytics) document.getElementById('analytics').innerHTML = data.analytics;
      document.getElementById('current-step').textContent = data.current_step;
      document.getElementById('total-steps').textContent = data.total_steps;
    });

    // Graph generation
    document.getElementById('btn-gen-random')?.addEventListener('click', async () => {
      const data = await post('/api/graph/generate', {
        mode: 'random',
        nodes: +document.getElementById('rand-nodes').value,
        prob: +document.getElementById('rand-prob').value,
        directed: document.getElementById('rand-directed').checked,
        weighted: document.getElementById('rand-weighted').checked,
      });
      if (data.svg) document.getElementById('canvas-svg').innerHTML = data.svg;
    });

    document.getElementById('btn-gen-grid')?.addEventListener('click', async () => {
      const data = await post('/api/graph/generate', {
        mode: 'grid',
        rows: +document.getElementById('grid-rows').value,
        cols: +document.getElementById('grid-cols').value,
        wall_prob: +document.getElementById('grid-walls').value,
      });
      if (data.svg) document.getElementById('canvas-svg').innerHTML = data.svg;
    });

    document.getElementById('btn-gen-sf')?.addEventListener('click', async () => {
      const data = await post('/api/graph/generate', {
        mode: 'scale-free',
        nodes: +document.getElementById('sf-nodes').value,
        m: +document.getElementById('sf-m').value,
        weighted: document.getElementById('sf-weighted').checked,
      });
      if (data.svg) document.getElementById('canvas-svg').innerHTML = data.svg;
    });

    // Range sliders update labels
    document.getElementById('rand-prob')?.addEventListener('input', (e) => {
      document.getElementById('rand-prob-val').textContent = e.target.value;
    });
    document.getElementById('grid-walls')?.addEventListener('input', (e) => {
      document.getElementById('grid-walls-val').textContent = e.target.value;
    });

    // Algorithm selector
    document.getElementById('algo-selector')?.addEventListener('change', async (e) => {
      const data = await post('/api/config/algo', {algo_key: e.target.value});
      if (data.algo_selector) {
        const parent = document.getElementById('algo-selector').parentElement;
        parent.innerHTML = data.algo_selector;
      }
      if (data.pseudocode) document.getElementById('pseudocode').innerHTML = data.pseudocode;
    });

    // Heuristic selector
    document.addEventListener('change', async (e) => {
      if (e.target.id === 'heuristic-selector') {
        await post('/api/config/heuristic', {heuristic: e.target.value});
      }
    });

    // Speed selector
    document.getElementById('speed-selector')?.addEventListener('change', async (e) => {
      await post('/api/config/speed', {speed: e.target.value});
    });

    // Source/target selectors
    document.getElementById('source-selector')?.addEventListener('change', async (e) => {
      await post('/api/config/source_target', {source: e.target.value});
    });
    document.getElementById('target-selector')?.addEventListener('change', async (e) => {
      await post('/api/config/source_target', {target: e.target.value});
    });
  </script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  Graph Algorithm Visualizer")
    print("  Starting Flask server...")
    print("  Open http://localhost:5000")
    print("=" * 60)
    app.run(debug=True, host="0.0.0.0", port=5000)