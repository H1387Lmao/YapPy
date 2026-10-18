from .core import *
from .consts import BASE_URL
from .api import *
from .errors import ImproperToken, InvalidSignature

import inspect
import asyncio
import aiohttp
from functools import wraps
from typing import Callable

class App:
    def __init__(self, verbose=False):
        self.__commands = {}
        self.__event_handlers = {}

        self.user  = None
        self._token = None

        self._verbose = verbose

        self.__cache = {"users":{}}

    async def _load_bot_info(self):
        my_info = await api.get(self.session, "/me")

        if self._verbose:
            print(my_info)

        return Bot(
            name=my_info["username"],
            display_name=my_info["display_name"],
            id=my_info["id"],
            profile=Profile(
                avatar=my_info["avatar_url"],
                banner=my_info["banner_url"],
            ),
            bio=my_info["bio"],
            created_at=my_info["created_at"],
            
            owner_id=my_info["bot"]["owner_id"],
            is_bot=True
        )

    def get_user(
        self,
        id,
        _data
    ):
        if id in self.__cache["users"]:
            return self.__cache["users"]
        user = User(
            name=_data["author"],
            id=id
        )

        self.__cache[id]=user
        return user

    def _build_context(self, ev):
        d = ev["data"]
        
        channel=Channel(
            self,
            id=d["channel_id"],
            name=d["channel_name"]
        )

        return Context(
            self,
            is_bot=ev.get("author_bot", False),
            message=Message(
                self,
                id=d["id"],
                author=self.get_user(
                    d["author_id"], d
                ),
                channel=channel,
                created_at=d["created_at"],
                content=d["content"]
            ),
            channel=channel
        )

    async def _handle_event(self, session: aiohttp.ClientSession, ev):
        if self._verbose:
            print(ev)
        d = ev["data"]

        if ev["type"] in self.__event_handlers:
            if (cmd_name:=d.get("command")):
                if cmd_name in self.__commands:
                    await self.__commands[cmd_name].func(
                        self._build_context(
                            ev
                        )
                    )
                elif cmd_name in self.__aliases:
                    await self.__aliases[cmd_name](
                        self._build_context(
                            ev
                        )
                    )
                else:
                    raise UnknownCommand(
                        f"Unhandled command '{cmd_name}'!"
                    )
            else:
                await self.__event_handlers[ev["type"]](
                    self._build_context(
                        ev
                    )
                )

    async def _init_commands(self):
        _commands = []
        for name, func in self.__commands.items():
            _commands.append(
                {"name": name, "description": func.description}
            )
            
        await api.put(
            self.session,
            "/commands",
            {"commands": _commands}
        )

    async def _event_loop(self):
        async with aiohttp.ClientSession() as self.session:
            self.session._bearer_token=self._token
        
            self.user = await self._load_bot_info()
            await self._init_commands()

            events_init = await api.get(self.session, "/events?after=0&wait=0")
            last = events_init["last"]
            fails = 0

            while True:
                try:
                    out = await api.get(self.session, f"/events?after={last}&wait=25")
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
                        print("error handling", ev["type"], "event:", e)
                                        

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
           self.__commands[name]=Command(
                name=name,
                aliases=aliases,
                description=description,
                func=func
            )

           for alias in aliases:
               self.__aliases[alias] = self.__commands[name]

        return wrapper

    def run(self, token: str):
        self._token = token

        self._yappy_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._yappy_loop)

        try:
            self._yappy_loop.run_until_complete(self._event_loop())
        finally:
            self._yappy_loop.close()
