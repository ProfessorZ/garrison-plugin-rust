"""Rust RCON command schema for Garrison."""


def get_commands():
    """Return the list of CommandDef objects for Rust."""
    from app.plugins.base import CommandDef, CommandParam

    return [
        # ── PLAYER MANAGEMENT ─────────────────────────────────────────
        CommandDef(
            name="kick",
            description="Kick a player from the server",
            category="PLAYER_MGMT",
            params=[
                CommandParam(name="steamid", type="string", description="Player SteamID or name"),
                CommandParam(name="reason", type="string", required=False, description="Kick reason"),
            ],
            admin_only=True,
            example='kick 76561198000000000 "Breaking rules"',
        ),
        CommandDef(
            name="ban",
            description="Ban a player by name",
            category="PLAYER_MGMT",
            params=[
                CommandParam(name="name", type="string", description="Player name"),
                CommandParam(name="reason", type="string", required=False, description="Ban reason"),
            ],
            admin_only=True,
            example='ban "PlayerName" "Cheating"',
        ),
        CommandDef(
            name="banid",
            description="Ban a player by SteamID",
            category="PLAYER_MGMT",
            params=[
                CommandParam(name="steamid", type="string", description="Player SteamID"),
                CommandParam(name="username", type="string", required=False, description="Username for records"),
                CommandParam(name="reason", type="string", required=False, description="Ban reason"),
            ],
            admin_only=True,
            example='banid 76561198000000000 "PlayerName" "Cheating"',
        ),
        CommandDef(
            name="unban",
            description="Unban a player by SteamID",
            category="PLAYER_MGMT",
            params=[
                CommandParam(name="steamid", type="string", description="Player SteamID"),
            ],
            admin_only=True,
            example="unban 76561198000000000",
        ),
        CommandDef(
            name="inventory.giveto",
            description="Give an item to a player",
            category="PLAYER_MGMT",
            params=[
                CommandParam(name="steamid", type="string", description="Player SteamID"),
                CommandParam(name="item", type="string", description="Item short name (e.g. wood, stones, rifle.ak)"),
                CommandParam(name="amount", type="integer", required=False, description="Amount to give", default="1"),
            ],
            admin_only=True,
            example="inventory.giveto 76561198000000000 rifle.ak 1",
        ),
        # ── ADMIN ROLES ───────────────────────────────────────────────
        CommandDef(
            name="ownerid",
            description="Grant server owner role to a player",
            category="ADMIN",
            params=[
                CommandParam(name="steamid", type="string", description="Player SteamID"),
                CommandParam(name="username", type="string", required=False, description="Username for records"),
            ],
            admin_only=True,
            example='ownerid 76561198000000000 "PlayerName"',
        ),
        CommandDef(
            name="moderatorid",
            description="Grant moderator role to a player",
            category="ADMIN",
            params=[
                CommandParam(name="steamid", type="string", description="Player SteamID"),
                CommandParam(name="username", type="string", required=False, description="Username for records"),
            ],
            admin_only=True,
            example='moderatorid 76561198000000000 "PlayerName"',
        ),
        CommandDef(
            name="removeowner",
            description="Remove owner role from a player",
            category="ADMIN",
            params=[
                CommandParam(name="steamid", type="string", description="Player SteamID"),
            ],
            admin_only=True,
            example="removeowner 76561198000000000",
        ),
        CommandDef(
            name="removemoderator",
            description="Remove moderator role from a player",
            category="ADMIN",
            params=[
                CommandParam(name="steamid", type="string", description="Player SteamID"),
            ],
            admin_only=True,
            example="removemoderator 76561198000000000",
        ),
        # ── CHAT & COMMUNICATION ──────────────────────────────────────
        CommandDef(
            name="say",
            description="Broadcast a message to all players",
            category="CHAT",
            params=[
                CommandParam(name="message", type="string", description="Message to broadcast"),
            ],
            admin_only=True,
            example='say "Server restart in 5 minutes"',
        ),
        # ── SERVER MANAGEMENT ─────────────────────────────────────────
        CommandDef(
            name="status",
            description="Show server status (players, version, fps)",
            category="SERVER",
            params=[],
            admin_only=False,
            example="status",
        ),
        CommandDef(
            name="playerlist",
            description="List connected players with SteamID, ping, health",
            category="SERVER",
            params=[],
            admin_only=False,
            example="playerlist",
        ),
        CommandDef(
            name="server.save",
            description="Force save the server",
            category="SERVER",
            params=[],
            admin_only=True,
            example="server.save",
        ),
        CommandDef(
            name="env.time",
            description="Get or set the in-game time (0–24)",
            category="SERVER",
            params=[
                CommandParam(name="time", type="float", required=False, description="Time value 0-24"),
            ],
            admin_only=True,
            example="env.time 12",
        ),
        CommandDef(
            name="weather.fog",
            description="Set fog level (0.0–1.0)",
            category="SERVER",
            params=[
                CommandParam(name="value", type="float", required=False, description="Fog intensity 0.0-1.0"),
            ],
            admin_only=True,
            example="weather.fog 0",
        ),
        CommandDef(
            name="server.fps",
            description="Show server FPS",
            category="SERVER",
            params=[],
            admin_only=False,
            example="server.fps",
        ),
        CommandDef(
            name="global.kill",
            description="Kill a player",
            category="PLAYER_MGMT",
            params=[
                CommandParam(name="steamid", type="string", description="Player SteamID"),
            ],
            admin_only=True,
            example="global.kill 76561198000000000",
        ),
        CommandDef(
            name="oxide.reload",
            description="Reload an Oxide/uMod plugin",
            category="PLUGINS",
            params=[
                CommandParam(name="plugin", type="string", required=False, description="Plugin name (omit to reload all)"),
            ],
            admin_only=True,
            example="oxide.reload MyPlugin",
        ),
        CommandDef(
            name="oxide.load",
            description="Load an Oxide/uMod plugin",
            category="PLUGINS",
            params=[
                CommandParam(name="plugin", type="string", description="Plugin name"),
            ],
            admin_only=True,
            example="oxide.load MyPlugin",
        ),
        CommandDef(
            name="oxide.unload",
            description="Unload an Oxide/uMod plugin",
            category="PLUGINS",
            params=[
                CommandParam(name="plugin", type="string", description="Plugin name"),
            ],
            admin_only=True,
            example="oxide.unload MyPlugin",
        ),
    ]
