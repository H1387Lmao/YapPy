from .api import *
from typing import Callable
import inspect
import logging
import typing
import urllib.parse
from dataclasses import dataclass
from .errors import InvalidSignature, MissingArgument, TooManyArguments
from .utils import get_asset_url

log = logging.getLogger(__name__)

class Assets:
    def __init__(self,
        avatar: str = "",
        banner: str = "",
        icon: str = ""
    ):
        self.avatar = get_asset_url("avatar", avatar)
        self.banner = get_asset_url("banner", banner)
        self.icon = get_asset_url("icon", icon)

class User:
    def __init__(self,
        bot = None,
        name: str ="",
        display_name: str = "",
        id=0,
        assets: Assets | None = None,
        created_at: str = "",
        bio: str = "",
        pronouns: str = "",
        badges: list = [],
        is_bot: bool = True
    ):
        self.bot = bot
        self.name = name
        self.id = id
        self.assets = assets
        self.display_name = display_name or name
        self.is_bot = is_bot
        self.bio = bio

class Bot(User):
    def __init__(self, owner_id=None, **kwargs):
        super().__init__(**kwargs)
        self.owner_id = owner_id

@dataclass(frozen=True)
class CommandParam:
    """One argument a command accepts (not counting ``ctx``)."""
    name: str
    annotation: object = inspect.Parameter.empty
    required: bool = True

class Command:
    def __init__(self,
        name: str,
        aliases: list[str] = [],
        description: str = "",
        func: Callable = None,
    ):
        self.name = name
        self.aliases = aliases
        self.description = description
        self.func = func

        self.params: list[CommandParam] = []
        self.var_positional: CommandParam | None = None
        if func is not None:
            self._inspect_signature()

    def _inspect_signature(self):
        P = inspect.Parameter
        params = list(inspect.signature(self.func).parameters.values())

        if not params or params[0].kind not in (
            P.POSITIONAL_ONLY, P.POSITIONAL_OR_KEYWORD
        ):
            raise InvalidSignature(
                f"Command '{self.name}' must accept 'ctx' as its first argument!"
            )

        try:
            hints = typing.get_type_hints(self.func)
        except Exception:
            # unresolvable annotations: treat them as "no annotation"
            hints = {}

        for p in params[1:]:
            ann = hints.get(p.name, p.annotation)
            if p.kind in (P.POSITIONAL_ONLY, P.POSITIONAL_OR_KEYWORD):
                self.params.append(
                    CommandParam(p.name, ann, p.default is P.empty)
                )
            elif p.kind is P.VAR_POSITIONAL:
                self.var_positional = CommandParam(p.name, ann, False)
            elif p.kind is P.KEYWORD_ONLY and p.default is P.empty:
                raise InvalidSignature(
                    f"Command '{self.name}' has a required keyword-only "
                    f"argument '{p.name}', which can't be filled from chat!"
                )

    def param_for(self, index: int) -> CommandParam | None:
        """The parameter that the argument at ``index`` is bound to."""
        if index < len(self.params):
            return self.params[index]
        return self.var_positional

    def check_arguments(self, args: list):
        """Raise if ``args`` doesn't fit this command's parameters."""
        required = sum(1 for p in self.params if p.required)
        if len(args) < required:
            raise MissingArgument(self.params[len(args)].name, command=self)
        if self.var_positional is None and len(args) > len(self.params):
            raise TooManyArguments(len(self.params), len(args), command=self)

    def usage(self, prefix: str = "") -> str:
        parts = [
            f"<{p.name}>" if p.required else f"[{p.name}]"
            for p in self.params
        ]
        if self.var_positional is not None:
            parts.append(f"[{self.var_positional.name}...]")
        return " ".join([f"{prefix}{self.name}", *parts])

class Permissions:
    def __init__(self, **perms):
        self._perms = perms
    def has_perm(self, perm):
        return self._perms.get(perm, False)

class Role:
    def __init__(self,
        id: str = "",
        name: str = "",
        color: str = "",
        permissions: Permissions | None = None,
        auto: None = None, # unused
        position: int = 0,
        
    ):
        self.id = id
        self.name = name
        self.color = color
        self.permissions = permissions
        self.auto = auto
        self.position = position

