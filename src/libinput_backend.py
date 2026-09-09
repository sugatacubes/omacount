"""ctypes binding for the small libinput surface Omacount needs.

Using the installed system libinput keeps device acceleration, touchpad scroll,
hotplug, and device classification identical to the compositor while avoiding
an additional Python package or a polling loop.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import errno
import os
import time


DEVICE_ADDED = 1
DEVICE_REMOVED = 2
KEYBOARD_KEY = 300
POINTER_MOTION = 400
POINTER_BUTTON = 402
POINTER_AXIS_LEGACY = 403
POINTER_SCROLL_WHEEL = 404
POINTER_SCROLL_FINGER = 405
POINTER_SCROLL_CONTINUOUS = 406

CAP_KEYBOARD = 0
CAP_POINTER = 1
AXIS_VERTICAL = 0
AXIS_HORIZONTAL = 1


OPEN_CALLBACK = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
CLOSE_CALLBACK = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_void_p)


class LibinputInterface(ctypes.Structure):
    _fields_ = [("open_restricted", OPEN_CALLBACK), ("close_restricted", CLOSE_CALLBACK)]


class LibinputBackend:
    def __init__(self, seat: str = "seat0"):
        libinput_path = ctypes.util.find_library("input")
        udev_path = ctypes.util.find_library("udev")
        if not libinput_path or not udev_path:
            raise RuntimeError("libinput and libudev are required")
        self.li = ctypes.CDLL(libinput_path, use_errno=True)
        self.udev = ctypes.CDLL(udev_path, use_errno=True)
        self.permission_denied: set[str] = set()
        self.devices: dict[int, dict] = {}
        self._configure_abi()

        @OPEN_CALLBACK
        def open_restricted(path, flags, _user_data):
            decoded = os.fsdecode(path)
            try:
                # Omacount never configures or grabs devices. Force the access
                # mode to read-only even if a future libinput changes the flags
                # it asks the callback to use.
                safe_flags = (flags & ~os.O_ACCMODE) | os.O_RDONLY
                return os.open(decoded, safe_flags | os.O_CLOEXEC | os.O_NONBLOCK)
            except OSError as exc:
                if exc.errno in {errno.EACCES, errno.EPERM}:
                    self.permission_denied.add(decoded)
                return -int(exc.errno or errno.EIO)

        @CLOSE_CALLBACK
        def close_restricted(fd, _user_data):
            try:
                os.close(fd)
            except OSError:
                pass

        self._open_callback = open_restricted
        self._close_callback = close_restricted
        self._interface = LibinputInterface(open_restricted, close_restricted)
        self._udev_context = self.udev.udev_new()
        if not self._udev_context:
            raise RuntimeError("udev_new failed")
        self._context = self.li.libinput_udev_create_context(
            ctypes.byref(self._interface), None, self._udev_context)
        if not self._context:
            self.udev.udev_unref(self._udev_context)
            raise RuntimeError("libinput_udev_create_context failed")
        if self.li.libinput_udev_assign_seat(self._context, seat.encode()) != 0:
            self.close()
            raise RuntimeError(f"could not assign libinput seat {seat}")
        self.li.libinput_dispatch(self._context)

    def _configure_abi(self):
        void_p = ctypes.c_void_p
        self.udev.udev_new.restype = void_p
        self.udev.udev_unref.argtypes = [void_p]
        self.udev.udev_unref.restype = void_p
        self.udev.udev_device_unref.argtypes = [void_p]
        self.udev.udev_device_unref.restype = void_p
        self.udev.udev_device_get_property_value.argtypes = [void_p, ctypes.c_char_p]
        self.udev.udev_device_get_property_value.restype = ctypes.c_char_p

        self.li.libinput_udev_create_context.argtypes = [ctypes.POINTER(LibinputInterface), void_p, void_p]
        self.li.libinput_udev_create_context.restype = void_p
        self.li.libinput_udev_assign_seat.argtypes = [void_p, ctypes.c_char_p]
        self.li.libinput_udev_assign_seat.restype = ctypes.c_int
        self.li.libinput_get_fd.argtypes = [void_p]
        self.li.libinput_get_fd.restype = ctypes.c_int
        self.li.libinput_dispatch.argtypes = [void_p]
        self.li.libinput_dispatch.restype = ctypes.c_int
        self.li.libinput_get_event.argtypes = [void_p]
        self.li.libinput_get_event.restype = void_p
        self.li.libinput_event_destroy.argtypes = [void_p]
        self.li.libinput_event_get_type.argtypes = [void_p]
        self.li.libinput_event_get_type.restype = ctypes.c_int
        self.li.libinput_event_get_device.argtypes = [void_p]
        self.li.libinput_event_get_device.restype = void_p
        self.li.libinput_event_get_keyboard_event.argtypes = [void_p]
        self.li.libinput_event_get_keyboard_event.restype = void_p
        self.li.libinput_event_get_pointer_event.argtypes = [void_p]
        self.li.libinput_event_get_pointer_event.restype = void_p
        self.li.libinput_unref.argtypes = [void_p]
        self.li.libinput_unref.restype = void_p
        self.li.libinput_log_set_priority.argtypes = [void_p, ctypes.c_int]

        self.li.libinput_device_get_name.argtypes = [void_p]
        self.li.libinput_device_get_name.restype = ctypes.c_char_p
        self.li.libinput_device_has_capability.argtypes = [void_p, ctypes.c_int]
        self.li.libinput_device_has_capability.restype = ctypes.c_int
        self.li.libinput_device_get_udev_device.argtypes = [void_p]
        self.li.libinput_device_get_udev_device.restype = void_p

        self.li.libinput_event_keyboard_get_key.argtypes = [void_p]
        self.li.libinput_event_keyboard_get_key.restype = ctypes.c_uint32
        self.li.libinput_event_keyboard_get_key_state.argtypes = [void_p]
        self.li.libinput_event_keyboard_get_key_state.restype = ctypes.c_int
        self.li.libinput_event_keyboard_get_time_usec.argtypes = [void_p]
        self.li.libinput_event_keyboard_get_time_usec.restype = ctypes.c_uint64

        self.li.libinput_event_pointer_get_dx.argtypes = [void_p]
        self.li.libinput_event_pointer_get_dx.restype = ctypes.c_double
        self.li.libinput_event_pointer_get_dy.argtypes = [void_p]
        self.li.libinput_event_pointer_get_dy.restype = ctypes.c_double
        self.li.libinput_event_pointer_get_button.argtypes = [void_p]
        self.li.libinput_event_pointer_get_button.restype = ctypes.c_uint32
        self.li.libinput_event_pointer_get_button_state.argtypes = [void_p]
        self.li.libinput_event_pointer_get_button_state.restype = ctypes.c_int
        self.li.libinput_event_pointer_get_time_usec.argtypes = [void_p]
        self.li.libinput_event_pointer_get_time_usec.restype = ctypes.c_uint64
        self.li.libinput_event_pointer_has_axis.argtypes = [void_p, ctypes.c_int]
        self.li.libinput_event_pointer_has_axis.restype = ctypes.c_int
        self.li.libinput_event_pointer_get_scroll_value.argtypes = [void_p, ctypes.c_int]
        self.li.libinput_event_pointer_get_scroll_value.restype = ctypes.c_double
        self.li.libinput_event_pointer_get_scroll_value_v120.argtypes = [void_p, ctypes.c_int]
        self.li.libinput_event_pointer_get_scroll_value_v120.restype = ctypes.c_double

    @property
    def fd(self) -> int:
        return self.li.libinput_get_fd(self._context)

    def _property(self, device, name: bytes) -> str:
        udev_device = self.li.libinput_device_get_udev_device(device)
        if not udev_device:
            return ""
        try:
            value = self.udev.udev_device_get_property_value(udev_device, name)
            return os.fsdecode(value) if value else ""
        finally:
            self.udev.udev_device_unref(udev_device)

    def _describe_device(self, device) -> dict:
        name = self.li.libinput_device_get_name(device)
        return {
            "name": os.fsdecode(name) if name else "Input device",
            "keyboard": bool(self.li.libinput_device_has_capability(device, CAP_KEYBOARD)),
            "pointer": bool(self.li.libinput_device_has_capability(device, CAP_POINTER)),
            "trackpad": self._property(device, b"ID_INPUT_TOUCHPAD") == "1",
        }

    def _time(self, pointer_event=None, keyboard_event=None) -> float:
        usec = 0
        if pointer_event:
            usec = self.li.libinput_event_pointer_get_time_usec(pointer_event)
        elif keyboard_event:
            usec = self.li.libinput_event_keyboard_get_time_usec(keyboard_event)
        return usec / 1_000_000.0 if usec else time.monotonic()

    def dispatch(self) -> list[dict]:
        result = []
        if self.li.libinput_dispatch(self._context) != 0:
            return result
        while True:
            event = self.li.libinput_get_event(self._context)
            if not event:
                break
            try:
                event_type = self.li.libinput_event_get_type(event)
                device = self.li.libinput_event_get_device(event)
                device_key = int(device or 0)
                if event_type == DEVICE_ADDED:
                    descriptor = self._describe_device(device)
                    self.devices[device_key] = descriptor
                    result.append({"kind": "device-added", "device": descriptor})
                    continue
                if event_type == DEVICE_REMOVED:
                    descriptor = self.devices.pop(device_key, self._describe_device(device))
                    result.append({"kind": "device-removed", "device": descriptor})
                    continue

                descriptor = self.devices.get(device_key, {})
                if event_type == KEYBOARD_KEY:
                    keyboard = self.li.libinput_event_get_keyboard_event(event)
                    result.append({
                        "kind": "key", "code": int(self.li.libinput_event_keyboard_get_key(keyboard)),
                        "pressed": self.li.libinput_event_keyboard_get_key_state(keyboard) == 1,
                        "time": self._time(keyboard_event=keyboard), "device": descriptor,
                    })
                elif event_type == POINTER_MOTION:
                    pointer = self.li.libinput_event_get_pointer_event(event)
                    result.append({
                        "kind": "motion", "dx": self.li.libinput_event_pointer_get_dx(pointer),
                        "dy": self.li.libinput_event_pointer_get_dy(pointer),
                        "time": self._time(pointer_event=pointer), "device": descriptor,
                    })
                elif event_type == POINTER_BUTTON:
                    pointer = self.li.libinput_event_get_pointer_event(event)
                    result.append({
                        "kind": "button", "button": int(self.li.libinput_event_pointer_get_button(pointer)),
                        "pressed": self.li.libinput_event_pointer_get_button_state(pointer) == 1,
                        "time": self._time(pointer_event=pointer), "device": descriptor,
                    })
                elif event_type in {POINTER_SCROLL_WHEEL, POINTER_SCROLL_FINGER,
                                    POINTER_SCROLL_CONTINUOUS}:
                    pointer = self.li.libinput_event_get_pointer_event(event)
                    axes = []
                    for axis in (AXIS_VERTICAL, AXIS_HORIZONTAL):
                        if self.li.libinput_event_pointer_has_axis(pointer, axis):
                            value = self.li.libinput_event_pointer_get_scroll_value(pointer, axis)
                            if event_type == POINTER_SCROLL_WHEEL:
                                # One normalized wheel detent is represented as
                                # 120 compositor-like logical pixels.
                                value = (self.li.libinput_event_pointer_get_scroll_value_v120(pointer, axis)
                                         / 120.0 * 120.0)
                            axes.append(value)
                        else:
                            axes.append(0.0)
                    result.append({
                        "kind": "scroll", "dy": axes[0], "dx": axes[1],
                        "source": ("wheel" if event_type == POINTER_SCROLL_WHEEL else
                                   "finger" if event_type == POINTER_SCROLL_FINGER else "continuous"),
                        "time": self._time(pointer_event=pointer), "device": descriptor,
                    })
                # POINTER_AXIS_LEGACY is intentionally ignored: libinput 1.19+
                # emits it in addition to the source-specific events above.
            finally:
                self.li.libinput_event_destroy(event)
        return result

    @property
    def status(self) -> dict:
        devices = list(self.devices.values())
        return {
            "permission_ok": bool(devices) or not self.permission_denied,
            "permission_denied_nodes": len(self.permission_denied),
            "trackpad_present": any(device.get("trackpad") for device in devices),
            "keyboard_count": sum(1 for device in devices if device.get("keyboard")),
            "pointer_count": sum(1 for device in devices if device.get("pointer")),
            "devices": devices,
        }

    def close(self) -> None:
        context = getattr(self, "_context", None)
        if context:
            self.li.libinput_unref(context)
            self._context = None
        udev_context = getattr(self, "_udev_context", None)
        if udev_context:
            self.udev.udev_unref(udev_context)
            self._udev_context = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
