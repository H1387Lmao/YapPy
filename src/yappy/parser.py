import re
from typing import Any, List, Union

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

    async def parse_args(self, bot, text: str) -> List[Any]:
        parsed_arguments = []
        
        for match in self.token_regex.finditer(text):
            dq_str, sq_str, _raw, unquoted = match.groups()
            
            if dq_str is not None:
                parsed_arguments.append(dq_str.encode().decode('unicode_escape'))
                continue
            if sq_str is not None:
                parsed_arguments.append(sq_str.encode().decode('unicode_escape'))
                continue
                
            if _raw is not None:
                parsed_arguments.append(await self._process_mentions(bot, _raw))
                continue
                
            if unquoted is not None:
                parsed_arguments.append(self._parse_primitive(unquoted))
                
        return parsed_arguments

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