class Guild:
    def __init__(self,
        bot,
        id: str = "",
        name: str = "",
        created_at: str = "",
        discoverable: bool = True,
        member_count: int = 1,
        owner: User | None = None,
        assets: Assets | None = None,
        roles: list[Role] = [],
        members: list[Member] = []
    ):
        self.id = id
        self.name = name
        self.created_at = created_at
        self.member_count = member_count
        self.owner = owner
        self.assets = assets
        self.discoverable = discoverable
        self.roles = roles
        self.bot = bot
        
        self.members = members

        self._cache={"members": {}, "roles": {
            r.id: r for r in roles
        }}

        for m in members:
            if m.id is not None:
                self._cache["members"][m.id] = m
            m. guild = self
    async def find_member(self, mid):
        member = self.get_member(mid)
        if member is None:
            # concurrent lookups of the same member share one request
            member = await self.bot._once(
                ("member", self.id, mid), self._load_member, mid
            )
        return member

    async def _load_member(self, mid):
        _user_data = (await API.get(
            self.bot.session,
            f"/servers/{self.id}/members/{mid}"
        ))["member"]

        roles = [
            self._cache["roles"][role_id]
            for role_id in _user_data["roles"]
            if role_id in self._cache["roles"]
        ]

        member = Member(
            bot=self.bot,
            guild=self, roles=roles,
            id=mid,
            name = _user_data["username"],
            display_name = _user_data["display_name"],
            badges = _user_data["badges"],
            joined_at = _user_data["joined_at"],
            nickname = _user_data["nickname"],
            assets = Assets(
                avatar = "https://files.yapper.website/avatars/"+_user_data.get("avatar_path",""),
                banner = "https://files.yapper.website/banners/"+_user_data.get("banner_path", "")
            ),
        )

        self._cache["members"][mid] = member
        return member

    def get_member(self, mid):
        return self._cache["members"].get(mid, None)

class Channel:
    def __init__(self,
        bot,
        id=0,
        name: str = "",
        kind: str = "",
        private: bool = False,
        slowmode: int = 0,
        category_id: str = "",
        guild: Guild | None = None,
        read_only: bool = False
    ):
        self.id = id
        self.bot = bot
        self.name = name
        self.kind = kind
        self.private = private
        self.slowmode = slowmode
        self.category_id = category_id
        self.guild = guild
        self.read_only = read_only
        
    async def send(self, content, embeds=[], components=[]):
        await API.send(
            self.bot.session, self.id, {
                "content": content,
                "embeds": embeds,
                "components": components,
                "reply_to": None
            }
        )

class Member(User):
    def __init__(
        self,
        guild: guild | None = None,
        roles: list[Role] = [],
        joined_at: str = "",
        nickname: str = "",
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.guild = guild
        self.roles = roles
        self.joined_at = joined_at
        self.nickname = nickname or self.display_name

    async def add_role(self, role):
        role_id = role if isinstance(role, str) else role.id
        return API.put(self.bot.session, f"/servers/{self.guild.id}/members/{self.id}/roles/{role_id}")
    
    async def remove_role(self, role):
        role_id = role if isinstance(role, str) else role.id
        return API.delete(self.bot.session, f"/servers/{self.guild.id}/members/{self.id}/roles/{role_id}")
    
    async def kick(self):
        return API.post(self.bot.session, f"/servers/{self.guild.id}/", {"user_id": self.id})
    
    async def ban(self):
        return API.post(self.bot.session, f"/servers/{self.guild.id}/bans", {"user_id": self.id})
    
    async def unban(self):
        return API.delete(self.bot.session, f"/servers/{self.guild.id}/bans/{self.id}")
    
    async def timeout(self, minutes, reason=""):
        return API.post(self.bot.session, f"/servers/{self.guild.id}/timeouts", {"user_id": self._id, "minutes": minutes, "reason": reason})
    

class Message:
    def __init__(self,
        bot,
        id=0,
        channel: Channel | None = None,
        author: User | None = None,
        created_at: str = "",
        content: str = ""
    ):
        self.id = id
        self.channel = channel
        self.bot = bot
        self.created_at = created_at
        self.content = content

        self.author = author
    async def reply(self, content, embeds=[], components=[]):
        await API.send(
            self.bot.session, self.channel.id, {
                "content": content,
                "embeds": embeds,
                "components": components,
                "reply_to": self.id
            }
        )
    async def delete(self):
        await API.delete(self.bot.session, f"/channels/{self.channel.id}/messages/{self.id}")
    async def edit(self, content, embeds=[], components=[]):
        await API.patch(self.bot.session, f"/channels/{self.channels.id}/messages/{self.id}", {
            "content": content,
            "embeds": embeds,
            "components": components
        })
    async def send(self, content, embeds=[], components=[]):
        await self.channel.send(*args, **kwargs)
    async def react(self, emoji):
        return await API.put(
            self.bot.session,
            f"/channels/{self.channel.id}/messages/{self.id}/reactions/{urllib.parse.quote(emoji)}"
        )


class Context:
    def __init__(self,
        bot,
        is_bot: bool = False,
        message: Message | None = None,
        channel: Channel | None = None,
        author: Member | None = None
    ):
        self.bot = bot
        self.is_bot = is_bot
        self.message = message
        self.channel = channel
        self.author = author

        self.reply = self.message.reply
        self.delete = self.message.delete
        self.edit = self.message.edit
        self.react = self.message.react
        self.send = self.message.send
