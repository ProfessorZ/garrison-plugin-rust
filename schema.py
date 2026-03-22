from pydantic import BaseModel
from typing import Optional


class RustConnectionConfig(BaseModel):
    host: str
    rcon_port: int = 28016
    rcon_password: str
    display_name: Optional[str] = None
