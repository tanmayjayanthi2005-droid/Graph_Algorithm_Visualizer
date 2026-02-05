"""
canvas.py — SVG Graph Renderer
================================
Pure rendering function: Graph + Step → SVG string.

The renderer consumes:
  • graph      – the Graph object (node positions, edges)
  • step       – the current Step snapshot (node/edge states, overlay data)
  • config     – visual config (canvas size, colors, fonts, …)

And produces an SVG string ready to inject into the DOM.

Design decisions:
  - NO mutation.  This function is stateless — the caller passes in
    everything it needs and gets back a string.
  - State-based coloring is a simple dict lookup: NodeState → hex color.
  - Edge rendering respects directedness (arrows), state (relaxed/chosen),
    and draws weights as labels.
  - Overlay panels (queue, distances, matrix) are rendered as separate
    SVG <g> groups positioned in fixed spots on the canvas.
"""

from typing import Dict, Optional, List, Tuple
import math

from graph import Graph, Node, Edge, NodeState, EdgeState
from algorithms.step import Step


# ---------------------------------------------------------------------------
# Visual Config — color palette, dimensions, fonts
# ---------------------------------------------------------------------------
class CanvasConfig:
    # canvas
    width:  int = 900
    height: int = 600
    bg:     str = "#0d1117"   # matches new theme

    # node colors (state → fill) - updated for cyan/teal theme
    node_colors: Dict[str, str] = {
        "unvisited":  "#1c2128",   # dark grey
        "frontier":   "#0ea5e9",   # cyan blue
        "frontier_b": "#f97316",   # orange (for bidirectional backward frontier)
        "visited":    "#10b981",   # emerald green
        "current":    "#06b6d4",   # bright teal — current highlight
        "path":       "#a855f7",   # purple — final path
        "blocked":    "#991b1b",   # dark red
        "source":     "#0ea5e9",   # cyan
        "target":     "#ec4899",   # pink
    }

    # edge colors - updated
    edge_colors: Dict[str, str] = {
        "default":  "#30363d",   # medium grey
        "relaxed":  "#06b6d4",   # teal pulse
        "chosen":   "#a855f7",   # purple — on the path
        "ignored":  "#21262d",   # faded grey
        "active":   "#06b6d4",   # current-step teal
    }

    # node
    node_radius:        int = 20
    node_stroke:        str = "#30363d"
    node_stroke_width:  int = 2
    node_label_color:   str = "#e6edf3"
    node_label_size:    int = 13
    node_label_weight:  str = "600"

    # edge
    edge_width:         int = 2
    edge_width_chosen:  int = 4
    edge_arrow_size:    int = 10
    edge_weight_color:  str = "#7d8590"
    edge_weight_size:   int = 12
    edge_weight_bg:     str = "#161b22"

    # overlay panels - updated to match theme
    overlay_bg:         str = "#161b22"
    overlay_border:     str = "#30363d"
    overlay_text:       str = "#7d8590"
    overlay_header:     str = "#e6edf3"
    overlay_accent:     str = "#0ea5e9"
    overlay_font_size:  int = 13


CONFIG = CanvasConfig()


# ---------------------------------------------------------------------------
# Main Render Function
# ---------------------------------------------------------------------------
def render_canvas(
    graph: Graph,
    step: Optional[Step] = None,
    config: CanvasConfig = CONFIG,
    show_overlays: bool = True,
) -> str:
    """
    Returns an SVG string.

    Args:
        graph         : The graph to render.
        step          : Current algorithm step (or None for static graph).
        config        : Visual config.
        show_overlays : If True, render queue/distances/matrix panels.
    """

    svg_parts = [
        f'<svg width="{config.width}" height="{config.height}" '
        f'viewBox="0 0 {config.width} {config.height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="background: {config.bg};">'
    ]

    # background rect
    svg_parts.append(
        f'<rect width="{config.width}" height="{config.height}" fill="{config.bg}"/>'
    )

    # -- edges (draw first so nodes sit on top) --
    for edge in graph.edges.values():
        svg_parts.append(_render_edge(graph, edge, step, config))

    # -- nodes --
    for node in graph.nodes.values():
        svg_parts.append(_render_node(node, step, config))

    # -- overlays --
    if show_overlays and step:
        svg_parts.append(_render_overlays(step, config))

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


