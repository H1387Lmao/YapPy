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

@bot.event(
    "ready"
)
async def on_ready():
    print("Logged as", bot.user.name)



bot.run(os.getenv("TOKEN"))
