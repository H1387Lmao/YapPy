from .core import *
from .consts import BASE_URL
from .api import *
from .errors import ImproperToken, InvalidSignature, UnknownCommand
from .parser import parser

import inspect
import asyncio
import aiohttp
import traceback
from functools import wraps
from typing import Callable

class App:
    def __init__(
        self, verbose=False,
        prefix = "!"
    ):
        self.__commands = {}
        self.__event_handlers = {
            "message": self.on_message
        }
        self.__aliases = {}

        self.user  = None
        self.prefix = prefix

        self._token = None

        self._verbose = verbose

        self.__cache = {
            "users":{}, "channels":{},
            "guilds": {}, "roles": {}
        }

    async def _load_bot_info(self):
        my_info = await API.get(self.session, "/me")

        return Bot(
            name=my_info["username"],
            display_name=my_info["display_name"],
            id=my_info["id"],
            assets=Assets(
                avatar=my_info["avatar_url"],
                banner=my_info["banner_url"],
            ),
            bio=my_info["bio"],
            created_at=my_info["created_at"],
            
            owner_id=my_info["bot"]["owner_id"],
            is_bot=True
        )

    async def _cache_members(
        self, id
    ):
        _members_data = (await API.get(
            self.session, f"/servers/{id}/members"
        ))["members"]

        members = []

        for _user_data in _members_data:
            roles = [
                self.__cache["roles"][role_id]
                for role_id in _user_data["roles"]
                if role_id in self.__cache["roles"]
            ]
    
            members.append(
                Member(
                    bot=self,
                    guild=None, roles=roles,
                    id=id,
                    name = _user_data["username"],
                    display_name = _user_data["display_name"],
                    badges = _user_data["badges"],
                    joined_at = _user_data["joined_at"],
                    nickname = _user_data["nickname"],
                    assets = Assets(
                        avatar = "https://files.yapper.website/avatars/"+_user_data.get("avatar_path",""),
                        banner = "https://files.yapper.website/banners/"+_user_data.get("banner_path", "")
                    )
                )
            )

        return members

    async def _cache_roles(
        self, id
    ):
        _roles_data = (await API.get(
            self.session, f"/servers/{id}/roles"
        ))

        roles = []

        for role in _roles_data["roles"]:
            roles.append(
                r:= Role(
                    id = role["id"],
                    name = role["name"],
                    color = role["color"],
                    permissions = Permissions(
                        manage_server=role["manage_server"],
                        manage_messages=role["manage_messages"],
                        **role["perms"]
                    ),
                    auto = role["auto"],
                    position = role["position"]
                )
            )
            self.__cache["roles"][id]=r
        return roles

    def get_role(self, rid):
        return self.__cache["roles"].get(id)
       
    async def fetch_guild(
        self, id
    ) -> Guild:
        _guild_data = (await API.get(
            self.session, f"/servers/{id}"
        ))["server"]

        roles = await self._cache_roles(id)
        members = await self._cache_members(id)

        return Guild(
            self,
            id = id,
            name=_guild_data["name"],
            owner=await self.find_user(
                _guild_data["owner_id"]
            ),
            member_count = _guild_data["member_count"],
            discoverable = _guild_data["discoverable"],
            created_at = _guild_data["created_at"],
            assets = Assets(
                icon = _guild_data["icon_path"],
                banner = _guild_data["banner_path"]
            ),
            roles = roles,
            members = members
        )
    async def find_guild(
        self, id
    ):
        guild = self.get_guild(id)
        if guild is None:
            guild = await self.fetch_guild(id)
            self.__cache["guilds"]=guild
        return guild

    def get_guild(
        self, id
    ):
        return self.__cache["guilds"].get(id)

    async def fetch_channel(
        self, id
    ) -> Channel:
        _channel_data = (await API.get(
            self.session, f"/channels/{id}"
        ))["channel"]

        return Channel(
            self,
            id=_channel_data["id"],
            kind=_channel_data["kind"],
            name=_channel_data["name"],
            slowmode=_channel_data["slowmode"],
            private=_channel_data["private"],
            guild=await self.find_guild(
                _channel_data["server_id"]
            ),
            read_only=_channel_data["read_only"],
            category_id=_channel_data["category_id"]
        )

    async def find_channel(
        self, id
    ):
        channel = self.get_channel(id)
        if channel is None:
            channel = await self.fetch_channel(id)
            self.__cache["channels"][id] = channel
        return channel

    def get_channel(
        self, id
    ):
        return self.__cache["channels"].get(id)

    async def fetch_user(
        self,
        id
    ) -> User:
        _user_data = (await API.get(
            self.session, f"/users/{id}"
        ))["user"]

        return User(
            bot=self,
            id=id,
            name = _user_data["username"],
            display_name = _user_data["display_name"],
            badges = _user_data["badges"],
            created_at = _user_data["created_at"],
            bio = _user_data["bio"],
            pronouns = _user_data["pronouns"],
            assets = Assets(
                avatar = _user_data["avatar_path"],
                banner = _user_data["banner_path"]
            )
        )

    async def find_user(
        self,
        id,
    ) -> User:
        user = self.get_user(id)

        if user is None:
            user = await self.fetch_user(
                id
            )

            self.__cache["users"][id]=user
        return user

    def get_user(
        self, id
    ):
        return self.__cache["users"].get(id)

    async def _build_context(self, ev):
        d = ev["data"]
        
        channel = await self.find_channel(d["channel_id"])

        return Context(
            self,
            is_bot=ev.get("author_bot", False),
            message=Message(
                self,
                id=d["id"],
                author=await channel.guild.find_member(
                    d["author_id"]
                ),
                channel=channel,
                created_at=d["created_at"],
                content=d["content"]
            ),
            channel=channel
        )

    async def _parse_arguments(self, content):
        return await parser.parse_args(self, content)

    async def _handle_prefix_command(self, ctx):
        if ctx.message.content.startswith(self.prefix):
            if " " in ctx.message.content:
                name, raw = ctx.message.content.removeprefix(self.prefix).split(" ", maxsplit=1)
            else:
                name = ctx.message.content.removeprefix(self.prefix)
                raw = ""
            arguments = await self._parse_arguments(
                raw
            )

            cmd = None
            if name in self.__commands:
                cmd = self.__commands[name.lower()]
            elif name in self.__aliases:
                cmd = self.__aliases[name.lower()]
            else:
                raise UnknownCommand(
                    f"Unhandled command '{name.lower()}'!"
                )
                
            await cmd.func(
                ctx, *arguments
            )

            return True
        return False

    async def process_command(self, ctx):
        await self._handle_prefix_command(
            ctx
        )

    async def on_message(self, ctx):
        if ctx.is_bot: return
        await process_command(ctx)

    async def _handle_event(self, session: aiohttp.ClientSession, ev):
        d = ev["data"]

        if ev["type"] in self.__event_handlers:
            await self.__event_handlers[ev["type"]](
                await self._build_context(
                    ev
                )
            )

    async def _init_commands(self):
        _commands = []
        for name, func in self.__commands.items():
            _commands.append(
                {"name": name, "description": func.description}
            )
            
        await API.put(
            self.session,
            "/commands",
            {"commands": _commands}
        )

    async def _event_loop(self):
        async with aiohttp.ClientSession() as self.session:
            self.session._bearer_token=self._token

            self.user = await self._load_bot_info()
            await self._init_commands()

            events_init = await API.get(self.session, "/events?after=0&wait=0")
            last = events_init["last"]
            fails = 0

            if "ready" in self.__event_handlers:
                await self.__event_handlers["ready"]()

            while True:
                try:
                    out = await API.get(self.session, f"/events?after={last}&wait=25")
                    fails = 0
                except Exception as e:
                    fails += 1
                    if "(401)" in str(e):
                        raise ImproperToken("Please check if your token is correctly used!")
                    wait = min(30, 2 ** fails)
                    
                    print(f"retrying in {wait}s:", e)
                    
                    await asyncio.sleep(wait)
                    continue
                for ev in out["events"]:
                    if ev["id"] <= last:
                        continue
                    last = ev["id"]
                    try:
                        await self._handle_event(self.session, ev)
                    except Exception as e: 
                        traceback.print_exc()
                                        

    def event(self, event_type: str):
        def wrapper(func):
            if not inspect.iscoroutinefunction(func):
                raise InvalidSignature(f"Expected event handler for '{event_type}' to be a coroutine!")
            self.__event_handlers[
                event_type
            ] = func
        return wrapper

    def command(
        self,
        name, *,
        aliases=[],
        description=""
    ):
        def wrapper(
            func
        ):
           if not inspect.iscoroutinefunction(func):
                raise InvalidSignature(f"Expected command handler for '{name}' to be a coroutine!")
           self.__commands[name.lower()]=Command(
                name=name,
                aliases=aliases,
                description=description,
                func=func
            )

           for alias in aliases:
               self.__aliases[alias.lower()] = self.__commands[name.lower()]
        return wrapper

    def run(self, token: str):
        self._token = token

        self._yappy_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._yappy_loop)

        try:
            self._yappy_loop.run_until_complete(self._event_loop())
        finally:
            self._yappy_loop.close()
__all__=["App"]
