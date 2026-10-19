from .api import *
from typing import Callable
import urllib.parse
from .utils import get_asset_url

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
            self._cache[m.id] = m
            m. guild = self
    async def find_member(self, mid):
        member = self.get_member(mid)
        if member is None:
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
                id=id,
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
        return self._cache.get(mid, None)

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
