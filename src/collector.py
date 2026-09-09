#!/usr/bin/env python3
"""Omacount's event-driven, aggregate-only user service."""

from __future__ import annotations

import argparse
import json
import os
import selectors
import signal
import socket
import sys
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from hyprland import HyprlandGeometry
from libinput_backend import LibinputBackend
from metrics import MetricsEngine, default_state, sanitize_state
from storage import METRIC_KEYS, Store, sanitize_settings


class Collector:
    SNAPSHOT_INTERVAL = 1.0
    PERSIST_INTERVAL = 10.0

    def __init__(self, store: Store | None = None, runtime_dir: str | None = None,
                 backend_factory=LibinputBackend):
        self.store = store or Store()
        self.store.prepare()
        self.settings = self.store.load_settings()
        saved = self.store.read_json(self.store.persistent_path, default_state())
        self.metrics = MetricsEngine(sanitize_state(saved))
        self.geometry = HyprlandGeometry(runtime_dir)
        self.geometry.refresh()
        self.selector = selectors.DefaultSelector()
        self.backend = None
        self.backend_error = ""
        self.hyrp_event_stream = None
        self.hypr_buffer = ""
        self.running = True
        self.dirty = True
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.last_snapshot = 0.0
        self.last_persist = 0.0
        self.next_hypr_retry = 0.0
        self._setup_backend(backend_factory)
        self._setup_control(runtime_dir)
        self._connect_hypr_events()

    def _setup_backend(self, factory) -> None:
        try:
            self.backend = factory()
            self.selector.register(self.backend.fd, selectors.EVENT_READ, self._read_input)
            # Drain initial DEVICE_ADDED notifications now so the very first
            # snapshot accurately reports permissions and trackpad presence.
            self._read_input()
        except Exception as exc:
            self.backend_error = f"{type(exc).__name__}: {exc}"
            self.backend = None

    def _setup_control(self, runtime_dir: str | None) -> None:
        managed_runtime = os.environ.get("OMACOUNT_RUNTIME_DIR", "")
        base = (Path(managed_runtime) if managed_runtime else
                Path(runtime_dir or os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "omacount")
        base.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(base, 0o700)
        self.socket_path = base / "control.sock"
        try:
            self.socket_path.unlink()
        except FileNotFoundError:
            pass
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(str(self.socket_path))
        os.chmod(self.socket_path, 0o600)
        self.server.listen(8)
        self.server.setblocking(False)
        self.selector.register(self.server, selectors.EVENT_READ, self._accept_control)

    def _connect_hypr_events(self) -> None:
        if self.hyrp_event_stream is not None:
            return
        stream = self.geometry.connect_events()
        if stream is not None:
            self.hyrp_event_stream = stream
            self.selector.register(stream, selectors.EVENT_READ, self._read_hypr_events)
            self.next_hypr_retry = 0.0
        else:
            self.next_hypr_retry = time.monotonic() + 5.0

    def _disconnect_hypr_events(self) -> None:
        if self.hyrp_event_stream is not None:
            try:
                self.selector.unregister(self.hyrp_event_stream)
            except Exception:
                pass
            self.hyrp_event_stream.close()
            self.hyrp_event_stream = None
        self.next_hypr_retry = time.monotonic() + 5.0

    def _read_hypr_events(self, _fileobj=None, _mask=None) -> None:
        try:
            chunk = self.hyrp_event_stream.recv(65536)
        except BlockingIOError:
            return
        except OSError:
            self._disconnect_hypr_events()
            return
        if not chunk:
            self._disconnect_hypr_events()
            return
        self.hypr_buffer += chunk.decode("utf-8", "replace")
        lines = self.hypr_buffer.split("\n")
        self.hypr_buffer = lines.pop()
        if any(self.geometry.event_requires_refresh(line) for line in lines):
            self.geometry.refresh()
            self.dirty = True
        focus_changed = False
        for line in lines:
            focus_changed = self.geometry.update_focus_event(line) or focus_changed
        if focus_changed:
            self.dirty = True

    def _typing_context_active(self) -> bool:
        # Wayland deliberately offers no universal cross-application text-field
        # focus API. Hyprland's boolean active-window signal is reliable across
        # native Wayland, XWayland, and terminals, and becomes false on the
        # empty home/desktop screen. No window identity is retained.
        return self.geometry.window_focused

    def _read_input(self, _fileobj=None, _mask=None) -> None:
        if not self.backend:
            return
        for event in self.backend.dispatch():
            kind = event["kind"]
            if kind in {"device-added", "device-removed"}:
                self.dirty = True
                continue
            if self.settings["paused"]:
                continue
            now = float(event.get("time", time.monotonic()))
            if kind == "motion":
                dx, dy = float(event["dx"]), float(event["dy"])
                mm_x, mm_y = self.geometry.scale_for_motion(dx, dy)
                self.metrics.pointer_motion(dx, dy, mm_x, mm_y, now)
            elif kind == "scroll":
                mm_x, mm_y = self.geometry.scale_here()
                self.metrics.scroll(event["dx"], event["dy"], mm_x, mm_y, now)
            elif kind == "button":
                self.metrics.pointer_button(event["button"], event["pressed"],
                                            self.geometry.cursor_x,
                                            self.geometry.cursor_y, now)
            elif kind == "key":
                self.metrics.keyboard_key(
                    event["code"], event["pressed"], now,
                    typing_context=self._typing_context_active())
            self.dirty = True

    def _accept_control(self, _fileobj=None, _mask=None) -> None:
        try:
            connection, _ = self.server.accept()
        except BlockingIOError:
            return
        with connection:
            connection.settimeout(0.25)
            try:
                payload = connection.recv(65536)
                request = json.loads(payload.decode("utf-8"))
                response = self.handle_command(request)
            except Exception as exc:
                response = {"ok": False, "error": str(exc)}
            try:
                connection.sendall((json.dumps(response, separators=(",", ":")) + "\n").encode())
            except OSError:
                pass

    @staticmethod
    def _boolean(value) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.lower() in {"true", "on", "yes", "1"}:
            return True
        if isinstance(value, str) and value.lower() in {"false", "off", "no", "0"}:
            return False
        raise ValueError("expected on/off boolean")

    def _save_settings(self) -> None:
        self.settings = self.store.save_settings(self.settings)
        self.dirty = True
        self.write_snapshot(force=True)

    def handle_command(self, request: dict) -> dict:
        if not isinstance(request, dict):
            raise ValueError("request must be a JSON object")
        command = request.get("command")
        if command == "status":
            self.write_snapshot(force=True)
            return {"ok": True, "snapshot": str(self.store.snapshot_path)}
        if command == "set-paused":
            paused = self._boolean(request.get("value"))
            if paused != self.settings["paused"]:
                self.metrics.suspend()
                self.settings["paused"] = paused
                self._save_settings()
            return {"ok": True, "paused": self.settings["paused"]}
        if command == "toggle-paused":
            self.metrics.suspend()
            self.settings["paused"] = not self.settings["paused"]
            self._save_settings()
            return {"ok": True, "paused": self.settings["paused"]}
        if command == "set-unit":
            value = str(request.get("value", ""))
            if value not in {"miles", "meters", "bananas", "custom"}:
                raise ValueError("unknown distance unit")
            self.settings["unit"] = value
            self._save_settings()
            return {"ok": True}
        if command == "set-custom":
            custom = deepcopy(self.settings["custom_unit"])
            for key in ("name", "symbol", "metres_per_unit"):
                if key in request:
                    custom[key] = request[key]
            candidate = deepcopy(self.settings)
            candidate["custom_unit"] = custom
            self.settings = sanitize_settings(candidate)
            self._save_settings()
            return {"ok": True, "custom_unit": self.settings["custom_unit"]}
        if command == "set-metric":
            key = str(request.get("key", ""))
            if key not in METRIC_KEYS:
                raise ValueError("unknown metric")
            self.settings["metrics"][key] = self._boolean(request.get("value"))
            self._save_settings()
            return {"ok": True}
        if command == "reset":
            self.metrics.reset()
            self.write_snapshot(force=True, persist=True)
            return {"ok": True}
        raise ValueError("unknown command")

    def collector_status(self) -> dict:
        backend = (self.backend.status if self.backend else {
            "permission_ok": False, "permission_denied_nodes": 0,
            "trackpad_present": False, "keyboard_count": 0,
            "pointer_count": 0, "devices": [],
        })
        if self.backend_error:
            backend["error"] = self.backend_error
        backend.update({
            "running": True,
            "paused": self.settings["paused"],
            "started_at": self.started_at,
            "distance_calibration": self.geometry.calibration,
            "monitor_count": len(self.geometry.monitors),
            "typing_context_active": self._typing_context_active(),
            "text_focus_signal": "hyprland-focused-window",
        })
        return backend

    def write_snapshot(self, force: bool = False, persist: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self.last_snapshot < self.SNAPSHOT_INTERVAL:
            return
        snapshot = self.metrics.snapshot(now if not self.settings["paused"] else None)
        snapshot["updated_at"] = datetime.now(timezone.utc).isoformat()
        snapshot["collector"] = self.collector_status()
        snapshot["privacy"] = {
            "aggregate_only": True,
            "network_access": False,
            "stores_text": False,
            "stores_key_order": False,
        }
        self.store.write_json(self.store.snapshot_path, snapshot)
        self.last_snapshot = now
        if persist or now - self.last_persist >= self.PERSIST_INTERVAL:
            self.store.write_json(self.store.persistent_path,
                                  self.metrics.persistent_state(now if not self.settings["paused"] else None))
            self.last_persist = now
        self.dirty = False

    def run(self) -> None:
        self.write_snapshot(force=True, persist=True)
        while self.running:
            for key, mask in self.selector.select(timeout=1.0):
                key.data(key.fileobj, mask)
            now = time.monotonic()
            if self.hyrp_event_stream is None and now >= self.next_hypr_retry:
                self.geometry.refresh()
                self._connect_hypr_events()
            # Advancing once a second makes active-time readouts live. Input
            # itself remains fd-driven; there is no input or cursor polling.
            if not self.settings["paused"]:
                self.metrics.advance(now)
            self.write_snapshot(force=self.dirty or now - self.last_snapshot >= self.SNAPSHOT_INTERVAL)

    def stop(self, *_args) -> None:
        self.running = False

    def close(self) -> None:
        try:
            self.write_snapshot(force=True, persist=True)
        except Exception:
            pass
        self._disconnect_hypr_events()
        if self.backend:
            try:
                self.selector.unregister(self.backend.fd)
            except Exception:
                pass
            self.backend.close()
        try:
            self.selector.unregister(self.server)
        except Exception:
            pass
        self.server.close()
        self.selector.close()
        try:
            self.socket_path.unlink()
        except FileNotFoundError:
            pass


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Aggregate-only system input meter")
    parser.add_argument("--check", action="store_true",
                        help="initialize libinput, print capability status, and exit")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.check:
        try:
            backend = LibinputBackend()
            backend.dispatch()
            print(json.dumps(backend.status, indent=2))
            backend.close()
            return 0 if backend.status.get("permission_ok", False) else 2
        except Exception as exc:
            print(json.dumps({"permission_ok": False, "error": str(exc)}, indent=2))
            return 2

    collector = Collector()
    signal.signal(signal.SIGTERM, collector.stop)
    signal.signal(signal.SIGINT, collector.stop)
    try:
        collector.run()
    finally:
        collector.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
