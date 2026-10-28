#!/usr/bin/env python3
"""Read-only observer of WestPlay ATS's public shared-memory bridge.

This never creates a mapping, sends input, changes a route or opens game memory.
Generate the independent Rust layout manifest after protocol changes:
    cargo run -p westplay-shared --example bridge_layout > tools/ats_bridge_layout.json
Then sample the real plugin/host bridge (JSON Lines, UTC timestamps):
    python tools/ats_probe.py --seconds 30 --output evidence/drive.jsonl
The route section is the bridge's command/status block, not the game's route geometry.
"""

from __future__ import annotations

import argparse
import ctypes as C
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import struct
import sys
import time
from typing import Any

U8, U32, I32, U64, F32, F64 = C.c_uint8, C.c_uint32, C.c_int32, C.c_uint64, C.c_float, C.c_double
BRIDGE_NAME = r"Local\WestPlay.ATS.Bridge.v24"
BRIDGE_VERSION = 24
BRIDGE_MAGIC = int.from_bytes(b"WPB7", "little")
FILE_MAP_READ = 0x0004


class Telemetry(C.Structure):
    _fields_ = [
        ("x", F64), ("y", F64), ("z", F64),
        ("heading", F32), ("pitch", F32), ("roll", F32), ("speed", F32),
        ("engine_rpm", F32), ("gear", I32), ("displayed_gear", I32),
        ("cruise_control_speed", F32), ("fuel", F32), ("fuel_range", F32),
        ("navigation_distance", F32), ("navigation_time", F32), ("navigation_speed_limit", F32),
        ("game_time", U32), ("local_scale", F32), ("dashboard_backlight", F32),
        ("electric_enabled", U8), ("engine_enabled", U8), ("parking_brake", U8),
        ("low_beam", U8), ("high_beam", U8), ("left_blinker", U8), ("right_blinker", U8), ("paused", U8),
        ("head_x", F32), ("head_y", F32), ("head_z", F32), ("head_heading", F32), ("head_pitch", F32),
        ("camera_known", U8), ("camera_x", F32), ("camera_y", F32), ("camera_z", F32),
        ("cabin_x", F32), ("cabin_y", F32), ("cabin_z", F32), ("steering", F32),
        ("multiplayer_time_offset", I32),
    ]


class TruckInfo(C.Structure):
    _fields_ = [
        ("brand_id", C.c_char * 32), ("brand", C.c_char * 64),
        ("id", C.c_char * 64), ("name", C.c_char * 64), ("head", F32 * 3),
        ("plate", C.c_char * 32), ("plate_country", C.c_char * 32),
    ]


class JobInfo(C.Structure):
    _fields_ = [
        ("active", U8), ("cargo_loaded", U8), ("special", U8), ("cargo", C.c_char * 64),
        ("cargo_mass", F32), ("source_city", C.c_char * 64), ("source_company", C.c_char * 64),
        ("destination_city", C.c_char * 64), ("destination_company", C.c_char * 64),
        ("delivery_time", U32), ("planned_distance_km", U32), ("income", U64),
    ]


class NearbyPlayer(C.Structure):
    _fields_ = [("id", I32), ("heading", F32), ("x", F64), ("z", F64)]


class Nearby(C.Structure):
    _fields_ = [("frame", U64), ("server", U64), ("local", I32), ("count", U32), ("players", NearbyPlayer * 128)]


class PointerBlock(C.Structure):
    _fields_ = [("active", U32), ("dx", I32), ("dy", I32), ("wheel", I32), ("buttons", U32)]


def sequence_type(name: str, value_type: type[C.Structure]) -> type[C.Structure]:
    return type(name, (C.Structure,), {"_fields_": [("sequence", U32), ("value", value_type)]})


SeqTelemetry = sequence_type("SeqTelemetry", Telemetry)
SeqTruck = sequence_type("SeqTruck", TruckInfo)
SeqJob = sequence_type("SeqJob", JobInfo)
SeqNearby = sequence_type("SeqNearby", Nearby)


