import time
from typing import TYPE_CHECKING, Literal, Optional, Union

from nonebot.adapters.onebot.v11 import Event as OneBot11Event
from nonebot.adapters.onebot.v11 import GroupMessageEvent, PrivateMessageEvent
from pydantic import BaseModel, Extra, Field, ValidationError

from .utils import encode_message_id

if TYPE_CHECKING:
    from .message import MessageFormatter


class Event(BaseModel, extra=Extra.forbid):
    """全部事件"""

    type_: Literal["message", "notice"] = Field(alias="type")
    """消息类型"""
    botId: str
    """自己的QQ号"""
    userId: str
    """发送者QQ号"""

    @classmethod
    def from_json(cls, data: Union[str, bytes]) -> Optional["Event"]:
        subclasses = cls.__subclasses__()

        for subclass in subclasses:
            try:
                return subclass.parse_raw(data)
            except ValidationError:
                continue
        return None

    async def to_onebot11_event(self, formatter: "MessageFormatter") -> OneBot11Event:
        raise NotImplementedError


class PrivateEvent(Event):
    type_: Literal["message"] = Field(alias="type")
    """消息类型"""
    isSelf: bool
    """是否为自身消息"""
    messageId: str
    """消息ID"""
    content: str
    """消息内容"""
    from_: Literal["friend", "groupTemporary"] = Field(alias="from")
    """消息类型"""

    async def to_onebot11_event(
        self, formatter: "MessageFormatter"
    ) -> PrivateMessageEvent:
        message = await formatter.s2m(self.content, self)
        return PrivateMessageEvent.parse_obj(
            {
                "time": int(time.time()),
                "self_id": int(self.botId),
                "post_type": "message",
                "sub_type": "group" if self.from_ == "groupTemporary" else "friend",
                "user_id": int(self.userId),
                "message_type": "private",
                "message_id": encode_message_id(self.messageId),
                "message": message,
                "original_message": message,
                "raw_message": self.content,
                "font": 0,
                "sender": {
                    "user_id": int(self.userId),
                },
            }
        )


class GroupEvent(Event):
    type_: Literal["message"] = Field(alias="type")
    """消息类型"""
    isSelf: bool
    """是否为自身消息"""
    messageId: str
    """消息ID"""
    content: str
    """消息内容"""
    from_: Literal["group"] = Field(alias="from")
    """消息类型"""
    groupId: str
    """群号"""
    groupMemberCard: str
    """发送者群名片"""
    groupName: str
    """群名"""

    async def to_onebot11_event(
        self, formatter: "MessageFormatter"
    ) -> GroupMessageEvent:
        message = await formatter.s2m(self.content, self)
        return GroupMessageEvent.parse_obj(
            {
                "time": int(time.time()),
                "self_id": int(self.botId),
                "post_type": "message",
                "sub_type": "normal",
                "user_id": int(self.userId),
                "group_id": int(self.groupId),
                "message_type": "group",
                "anonymous": None,
                "message_id": encode_message_id(self.messageId),
                "message": message,
                "original_message": message,
                "raw_message": self.content,
                "font": 0,
                "sender": {
                    "user_id": int(self.userId),
                },
            }
        )


# class FriendRequest(Event):
#     userName: str
#     """用户昵称"""
#     requestType: int
#     """请求类型"""
#     token: str
#     """好友申请token"""
