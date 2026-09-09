# Omameter for Omarchy

Omameter is a native Omarchy/Hyprland/Quickshell plugin that counts real,
system-wide keyboard, mouse, and touchpad activity. A compact bar entry opens a
three-page dashboard for pointer statistics, keyboard statistics, and settings.

The collector is a systemd-managed per-user-session process: it runs as your user, 
starts with that user's runtime, stops after logout, consumes libinput file-descriptor 
events, and persists aggregate state across restarts. Pointer activity and shortcuts
are system-wide; typed-key metrics are admitted while Hyprland has a focused application
and are rejected on the empty home/desktop screen.

## What this machine supports

The implementation was selected after inspecting the target system:

- Hyprland exposes one `eDP-1` monitor at 1920×1080, scale 1, with a reported
  physical size of 310×170 mm.
- libinput 1.31.3 and libudev are installed.
- A Synaptics `SYNA328B` touchpad, a USB mouse, and an AT keyboard are present.
- `/dev/input/event*` is owned by `root:input` at mode `0660`, with no existing
  active-user ACL. A normal user service therefore cannot collect global input.

Hyprland itself does not publish global key and pointer events over its IPC
socket. Omameter uses libinput—the same event-driven input stack a Wayland
compositor uses—instead of polling cursor position or fabricating data.

## Privacy model

Omameter never requests or persists:

- typed strings, passwords, composed characters, or ordered keystrokes;
- clipboard data, window titles, window contents, application names, or focus
  history;
- pointer trails or click coordinates;
- any network identifier or remote endpoint.

Persisted data contains totals, typed-key-only per-physical-key counts, and
aggregate shortcut names such as `Ctrl+C`. Modifier state, a single
focused-window boolean, anonymous per-second typing buckets, and the small
rage-click detection window exist only in memory and are discarded on service
restart. The service is restricted to Unix and netlink sockets, so it cannot
open IPv4 or IPv6 sockets.

Hyprland contributes only a boolean saying whether any application window is
focused. The returned address, title, class, and application identity are
discarded immediately and never written to state.

The state and settings files are private (`0600`) beneath:

```text
~/.local/state/omameter/aggregate.json  durable counters
~/.local/state/omameter/stats.json      derived dashboard snapshot
~/.config/omameter/settings.json        persisted settings
```

The local control socket lives in systemd's private
`/run/omameter-UID/control.sock` runtime directory and disappears when the
collector stops.

### Input permission security implication

The installer does **not** add the login account to the `input` group and does
not add a broad device ACL. It installs a system service generated for this
specific UID. systemd runs that service as the normal user but gives only its
processes the supplementary `input` group. The unit is bound to
`user-runtime-dir@UID.service`, so it is stopped when the user's login runtime
goes away.

The collector can still observe raw input while it runs—that access is
unavoidable for system-wide counts. The service applies a read-only input-device
cgroup, the libinput open callback independently forces read-only descriptors,
and systemd hardening makes the filesystem read-only except for Omameter's two
state directories. The service cannot open IPv4 or IPv6 sockets. Other apps
running as the same user do not inherit the collector service's supplementary
group.

## Statistics and definitions

Page 1 includes cursor distance, scroll distance, total active input time,
rage-click bursts, average/peak scroll speed, detected trackpad state, and a
small energy estimate. Touchpad-generated pointer motion is included in cursor
distance automatically.

Page 2 includes focused-application typing presses, separately counted shortcut use,
average/peak WPM, typed vs undone accuracy, typing-to-mouse active-time ratio,
and energy. Shortcut components never inflate the typed-key headline or
heatmap. The shortcut breakdown and US physical keyboard heatmap use the real
aggregate counters; hovering a heatmap key reveals its exact typed total.

Definitions:

- Active time uses a five-second grace window after an input event, avoiding
  inflated always-on session time.
- Rage click means the first three primary-button presses within 0.8 seconds
  and a 28-logical-pixel radius. Only the aggregate episode count survives.
- Average WPM uses printable physical keys, the five-keys-per-word convention,
  and measured typing-active time. Peak WPM is the best rolling 60-second key
  bucket.
- Accuracy is a privacy-preserving proxy: printable presses remaining after
  Backspace/Delete presses, divided by printable presses. Omameter cannot know
  editor undo state without observing content, which it intentionally avoids.
