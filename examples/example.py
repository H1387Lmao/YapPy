from yappy import App, Embed

import os
from dotenv import load_dotenv

load_dotenv()

bot = App(verbose=True)

@bot.event(
    "message"
)
async def on_message(ctx):
    if ctx.is_bot:
        return

    await bot.process_command(ctx)

@bot.command(
    name="ping",
    description="replies with 'Pong!'"
)
async def ping(ctx):
    await ctx.reply("Pong!")

@bot.command(
    name="react",
    description="React your message with a certain emoji!"
)
async def react(ctx, emoji: str):
    await ctx.message.react(emoji)

@bot.command(
    name="add",
    description="Adds two numbers"
)
async def add(ctx, a: int, b: int = 0):
    await ctx.reply(f"{a} + {b} = {a + b}")

@bot.command(
    name="send_embed",
)
async def send_embed(ctx):
    embed = Embed(
        "Embed",
        description="My Embed",
        color="#FF1818"
    )
    embed.add_field("Test1", "1")
    embed.add_field("Test2", "2")
    embed.add_field("Test3", "3")

    embed.set_footer("My Footer", None)

    await ctx.send(
        embeds=[
            embed
        ]
    )

@bot.event(
    "ready"
)
async def on_ready():
    print("Logged as", bot.user.name)



bot.run(os.getenv("TOKEN"))
