import re
from typing import TYPE_CHECKING, Dict, Optional, Union

from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.log import logger

if TYPE_CHECKING:
    from .adapter import Adapter
    from .event import Event


class MessageFormatter:
    def __init__(self, adapter: "Adapter") -> None:
        self.adapter = adapter

    async def _image_m2s(
        self, segment: MessageSegment, event: Union["Event", Dict]
    ) -> str:
        _data = {
            "botId": dict(event).get("botId"),
            "image": segment.data.get("file"),
            "isTemp": False,
            "isGif": False,
        }
        if gid := dict(event).get("groupId"):
            _data["path"] = "uploadGroupImage"
            _data["groupId"] = gid
        else:
            _data["path"] = "uploadUserImage"
            _data["userId"] = dict(event).get("userId")
        data = await self.adapter.post(**_data)
        return data["imageCode"]

    async def _image_s2m(
        self, segment: str, event: Union["Event", Dict]
    ) -> MessageSegment:
        _data = {
            "botId": dict(event).get("botId"),
            "imageCode": segment,
        }
        if gid := dict(event).get("groupId"):
            _data["groupId"] = gid

        data = await self.adapter.post(
            "getImageCodeUrl",
            **_data,
        )

        return MessageSegment.image(data["url"])

    async def m2s(
        self, message: Union[Message, str], event: Optional[Union["Event", Dict]]
    ) -> str:
        if isinstance(message, str):
            return message
        result = []
        for segment in message:
            if isinstance(segment, str) or segment.type == "text":
                result.append(
                    str(segment).replace("[", "\u005b").replace("]", "\u005d")
                )
            elif segment.type == "at":
                result.append(f"[@{segment.data['qq']}]")
            elif segment.type == "image":
                assert event
                result.append(await self._image_m2s(segment, event))
            else:
                logger.info(f"NotImplemented MessageSegment {segment.type}")

        return "".join(result)

    async def s2m(self, s: str, event: Optional[Union["Event", Dict]]) -> Message:
        segments = []
        # 找出全部可被处理的富文本
        pattern = r"(\[@(\d+|all)\])|(\[pic,.+?\])|(\[Reply,.*?SendQQID=(\d+),.*?\])"
        matches = re.finditer(pattern, s)

        last_end = 0
        for match in matches:
            start, end = match.span()
            if start > last_end:
                segment_str = (
                    s[last_end:start].replace("\u005b", "[").replace("\u005d", "]")
                )
                segments.append(segment_str)

            if match.group(2):  # @提及片段
                segments.append(MessageSegment.at(match.group(2)))
            elif match.group(3):  # 图片片段
                assert event
                segments.append(await self._image_s2m(match.group(3), event))
            elif match.group(5):  # 回复片段
                segments.append(MessageSegment.at(match.group(5)))

            last_end = end

        # 捕获最后一个匹配后的任何剩余纯文本
        if last_end < len(s):
            segment_str = s[last_end:].replace("\u005b", "[").replace("\u005d", "]")
            segments.append(segment_str)

        return Message(segments)
