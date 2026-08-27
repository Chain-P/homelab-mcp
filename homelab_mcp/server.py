"""MCP server exposing Raspberry Pi homelab status. Read-only by design."""
from __future__ import annotations

import socket
from typing import Literal

from mcp.server.mcpserver import MCPServer

from homelab_mcp import core

mcp = MCPServer(
    "homelab-mcp",
    instructions=(
        "Read-only Raspberry Pi homelab status: systemd services, disk, "
        "CPU temp, and the LAN game-server feed."
    ),
)

ServiceName = Literal["tracker-app", "coinbot", "zero-bot", "zero-two"]
_UNIT_BY_NAME = {name: f"{name}.service" for name in ("tracker-app", "coinbot", "zero-bot", "zero-two")}


@mcp.tool()
def service_status(name: ServiceName) -> dict:
    """Get detailed systemd status (active state, uptime, memory) for one known homelab service.

    Args:
        name: Which service to query: tracker-app, coinbot, zero-bot, or zero-two.
    """
    return core.service_status(_UNIT_BY_NAME[name])


@mcp.tool()
def disk_usage(path: str = "/") -> dict:
    """Get disk usage (total/used/free bytes, percent used) for a filesystem path on the Pi."""
    return core.disk_usage(path)


@mcp.tool()
def game_server_status() -> dict:
    """Get the current game-server status feed from the LAN Windows box (Minecraft/Zomboid/Terraria host)."""
    return core.game_server_status()


@mcp.tool()
def system_summary() -> dict:
    """One-shot homelab health check: hostname, uptime, load average, disk usage, CPU temp, and every service's status."""
    return {
        "hostname": socket.gethostname(),
        "uptime_seconds": core.uptime_seconds(),
        "load_average": core.load_average(),
        "disk": core.disk_usage("/"),
        "cpu_temp_celsius": core.cpu_temp_celsius(),
        "services": {name: core.service_status(unit) for name, unit in _UNIT_BY_NAME.items()},
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
