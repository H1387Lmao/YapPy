from .api import *
from typing import Callable
import urllib.parse

class Profile:
    def __init__(self,
        avatar: str = "",
        banner: str = ""
    ):
        self.avatar = avatar
        self.banner = banner

class User:
    def __init__(self,
        name: str ="",
        display_name: str = "",
        id=0,
        profile: Profile | None = None,
        created_at: str = "",
        bio: str = "",
        pronouns: str = "",
        is_bot: bool = True
    ):
        self.name = name
        self.id = id
        self.profile = profile
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

class Guild:
    def __init__(self,
        bot,
        id=0,
        name=None,
    ):
        self.id = id
        self.name = name

class Channel:
    def __init__(self,
        bot,
        id=0,
        name: str = ""
    ):
        self.id = id
        self.bot = bot
        self.name = name
    async def send(self, content, embeds=[], components=[]):
        await api.send(
            self.bot.session, self.id, data={
                "content": content,
                "embeds": embeds,
                "components": components,
                "reply_to": None
            }
        )

class Member(User):
    def __init__(
        self, guild = None,
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.guild = guild

    async def add_role(self, role_id):
        return api.put(f"/servers/{self.guild.id}/members/{self.id}/roles/{role_id}")
    
    async def remove_role(self, role_id):
        return api.delete(f"/servers/{self.guild.id}/members/{self.id}/roles/{role_id}")
    
    async def kick(self):
        return api.post(f"/servers/{self.guild.id}/", {"user_id": self.id})
    
    async def ban(self):
        return api.post(f"/servers/{self.guild.id}/bans", {"user_id": self.id})
    
    async def unban(self):
        return api.delete(f"/servers/{self.guild.id}/bans/{self.id}")
    
    async def timeout(self, minutes, reason=""):
        return api.post(f"/servers/{self.guild.id}/timeouts", {"user_id": self._id, "minutes": minutes, "reason": reason})
    

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
        await api.send(
            self.bot.session, self.channel.id, data={
                "content": content,
                "embeds": embeds,
                "components": components
                "reply_to": self.id
            }
        )
    async def delete(self):
        api.delete(f"/channels/{self.channel.id}/messages/{self.id}")
    async def edit(self, content, embeds=[], components=[]):
        api.patch(f"/channels/{self.channels.id}/messages/{self.id}", {
            "content": content,
            "embeds": embeds,
            "components": components
        })
    async def send(self, content, embeds=[], components=[]):
        await self.channel.send(*args, **kwargs)
    async def react(self, emoji):
        return await api.put(
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
