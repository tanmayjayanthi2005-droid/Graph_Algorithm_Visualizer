"""
stepper.py — Step-by-Step Playback Engine
==========================================
The Stepper is the ONLY object the UI interacts with during a run.
It owns the generator, buffers every Step it has seen (enabling rewind),
and exposes a clean play/pause/next/prev/speed API.

State machine:
    IDLE  →  start()  →  PAUSED
    PAUSED  →  play()   →  PLAYING
    PLAYING →  pause()  →  PAUSED
    PLAYING →  (step exhausted) → FINISHED
    any     →  reset()  →  IDLE

Thread safety:
  This class is NOT thread-safe.  The UI must call advance() / play()
  from a single thread (or use an async event loop).  For the browser-
  based UI that's fine; for a Qt / Tk desktop app wrap calls in the
  main-thread dispatcher.
"""

import time
from enum import Enum
from typing import Generator, Optional, Callable, List

from algorithms.step import Step


# ---------------------------------------------------------------------------
# States
# ---------------------------------------------------------------------------
class StepperState(Enum):
    IDLE     = "idle"
    PAUSED   = "paused"
    PLAYING  = "playing"
    FINISHED = "finished"


# ---------------------------------------------------------------------------
# Speed presets (seconds per step)
# ---------------------------------------------------------------------------
SPEED_PRESETS = {
    "slow":   1.0,    # teaching mode
    "medium": 0.4,
    "fast":   0.15,   # demo mode
    "turbo":  0.05,
}


# ---------------------------------------------------------------------------
# Stepper
# ---------------------------------------------------------------------------
class Stepper:
    """
    Attributes:
        state       : Current StepperState.
        steps       : List of all Steps yielded so far (buffer for rewind).
        current_idx : Index into `steps` that is currently displayed.
        speed       : Seconds between auto-advance ticks.
        on_step     : Optional callback(Step) fired every time current step changes.
                      The UI hooks its re-render here.
    """

    def __init__(self, on_step: Optional[Callable[[Step], None]] = None):
        self._generator:  Optional[Generator[Step, None, None]] = None
        self.steps:       List[Step]    = []
        self.current_idx: int          = -1
        self.state:       StepperState = StepperState.IDLE
        self.speed:       float        = SPEED_PRESETS["medium"]
        self.on_step:     Optional[Callable[[Step], None]] = on_step

        # for auto-play timing
        self._last_tick:  float = 0.0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self, generator: Generator[Step, None, None]) -> None:
        """Attach a fresh algorithm generator and load the first step."""
        self._generator  = generator
        self.steps       = []
        self.current_idx = -1
        self.state       = StepperState.PAUSED
        # eagerly fetch step 0 so the UI can show the initial state
        self._fetch_next()
        self._goto(0)

    def reset(self) -> None:
        """Back to IDLE — caller must call start() again."""
        self._generator  = None
        self.steps       = []
        self.current_idx = -1
        self.state       = StepperState.IDLE
        self._notify(None)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def next_step(self) -> bool:
        """Advance one step forward.  Returns False if already at end."""
        target = self.current_idx + 1
        # if we haven't fetched this step yet, try
        if target >= len(self.steps):
            if not self._fetch_next():
                self.state = StepperState.FINISHED
                return False
        self._goto(target)
        return True

    def prev_step(self) -> bool:
        """Rewind one step.  Returns False if already at start."""
        if self.current_idx <= 0:
            return False
        self._goto(self.current_idx - 1)
        return True

    def goto_step(self, idx: int) -> bool:
        """Jump to an arbitrary buffered step index."""
        # fetch forward if needed
        while idx >= len(self.steps):
            if not self._fetch_next():
                break
        if 0 <= idx < len(self.steps):
            self._goto(idx)
            return True
        return False

    def rewind(self) -> None:
        """Jump back to step 0."""
        self._goto(0)

    def jump_to_end(self) -> None:
        """Exhaust the generator and jump to the final step."""
        while self._fetch_next():
            pass
        if self.steps:
            self._goto(len(self.steps) - 1)
        self.state = StepperState.FINISHED

    # ------------------------------------------------------------------
    # Play / Pause
    # ------------------------------------------------------------------
    def play(self) -> None:
        if self.state == StepperState.FINISHED:
            return
        self.state      = StepperState.PLAYING
        self._last_tick = time.monotonic()

    def pause(self) -> None:
        self.state = StepperState.PAUSED

    def toggle_play(self) -> None:
        if self.state == StepperState.PLAYING:
            self.pause()
        else:
            self.play()

    # ------------------------------------------------------------------
    # Tick  (call this from your event loop / timer)
    # ------------------------------------------------------------------
    def tick(self) -> bool:
        """
        Call periodically (e.g. every 50 ms).  If playing and enough
        time has elapsed, advances one step.  Returns True if a step
        was taken.
        """
        if self.state != StepperState.PLAYING:
            return False
        now = time.monotonic()
        if now - self._last_tick >= self.speed:
            self._last_tick = now
            if not self.next_step():
                self.state = StepperState.FINISHED
                return False
            return True
        return False

    # ------------------------------------------------------------------
    # Speed
    # ------------------------------------------------------------------
    def set_speed(self, preset: str) -> None:
        self.speed = SPEED_PRESETS.get(preset, 0.4)

    def set_speed_value(self, seconds: float) -> None:
        self.speed = max(0.02, seconds)

    # ------------------------------------------------------------------
    # Read-only accessors
    # ------------------------------------------------------------------
    @property
    def current_step(self) -> Optional[Step]:
        if 0 <= self.current_idx < len(self.steps):
            return self.steps[self.current_idx]
        return None

    @property
    def total_steps_fetched(self) -> int:
        return len(self.steps)

    @property
    def is_finished(self) -> bool:
        return self.state == StepperState.FINISHED

    @property
    def is_playing(self) -> bool:
        return self.state == StepperState.PLAYING

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _fetch_next(self) -> bool:
        """Pull one Step from the generator into the buffer."""
        if self._generator is None:
            return False
        try:
            step = next(self._generator)
            self.steps.append(step)
            return True
        except StopIteration:
            return False

    def _goto(self, idx: int) -> None:
        self.current_idx = idx
        self._notify(self.steps[idx] if 0 <= idx < len(self.steps) else None)

    def _notify(self, step: Optional[Step]) -> None:
        if self.on_step and step is not None:
            self.on_step(step)
