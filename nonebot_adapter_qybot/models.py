from typing import Literal, Optional, Union

from nonebot.adapters.onebot.v11 import Event as OneBot11Event
from pydantic import BaseModel, Field, ValidationError


class Event(BaseModel):
    isSelf: bool
    """是否为自身消息"""
    type_: Literal["message", "notice"] = Field(alias="type")
    """消息类型"""
    userId: str
    """发送者QQ号"""
    messageId: str
    """消息ID"""
    botId: str
    """自己的QQ号"""
    content: str
    """消息内容"""

    @classmethod
    def from_json(cls, data: Union[str, bytes]) -> Optional["Event"]:
        subclasses = cls.__subclasses__()

        for subclass in subclasses:
            try:
                return subclass.parse_raw(data)
            except ValidationError:
                continue
        return None

    def to_onebot11_event(self) -> OneBot11Event:
        raise NotImplementedError


class PrivateEvent(Event):
    from_: Literal["friend", "groupTemporary"] = Field(alias="from")
    """消息类型"""


class GroupEvent(Event):
    from_: Literal["group"] = Field(alias="from")
    """消息类型"""
    groupId: str
    """群号"""
    groupMemberCard: str
    """发送者群名片"""
    groupName: str
    """群名"""


class FriendRequest(Event):
    userName: str
    """用户昵称"""
    requestType: int
    """请求类型"""
    token: str
    """好友申请token"""
