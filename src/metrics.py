"""Privacy-preserving aggregate metrics for Omacount.

This module deliberately has no concept of text, applications, windows, or
ordered key history.  It consumes one input event at a time and retains only
totals, short-lived modifier state, and anonymous per-second typing buckets.
"""

from __future__ import annotations

import math
import time
from collections import deque
from copy import deepcopy


SCHEMA_VERSION = 2
ACTIVE_GRACE_SECONDS = 5.0
SCROLL_GRACE_SECONDS = 1.0
RAGE_WINDOW_SECONDS = 0.8
RAGE_RADIUS_PX = 28.0


# Linux input-event key codes.  Human-readable labels are derived from the
# physical key only; no keyboard layout, composed character, or typed string is
# ever requested or retained.
KEY_NAMES = {
    1: "Esc", 2: "1", 3: "2", 4: "3", 5: "4", 6: "5", 7: "6",
    8: "7", 9: "8", 10: "9", 11: "0", 12: "-", 13: "=",
    14: "Backspace", 15: "Tab", 16: "Q", 17: "W", 18: "E", 19: "R",
    20: "T", 21: "Y", 22: "U", 23: "I", 24: "O", 25: "P",
    26: "[", 27: "]", 28: "Enter", 29: "Left Ctrl", 30: "A",
    31: "S", 32: "D", 33: "F", 34: "G", 35: "H", 36: "J",
    37: "K", 38: "L", 39: ";", 40: "'", 41: "`", 42: "Left Shift",
    43: "\\", 44: "Z", 45: "X", 46: "C", 47: "V", 48: "B",
    49: "N", 50: "M", 51: ",", 52: ".", 53: "/", 54: "Right Shift",
    55: "Numpad *", 56: "Left Alt", 57: "Space", 58: "Caps Lock",
    59: "F1", 60: "F2", 61: "F3", 62: "F4", 63: "F5", 64: "F6",
    65: "F7", 66: "F8", 67: "F9", 68: "F10", 69: "Num Lock",
    70: "Scroll Lock", 71: "Numpad 7", 72: "Numpad 8", 73: "Numpad 9",
    74: "Numpad -", 75: "Numpad 4", 76: "Numpad 5", 77: "Numpad 6",
    78: "Numpad +", 79: "Numpad 1", 80: "Numpad 2", 81: "Numpad 3",
    82: "Numpad 0", 83: "Numpad .", 87: "F11", 88: "F12",
    96: "Numpad Enter", 97: "Right Ctrl", 98: "Numpad /",
    99: "Print Screen", 100: "Right Alt", 102: "Home", 103: "Up",
    104: "Page Up", 105: "Left", 106: "Right", 107: "End", 108: "Down",
    109: "Page Down", 110: "Insert", 111: "Delete", 113: "Mute",
    114: "Volume Down", 115: "Volume Up", 116: "Power", 119: "Pause",
    125: "Left Super", 126: "Right Super", 127: "Menu",
}

KEY_IDS = {code: "KEY_" + name.upper().replace(" ", "_").replace("-", "MINUS")
           .replace("=", "EQUAL").replace("[", "LEFTBRACE")
           .replace("]", "RIGHTBRACE").replace(";", "SEMICOLON")
           .replace("'", "APOSTROPHE").replace("`", "GRAVE")
           .replace("\\", "BACKSLASH").replace(",", "COMMA")
           .replace(".", "DOT").replace("/", "SLASH").replace("*", "ASTERISK")
           for code, name in KEY_NAMES.items()}

# Match canonical Linux names used by the QML heatmap.
KEY_IDS.update({
    12: "KEY_MINUS", 13: "KEY_EQUAL", 26: "KEY_LEFTBRACE",
    27: "KEY_RIGHTBRACE", 39: "KEY_SEMICOLON", 40: "KEY_APOSTROPHE",
    41: "KEY_GRAVE", 43: "KEY_BACKSLASH", 51: "KEY_COMMA",
    52: "KEY_DOT", 53: "KEY_SLASH", 55: "KEY_KPASTERISK",
    96: "KEY_KPENTER", 98: "KEY_KPSLASH", 99: "KEY_SYSRQ",
    125: "KEY_LEFTMETA", 126: "KEY_RIGHTMETA", 127: "KEY_COMPOSE",
})

