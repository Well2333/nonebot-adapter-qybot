from typing import List

from pydantic import BaseModel, Extra, Field, IPvAnyAddress


class Config(BaseModel, extra=Extra.ignore):
    qy_host: IPvAnyAddress = "127.0.0.1" # type: ignore
    qy_port: int = Field(80, ge=0, le=65535)
    qy_token: str
    qy_bots: List[str] = []
    qy_bot_refresh_interval :int = 60
