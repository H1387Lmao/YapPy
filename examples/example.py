from yappy import App
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
    # try "!add", "!add x" or "!add 1 2 3" to see the argument errors
    await ctx.reply(f"{a} + {b} = {a + b}")

@bot.event(
    "ready"
)
async def on_ready():
    print("Logged as", bot.user.name)



bot.run(os.getenv("TOKEN"))