# ---------------------------------------------------------------------------
# Node Rendering
# ---------------------------------------------------------------------------
def _render_node(node: Node, step: Optional[Step], config: CanvasConfig) -> str:
    # determine fill color from step's node_states, or fallback to node.state
    state_key = node.state.value
    if step and node.id in step.node_states:
        state_key = step.node_states[node.id]

    fill = config.node_colors.get(state_key, config.node_colors["unvisited"])

    # highlight if this is the current node
    stroke = config.node_stroke
    stroke_width = config.node_stroke_width
    glow = ""
    
    if step and step.current_node == node.id:
        stroke = config.node_colors["current"]
        stroke_width = 3
        # add glow effect for current node
        glow = f'<circle cx="{node.x}" cy="{node.y}" r="{config.node_radius + 8}" fill="none" stroke="{config.node_colors["current"]}" stroke-width="2" opacity="0.3"/>'

    cx, cy = node.x, node.y
    r = config.node_radius

    parts = [
        f'<g class="node" data-id="{node.id}">',
        glow,
        f'  <circle cx="{cx}" cy="{cy}" r="{r}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>',
        f'  <text x="{cx}" y="{cy + 5}" text-anchor="middle" '
        f'font-size="{config.node_label_size}" font-family="\'DM Sans\', sans-serif" '
        f'fill="{config.node_label_color}" font-weight="{config.node_label_weight}">{node.label}</text>',
        '</g>',
    ]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Edge Rendering
# ---------------------------------------------------------------------------
def _render_edge(graph: Graph, edge: Edge, step: Optional[Step], config: CanvasConfig) -> str:
    src_node = graph.get_node(edge.source)
    tgt_node = graph.get_node(edge.target)
    if not src_node or not tgt_node:
        return ""

    # determine stroke color from step's edge_states
    state_key = edge.state.value
    if step and edge.id in step.edge_states:
        state_key = step.edge_states[edge.id]

    stroke = config.edge_colors.get(state_key, config.edge_colors["default"])
    stroke_width = config.edge_width
    if state_key == "chosen":
        stroke_width = config.edge_width_chosen

    # highlight if this is the current edge
    if step and step.current_edge == edge.id:
        stroke = config.edge_colors["active"]
        stroke_width = 4

    # compute line endpoints (adjusted for node radius so line doesn't overlap circle)
    x1, y1 = src_node.x, src_node.y
    x2, y2 = tgt_node.x, tgt_node.y

    # shorten the line by node_radius on both ends
    dx, dy = x2 - x1, y2 - y1
    dist = math.sqrt(dx * dx + dy * dy)
    if dist < 0.001:
        return ""  # degenerate edge

    ux, uy = dx / dist, dy / dist
    r = config.node_radius

    x1_adj = x1 + ux * r
    y1_adj = y1 + uy * r
    x2_adj = x2 - ux * r
    y2_adj = y2 - uy * r

    parts = [f'<g class="edge" data-id="{edge.id}">']

    # line
    parts.append(
        f'  <line x1="{x1_adj}" y1="{y1_adj}" x2="{x2_adj}" y2="{y2_adj}" '
        f'stroke="{stroke}" stroke-width="{stroke_width}"/>'
    )

    # arrow (if directed)
    if edge.directed:
        parts.append(_render_arrow(x2_adj, y2_adj, ux, uy, stroke, config))

    # weight label (at midpoint)
    if graph.weighted and edge.weight != 1.0:
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2
        # offset label perpendicular to edge
        perp_x = -uy * 12
        perp_y = ux * 12
        # background circle for better readability
        parts.append(
            f'  <circle cx="{mx + perp_x}" cy="{my + perp_y}" r="12" '
            f'fill="{config.edge_weight_bg}" opacity="0.9"/>'
        )
        parts.append(
            f'  <text x="{mx + perp_x}" y="{my + perp_y + 4}" text-anchor="middle" '
            f'font-size="{config.edge_weight_size}" font-family="\'DM Sans\', sans-serif" '
            f'fill="{config.edge_weight_color}" font-weight="600">{edge.weight}</text>'
        )

    parts.append('</g>')
    return "\n".join(parts)


def _render_arrow(x: float, y: float, ux: float, uy: float, color: str, config: CanvasConfig) -> str:
    """Draw an arrowhead at (x, y) pointing in direction (ux, uy)."""
    size = config.edge_arrow_size
    # perpendicular
    px, py = -uy, ux
    # two points of the triangle
    p1_x = x - ux * size + px * (size * 0.5)
    p1_y = y - uy * size + py * (size * 0.5)
    p2_x = x - ux * size - px * (size * 0.5)
    p2_y = y - uy * size - py * (size * 0.5)
    return f'<polygon points="{x},{y} {p1_x},{p1_y} {p2_x},{p2_y}" fill="{color}"/>'


