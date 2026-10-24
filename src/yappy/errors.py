class YappyError(Exception):
    """Base class for all YapPy errors."""


class ImproperToken(YappyError):
    pass


class InvalidSignature(YappyError):
    pass


class CommandError(YappyError):
    """Base class for errors raised while handling a command.

    ``str(error)`` is a message that is safe to show to the person who ran
    the command. ``command`` is the :class:`~yappy.core.Command` involved
    (``None`` if the command couldn't be found).
    """

    def __init__(self, message: str = "", *, command=None):
        super().__init__(message)
        self.command = command


class UnknownCommand(CommandError):
    pass


class MissingArgument(CommandError):
    """A required argument was not given."""

    def __init__(self, param: str, *, command=None):
        super().__init__(
            f"Missing required argument '{param}'.", command=command
        )
        self.param = param


class TooManyArguments(CommandError):
    """More arguments were given than the command accepts."""

    def __init__(self, expected: int, given: int, *, command=None):
        noun = "argument" if expected == 1 else "arguments"
        super().__init__(
            f"Too many arguments: expected at most {expected} {noun}, "
            f"got {given}.",
            command=command,
        )
        self.expected = expected
        self.given = given


class BadArgument(CommandError):
    """An argument couldn't be converted to what the command expects."""

    def __init__(self, param: str, value, expected: str, *, command=None):
        shown = str(value)
        if len(shown) > 40:
            shown = shown[:37] + "..."
        super().__init__(
            f"Invalid value {shown!r} for '{param}': expected {expected}.",
            command=command,
        )
        self.param = param
        self.value = value
        self.expected = expected


class CommandInvokeError(CommandError):
    """The command itself raised an exception. The original is ``original``."""

    def __init__(self, original: BaseException, *, command=None):
        name = command.name if command is not None else "?"
        super().__init__(
            f"Command '{name}' raised {type(original).__name__}: {original}",
            command=command,
        )
        self.original = original
