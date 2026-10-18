from .api import *
from typing import Callable

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
        is_bot: bool = True
    ):
        self.name = name
        self.id = id
        self.profile = profile
        self.display_name = display_name
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

class Channel:
    def __init__(self,
        bot,
        id=0,
        name: str = ""
    ):
        self.id = id
        self.bot = bot
        self.name = name

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

class Context:
    def __init__(self,
        bot,
        is_bot: bool = False,
        message: Message | None = None,
        channel: Channel | None = None
    ):
        self.bot = bot
        self.is_bot = is_bot
        self.message = message
        self.channel = channel
        
    async def reply(
        self,
        content: str = "Hi"
    ):
        await api.send(
            self.bot.session, self.channel.id, data={
                "content": content,
                "reply_to": self.message.id
            }
        )

    async def send(
        self,
        content: str = "Hi"
    ):
        await api.send(
            self.bot.session, self.channel.id, data={
                "content": content,
                "reply_to": None
            }
        )
