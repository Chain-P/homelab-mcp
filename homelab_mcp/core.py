"""Homelab status: systemd services, disk, CPU temp, and the LAN game-server feed."""
from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from pathlib import Path
from shutil import disk_usage as _disk_usage

SERVICE_UNITS = ("tracker-app.service", "coinbot.service", "zero-bot.service", "zero-two.service")

THERMAL_ZONE = Path("/sys/class/thermal/thermal_zone0/temp")
UPTIME_FILE = Path("/proc/uptime")
GAME_SERVER_URL = "http://192.168.1.111:8091/"


def _parse_memory(value: str | None) -> int | None:
    if not value or value == "[not set]":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def service_status(unit: str) -> dict:
    """Query one allowlisted systemd unit's status via `systemctl show`."""
    if unit not in SERVICE_UNITS:
        raise ValueError(f"Unknown service unit: {unit!r}. Known units: {SERVICE_UNITS}")

    result = subprocess.run(
        [
            "systemctl", "show", unit, "--no-pager",
            "-p", "ActiveState", "-p", "SubState",
            "-p", "ActiveEnterTimestamp", "-p", "MemoryCurrent",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    fields = dict(line.split("=", 1) for line in result.stdout.strip().splitlines() if "=" in line)
    return {
        "unit": unit,
        "active_state": fields.get("ActiveState", "unknown"),
        "sub_state": fields.get("SubState", "unknown"),
        "active_since": fields.get("ActiveEnterTimestamp") or None,
        "memory_bytes": _parse_memory(fields.get("MemoryCurrent")),
    }


def disk_usage(path: str = "/") -> dict:
    total, used, free = _disk_usage(path)
    return {
        "path": path,
        "total_bytes": total,
        "used_bytes": used,
        "free_bytes": free,
        "used_percent": round(used / total * 100, 1),
    }


def cpu_temp_celsius() -> float | None:
    if not THERMAL_ZONE.exists():
        return None
    millidegrees = int(THERMAL_ZONE.read_text().strip())
    return round(millidegrees / 1000, 1)


def load_average() -> dict:
    one, five, fifteen = os.getloadavg()
    return {"1min": one, "5min": five, "15min": fifteen}


def uptime_seconds() -> float:
    return float(UPTIME_FILE.read_text().split()[0])


def game_server_status(timeout: float = 5.0) -> dict:
    """Fetch the game-server status feed from the Windows box's PowerShell TCP listener."""
    try:
        with urllib.request.urlopen(GAME_SERVER_URL, timeout=timeout) as response:
            return json.loads(response.read())
    except (OSError, ValueError) as exc:
        return {"error": str(exc), "reachable": False}