- A shortcut is a non-modifier pressed while Ctrl, left Alt, or Super is held.
  Shift and AltGr remain typing modifiers. Shortcuts count globally but are
  excluded from typed-key totals, WPM, typing time, energy, and the heatmap.
- Calories are explicitly a playful mechanical-work estimate derived from
  movement, scroll, button, and key totals. They are not a health measurement.

## Distance calibration and limitations

libinput reports accelerated relative motion in standardized mouse-pixel units.
Omameter converts each delta through the active Hyprland monitor's logical size,
scale, and EDID physical dimensions. It initializes cursor location through the
direct Hyprland Unix socket, listens for monitor/config events, and resynchronizes
only on multi-monitor boundary crossings. This accounts for layouts where
monitors have different scales and physical pixel densities without an input
polling loop.

There are unavoidable limitations:

- EDID physical dimensions can be absent or inaccurate. Omameter marks the
  dashboard `EDID calibrated` when present and otherwise falls back to 96 DPI.
- Cursor distance is on-screen pointer travel, not the hand's physical travel
  over a mouse mat or a finger's travel over the touchpad.
- Pointer acceleration, confinement, application pointer lock, and compositor
  transforms can make physical-distance conversion approximate.
- Scroll has no universal physical or content distance across applications.
  Touchpad/continuous scroll uses libinput's cursor-equivalent units; one
  normalized wheel detent is represented as 120 logical pixels. Applications
  may apply their own sensitivity or line height.
- Trackpad detection depends on the standard udev `ID_INPUT_TOUCHPAD` property.
- The heatmap represents Linux physical key codes in a US-layout drawing. Counts
  remain correct on other layouts, while printed legends may differ.
- Wayland deliberately provides no universal API that lets another process
  inspect arbitrary in-application text-field focus. Omameter therefore treats
  typing-capable keys in a focused application as typing and rejects them when
  no application window is focused. This works consistently in terminals,
  native Wayland clients, and XWayland while keeping the home screen excluded;
  a single unmodified letter used as an application command can be
  indistinguishable from typed text without observing content, which Omameter
  refuses to do.
- Version 1.1 migrates older data by clearing only the previously mixed
  typed-key, heatmap, typing-time, WPM, and accuracy inputs. Pointer and shortcut
  aggregates are preserved; future typed totals are cleanly separated.

## Install

Run from a terminal so `sudo` can install and enable the process-scoped system
service:

```bash
cd /home/sugata/Work/omameter
./install.sh
```

The installer follows the same lifecycle as `omarchy-now-playing`: it validates
the manifest, backs up `shell.json`, allowlists copied plugin files, asks the
shell to rescan, and enables only `omameter.activity`. In addition it installs
the private runtime and `omameter-collector-UID.service`, then binds the service
to this user's login runtime. It never edits `/usr/share/omarchy/`, never changes
account group membership or input ACLs, and does not modify
`omarchy-now-playing`.

Preview all intended destinations without making changes:

```bash
./install.sh --dry-run
```

## Controls

| Action | Result |
| --- | --- |
| Left-click bar icon | Open/close the full dashboard |
| Right-click bar icon | Pause/resume all statistics |
| Settings master toggle | Pause/resume all statistics |
| Settings metric toggles | Hide/show individual dashboard metrics |
| Reset statistics | Confirm, then clear all aggregates but keep settings |

The local CLI is also available:

```bash
omameterctl status
omameterctl pause
omameterctl resume
omameterctl set-unit bananas
omameterctl set-custom "desk lengths" desk 1.2
omameterctl set-metric rage_clicks off
omameterctl reset
```

## Diagnostics and tests

```bash
systemctl status "omameter-collector-$(id -u)"
journalctl -u "omameter-collector-$(id -u)" -b
python3 ~/.local/lib/omameter/collector.py --check
./tests/run.sh
```

The collector uses no third-party Python modules. Runtime dependencies are the
system Python, libinput, libudev, systemd, Hyprland, Quickshell, jq, and Omarchy.

## Uninstall

```bash
./uninstall.sh
```

The uninstall disables the exact bar entry and removes the Omameter-marked
system unit, then moves installed files to a timestamped recoverable backup. It
does not alter the `input` group or any device ACL. Statistics/settings stay in
place by default. To move those into the backup too:

```bash
./uninstall.sh --purge-data
```
