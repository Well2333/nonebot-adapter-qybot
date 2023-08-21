from typing import Optional, Union

from nonebot.utils import logger_wrapper

logger = logger_wrapper("QY Bot")


class Log:
    @staticmethod
    def trace(message: str, exception: Optional[Exception] = None) -> None:
        logger("TRACE", message, exception)

    @staticmethod
    def debug(message: str, exception: Optional[Exception] = None) -> None:
        logger("DEBUG", message, exception)

    @staticmethod
    def info(message: str, exception: Optional[Exception] = None) -> None:
        logger("INFO", message, exception)

    @staticmethod
    def success(message: str, exception: Optional[Exception] = None) -> None:
        logger("SUCCESS", message, exception)

    @staticmethod
    def warning(message: str, exception: Optional[Exception] = None) -> None:
        logger("WARNING", message, exception)

    @staticmethod
    def error(message: str, exception: Optional[Exception] = None) -> None:
        logger("ERROR", message, exception)

    @staticmethod
    def exception(message: str, exception: Optional[Exception] = None) -> None:
        logger("EXCEPTION", message, exception)


def encode_message_id(s: str) -> int:
    parts = s.split("-")
    encoded = "".join([f"{len(part):02}" + part for part in parts])
    return int(encoded)


def decode_message_id(s: Union[int, str]) -> str:
    s = str(s)
    i = 0
    parts = []
    while i < len(s):
        length = int(s[i : i + 2])
        i += 2
        parts.append(s[i : i + length])
        i += length
    return "-".join(parts)
