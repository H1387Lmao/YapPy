from .core import *
from .consts import BASE_URL
from .api import *
from .errors import (
    CommandError, CommandInvokeError, ImproperToken, InvalidSignature,
    UnknownCommand,
)
from .logger import setup_logging
from .parser import parser

import inspect
import asyncio
import aiohttp
import logging
from functools import wraps
from typing import Callable

log = logging.getLogger(__name__)

class App:
    def __init__(
        self, verbose=False,
        prefix = "!",
        configure_logging = True
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
        self._configure_logging = configure_logging

        self.__cache = {
            "users":{}, "channels":{},
            "guilds": {}, "roles": {}
        }

        # in-flight lookups, so concurrent events share one request
        self.__inflight = {}
        # running event-handler tasks (kept so they aren't garbage collected)
        self.__tasks = set()

    def _once(self, key, fn, *args):
        """Run ``fn(*args)`` once per ``key`` at a time; concurrent callers
        with the same key all wait on the same request."""
        task = self.__inflight.get(key)
        if task is None:
            task = asyncio.ensure_future(fn(*args))
            self.__inflight[key] = task
            task.add_done_callback(
                lambda _t, k=key: self.__inflight.pop(k, None)
            )
        return asyncio.shield(task)

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

    def _build_members(self, data):
        members = []

        for _user_data in data["members"]:
            roles = [
                self.__cache["roles"][role_id]
                for role_id in _user_data["roles"]
                if role_id in self.__cache["roles"]
            ]
    
            members.append(
                Member(
                    bot=self,
                    guild=None, roles=roles,
                    id=_user_data.get("id", _user_data.get("user_id")),
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

    def _build_roles(self, id, _roles_data):
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
        # The server, roles and members endpoints don't depend on each other,
        # so request them together (one round trip instead of three), and
        # look up the owner as soon as the server payload is in.
        server_t = asyncio.ensure_future(
            API.get(self.session, f"/servers/{id}")
        )
        roles_t = asyncio.ensure_future(
            API.get(self.session, f"/servers/{id}/roles")
        )
        members_t = asyncio.ensure_future(
            API.get(self.session, f"/servers/{id}/members")
        )
        try:
            _guild_data = (await server_t)["server"]
            owner, roles_data, members_data = await asyncio.gather(
                self.find_user(_guild_data["owner_id"]),
                roles_t, members_t
            )
        except BaseException:
            for t in (server_t, roles_t, members_t):
                t.cancel()
            raise

        roles = self._build_roles(id, roles_data)
        members = self._build_members(members_data)

        return Guild(
            self,
            id = id,
            name=_guild_data["name"],
            owner=owner,
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
            guild = await self._once(("guild", id), self._load_guild, id)
        return guild

    async def _load_guild(self, id):
        guild = await self.fetch_guild(id)
        self.__cache["guilds"][id] = guild
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
            channel = await self._once(("channel", id), self._load_channel, id)
        return channel

    async def _load_channel(self, id):
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
            user = await self._once(("user", id), self._load_user, id)
        return user

    async def _load_user(self, id):
        user = await self.fetch_user(id)
        self.__cache["users"][id] = user
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

    async def _parse_arguments(self, content, command=None):
        return await parser.parse_args(self, content, command)

    async def _handle_prefix_command(self, ctx):
        content = ctx.message.content
        if not content.startswith(self.prefix):
            return False

        parts = content[len(self.prefix):].split(None, 1)
        if not parts:
            return False  # nothing but the prefix
        name = parts[0].lower()
        raw = parts[1] if len(parts) > 1 else ""

        cmd = self.__commands.get(name) or self.__aliases.get(name)
        if cmd is None:
            raise UnknownCommand(f"Unknown command '{name}'.")

        # Arguments are parsed per the command's signature, so this is also
        # where bad types are caught (BadArgument) and, right after, wrong
        # counts (MissingArgument / TooManyArguments).
        arguments = await self._parse_arguments(raw, cmd)
        cmd.check_arguments(arguments)

        log.debug(
            "Command '%s' invoked by %s",
            cmd.name, getattr(ctx.message.author, "name", "?")
        )
        try:
            await cmd.func(ctx, *arguments)
        except CommandError:
            raise
        except Exception as e:
            raise CommandInvokeError(e, command=cmd) from e

        return True

    async def process_command(self, ctx):
        """Run the command in ``ctx.message`` if it is one.

        Returns whether a command ran. Problems (unknown command, wrong
        arguments, an exception inside the command) don't propagate: they go
        to the ``command_error`` event handler if you registered one, or are
        handled by :meth:`_default_command_error` otherwise.
        """
        try:
            return await self._handle_prefix_command(ctx)
        except CommandError as e:
            await self._on_command_error(ctx, e)
            return False

    async def _on_command_error(self, ctx, error):
        handler = self.__event_handlers.get("command_error")
        if handler is None:
            await self._default_command_error(ctx, error)
            return
        try:
            await handler(ctx, error)
        except Exception:
            log.exception("Exception in the 'command_error' handler")

    async def _default_command_error(self, ctx, error):
        if isinstance(error, UnknownCommand):
            # people type "!!!" or "!lol" all the time; don't answer those
            log.debug("%s", error)
            return

        if isinstance(error, CommandInvokeError):
            cmd = error.command
            log.error(
                "Command '%s' failed", cmd.name if cmd else "?",
                exc_info=error.original
            )
            return

        # The person used the command wrong, so tell them how to use it.
        author = getattr(ctx.message.author, "name", "?")
        log.info("%s: %s (from %s)", type(error).__name__, error, author)

        reply = str(error)
        if error.command is not None:
            reply += f"\nUsage: `{error.command.usage(self.prefix)}`"
        try:
            await ctx.reply(reply)
        except Exception:
            log.exception("Couldn't send the command error message")

    async def on_message(self, ctx):
        if ctx.is_bot: return
        await self.process_command(ctx)

    async def _handle_event(self, session: aiohttp.ClientSession, ev):
        d = ev["data"]

        if ev["type"] in self.__event_handlers:
            await self.__event_handlers[ev["type"]](
                await self._build_context(
                    ev
                )
            )

    async def _dispatch(self, ev):
        log.debug("Event '%s' (id %s)", ev["type"], ev["id"])
        try:
            await self._handle_event(self.session, ev)
        except Exception:
            log.exception("Unhandled exception in event '%s'", ev["type"])

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
        log.info(
            "Registered %d command(s): %s",
            len(_commands), ", ".join(c["name"] for c in _commands) or "-"
        )

    async def _event_loop(self):
        async with aiohttp.ClientSession() as self.session:
            self.session._bearer_token=self._token

            self.user = await self._load_bot_info()
            log.info("Logged in as %s (id %s)", self.user.name, self.user.id)
            await self._init_commands()

            events_init = await API.get(self.session, "/events?after=0&wait=0")
            last = events_init["last"]
            fails = 0

            if "ready" in self.__event_handlers:
                await self.__event_handlers["ready"]()

            try:
                while True:
                    try:
                        out = await API.get(self.session, f"/events?after={last}&wait=25")
                        if fails:
                            log.info("Connection to Yapper restored")
                        fails = 0
                    except Exception as e:
                        fails += 1
                        if "(401)" in str(e):
                            raise ImproperToken("Please check if your token is correctly used!")
                        wait = min(30, 2 ** fails)

                        log.warning("Problem reaching Yapper: %s. Retrying in %ss", e, wait)

                        await asyncio.sleep(wait)
                        continue
                    for ev in out["events"]:
                        if ev["id"] <= last:
                            continue
                        last = ev["id"]
                        # Run each event in its own task so one slow handler
                        # doesn't hold up the others or the next poll.
                        task = asyncio.create_task(self._dispatch(ev))
                        self.__tasks.add(task)
                        task.add_done_callback(self.__tasks.discard)
            finally:
                # let in-flight handlers finish cancelling before the
                # session is closed underneath them
                tasks = list(self.__tasks)
                for task in tasks:
                    task.cancel()
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)


    def event(self, event_type: str):
        """Register a coroutine as the handler for ``event_type``.

        Besides Yapper's own events (``"message"``, ``"ready"``) there is
        ``"command_error"``: ``async def handler(ctx, error)``, called when a
        command is unknown, given bad arguments, or raises. ``error`` is a
        :class:`yappy.errors.CommandError`. Registering it replaces the
        default behaviour (replying with the problem and a usage line).
        """
        def wrapper(func):
            if not inspect.iscoroutinefunction(func):
                raise InvalidSignature(f"Expected event handler for '{event_type}' to be a coroutine!")
            self.__event_handlers[
                event_type
            ] = func
            return func
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
           return func
        return wrapper

    def run(self, token: str):
        self._token = token

        if self._configure_logging:
            setup_logging(verbose=self._verbose)

        # asyncio.run turns Ctrl+C into a cancellation of the main task, so
        # _event_loop unwinds normally and the HTTP session gets closed.
        try:
            asyncio.run(self._event_loop())
        except KeyboardInterrupt:
            log.info("Shutting down")
__all__=["App"]
