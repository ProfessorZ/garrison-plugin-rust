from pydantic import BaseModel
from typing import Optional


class RustConnectionConfig(BaseModel):
    host: str
    rcon_port: int = 28016
    rcon_password: str
    display_name: Optional[str] = None


def get_commands():
    from app.plugins.base import CommandDef, CommandParam
    return [
        CommandDef(name="status", description="Show server status", category="SERVER"),
        CommandDef(name="playerlist", description="List connected players", category="PLAYER_MGMT"),
        CommandDef(
            name="kick",
            description="Kick a player",
            category="PLAYER_MGMT",
            params=[CommandParam(name="player_id", type="string", description="Steam ID")],
        ),
        CommandDef(
            name="banid",
            description="Ban a player by Steam ID",
            category="MODERATION",
            params=[CommandParam(name="player_id", type="string", description="Steam ID")],
        ),
        CommandDef(
            name="say",
            description="Broadcast a message",
            category="SERVER",
            params=[CommandParam(name="message", type="string", description="Message text")],
        ),
    ]