MODIFIERS = {
    29: "Ctrl", 97: "Ctrl", 42: "Shift", 54: "Shift",
    56: "Alt", 100: "AltGr", 125: "Super", 126: "Super",
}
MODIFIER_ORDER = ("Ctrl", "Alt", "AltGr", "Shift", "Super")
PRINTABLE_CODES = set(range(2, 14)) | set(range(16, 28)) | set(range(30, 54)) | {57}
UNDO_CODES = {14, 111}
TEXT_CONTROL_CODES = {15, 28, 96}  # Tab, Enter, and numpad Enter.
TYPING_CODES = PRINTABLE_CODES | UNDO_CODES | TEXT_CONTROL_CODES
LEFT_BUTTON = 272


def default_totals() -> dict:
    return {
        "pointer_distance_mm": 0.0,
        "scroll_distance_mm": 0.0,
        "active_time_seconds": 0.0,
        "mouse_time_seconds": 0.0,
        "typing_time_seconds": 0.0,
        "scroll_time_seconds": 0.0,
        "rage_clicks": 0,
        "button_presses": 0,
        "keys_pressed": 0,
        "shortcut_count": 0,
        "typed_keys": 0,
        "undone_keys": 0,
        "peak_wpm": 0.0,
        "peak_scroll_speed_mm_s": 0.0,
    }


def default_state() -> dict:
    return {
        "schema": SCHEMA_VERSION,
        "totals": default_totals(),
        "per_key": {},
        "shortcuts": {},
    }


def _finite_nonnegative(value, fallback=0.0):
    try:
        value = float(value)
        return value if math.isfinite(value) and value >= 0 else fallback
    except (TypeError, ValueError):
        return fallback


def sanitize_state(raw: dict | None) -> dict:
    """Return a schema-safe state, discarding unknown/private structures."""
    state = default_state()
    if not isinstance(raw, dict) or raw.get("schema") not in {1, SCHEMA_VERSION}:
        return state

    legacy_keyboard_totals = raw.get("schema") == 1

    source_totals = raw.get("totals") if isinstance(raw.get("totals"), dict) else {}
    integer_fields = {"rage_clicks", "button_presses", "keys_pressed",
                      "shortcut_count", "typed_keys", "undone_keys"}
    for key in state["totals"]:
        # Schema 1 counted shortcut components as typed keys and placed them in
        # the heatmap. Those aggregates cannot be separated after the fact, so
        # reset only the affected keyboard-derived fields during migration.
        if legacy_keyboard_totals and key in {
                "keys_pressed", "typed_keys", "undone_keys", "peak_wpm",
                "typing_time_seconds"}:
            continue
        value = _finite_nonnegative(source_totals.get(key, 0))
        state["totals"][key] = int(value) if key in integer_fields else value

    for field in ("per_key", "shortcuts"):
        if legacy_keyboard_totals and field == "per_key":
            continue
        source = raw.get(field) if isinstance(raw.get(field), dict) else {}
        clean = {}
        for key, value in source.items():
            if not isinstance(key, str) or not key or len(key) > 80:
                continue
            count = int(_finite_nonnegative(value))
            if count:
                clean[key] = count
        state[field] = clean
    return state


