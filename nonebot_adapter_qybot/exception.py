import json
from typing import Optional

from nonebot.adapters.onebot.v11.exception import ActionFailed as OneBot11ActionFailed
from nonebot.drivers import Response


class ActionFailed(OneBot11ActionFailed):
    def __init__(self, response: Response):
        self.status_code: int = response.status_code
        self.code: Optional[int] = None
        self.message: Optional[str] = None
        self.data: Optional[dict] = None
        if response.content:
            body = json.loads(response.content)
            self._prepare_body(body)

    def __repr__(self) -> str:
        return (
            f"<ActionFailed: {self.status_code}, code={self.code}, "
            f"message={self.message}, data={self.data}>"
        )

    def __str__(self):
        return self.__repr__()

    def _prepare_body(self, body: dict):
        self.code = body.get("code", None)
        self.message = body.get("msg", None)
        self.data = body.get("data", None)
