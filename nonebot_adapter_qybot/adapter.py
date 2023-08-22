import asyncio
import json
from typing import Any, Dict, List, Union

from nonebot.adapters import Adapter as BaseAdapter
from nonebot.adapters.onebot.v11 import Bot, Event
from nonebot.adapters.onebot.v11.exception import ApiNotAvailable
from nonebot.drivers import Driver, ForwardDriver, Request, WebSocket
from nonebot.exception import WebSocketClosed
from nonebot.typing import overrides
from nonebot.utils import escape_tag

from .api import API_HANDLERS
from .config import Config
from .event import Event as RawEvent
from .exception import ActionFailed
from .message import MessageFormatter
from .utils import Log

RECONNECT_INTERVAL = 3.0
BOT_REFRESH_LOCK = asyncio.Lock()


class Adapter(BaseAdapter):
    @overrides(BaseAdapter)
    def __init__(self, driver: Driver, **kwargs: Any):
        super().__init__(driver, **kwargs)
        self.adap_config: Config = Config(**self.config.dict())
        self.ws_url = f"ws://{self.adap_config.qy_host}:{self.adap_config.qy_port}/event?token={self.adap_config.qy_token}"
        self.http_url = f"http://{self.adap_config.qy_host}:{self.adap_config.qy_port}"
        self.bots: Dict[str, Bot] = {}
        self.formatter = MessageFormatter(self)
        self.setup()

    @classmethod
    @overrides(BaseAdapter)
    def get_name(cls) -> str:
        return "QY Bot"

    def setup(self) -> None:
        if not isinstance(self.driver, ForwardDriver):
            raise RuntimeError(
                f"Current driver {self.config.driver} does not support "
                "forward connections! QY Bot Adapter need a ForwardDriver to work."
            )
        self.driver.on_startup(self._forward_ws)

    async def _forward_ws(self) -> None:
        request = Request(
            "GET",
            self.ws_url,
            timeout=9999999,
        )

        while True:
            try:
                async with self.websocket(request) as ws:
                    Log.debug(
                        (
                            "WebSocket Connection to "
                            f"{escape_tag(self.ws_url)} established"
                        ),
                    )

                    task = asyncio.create_task(self._bots_control_inf())  # 创建循环 Bot 刷新
                    try:
                        await self._loop(ws)
                    except WebSocketClosed as e:
                        Log.error(
                            "<r><bg #f8bbd0>WebSocket Closed</bg #f8bbd0></r>",
                            e,
                        )
                    except Exception as e:
                        Log.error(
                            (
                                "<r><bg #f8bbd0>"
                                "Error while process data from websocket "
                                f"{escape_tag(self.ws_url)}. Trying to reconnect..."
                                "</bg #f8bbd0></r>"
                            ),
                            e,
                        )
                    finally:
                        task.cancel()  # 取消循环 Bot 刷新
                        await ws.close()
                        # 销毁全部 Bot
                        for bot in self.bots.values():
                            self.bot_disconnect(bot)

            except Exception as e:
                Log.error(
                    (
                        "<r><bg #f8bbd0>"
                        "Error while setup websocket to "
                        f"{escape_tag(self.ws_url)}. Trying to reconnect..."
                        "</bg #f8bbd0></r>"
                    ),
                    e,
                )

            await asyncio.sleep(RECONNECT_INTERVAL)

    async def _loop(self, ws: WebSocket) -> None:
        """接收并处理事件"""
        while True:
            payload = await ws.receive()
            Log.trace(
                f"Received payload: {escape_tag(repr(payload))}",
            )
            try:
                if raw_event := RawEvent.from_json(payload):
                    await self._handle_event(
                        raw_event.botId,
                        await raw_event.to_onebot11_event(self.formatter),
                    )
                else:
                    Log.warning(
                        f"Unknown payload from server: {escape_tag(repr(payload))}",
                    )
            except Exception as e:
                Log.error(
                    f"Error while parse event to OneBot event: {escape_tag(repr(payload))}",
                    e,
                )

    async def _handle_event(self, botId: str, event: Event, retry: bool = True) -> None:
        if bot := self.bots.get(botId):
            # 如果 Bot 存在
            asyncio.create_task(bot.handle_event(event=event))
        elif retry and (
            not self.adap_config.qy_bots or botId in self.adap_config.qy_bots
        ):
            # 如果不存在，但在监听列表中(或无监听列表)，则刷新bot列表后重试一次
            await self._bots_control()
            await self._handle_event(botId, event, retry=False)
        else:
            Log.warning(
                f"Event cannot get the corresponding Bot: {event.json()}",
            )

    async def _bots_control_inf(self):
        while True:
            try:
                await self._bots_control()
                await asyncio.sleep(self.adap_config.qy_bot_refresh_interval)
            except Exception as e:
                Log.error("Refresh Bot list failed", e)

    async def _bots_control(self):
        async with BOT_REFRESH_LOCK:
            Log.trace("Refreshing Bot list...")
            data = await self.post("listBot")
            bots: List[Dict[str, str]] = data.get("bots", [])
            connected_bots = list(self.bots.keys())
            for bot in bots:
                if (
                    self.adap_config.qy_bots
                    and bot["id"] not in self.adap_config.qy_bots
                ):
                    # 不在监听列表 -> 忽略
                    continue
                if bot["status"] != "登录完毕":
                    # Bot 未上线 -> 忽略
                    continue
                elif bot["id"] in connected_bots:
                    # 已存在 Bot 实例 -> 忽略
                    connected_bots.remove(bot["id"])
                else:
                    # 不存在 Bot 实例 -> 新建
                    bot_ = Bot(self, bot["id"])
                    self.bot_connect(bot_)
                    Log.info(
                        f"<g>Bot {escape_tag(str(bot['id']))} connected</g>",
                    )
            # 已掉线但仍存在的 Bot 实例 -> 销毁
            for bot_id in connected_bots:
                bot_ = self.bots[bot_id]
                self.bot_disconnect(bot_)
                Log.warning(
                    f"<r>Bot {escape_tag(str(bot_id))} disconnected</r>",
                )

    async def post(self, path: str, **data) -> Dict[str, Any]:
        Log.trace(data)
        path = path.strip("/")
        data = await self.request(
            Request(
                "POST",
                url=f"{self.http_url}/{path}/",
                headers={
                    "X-Token": self.adap_config.qy_token,
                    "Content-Type": "application/json",
                },
                json=data,
            )
        )

        if data.content and (content := json.loads(data.content)):
            if content["code"] == 0:
                Log.trace(content["data"])
                return content["data"]

        raise ActionFailed(data)

    @overrides(BaseAdapter)
    async def _call_api(self, bot: Bot, api: str, **data: Any) -> Any:
        Log.debug(f"Calling API <y>{api}</y>")
        api_handler = API_HANDLERS.get(api, None)
        if api_handler is None:
            raise ApiNotAvailable
        return await api_handler(self, botId=bot.self_id, **data)