class MetricsEngine:
    """Incrementally updates aggregate statistics from sanitized input events."""

    def __init__(self, state: dict | None = None, now: float | None = None):
        clean = sanitize_state(state)
        self.totals = clean["totals"]
        self.per_key = clean["per_key"]
        self.shortcuts = clean["shortcuts"]
        self._last_clock = time.monotonic() if now is None else now
        self._last_any = None
        self._last_mouse = None
        self._last_typing = None
        self._last_scroll = None
        self._last_scroll_event = None
        self._modifiers_down: set[int] = set()
        self._typing_buckets: deque[list[float]] = deque()
        self._clicks: deque[tuple[float, float, float]] = deque()
        self._rage_latched = False

    def _accrue_window(self, start: float, end: float, last, grace: float) -> float:
        if last is None or end <= start:
            return 0.0
        return max(0.0, min(end, last + grace) - start)

    def advance(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        # Suspend/resume and clock anomalies should not manufacture activity.
        start = max(self._last_clock, now - 60.0)
        self.totals["active_time_seconds"] += self._accrue_window(
            start, now, self._last_any, ACTIVE_GRACE_SECONDS)
        self.totals["mouse_time_seconds"] += self._accrue_window(
            start, now, self._last_mouse, ACTIVE_GRACE_SECONDS)
        self.totals["typing_time_seconds"] += self._accrue_window(
            start, now, self._last_typing, ACTIVE_GRACE_SECONDS)
        self.totals["scroll_time_seconds"] += self._accrue_window(
            start, now, self._last_scroll, SCROLL_GRACE_SECONDS)
        self._last_clock = now

    def _mark_activity(self, kind: str, now: float) -> None:
        self.advance(now)
        self._last_any = now
        if kind == "mouse":
            self._last_mouse = now
        elif kind == "typing":
            self._last_typing = now

    def pointer_motion(self, dx: float, dy: float, mm_per_px_x: float,
                       mm_per_px_y: float, now: float) -> float:
        dx = float(dx)
        dy = float(dy)
        distance = math.hypot(dx * mm_per_px_x, dy * mm_per_px_y)
        if not math.isfinite(distance) or distance <= 0:
            return 0.0
        self._mark_activity("mouse", now)
        self.totals["pointer_distance_mm"] += distance
        return distance

    def scroll(self, dx_px: float, dy_px: float, mm_per_px_x: float,
               mm_per_px_y: float, now: float) -> float:
        distance = math.hypot(float(dx_px) * mm_per_px_x,
                              float(dy_px) * mm_per_px_y)
        if not math.isfinite(distance) or distance <= 0:
            return 0.0
        self._mark_activity("mouse", now)
        self._last_scroll = now
        self.totals["scroll_distance_mm"] += distance
        if self._last_scroll_event is not None:
            dt = now - self._last_scroll_event
            if 0.002 <= dt <= 1.0:
                speed = distance / dt
                self.totals["peak_scroll_speed_mm_s"] = max(
                    self.totals["peak_scroll_speed_mm_s"], speed)
        self._last_scroll_event = now
        return distance

    def pointer_button(self, button: int, pressed: bool, x: float, y: float,
                       now: float) -> None:
        if not pressed:
            return
        self._mark_activity("mouse", now)
        self.totals["button_presses"] += 1
        if button != LEFT_BUTTON:
            return

        while self._clicks and now - self._clicks[0][0] > RAGE_WINDOW_SECONDS:
            self._clicks.popleft()
        if self._clicks and math.hypot(x - self._clicks[-1][1], y - self._clicks[-1][2]) > RAGE_RADIUS_PX:
            self._clicks.clear()
            self._rage_latched = False
        self._clicks.append((now, x, y))
        if len(self._clicks) < 3:
            self._rage_latched = False
        elif not self._rage_latched:
            self.totals["rage_clicks"] += 1
            self._rage_latched = True

    def _active_modifier_names(self) -> list[str]:
        active = {MODIFIERS[code] for code in self._modifiers_down if code in MODIFIERS}
        return [name for name in MODIFIER_ORDER if name in active]

    def _shortcut_name(self, code: int) -> str | None:
        modifiers = self._active_modifier_names()
        # Shift alone is normal typing; Ctrl/Alt/Super makes a chord a shortcut.
        if not ({"Ctrl", "Alt", "Super"} & set(modifiers)):
            return None
        key = KEY_NAMES.get(code, f"Key {code}")
        return "+".join(modifiers + [key])

    def _update_peak_wpm(self, now: float) -> None:
        second = int(now)
        while self._typing_buckets and self._typing_buckets[0][0] < second - 59:
            self._typing_buckets.popleft()
        if self._typing_buckets and self._typing_buckets[-1][0] == second:
            self._typing_buckets[-1][1] += 1
        else:
            self._typing_buckets.append([second, 1])
        # A fixed 60-second denominator avoids advertising absurd instant WPM.
        rolling = sum(bucket[1] for bucket in self._typing_buckets) / 5.0
        self.totals["peak_wpm"] = max(self.totals["peak_wpm"], rolling)

    def keyboard_key(self, code: int, pressed: bool, now: float,
                     typing_context: bool = True) -> None:
        """Count a physical key without retaining text or key order.

        Ctrl/Alt/Super chords are shortcut aggregates regardless of text
        focus. The typed-key headline, WPM inputs, and heatmap receive only
        typing-capable keys pressed while a text input context is focused.
        """
        if not pressed:
            self._modifiers_down.discard(code)
            return

        if code in MODIFIERS:
            self._modifiers_down.add(code)
            return

        shortcut = self._shortcut_name(code)
        if shortcut:
            self._mark_activity("keyboard", now)
            self.totals["shortcut_count"] += 1
            self.shortcuts[shortcut] = self.shortcuts.get(shortcut, 0) + 1
            return

        if not typing_context or code not in TYPING_CODES:
            return

        self._mark_activity("typing", now)
        self.totals["keys_pressed"] += 1
        key_id = KEY_IDS.get(code, f"KEY_{code}")
        self.per_key[key_id] = self.per_key.get(key_id, 0) + 1

        if code in PRINTABLE_CODES:
            self.totals["typed_keys"] += 1
            self._update_peak_wpm(now)
        if code in UNDO_CODES:
            self.totals["undone_keys"] += 1

    def reset(self, now: float | None = None) -> None:
        self.totals = default_totals()
        self.per_key = {}
        self.shortcuts = {}
        self._last_clock = time.monotonic() if now is None else now
        self._last_any = self._last_mouse = self._last_typing = None
        self._last_scroll = self._last_scroll_event = None
        self._modifiers_down.clear()
        self._typing_buckets.clear()
        self._clicks.clear()
        self._rage_latched = False

    def suspend(self, now: float | None = None) -> None:
        """Close activity windows and forget all ephemeral input state."""
        now = time.monotonic() if now is None else now
        self.advance(now)
        self._last_any = self._last_mouse = self._last_typing = None
        self._last_scroll = self._last_scroll_event = None
        self._modifiers_down.clear()
        self._typing_buckets.clear()
        self._clicks.clear()
        self._rage_latched = False

    def persistent_state(self, now: float | None = None) -> dict:
        self.advance(now)
        return {
            "schema": SCHEMA_VERSION,
            "totals": deepcopy(self.totals),
            "per_key": deepcopy(self.per_key),
            "shortcuts": deepcopy(self.shortcuts),
        }

    def snapshot(self, now: float | None = None) -> dict:
        state = self.persistent_state(now)
        totals = state["totals"]
        typing_minutes = totals["typing_time_seconds"] / 60.0
        totals["average_wpm"] = ((totals["typed_keys"] / 5.0) / typing_minutes
                                 if typing_minutes > 0 else 0.0)
        totals["accuracy_percent"] = (max(0.0, 1.0 - totals["undone_keys"] /
                                                  totals["typed_keys"]) * 100.0
                                      if totals["typed_keys"] else 100.0)
        totals["typing_mouse_ratio"] = (totals["typing_time_seconds"] /
                                          totals["mouse_time_seconds"]
                                          if totals["mouse_time_seconds"] else
                                          (1.0 if totals["typing_time_seconds"] else 0.0))
        totals["average_scroll_speed_mm_s"] = (
            totals["scroll_distance_mm"] / totals["scroll_time_seconds"]
            if totals["scroll_time_seconds"] else 0.0)

        pointer_metres = totals["pointer_distance_mm"] / 1000.0
        scroll_metres = totals["scroll_distance_mm"] / 1000.0
        totals["pointer_calories"] = (pointer_metres * 0.00010
                                       + scroll_metres * 0.00015
                                       + totals["button_presses"] * 0.000001)
        totals["keyboard_calories"] = totals["keys_pressed"] * 0.000002
        totals["calories_total"] = (totals["pointer_calories"]
                                     + totals["keyboard_calories"])
        return state