class PluginBlock(C.Structure):
    _fields_ = [
        ("pid", U32), ("heartbeat", U64), ("adapter_luid_low", U32), ("adapter_luid_high", I32),
        ("screen_layout", U32), ("screen_frame", U64), ("cab_frame", U64), ("truck_supported", U32),
        ("telemetry", SeqTelemetry), ("truck", SeqTruck), ("job", SeqJob),
        ("pointer", PointerBlock), ("nearby", SeqNearby), ("keybind_presses", U32 * 3),
    ]


class HostBlock(C.Structure):
    _fields_ = [
        ("pid", U32), ("heartbeat", U64), ("frame_generation", U32), ("frame_width", U32), ("frame_height", U32),
        ("frame_seq", U64), ("screen_enabled", U32), ("interaction_key", U32),
        ("interaction_toggle", U32), ("keybinds", U32 * 3),
    ]


class RouteBlock(C.Structure):
    _fields_ = [
        ("action", U32), ("node", U64), ("request", U32), ("answered", U32), ("answer", I32),
        ("vias", U64 * 9), ("via_count", U32),
    ]


class KeyQueue64(C.Structure):
    _fields_ = [("head", U32), ("tail", U32), ("keys", U32 * 64)]


class TypingBlock(C.Structure):
    _fields_ = [("selection", U32), ("state", U32), ("keys", KeyQueue64)]


class Bridge(C.Structure):
    _fields_ = [
        ("magic", U32), ("version", U32), ("plugin", PluginBlock), ("host", HostBlock),
        ("route", RouteBlock), ("typing", TypingBlock),
    ]


TYPES = {kind.__name__: kind for kind in [
    Bridge, PluginBlock, HostBlock, RouteBlock, TypingBlock, PointerBlock, Telemetry,
    TruckInfo, JobInfo, Nearby, NearbyPlayer, SeqTelemetry, SeqTruck, SeqJob, SeqNearby, KeyQueue64,
]}


def layout_manifest() -> dict[str, Any]:
    return {
        "bridge_name": BRIDGE_NAME, "magic": BRIDGE_MAGIC, "version": BRIDGE_VERSION,
        "types": {
            name: {
                "size": C.sizeof(kind), "align": C.alignment(kind),
                "fields": {name: getattr(kind, name).offset for name, *_ in kind._fields_},
            }
            for name, kind in TYPES.items()
        },
    }


def validate_layout(path: Path) -> str:
    """Compare every exported Rust offset, size and alignment; fail closed on drift."""
    rust = json.loads(path.read_text(encoding="utf-8-sig"))
    ours = layout_manifest()
    for key in ["bridge_name", "magic", "version"]:
        if rust[key] != ours[key]:
            raise ValueError(f"Rust/Python {key} mismatch: {rust[key]!r} != {ours[key]!r}")
    for name, expected in rust["types"].items():
        actual = ours["types"][name]
        for key in ["size", "align"]:
            if actual[key] != expected[key]:
                raise ValueError(f"Rust/Python {name}.{key} mismatch: {expected[key]} != {actual[key]}")
        for field, offset in expected["fields"].items():
            if actual["fields"][field] != offset:
                raise ValueError(f"Rust/Python offset mismatch at {name}.{field}")
    return "rust_manifest_verified"


def fixed_text(value: bytes) -> str:
    return value.split(b"\0", 1)[0].decode("utf-8", "replace")


def clean_float(value: float, digits: int = 5) -> float | None:
    return round(value, digits) if math.isfinite(value) else None


