"""
Garrison plugin for Rust dedicated servers.

Uses WebSocket RCON (ws://host:rconport/<password>).
Protocol: JSON messages with Identifier, Message, Name fields.
"""

import asyncio
import json
import logging
from typing import Optional

try:
    import websockets
    from websockets.exceptions import ConnectionClosed, WebSocketException
except ImportError:
    websockets = None

from app.plugins.base import GamePlugin, PlayerInfo, ServerStatus, CommandDef

logger = logging.getLogger(__name__)

RESPONSE_TIMEOUT = 10.0
RECONNECT_DELAY = 5.0


class RustPlugin(GamePlugin):
    """Rust dedicated server plugin using WebSocket RCON."""

    custom_connection = True

    @property
    def game_type(self) -> str:
        return "rust"

    @property
    def display_name(self) -> str:
        return "Rust"

    def __init__(self):
        super().__init__()
        self._ws = None
        self._msg_id = 0
        self._host: Optional[str] = None
        self._port: Optional[int] = None
        self._password: Optional[str] = None
        self._lock = asyncio.Lock()
        self._pending: dict[int, asyncio.Future] = {}
        self._listener_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect_custom(self, host: str, port: int, password: str) -> None:
        if websockets is None:
            raise RuntimeError("websockets library is not installed")
        self._host = host
        self._port = port
        self._password = password
        await self._do_connect()

    async def _do_connect(self) -> None:
        uri = f"ws://{self._host}:{self._port}/{self._password}"
        logger.info("Connecting to Rust RCON at %s:%s", self._host, self._port)
        self._ws = await websockets.connect(uri, ping_interval=None, open_timeout=10)
        logger.info("Connected to Rust RCON")
        self._listener_task = asyncio.create_task(self._listener())

    async def disconnect_custom(self) -> None:
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

    async def _reconnect(self) -> None:
        logger.warning("Rust RCON disconnected, reconnecting in %ss", RECONNECT_DELAY)
        await asyncio.sleep(RECONNECT_DELAY)
        try:
            await self._do_connect()
        except Exception as exc:
            logger.error("Reconnect failed: %s", exc)

    # ------------------------------------------------------------------
    # Message handling
    # ------------------------------------------------------------------

    async def _listener(self) -> None:
        try:
            async for raw in self._ws:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    logger.debug("Non-JSON message: %s", raw)
                    continue

                identifier = data.get("Identifier", -1)
                if identifier in self._pending:
                    fut = self._pending.pop(identifier)
                    if not fut.done():
                        fut.set_result(data)
                else:
                    logger.debug("Unhandled RCON message id=%s: %s", identifier, data.get("Message", "")[:200])
        except ConnectionClosed:
            logger.warning("Rust RCON WebSocket connection closed")
        except WebSocketException as exc:
            logger.error("WebSocket error: %s", exc)
        finally:
            for fut in self._pending.values():
                if not fut.done():
                    fut.set_exception(ConnectionError("RCON connection lost"))
            self._pending.clear()
            asyncio.create_task(self._reconnect())

    async def send_command_custom(self, command: str, content: str = "") -> str:
        """Send a command via WebSocket RCON and return the response message string."""
        async with self._lock:
            self._msg_id += 1
            identifier = self._msg_id

        if self._ws is None:
            raise ConnectionError("Not connected to Rust RCON")

        loop = asyncio.get_event_loop()
        fut: asyncio.Future = loop.create_future()
        self._pending[identifier] = fut

        payload = json.dumps({
            "Identifier": identifier,
            "Message": command,
            "Name": "Garrison",
        })

        try:
            await self._ws.send(payload)
            response = await asyncio.wait_for(fut, timeout=RESPONSE_TIMEOUT)
            return response.get("Message", "")
        except asyncio.TimeoutError:
            self._pending.pop(identifier, None)
            raise TimeoutError(f"No response for command '{command}' within {RESPONSE_TIMEOUT}s")
        except Exception:
            self._pending.pop(identifier, None)
            raise

    # ------------------------------------------------------------------
    # GamePlugin interface
    # ------------------------------------------------------------------

    async def parse_players(self, raw_response: str) -> list[PlayerInfo]:
        """Parse JSON from playerlist command."""
        try:
            players_data = json.loads(raw_response)
        except (json.JSONDecodeError, TypeError):
            logger.warning("playerlist returned non-JSON: %s", raw_response)
            return []

        players = []
        for p in players_data:
            players.append(PlayerInfo(
                name=p.get("DisplayName") or p.get("Username", "Unknown"),
                steam_id=str(p.get("SteamID", "")),
            ))
        return players

    async def get_status(self, send_command) -> ServerStatus:
        """Call status command and return ServerStatus."""
        try:
            raw = await send_command("status")
            # Parse player count from status output
            # Typical: "hostname: ...\nversion: ...\nplayers: 5 (100 max)"
            player_count = 0
            version = None
            for line in raw.splitlines():
                line_lower = line.lower()
                if "players" in line_lower:
                    import re
                    m = re.search(r"(\d+)\s*\(", line)
                    if m:
                        player_count = int(m.group(1))
                if line_lower.startswith("version"):
                    version = line.split(":", 1)[-1].strip()
            return ServerStatus(online=True, player_count=player_count, version=version, extra={"status": raw})
        except Exception:
            return ServerStatus(online=False, player_count=0)

    def get_commands(self) -> list[CommandDef]:
        from schema import get_commands
        return get_commands()

    async def get_players(self, send_command) -> list[PlayerInfo]:
        """Return list of currently connected players."""
        raw = await send_command("playerlist")
        return await self.parse_players(raw)

    async def kick_player(self, send_command, name: str, reason: str = "Kicked by admin") -> str:
        """Kick a player by SteamID or name."""
        cmd = f'kick {name} "{reason}"'
        return await send_command(cmd)

    async def ban_player(self, send_command, name: str, reason: str = "Banned by admin") -> str:
        """Ban a player by SteamID (banid) or name."""
        # If name looks like a SteamID (all digits, 17 chars), use banid
        if name.isdigit() and len(name) >= 15:
            cmd = f'banid {name} "" "{reason}"'
        else:
            cmd = f'ban "{name}" "{reason}"'
        return await send_command(cmd)

    async def unban_player(self, send_command, name: str) -> str:
        """Unban a player by SteamID."""
        return await send_command(f"unban {name}")

    async def message_player(self, send_command, name: str, message: str) -> str:
        """Send a message — Rust has no private whisper via RCON, use global say."""
        cmd = f'say "[To {name}] {message}"'
        return await send_command(cmd)

    async def give_item(self, send_command, player: str, item: str, count: int = 1) -> str:
        """Give item to player via inventory.giveto."""
        return await send_command(f"inventory.giveto {player} {item} {count}")

    async def get_player_roles(self) -> list[str]:
        return ["owner", "moderator"]

    async def promote_player(self, send_command, player: str, role: str) -> str:
        """Grant owner or moderator role to a player."""
        role = role.lower()
        if role == "owner":
            return await send_command(f'ownerid {player} ""')
        elif role in ("moderator", "mod"):
            return await send_command(f'moderatorid {player} ""')
        else:
            raise ValueError(f"Unknown role: {role}. Valid roles: owner, moderator")

    async def demote_player(self, send_command, player: str) -> str:
        """Remove all admin roles from a player."""
        # Try removeowner first, then removemoderator
        try:
            await send_command(f"removeowner {player}")
        except Exception:
            pass
        try:
            result = await send_command(f"removemoderator {player}")
            return result
        except Exception as exc:
            return str(exc)

    async def poll_events(self, send_command, since: str | None = None) -> list[dict]:
        """Rust events require log parsing — not implemented."""
        return []

    async def is_connected(self) -> bool:
        return self._ws is not None and not self._ws.closed
