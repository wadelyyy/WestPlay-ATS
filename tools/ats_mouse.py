#!/usr/bin/env python3
"""Plan a screenshot-guided relative ATS cursor move; execution is opt-in.

ATS can draw its own menu cursor from relative DirectInput movement. SetCursorPos
does not place that cursor. Measure its arrow tip in an actual screenshot, move
by a small known relative delta, capture again, and calculate gain = screen
pixels / injected count. Recheck a new screenshot before clicking a narrow item.

Examples (all plan-only unless --execute is supplied):
  python tools/ats_mouse.py --from 1280 720 --to 500 692
  python tools/ats_mouse.py --from 1180 720 --to 500 692 --gain 1 1
  python tools/ats_mouse.py --from 1180 720 --to 500 692 --gain 1 1 --pid 123 --execute --click

Coordinates must use the same full-resolution screenshot coordinate system.
For a 1/3 preview, multiply both source and target coordinates by 3 first.
This helper never focuses a window, changes settings, or uses SetCursorPos.
"""

import argparse
import ctypes as C
import json
import math
import os
import time


class MouseInput(C.Structure):
    _fields_ = [("dx", C.c_int32), ("dy", C.c_int32), ("data", C.c_uint32),
                ("flags", C.c_uint32), ("time", C.c_uint32), ("extra", C.c_size_t)]


class InputUnion(C.Union):
    _fields_ = [("mouse", MouseInput)]


class Input(C.Structure):
    _fields_ = [("type", C.c_uint32), ("payload", InputUnion)]


def relative_plan(source, target, gain):
    if any(not math.isfinite(v) for v in [*source, *target, *gain]) or any(v == 0 for v in gain):
        raise ValueError("Coordinates and gains must be finite; gains cannot be zero")
    return tuple(round((b - a) / scale) for a, b, scale in zip(source, target, gain))


def execute(pid, dx, dy, click):
    if os.name != "nt" or C.sizeof(C.c_void_p) != 8:
        raise RuntimeError("Execution requires 64-bit Windows Python")
    user = C.WinDLL("user32", use_last_error=True)
    user.GetForegroundWindow.restype = C.c_void_p
    user.GetWindowThreadProcessId.argtypes = [C.c_void_p, C.POINTER(C.c_uint32)]
    user.SendInput.argtypes = [C.c_uint32, C.POINTER(Input), C.c_int]
    user.SendInput.restype = C.c_uint32
    assert C.sizeof(Input) == 40

    def foreground():
        actual = C.c_uint32()
        user.GetWindowThreadProcessId(user.GetForegroundWindow(), C.byref(actual))
        if actual.value != pid:
            raise RuntimeError(f"Foreground PID {actual.value} is not target {pid}; no further input sent")

    def send(flags, x=0, y=0, guard=True):
        if guard:
            foreground()
        entry = Input(0, InputUnion(MouseInput(x, y, 0, flags, 0, 0)))
        if user.SendInput(1, C.byref(entry), C.sizeof(entry)) != 1:
            raise C.WinError(C.get_last_error())

    # Small timed increments make the route observable and let focus loss abort.
    steps = max(1, math.ceil(max(abs(dx), abs(dy)) / 80))
    old_x = old_y = 0
    for index in range(1, steps + 1):
        x, y = round(dx * index / steps), round(dy * index / steps)
        send(0x0001, x - old_x, y - old_y)  # MOUSEEVENTF_MOVE, relative only
        old_x, old_y = x, y
        time.sleep(0.015)
    if click:
        time.sleep(0.15)
        send(0x0002)  # click at the current game cursor, no cursor warp
        try:
            time.sleep(0.08)
        finally:
            send(0x0004, guard=False)  # always release a button this helper held


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from", dest="source", type=float, nargs=2, required=True, metavar=("X", "Y"))
    parser.add_argument("--to", dest="target", type=float, nargs=2, required=True, metavar=("X", "Y"))
    parser.add_argument("--gain", type=float, nargs=2, default=(1, 1), metavar=("X", "Y"))
    parser.add_argument("--pid", type=int, help="Exact game PID, required for execution")
    parser.add_argument("--execute", action="store_true", help="Opt in to sending the planned relative movement")
    parser.add_argument("--click", action="store_true", help="After movement, click in place without an absolute warp")
    args = parser.parse_args()
    dx, dy = relative_plan(args.source, args.target, args.gain)
    if args.execute and not args.pid:
        parser.error("--execute requires the exact --pid")
    print(json.dumps({"from": args.source, "to": args.target, "gain": args.gain,
                      "relative_counts": [dx, dy], "execute": args.execute, "click": args.click}), flush=True)
    if args.execute:
        execute(args.pid, dx, dy, args.click)
        print("Input submitted; verify the resulting game screenshot before claiming a successful click.")


if __name__ == "__main__":
    main()
