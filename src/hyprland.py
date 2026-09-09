"""Small direct Hyprland IPC client used for monitor-aware distance mapping."""

from __future__ import annotations

import glob
import json
import math
import os
import socket
import time
from dataclasses import dataclass
from pathlib import Path


FALLBACK_MM_PER_PX = 25.4 / 96.0


@dataclass
class Monitor:
    name: str
    x: float
    y: float
    logical_width: float
    logical_height: float
    mm_per_px_x: float
    mm_per_px_y: float
    calibrated: bool

    def contains(self, x: float, y: float) -> bool:
        return (self.x <= x < self.x + self.logical_width
                and self.y <= y < self.y + self.logical_height)

    def distance_to(self, x: float, y: float) -> float:
        near_x = min(max(x, self.x), self.x + self.logical_width)
        near_y = min(max(y, self.y), self.y + self.logical_height)
        return math.hypot(x - near_x, y - near_y)


class HyprlandGeometry:
    def __init__(self, runtime_dir: str | None = None):
        self.runtime_dir = runtime_dir or os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
        self.command_socket: str | None = None
        self.event_socket_path: str | None = None
        self.monitors: list[Monitor] = []
        self.cursor_x = 0.0
        self.cursor_y = 0.0
        # Boolean only: Omacount deliberately never retains a window address,
        # class, title, application name, or focus history.
        self.window_focused = False
        self.calibration = "fallback-96dpi"
        self._last_boundary_sync = 0.0

    def _discover(self) -> bool:
        signature = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "")
        candidates = []
        if signature:
            candidates.append(Path(self.runtime_dir) / "hypr" / signature)
        candidates.extend(Path(path) for path in glob.glob(str(Path(self.runtime_dir) / "hypr" / "*")))
        for directory in candidates:
            command = directory / ".socket.sock"
            events = directory / ".socket2.sock"
            if command.exists() and events.exists():
                self.command_socket = str(command)
                self.event_socket_path = str(events)
                return True
        self.command_socket = self.event_socket_path = None
        return False

    def request(self, command: str):
        if not self.command_socket and not self._discover():
            return None
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(1.0)
                client.connect(self.command_socket)
                client.sendall(command.encode("utf-8"))
                chunks = []
                while True:
                    chunk = client.recv(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
            return json.loads(b"".join(chunks).decode("utf-8"))
        except (OSError, ValueError, TypeError):
            self.command_socket = self.event_socket_path = None
            return None

    def refresh(self) -> bool:
        raw_monitors = self.request("j/monitors")
        raw_cursor = self.request("j/cursorpos")
        raw_window = self.request("j/activewindow")
        monitors = []
        if isinstance(raw_monitors, list):
            for raw in raw_monitors:
                try:
                    scale = max(0.01, float(raw.get("scale", 1)))
                    logical_width = float(raw["width"]) / scale
                    logical_height = float(raw["height"]) / scale
                    physical_width = float(raw.get("physicalWidth", 0))
                    physical_height = float(raw.get("physicalHeight", 0))
                    transform = int(raw.get("transform", 0))
                    if transform in {1, 3, 5, 7}:
                        physical_width, physical_height = physical_height, physical_width
                    calibrated = physical_width > 0 and physical_height > 0
                    mm_x = physical_width / logical_width if calibrated else FALLBACK_MM_PER_PX
                    mm_y = physical_height / logical_height if calibrated else FALLBACK_MM_PER_PX
                    monitors.append(Monitor(
                        str(raw.get("name", "display")), float(raw.get("x", 0)),
                        float(raw.get("y", 0)), logical_width, logical_height,
                        mm_x, mm_y, calibrated))
                except (KeyError, TypeError, ValueError, ZeroDivisionError):
                    continue
        if monitors:
            self.monitors = monitors
            self.calibration = ("edid-physical-size" if all(m.calibrated for m in monitors)
                                else "mixed-edid-and-96dpi")
        if isinstance(raw_cursor, dict):
            try:
                self.cursor_x = float(raw_cursor["x"])
                self.cursor_y = float(raw_cursor["y"])
            except (KeyError, TypeError, ValueError):
                pass
        self.window_focused = bool(
            isinstance(raw_window, dict)
            and raw_window.get("address") not in {None, "", "0x0"}
            and raw_window.get("mapped", True)
        )
        return bool(self.monitors)

    def resync_cursor(self) -> bool:
        raw_cursor = self.request("j/cursorpos")
        if not isinstance(raw_cursor, dict):
            return False
        try:
            self.cursor_x = float(raw_cursor["x"])
            self.cursor_y = float(raw_cursor["y"])
            return True
        except (KeyError, TypeError, ValueError):
            return False

    def current_monitor(self) -> Monitor | None:
        for monitor in self.monitors:
            if monitor.contains(self.cursor_x, self.cursor_y):
                return monitor
        if self.monitors:
            return min(self.monitors, key=lambda m: m.distance_to(self.cursor_x, self.cursor_y))
        return None

    def scale_for_motion(self, dx: float, dy: float) -> tuple[float, float]:
        monitor = self.current_monitor()
        mm_x = monitor.mm_per_px_x if monitor else FALLBACK_MM_PER_PX
        mm_y = monitor.mm_per_px_y if monitor else FALLBACK_MM_PER_PX
        self.cursor_x += dx
        self.cursor_y += dy
        # The event stream provides deltas but Hyprland may clamp or constrain
        # the cursor.  On multi-monitor boundary crossings only, resynchronize
        # through IPC so different monitor scales remain correctly selected.
        # This is input-triggered rather than a cursor-position polling loop.
        now = time.monotonic()
        if (len(self.monitors) > 1 and monitor
                and not monitor.contains(self.cursor_x, self.cursor_y)
                and now - self._last_boundary_sync >= 0.25):
            self._last_boundary_sync = now
            self.resync_cursor()
        return mm_x, mm_y

    def scale_here(self) -> tuple[float, float]:
        monitor = self.current_monitor()
        return ((monitor.mm_per_px_x, monitor.mm_per_px_y) if monitor
                else (FALLBACK_MM_PER_PX, FALLBACK_MM_PER_PX))

    def connect_events(self) -> socket.socket | None:
        if not self.event_socket_path and not self._discover():
            return None
        try:
            stream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            stream.setblocking(False)
            stream.connect(self.event_socket_path)
            return stream
        except OSError:
            try:
                stream.close()
            except UnboundLocalError:
                pass
            self.command_socket = self.event_socket_path = None
            return None

    @staticmethod
    def event_requires_refresh(line: str) -> bool:
        event = line.split(">>", 1)[0]
        return event in {"monitoradded", "monitoraddedv2", "monitorremoved",
                         "monitorremovedv2", "configreloaded"}

    def update_focus_event(self, line: str) -> bool:
        """Update only the presence/absence of a focused Hyprland window."""
        event, separator, payload = line.partition(">>")
        if not separator or event != "activewindowv2":
            return False
        self.window_focused = bool(payload.strip())
        return True
