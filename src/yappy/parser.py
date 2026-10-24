import inspect
import logging
import math
import re
from typing import Any, List, Union

from .core import Channel, Role, User
from .errors import BadArgument

log = logging.getLogger(__name__)

# What a person sees when an argument doesn't fit the annotation.
_EXPECTED = {
    int: "a whole number",
    float: "a number",
    bool: "true or false",
    User: "a user mention like <@123>",
    Channel: "a channel mention like <#123>",
    Role: "a role mention like <@&123>",
}
_NOT_FOUND = {
    User: "a user that exists",
    Channel: "a channel that exists",
    Role: "a role that exists",
}
_MODELS = (User, Channel, Role)
_INT = re.compile(r'^[+-]?[0-9]+$')
_TRUE = {"true", "yes", "y", "on", "1"}
_FALSE = {"false", "no", "n", "off", "0"}


class CommandParser:
    def __init__(self):
        self.token_regex = re.compile(
            r'"([^"\\]*(?:\\.[^"\\]*)*)"|'
            r"'([^'\\]*(?:\\.[^'\\]*)*)'|"
            r'(<[#@&!]+[^\s>]+>)|'
            r'([^\s"\']+)'
        )
        self.user_regex = re.compile(r'^<@!?([0-9\-]+)>$|^<@!(.+)>$')
        self.channel_regex = re.compile(r'^<#([0-9\-]+)>$|^<#(.+)>$')
        self.role_regex = re.compile(r'^<@&([0-9\-]+)>$|^<@&(.+)>$')

    async def parse_args(self, bot, text: str, command=None) -> List[Any]:
        """Split ``text`` into arguments.

        When ``command`` is given, each argument is converted according to
        the annotation of the parameter it will be passed to (``str``,
        ``int``, ``float``, ``bool``, ``User``, ``Channel`` or ``Role``) and
        a :class:`~yappy.errors.BadArgument` is raised if it doesn't fit.
        Without annotations the type is guessed, as before.
        """
        parsed_arguments = []

        for index, match in enumerate(self.token_regex.finditer(text)):
            dq_str, sq_str, _raw, unquoted = match.groups()

            if dq_str is not None:
                kind, token = "quoted", dq_str.encode().decode('unicode_escape')
            elif sq_str is not None:
                kind, token = "quoted", sq_str.encode().decode('unicode_escape')
            elif _raw is not None:
                kind, token = "mention", _raw
            else:
                kind, token = "bare", unquoted

            param = command.param_for(index) if command is not None else None
            parsed_arguments.append(
                await self._convert(bot, kind, token, param, index, command)
            )

        return parsed_arguments

    async def _convert(self, bot, kind, token, param, index, command):
        hint = param.annotation if param is not None else inspect.Parameter.empty
        name = param.name if param is not None else f"argument {index + 1}"

        def bad(expected):
            return BadArgument(name, token, expected, command=command)

        if hint is str:
            return token

        if hint is int:
            if kind == "mention" or not _INT.match(token):
                raise bad(_EXPECTED[int])
            return int(token)

        if hint is float:
            try:
                value = float(token) if kind != "mention" else math.nan
            except ValueError:
                value = math.nan
            if not math.isfinite(value):
                raise bad(_EXPECTED[float])
            return value

        if hint is bool:
            word = token.lower()
            if kind != "mention" and word in _TRUE:
                return True
            if kind != "mention" and word in _FALSE:
                return False
            raise bad(_EXPECTED[bool])

        # No annotation (or one we don't convert): same behaviour as before.
        if kind == "quoted":
            value = token
        elif kind == "mention":
            try:
                value = await self._process_mentions(bot, token)
            except RuntimeError as e:
                # the API said no (404 etc.); don't leak its message to chat
                log.debug("Couldn't resolve mention %r: %s", token, e)
                raise bad(_NOT_FOUND.get(hint, "a mention of something that exists"))
        else:
            value = self._parse_primitive(token)

        if hint in _MODELS and not isinstance(value, hint):
            raise bad(_EXPECTED[hint])
        return value

    async def _process_mentions(self, bot, token: str) -> Any:
        if user_match := self.user_regex.match(token):
            user_id = user_match.group(1) or user_match.group(2)
            return await self._parse_user(bot, user_id)

        if channel_match := self.channel_regex.match(token):
            channel_id = channel_match.group(1) or channel_match.group(2)
            return await self._parse_channel(bot, channel_id)

        if role_match := self.role_regex.match(token):
            role_id = role_match.group(1) or role_match.group(2)
            return await self._parse_role(bot, role_id)

        return token

    def _parse_primitive(self, token: str) -> Union[int, float, str]:
        if re.match(r'^-?\d+$', token):
            return int(token)
        if re.match(r'^-?\d*\.\d+$', token):
            return float(token)
        return token

    async def _parse_user(self, bot, user_id: str):
        return await bot.find_user(user_id)

    async def _parse_channel(self, bot, channel_id: str):
        return await bot.find_channel(channel_id)

    async def _parse_role(self, bot, role_id: str):
        return await bot.find_role(role_id)

parser = CommandParser()
