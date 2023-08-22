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

        # Split by rich text patterns
        pattern = r"(\[.*?\])"
        slices = re.split(pattern, s)

        for segment_str in slices:
            if not segment_str:
                continue
            if qq := re.search(r"\[@(\d+|all)\]", segment_str):  # At segment
                segments.append(MessageSegment.at(qq.group(1)))
            elif re.match(r"\[pic,.+?\]", segment_str):  # Image segment
                assert event
                segments.append(await self._image_s2m(segment_str, event))
            elif qq := re.search(
                r"\[Reply,.*?SendQQID=(\d+),.*?\]", segment_str
            ):  # Reply segment
                segments.append(MessageSegment.at(qq.group(1)))
            else:  # Plain text
                segments.append(
                    segment_str.replace("\u005b", "[").replace("\u005d", "]")
                )

        return Message(segments)
