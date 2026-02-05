"""
ui/
---
Presentation layer.

    from ui import render_canvas
    from ui import playback_controls, algorithm_selector, …
"""

from ui.canvas import render_canvas, CanvasConfig

from ui.controls import (
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

__all__ = [
    "render_canvas",
    "CanvasConfig",
    "playback_controls",
    "algorithm_selector",
    "graph_generator",
    "source_target_picker",
    "analytics_panel",
    "comparison_panel",
    "pseudocode_viewer",
    "explanation_panel",
    "heuristic_playground",
    "mode_toggle",
]
