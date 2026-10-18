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
    
    await ctx.reply("Hi!")

@bot.command(
    name="ping",
    description="replies with 'Pong!'"
)
async def ping(ctx):
    await ctx.reply("Pong!")

bot.run(os.getenv("TOKEN"))