# ---------------------------------------------------------------------------
# Overlay Panels
# ---------------------------------------------------------------------------
def _render_overlays(step: Step, config: CanvasConfig) -> str:
    """Render queue / distance table / matrix in fixed positions on the canvas."""
    parts = ['<g class="overlays">']

    # -- Queue / Stack panel (top-right) --
    if "queue" in step.overlay:
        parts.append(_render_queue_panel(step.overlay["queue"], config, x=620, y=20))
    elif "stack" in step.overlay:
        parts.append(_render_stack_panel(step.overlay["stack"], config, x=620, y=20))
    elif "queue_forward" in step.overlay or "queue_backward" in step.overlay:
        qf = step.overlay.get("queue_forward", [])
        qb = step.overlay.get("queue_backward", [])
        parts.append(_render_bidi_queues(qf, qb, config, x=620, y=20))

    # -- Distance / Scores table (bottom-right) --
    if "distances" in step.overlay and isinstance(step.overlay["distances"], dict):
        parts.append(_render_distances_panel(step.overlay["distances"], config, x=620, y=220))
    elif "scores" in step.overlay:
        parts.append(_render_scores_panel(step.overlay["scores"], config, x=620, y=220))

    # -- Matrix panel (for Floyd-Warshall) (center) --
    if "matrix" in step.overlay:
        parts.append(_render_matrix_panel(step.overlay["matrix"], config, x=200, y=50))

    parts.append('</g>')
    return "\n".join(parts)


def _render_queue_panel(queue: List, config: CanvasConfig, x: int, y: int) -> str:
    """Priority queue: [(priority, node_id), ...]"""
    parts = [
        f'<g class="queue-panel" transform="translate({x},{y})">',
        f'  <rect width="260" height="180" fill="{config.overlay_bg}" stroke="{config.overlay_border}" stroke-width="1" rx="8" opacity="0.95"/>',
        f'  <text x="12" y="22" font-size="13" font-weight="700" fill="{config.overlay_accent}" font-family="\'DM Sans\', sans-serif" text-transform="uppercase" letter-spacing="0.5">Priority Queue</text>',
    ]
    # show top 8 entries
    for i, item in enumerate(queue[:8]):
        if isinstance(item, tuple) and len(item) == 2:
            priority, nid = item
            txt = f"({priority:.1f}, {nid})"
        else:
            txt = str(item)
        parts.append(
            f'  <text x="16" y="{48 + i * 16}" font-size="{config.overlay_font_size}" '
            f'font-family="\'JetBrains Mono\', monospace" fill="{config.overlay_text}">{txt}</text>'
        )
    if len(queue) > 8:
        parts.append(
            f'  <text x="16" y="{48 + 8 * 16}" font-size="11" fill="#484f58">… +{len(queue)-8} more</text>'
        )
    parts.append('</g>')
    return "\n".join(parts)


def _render_stack_panel(stack: List, config: CanvasConfig, x: int, y: int) -> str:
    parts = [
        f'<g class="stack-panel" transform="translate({x},{y})">',
        f'  <rect width="260" height="180" fill="{config.overlay_bg}" stroke="{config.overlay_border}" stroke-width="1" rx="8" opacity="0.95"/>',
        f'  <text x="12" y="22" font-size="13" font-weight="700" fill="{config.overlay_accent}" font-family="\'DM Sans\', sans-serif" text-transform="uppercase" letter-spacing="0.5">Stack (DFS)</text>',
    ]
    for i, nid in enumerate(stack[:8]):
        parts.append(
            f'  <text x="16" y="{48 + i * 16}" font-size="{config.overlay_font_size}" '
            f'font-family="\'JetBrains Mono\', monospace" fill="{config.overlay_text}">{nid}</text>'
        )
    if len(stack) > 8:
        parts.append(
            f'  <text x="16" y="{48 + 8 * 16}" font-size="11" fill="#484f58">… +{len(stack)-8} more</text>'
        )
    parts.append('</g>')
    return "\n".join(parts)


def _render_bidi_queues(qf: List, qb: List, config: CanvasConfig, x: int, y: int) -> str:
    parts = [
        f'<g class="bidi-panel" transform="translate({x},{y})">',
        f'  <rect width="260" height="200" fill="{config.overlay_bg}" rx="6" opacity="0.95"/>',
        f'  <text x="10" y="20" font-size="14" font-weight="700" fill="{config.overlay_header}">Bidirectional BFS</text>',
        f'  <text x="10" y="40" font-size="12" font-weight="600" fill="#3b82f6">Forward:</text>',
    ]
    for i, nid in enumerate(qf[:4]):
        parts.append(
            f'  <text x="15" y="{55 + i * 14}" font-size="12" font-family="monospace" fill="{config.overlay_text}">{nid}</text>'
        )
    parts.append(f'  <text x="10" y="115" font-size="12" font-weight="600" fill="#f97316">Backward:</text>')
    for i, nid in enumerate(qb[:4]):
        parts.append(
            f'  <text x="15" y="{130 + i * 14}" font-size="12" font-family="monospace" fill="{config.overlay_text}">{nid}</text>'
        )
    parts.append('</g>')
    return "\n".join(parts)