def screen_ids() -> list[str]:
    path = Path(__file__).resolve().parents[1] / "crates" / "shared" / "screen_layouts.txt"
    return [line.split()[0] for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


class Mapping:
    """FILE_MAP_READ only. It intentionally uses Open..., never CreateFileMapping."""

    def __init__(self) -> None:
        if os.name != "nt" or C.sizeof(C.c_void_p) != 8:
            raise RuntimeError("Live observation requires 64-bit Python on Windows")
        self.kernel = C.WinDLL("kernel32", use_last_error=True)
        self.kernel.OpenFileMappingW.argtypes = [U32, C.c_int, C.c_wchar_p]
        self.kernel.OpenFileMappingW.restype = C.c_void_p
        self.kernel.MapViewOfFile.argtypes = [C.c_void_p, U32, U32, U32, C.c_size_t]
        self.kernel.MapViewOfFile.restype = C.c_void_p
        self.kernel.UnmapViewOfFile.argtypes = [C.c_void_p]
        self.kernel.UnmapViewOfFile.restype = C.c_int
        self.kernel.CloseHandle.argtypes = [C.c_void_p]
        self.kernel.CloseHandle.restype = C.c_int
        self.handle = self.kernel.OpenFileMappingW(FILE_MAP_READ, False, BRIDGE_NAME)
        self.address = None
        if not self.handle:
            raise OSError(C.get_last_error(), "WestPlay ATS mapping not available")
        self.address = self.kernel.MapViewOfFile(self.handle, FILE_MAP_READ, 0, 0, C.sizeof(Bridge))
        if not self.address:
            error = C.get_last_error()
            self.close()
            raise OSError(error, "Cannot map the complete WestPlay ATS bridge read-only")

    def close(self) -> None:
        if self.address:
            self.kernel.UnmapViewOfFile(self.address)
            self.address = None
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None

    def read(self, offset: int, size: int) -> bytes:
        if offset < 0 or offset + size > C.sizeof(Bridge):
            raise ValueError("Read is outside the public bridge")
        return C.string_at(self.address + offset, size)

    def sequence(self, offset: int, kind: type[C.Structure]) -> C.Structure | None:
        value_type = dict(kind._fields_)["value"]
        for _ in range(200):
            before = struct.unpack("<I", self.read(offset, 4))[0]
            if before & 1:
                continue
            value = self.read(offset + kind.value.offset, C.sizeof(value_type))
            after = struct.unpack("<I", self.read(offset, 4))[0]
            if before == after:
                return value_type.from_buffer_copy(value)
        return None

    def snapshot(self, layouts: list[str]) -> dict[str, Any]:
        bridge = Bridge.from_buffer_copy(self.read(0, C.sizeof(Bridge)))
        if bridge.magic != BRIDGE_MAGIC or bridge.version != BRIDGE_VERSION:
            raise ValueError(f"Unsupported bridge protocol: magic={bridge.magic:08x}, version={bridge.version}")
        p, h, r = bridge.plugin, bridge.host, bridge.route
        plugin_offset = Bridge.plugin.offset
        telemetry = self.sequence(plugin_offset + PluginBlock.telemetry.offset, SeqTelemetry)
        truck = self.sequence(plugin_offset + PluginBlock.truck.offset, SeqTruck)
        job = self.sequence(plugin_offset + PluginBlock.job.offset, SeqJob)
        layout = layouts[p.screen_layout - 1] if 0 < p.screen_layout <= len(layouts) else None
        sample: dict[str, Any] = {
            "mapping": "available", "protocol": bridge.version,
            "plugin": {
                "pid": p.pid, "heartbeat": p.heartbeat,
                "adapter_luid": [p.adapter_luid_low, p.adapter_luid_high],
                "screen_layout_code": p.screen_layout, "screen_layout": layout,
                "screen_frame": p.screen_frame, "cab_frame": p.cab_frame,
                "screen_age_frames": p.heartbeat - p.screen_frame if p.screen_frame and p.heartbeat >= p.screen_frame else None,
                "truck_supported": {0: "unknown", 1: "supported", 2: "unsupported"}.get(p.truck_supported, "invalid"),
                "interaction_active": bool(p.pointer.active), "mouse_buttons": p.pointer.buttons,
            },
            "host": {
                "pid": h.pid, "heartbeat": h.heartbeat, "frame_generation": h.frame_generation,
                "frame_size": [h.frame_width, h.frame_height], "frame_seq": h.frame_seq,
                "screen_enabled": bool(h.screen_enabled), "interaction_key": h.interaction_key,
                "interaction_toggle": bool(h.interaction_toggle),
            },
            "route_command": {
                "action": r.action, "node": f"{r.node:x}", "request": r.request,
                "answered": r.answered, "answer": r.answer,
                "answer_name": {0: "none", 1: "done", 2: "already_there", -1: "unsupported", -2: "no_such_node",
                                -3: "full", -4: "unexpected", -5: "on_job"}.get(r.answer, "unknown"),
                "via_count": r.via_count,
            },
            "vehicle": None if truck is None else {
                "id": fixed_text(truck.id), "brand": fixed_text(truck.brand), "name": fixed_text(truck.name),
            },
            "telemetry": None,
            "job": None if job is None else {
                "active": bool(job.active), "cargo": fixed_text(job.cargo),
                "source_city": fixed_text(job.source_city), "destination_city": fixed_text(job.destination_city),
                "planned_distance_km": job.planned_distance_km,
            },
        }
        if telemetry is not None:
            t = telemetry
            sample["telemetry"] = {
                "position_m": [clean_float(t.x), clean_float(t.y), clean_float(t.z)],
                "heading_turns": clean_float(t.heading), "speed_m_s": clean_float(t.speed),
                "speed_km_h": clean_float(t.speed * 3.6), "engine_rpm": clean_float(t.engine_rpm),
                "gear": t.gear, "game_time_minutes": t.game_time, "local_scale": clean_float(t.local_scale),
                "paused": bool(t.paused), "electric_enabled": bool(t.electric_enabled),
                "engine_enabled": bool(t.engine_enabled), "parking_brake": bool(t.parking_brake),
                "low_beam": bool(t.low_beam), "high_beam": bool(t.high_beam),
                "navigation_distance_m": clean_float(t.navigation_distance),
                "navigation_time_s": clean_float(t.navigation_time),
                "navigation_speed_limit_m_s": clean_float(t.navigation_speed_limit),
                "camera_known": bool(t.camera_known),
            }
        return sample


class Rates:
    def __init__(self) -> None:
        self.previous: tuple[float, int, int, int, int] | None = None

    def add(self, sample: dict[str, Any], now: float) -> None:
        if sample.get("mapping") != "available":
            self.previous = None
            return
        p, h = sample["plugin"], sample["host"]
        current = (now, p["pid"], p["heartbeat"], h["pid"], h["frame_seq"])
        game_fps = host_fps = None
        if self.previous is not None:
            old_time, old_pid, old_beat, old_host, old_seq = self.previous
            elapsed = now - old_time
            if elapsed > 0:
                if old_pid == p["pid"] and p["pid"] and p["heartbeat"] >= old_beat:
                    game_fps = round((p["heartbeat"] - old_beat) / elapsed, 2)
                if old_host == h["pid"] and h["pid"] and h["frame_seq"] >= old_seq:
                    host_fps = round((h["frame_seq"] - old_seq) / elapsed, 2)
        p["present_rate_fps"] = game_fps
        h["published_rate_fps"] = host_fps
        # A stored PID alone never proves that a process is still connected.
        sample["connection"] = {
            "plugin_advancing": game_fps is not None and game_fps > 0,
            "host_frames_advancing": host_fps is not None and host_fps > 0,
        }
        self.previous = current


class ProcessMemoryCounters(C.Structure):
    _fields_ = [
        ("cb", U32), ("page_fault_count", U32),
        ("peak_working_set", C.c_size_t), ("working_set", C.c_size_t),
        ("quota_peak_paged_pool", C.c_size_t), ("quota_paged_pool", C.c_size_t),
        ("quota_peak_nonpaged_pool", C.c_size_t), ("quota_nonpaged_pool", C.c_size_t),
        ("pagefile_usage", C.c_size_t), ("peak_pagefile_usage", C.c_size_t),
    ]


class ProcessMetrics:
    """OS process counters only; no PROCESS_VM_READ or ReadProcessMemory."""

    def __init__(self) -> None:
        self.kernel = C.WinDLL("kernel32", use_last_error=True)
        self.kernel.OpenProcess.argtypes = [U32, C.c_int, U32]
        self.kernel.OpenProcess.restype = C.c_void_p
        self.kernel.CloseHandle.argtypes = [C.c_void_p]
        self.kernel.GetProcessTimes.argtypes = [C.c_void_p] + [C.POINTER(U64)] * 4
        self.kernel.GetProcessTimes.restype = C.c_int
        self.kernel.GetExitCodeProcess.argtypes = [C.c_void_p, C.POINTER(U32)]
        self.kernel.GetExitCodeProcess.restype = C.c_int
        self.kernel.K32GetProcessMemoryInfo.argtypes = [C.c_void_p, C.POINTER(ProcessMemoryCounters), U32]
        self.kernel.K32GetProcessMemoryInfo.restype = C.c_int
        self.previous: dict[tuple[int, int], tuple[float, int]] = {}

    def read(self, pid: int, now: float) -> dict[str, Any] | None:
        if not pid:
            return None
        handle = self.kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return {"pid": pid, "query_error": C.get_last_error()}
        try:
            exit_code = U32()
            self.kernel.GetExitCodeProcess(handle, C.byref(exit_code))
            result: dict[str, Any] = {"pid": pid, "running": exit_code.value == 259}
            creation, exit_time, kernel_time, user_time = U64(), U64(), U64(), U64()
            if self.kernel.GetProcessTimes(handle, C.byref(creation), C.byref(exit_time),
                                           C.byref(kernel_time), C.byref(user_time)):
                cpu_ticks = kernel_time.value + user_time.value
                identity = (pid, creation.value)  # PID reuse must not yield a bogus CPU delta.
                previous = self.previous.get(identity)
                cpu = None
                if previous and now > previous[0] and cpu_ticks >= previous[1]:
                    cpu = 100 * (cpu_ticks - previous[1]) / 10_000_000 / (now - previous[0])
                result["cpu_pct_one_core"] = None if cpu is None else round(cpu, 2)
                result["cpu_pct_system"] = None if cpu is None else round(cpu / (os.cpu_count() or 1), 2)
                self.previous[identity] = (now, cpu_ticks)
            counters = ProcessMemoryCounters()
            counters.cb = C.sizeof(counters)
            if self.kernel.K32GetProcessMemoryInfo(handle, C.byref(counters), counters.cb):
                result["working_set_mb"] = round(counters.working_set / (1024 ** 2), 2)
                result["peak_working_set_mb"] = round(counters.peak_working_set / (1024 ** 2), 2)
            else:
                result["memory_query_error"] = C.get_last_error()
            return result
        finally:
            self.kernel.CloseHandle(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seconds", type=float, default=1, help="Duration; 0 takes one snapshot")
    parser.add_argument("--interval", type=float, default=1, help="Seconds between samples (default: 1)")
    parser.add_argument("--output", type=Path, help="New JSONL evidence file; existing files are never overwritten")
    parser.add_argument("--layout", type=Path, default=Path(__file__).with_name("ats_bridge_layout.json"))
    parser.add_argument("--print-layout", action="store_true", help="Print Python ABI description without observing the game")
    args = parser.parse_args()
    if args.print_layout:
        print(json.dumps(layout_manifest(), ensure_ascii=False, indent=2))
        return 0
    if args.seconds < 0 or args.interval <= 0:
        parser.error("--seconds must be nonnegative and --interval positive")
    if not args.layout.is_file():
        parser.error(f"Rust layout manifest required: generate {args.layout} with the bridge_layout example first")
    layout_status = validate_layout(args.layout)
    layouts, rates = screen_ids(), Rates()
    metrics = ProcessMetrics() if os.name == "nt" else None
    output = None
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        output = args.output.open("x", encoding="utf-8")
    started = time.monotonic()
    count = max(1, math.ceil(args.seconds / args.interval))
    mapping = None
    try:
        for index in range(count):
            due = started + index * args.interval
            time.sleep(max(0, due - time.monotonic()))
            sample = {"utc": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                      "elapsed_s": round(time.monotonic() - started, 4), "layout_check": layout_status}
            try:
                if mapping is None:
                    mapping = Mapping()
                sample.update(mapping.snapshot(layouts))
            except (OSError, ValueError) as error:
                sample.update({"mapping": "unavailable", "error": str(error)})
                if mapping is not None:
                    mapping.close()
                    mapping = None
            rates.add(sample, time.monotonic())
            if metrics is not None and sample.get("mapping") == "available":
                now = time.monotonic()
                sample["processes"] = {
                    "game": metrics.read(sample["plugin"]["pid"], now),
                    "host": metrics.read(sample["host"]["pid"], now),
                }
            line = json.dumps(sample, ensure_ascii=False, allow_nan=False)
            print(line, flush=True)
            if output:
                output.write(line + "\n")
                output.flush()
    finally:
        if mapping is not None:
            mapping.close()
        if output:
            output.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
