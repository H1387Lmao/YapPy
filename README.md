# YapPy

**A Python API binding for Yapper.**

YapPy brings a Python-friendly interface to [Yapper](https://yapper.website), a chat platform similar to Discord. It provides familiar models, event handlers, and command decorators so you can build Yapper bots with straightforward asynchronous Python.

> **Project status:** Early development. The current implementation includes `Context`, `Message`, `Channel`, and `User` models, along with bot event and command handling. The API may change as development continues.

## Features

- **Python-first API** — build bot logic using async functions and decorators.
- **Event handlers** — respond to Yapper events such as incoming messages.
- **Commands** — register named commands with descriptions.
- **Context-based interactions** — reply to messages through a context object.
- **Core models** — work with `Context`, `Message`, `Channel`, and `User` objects.
- **Optional logging** — enable verbose output when creating the application.

## Installation


```bash
pip install python-yappy
```

## Quick start

This example uses the dotenv module from `pip install load_dotenv`
Create a file named `main.py`:

```python
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
```

Create a `.env` file beside `bot.py`:

```dotenv
TOKEN=your_yapper_bot_token
```

Then run the bot:

```bash
python bot.py
```

This example registers a `message` event that replies with `Hi!` to messages not sent by bots, and a `ping` command that replies with `Pong!`.

**Keep your token private.** Do not commit your `.env` file or publish your bot token.

## Core concepts

### `App`

`App` is the main entry point for creating and running a YapPy bot.

```python
from yappy import App

bot = App(verbose=True)
bot.run("YOUR_TOKEN")
```

Set `verbose=True` to enable verbose output while developing. Keep credentials in environment variables rather than hard-coding them in source files.

### Events

Register an event handler with `@bot.event(...)`. Event handlers are asynchronous functions.

```python
@bot.event("message")
async def on_message(ctx):
    if ctx.is_bot:
        return

    await ctx.process.command(ctx)
```

The event name and handler arguments should match the event interface supported by the installed YapPy version.

### Commands

Register a command using `@bot.command(...)`:

```python
@bot.command(
    name="ping",
    description="replies with 'Pong!'",
)
async def ping(ctx):
    await ctx.reply("Pong!")
```

The `name` identifies the command, and `description` describes its purpose. Command registration and invocation behavior depend on the current implementation.

### Context and models

YapPy currently provides these core models:

| Model | Purpose |
| --- | --- |
| `Context` | Context for handling an interaction or message event. |
| `Message` | Represents a message. |
| `Channel` | Represents a channel. |
| `User` | Represents a user. |
| `Guild` | Represents a guild / server |
| `Role` | Represents a role |

The example uses the context object (`ctx`) to check `ctx.is_bot` and send a reply with `ctx.reply(...)`. Consult the source code for the currently available attributes and methods of each model.

## Project status

YapPy is under active development. Current implemented areas include:

- `Context`, `Message`, `Channel`, and `User` models
- Bot event registration and handling
- Command registration
- Message replies through the context API

Other features may be planned, incomplete, or unsupported. Check the source code and release notes for the actual capabilities of the version you are using.

## Contributing

Contributions, bug reports, and suggestions are welcome. Before opening a pull request, describe the change clearly and include a minimal reproduction or test where appropriate.

## License

This project is licensed under the MIT License.
