from __future__ import annotations

import argparse
import time
from typing import Dict, List, Optional, Tuple

from qt_app.backend.models import SensorConfig
from qt_app.backend.sensor_registry import SensorRegistry
from utils.profile_manager import ProfileManager


def _poll_phase(
    registry: SensorRegistry,
    sensor_name: str,
    phase: str,
    duration_sec: int,
    interval_sec: float,
) -> List[Tuple[float, str, bool, str]]:
    started = time.time()
    events: List[Tuple[float, str, bool, str]] = []

    while time.time() - started < duration_sec:
        values = registry.read_parameter_values(sensor_name, apply_profile_calibration=True)
        health = registry.get_sensor_health(sensor_name) or {}

        status = str(health.get("status", "unknown"))
        ok = values is not None
        last_error = str(health.get("last_error", "") or "")
        elapsed = time.time() - started

        print(
            f"[{phase}] t={elapsed:5.1f}s | status={status:12s} | "
            f"data={'ok' if ok else 'none':4s} | err={last_error}"
        )
        events.append((elapsed, status, ok, last_error))
        time.sleep(interval_sec)

    return events


def _summarize(events: List[Tuple[float, str, bool, str]]) -> Dict[str, int]:
    stats = {"connected": 0, "unstable": 0, "reconnecting": 0, "degraded": 0, "other": 0, "data_ok": 0}
    for _, status, ok, _ in events:
        if status in stats:
            stats[status] += 1
        else:
            stats["other"] += 1
        if ok:
            stats["data_ok"] += 1
    return stats


def _print_summary(title: str, stats: Dict[str, int]) -> None:
    print(
        f"{title}: connected={stats['connected']}, unstable={stats['unstable']}, "
        f"reconnecting={stats['reconnecting']}, degraded={stats['degraded']}, "
        f"other={stats['other']}, data_ok={stats['data_ok']}"
    )


def _build_registry() -> SensorRegistry:
    profile_manager = ProfileManager()
    profile_manager.create_default_profiles()
    return SensorRegistry(profile_manager)


def run_smoke(
    port: str,
    address: int,
    baudrate: int,
    profile: str,
    baseline_sec: int,
    disconnect_sec: int,
    reconnect_sec: int,
    interval_sec: float,
    no_prompt: bool,
) -> int:
    registry = _build_registry()
    cfg = SensorConfig(
        name="smoke-sensor",
        port=port,
        address=int(address),
        baudrate=int(baudrate),
        profile=profile,
        simulated=False,
    )

    ok, msg = registry.connect_sensor(cfg)
    if not ok:
        print(f"CONNECT FAILED: {msg}")
        return 2
    print("CONNECT OK")

    try:
        baseline = _poll_phase(registry, cfg.name, "baseline", baseline_sec, interval_sec)
        _print_summary("Baseline summary", _summarize(baseline))

        if not no_prompt:
            input("\nDisconnect sensor line/power now, then press Enter...")
        disconnected = _poll_phase(registry, cfg.name, "disconnect", disconnect_sec, interval_sec)
        _print_summary("Disconnect summary", _summarize(disconnected))

        if not no_prompt:
            input("\nReconnect sensor line/power now, then press Enter...")
        reconnected = _poll_phase(registry, cfg.name, "reconnect", reconnect_sec, interval_sec)
        _print_summary("Reconnect summary", _summarize(reconnected))

        saw_problem = any(status in {"degraded", "reconnecting"} for _, status, _, _ in disconnected)
        recovered = any(status == "connected" and ok_data for _, status, ok_data, _ in reconnected)

        if not saw_problem:
            print("SMOKE WARN: no degraded/reconnecting states observed during disconnect phase.")
            return 1
        if not recovered:
            print("SMOKE FAIL: sensor did not recover to connected+data during reconnect phase.")
            return 1

        print("SMOKE OK: disconnect/reconnect behavior looks healthy.")
        return 0
    finally:
        registry.disconnect_sensor(cfg.name)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manual hardware smoke for sensor disconnect/reconnect recovery."
    )
    parser.add_argument("--port", required=True, help="COM port (example: COM7)")
    parser.add_argument("--address", type=int, default=1, help="Modbus address")
    parser.add_argument("--baudrate", type=int, default=9600, help="Baudrate")
    parser.add_argument("--profile", required=True, help="Profile name from profiles folder")
    parser.add_argument("--baseline-sec", type=int, default=8, help="Baseline phase duration")
    parser.add_argument("--disconnect-sec", type=int, default=10, help="Disconnect phase duration")
    parser.add_argument("--reconnect-sec", type=int, default=12, help="Reconnect phase duration")
    parser.add_argument("--interval-sec", type=float, default=1.0, help="Polling interval")
    parser.add_argument("--no-prompt", action="store_true", help="Run phases without waiting for Enter")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    return run_smoke(
        port=args.port,
        address=args.address,
        baudrate=args.baudrate,
        profile=args.profile,
        baseline_sec=args.baseline_sec,
        disconnect_sec=args.disconnect_sec,
        reconnect_sec=args.reconnect_sec,
        interval_sec=args.interval_sec,
        no_prompt=bool(args.no_prompt),
    )


if __name__ == "__main__":
    raise SystemExit(main())
