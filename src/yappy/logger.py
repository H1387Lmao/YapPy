"""Logging for YapPy.

YapPy logs through the standard :mod:`logging` module under the ``"yappy"``
logger (``yappy.app``, ``yappy.api``, ...). :func:`setup_logging` attaches a
`Rich <https://rich.readthedocs.io>`_ handler so output is coloured and
exceptions are printed as readable tracebacks.

``App.run()`` calls it for you. To take over logging yourself, create the app
with ``App(configure_logging=False)`` and add your own handlers to
``logging.getLogger("yappy")``.
"""

import asyncio
import logging

import aiohttp
from rich.console import Console
from rich.logging import RichHandler

LOGGER_NAME = "yappy"
_MARKER = "_yappy_rich_handler"


def setup_logging(
    level: int | str | None = None,
    *,
    verbose: bool = False,
    console: Console | None = None,
    show_locals: bool = False,
) -> logging.Logger:
    """Send YapPy's logs to the terminal using Rich.

    :param level: a ``logging`` level. Defaults to ``DEBUG`` if ``verbose``
        else ``INFO``.
    :param verbose: also show debug output (events, HTTP calls, command
        invocations) and prefix each line with the module it came from.
    :param console: a ``rich.console.Console`` to print to.
    :param show_locals: include local variables in exception tracebacks.

    Safe to call more than once; it replaces the handler it added before.
    """
    if level is None:
        level = logging.DEBUG if verbose else logging.INFO

    logger = logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        if getattr(handler, _MARKER, False):
            logger.removeHandler(handler)

    handler = RichHandler(
        console=console,
        show_path=False,
        markup=False,  # chat content in log messages must not be parsed as markup
        rich_tracebacks=True,
        tracebacks_show_locals=show_locals,
        tracebacks_suppress=[aiohttp, asyncio],
        log_time_format="[%H:%M:%S]",
        omit_repeated_times=False,
    )
    handler.setFormatter(
        logging.Formatter("%(name)s  %(message)s" if verbose else "%(message)s")
    )
    setattr(handler, _MARKER, True)

    logger.addHandler(handler)
    logger.setLevel(level)
    # we own the output; don't print every line a second time via the root logger
    logger.propagate = False
    return logger
