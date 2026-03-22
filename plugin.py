"""
Garrison plugin for Rust dedicated servers.

Uses WebSocket RCON (ws://host:rconport/<password>).
Protocol: JSON messages with Identifier, Message, Name fields.
"""

import asyncio
import json
import logging
import re
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

    @property
    def game_type(self) -> str:
        return "rust"

    @property
    def display_name(self) -> str:
        return "Rust"

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect_custom(self, host: str, port: int, password: str) -> None:
        """Establish WebSocket connection to Rust RCON."""
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

    async def disconnect(self) -> None:
        """Close WebSocket connection."""
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
        """Attempt to reconnect after connection loss."""
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
        """Background task that reads incoming WebSocket messages."""
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
        """Send a command and return the response message string."""
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
    # GamePlugin abstract interface
    # ------------------------------------------------------------------

    async def parse_players(self, raw_response: str) -> list[PlayerInfo]:
        """Parse JSON playerlist response."""
        try:
            players_data = json.loads(raw_response)
        except (json.JSONDecodeError, TypeError):
            logger.warning("parse_players got non-JSON: %s", raw_response)
            return []

        players = []
        for p in players_data:
            players.append(PlayerInfo(
                name=p.get("DisplayName") or p.get("Username", "Unknown"),
                steam_id=str(p.get("SteamID", "")),
            ))
        return players

    async def get_status(self, send_command) -> ServerStatus:
        """Get server status via WebSocket RCON."""
        try:
            raw = await self.send_command_custom("status")
            # Parse player count from status output
            # e.g. "players : 3 (100 max) (3 sleepers) (0 joining) (0 queued)"
            player_count = 0
            m = re.search(r"players\s*:\s*(\d+)", raw, re.IGNORECASE)
            if m:
                player_count = int(m.group(1))
            version = None
            mv = re.search(r"version\s*:\s*(\S+)", raw, re.IGNORECASE)
            if mv:
                version = mv.group(1)
            return ServerStatus(online=True, player_count=player_count, version=version)
        except Exception as exc:
            logger.warning("get_status failed: %s", exc)
            return ServerStatus(online=False)

    def get_commands(self) -> list[CommandDef]:
        from schema import get_commands
        return get_commands()

    # ------------------------------------------------------------------
    # Optional overrides
    # ------------------------------------------------------------------

    async def get_players(self, send_command) -> list[PlayerInfo]:
        """Return list of currently connected players."""
        raw = await self.send_command_custom("playerlist")
        return await self.parse_players(raw)

    async def get_server_info(self) -> dict:
        """Return basic server status info."""
        status_raw = await self.send_command_custom("status")
        return {"status": status_raw}

    async def kick_player(self, send_command, player_id: str, reason: str = "Kicked by admin") -> bool:
        """Kick a player by SteamID."""
        cmd = f'kick {player_id} "{reason}"'
        try:
            await self.send_command_custom(cmd)
            return True
        except Exception as exc:
            logger.error("Kick failed: %s", exc)
            return False

    async def ban_player(self, send_command, player_id: str, reason: str = "Banned by admin", duration: Optional[int] = None) -> bool:
        """Ban a player by SteamID."""
        cmd = f'banid {player_id} "" "{reason}"'
        try:
            await self.send_command_custom(cmd)
            return True
        except Exception as exc:
            logger.error("Ban failed: %s", exc)
            return False

    async def unban_player(self, send_command, player_id: str) -> bool:
        """Unban a player by SteamID."""
        cmd = f"unban {player_id}"
        try:
            await self.send_command_custom(cmd)
            return True
        except Exception as exc:
            logger.error("Unban failed: %s", exc)
            return False

    async def send_message(self, message: str) -> bool:
        """Broadcast a message to all players."""
        cmd = f'say "{message}"'
        try:
            await self.send_command_custom(cmd)
            return True
        except Exception as exc:
            logger.error("Say failed: %s", exc)
            return False

    async def is_connected(self) -> bool:
        """Check if WebSocket is open."""
        return self._ws is not None and not self._ws.closed