def _render_distances_panel(distances: Dict[str, float], config: CanvasConfig, x: int, y: int) -> str:
    parts = [
        f'<g class="distances-panel" transform="translate({x},{y})">',
        f'  <rect width="260" height="340" fill="{config.overlay_bg}" rx="6" opacity="0.95"/>',
        f'  <text x="10" y="20" font-size="14" font-weight="700" fill="{config.overlay_header}">Distances</text>',
    ]
    # sort by distance
    items = sorted(distances.items(), key=lambda kv: (kv[1], kv[0]))
    for i, (nid, d) in enumerate(items[:18]):
        d_str = f"{d:.1f}" if d != float("inf") else "∞"
        parts.append(
            f'  <text x="15" y="{40 + i * 16}" font-size="{config.overlay_font_size}" '
            f'font-family="monospace" fill="{config.overlay_text}">{nid}: {d_str}</text>'
        )
    if len(items) > 18:
        parts.append(
            f'  <text x="15" y="{40 + 18 * 16}" font-size="12" fill="#6b7280">… +{len(items)-18} more</text>'
        )
    parts.append('</g>')
    return "\n".join(parts)


def _render_scores_panel(scores: List[Dict], config: CanvasConfig, x: int, y: int) -> str:
    """For A* / Greedy — shows g, h, f."""
    parts = [
        f'<g class="scores-panel" transform="translate({x},{y})">',
        f'  <rect width="260" height="340" fill="{config.overlay_bg}" rx="6" opacity="0.95"/>',
        f'  <text x="10" y="20" font-size="14" font-weight="700" fill="{config.overlay_header}">A* Scores</text>',
        f'  <text x="10" y="38" font-size="11" fill="#9ca3af">node  g    h    f</text>',
    ]
    for i, item in enumerate(scores[:16]):
        n = item.get("node", "?")
        g = item.get("g", float("inf"))
        h = item.get("h", 0)
        f = item.get("f", float("inf"))
        g_str = f"{g:.1f}" if g != float("inf") else "∞"
        h_str = f"{h:.1f}"
        f_str = f"{f:.1f}" if f != float("inf") else "∞"
        parts.append(
            f'  <text x="10" y="{55 + i * 16}" font-size="11" font-family="monospace" fill="{config.overlay_text}">'
            f'{n:4s} {g_str:4s} {h_str:4s} {f_str:4s}</text>'
        )
    if len(scores) > 16:
        parts.append(
            f'  <text x="10" y="{55 + 16 * 16}" font-size="11" fill="#6b7280">… +{len(scores)-16} more</text>'
        )
    parts.append('</g>')
    return "\n".join(parts)


def _render_matrix_panel(matrix: List[Dict], config: CanvasConfig, x: int, y: int) -> str:
    """Floyd-Warshall live matrix."""
    n = len(matrix)
    if n == 0:
        return ""
    cell_size = min(40, 500 // n)
    parts = [
        f'<g class="matrix-panel" transform="translate({x},{y})">',
        f'  <rect width="{n * cell_size + 20}" height="{n * cell_size + 40}" '
        f'fill="{config.overlay_bg}" rx="6" opacity="0.95"/>',
        f'  <text x="10" y="18" font-size="13" font-weight="700" fill="{config.overlay_header}">Distance Matrix</text>',
    ]
    # render grid
    for i, row_data in enumerate(matrix):
        label = row_data.get("label", str(i))
        values = row_data.get("values", [])
        # row label
        parts.append(
            f'  <text x="5" y="{35 + i * cell_size + cell_size // 2 + 4}" '
            f'font-size="10" fill="#9ca3af">{label}</text>'
        )
        for j, val in enumerate(values):
            cx = 30 + j * cell_size
            cy = 30 + i * cell_size
            val_str = str(val) if val != "∞" else "∞"
            # cell bg
            parts.append(
                f'  <rect x="{cx}" y="{cy}" width="{cell_size}" height="{cell_size}" '
                f'fill="#1f2937" stroke="#374151" stroke-width="1"/>'
            )
            # value
            parts.append(
                f'  <text x="{cx + cell_size // 2}" y="{cy + cell_size // 2 + 4}" '
                f'text-anchor="middle" font-size="9" fill="{config.overlay_text}">{val_str}</text>'
            )
    parts.append('</g>')
    return "\n".join(parts)