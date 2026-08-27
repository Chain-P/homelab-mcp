import json
import subprocess
from urllib.error import URLError

import pytest

from homelab_mcp import core


def test_service_status_rejects_unknown_unit():
    with pytest.raises(ValueError, match="Unknown service unit"):
        core.service_status("evil; rm -rf /.service")


def test_service_status_parses_systemctl_output(monkeypatch):
    def fake_run(cmd, **kwargs):
        assert cmd[:2] == ["systemctl", "show"]
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout=(
                "ActiveState=active\n"
                "SubState=running\n"
                "ActiveEnterTimestamp=Thu 2026-08-27 10:00:00 UTC\n"
                "MemoryCurrent=12345678\n"
            ),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = core.service_status("tracker-app.service")
    assert result == {
        "unit": "tracker-app.service",
        "active_state": "active",
        "sub_state": "running",
        "active_since": "Thu 2026-08-27 10:00:00 UTC",
        "memory_bytes": 12345678,
    }


def test_service_status_handles_unset_memory(monkeypatch):
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(
            cmd, 0, stdout="ActiveState=inactive\nSubState=dead\nMemoryCurrent=[not set]\n", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = core.service_status("coinbot.service")
    assert result["memory_bytes"] is None
    assert result["active_since"] is None


def test_disk_usage(monkeypatch):
    monkeypatch.setattr(core, "_disk_usage", lambda path: (1000, 250, 750))
    result = core.disk_usage("/")
    assert result == {
        "path": "/",
        "total_bytes": 1000,
        "used_bytes": 250,
        "free_bytes": 750,
        "used_percent": 25.0,
    }


def test_cpu_temp_reads_thermal_zone(monkeypatch, tmp_path):
    fake_zone = tmp_path / "temp"
    fake_zone.write_text("42800\n")
    monkeypatch.setattr(core, "THERMAL_ZONE", fake_zone)
    assert core.cpu_temp_celsius() == 42.8


def test_cpu_temp_missing_zone_returns_none(monkeypatch, tmp_path):
    monkeypatch.setattr(core, "THERMAL_ZONE", tmp_path / "does-not-exist")
    assert core.cpu_temp_celsius() is None


def test_uptime_seconds(monkeypatch, tmp_path):
    fake_uptime = tmp_path / "uptime"
    fake_uptime.write_text("12345.67 6789.01\n")
    monkeypatch.setattr(core, "UPTIME_FILE", fake_uptime)
    assert core.uptime_seconds() == 12345.67


def test_game_server_status_success(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def read(self):
            payload = {"hostname": "SERV", "services": [{"name": "zomboid", "running": True}]}
            return json.dumps(payload).encode()

    monkeypatch.setattr(core.urllib.request, "urlopen", lambda url, timeout=5.0: FakeResponse())
    result = core.game_server_status()
    assert result["hostname"] == "SERV"


def test_game_server_status_unreachable(monkeypatch):
    def raise_error(url, timeout=5.0):
        raise URLError("connection refused")

    monkeypatch.setattr(core.urllib.request, "urlopen", raise_error)
    result = core.game_server_status()
    assert result["reachable"] is False
