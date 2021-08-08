import datetime as dt
import re
from typing import Tuple, Union

import discord
from discord.ext import commands

from core.embed import ZEmbed
from exts.meta._objects import CustomCommand


def formatCmdParams(command):
    if isinstance(command, CustomCommand):
        return ""

    usage = command.usage
    if usage:
        return usage

    params = command.clean_params
    if not params:
        return ""

    result = []
    for name, param in params.items():
        if param.default is not param.empty or param.kind == param.VAR_POSITIONAL:
            result.append(f"[{name}]")
        else:
            result.append(f"({name})")

    return " ".join(result)


def formatCmd(prefix, command, params=True):
    try:
        parent = command.parent
    except AttributeError:
        parent = None

    entries = []
    while parent is not None:
        if (not parent.signature or parent.invoke_without_command) and not params:
            entries.append(parent.name)
        else:
            entries.append((parent.name + " " + formatCmdParams(parent)).strip())
        parent = parent.parent
    names = " ".join(reversed([command.name] + entries))

    return discord.utils.escape_markdown(
        f"{prefix}{names}" + (f" {formatCmdParams(command)}" if params else "")
    )


def formatMissingArgError(ctx, error):
    command = ctx.command
    e = ZEmbed.error(
        title="ERROR: Missing required arguments!",
        description="Usage: `{}`".format(formatCmd("", command)),
    )
    e.set_footer(
        text="`{}help {}` for more information.".format(
            ctx.clean_prefix, formatCmd("", command, params=False)
        )
    )
    return e


def formatDiscordDT(dt_: Union[dt.datetime, float], style: str = None) -> str:
    # Format datetime using new timestamp formatting
    if isinstance(dt_, dt.datetime):
        ts = int(dt_.timestamp())
    else:
        # Incase dt is already unix timestamp
        ts = int(dt_)
    return f"<t:{ts}:{style}>" if style else f"<t:{ts}>"


def formatDateTime(datetime):
    return datetime.strftime("%A, %d %b %Y • %H:%M:%S %Z")


def formatName(name: str):
    return name.strip().lower().replace(" ", "-")


class CMDName(commands.clean_content):
    def __init__(self, *, lower=True):
        self.lower = lower
        super().__init__()

    async def convert(self, ctx, argument: str):
        converted = await super().convert(ctx, argument)
        lower = formatName(converted)
        if not lower:
            raise commands.BadArgument("Missing command name.")
        return lower


def cleanifyPrefix(bot, prefix):
    """Cleanify prefix (similar to context.clean_prefix)"""
    pattern = re.compile(r"<@!?{}>".format(bot.user.id))
    return pattern.sub("@{}".format(bot.user.display_name.replace("\\", r"\\")), prefix)


def renderBar(
    value: int,
    *,
    gap: int = 0,
    length: int = 32,
    point: str = "",
    fill: str = "-",
    empty: str = "-",
) -> str:
    # make the bar not wider than 32 even with gaps > 0
    length = int(length / int(gap + 1))

    # handles fill and empty's length
    fillLength = int(length * value / 100)
    emptyLength = length - fillLength

    # handles gaps
    gapFill = " " * gap if gap else ""

    return gapFill.join(
        [fill] * (fillLength - len(point)) + [point] + [empty] * emptyLength
    )


FLAG_REGEX = re.compile(r"(\S+):")


def separateStringFlags(string: str) -> Tuple[str, str]:
    """Separate string and flags

    'String flags: String String' -> ('String', 'flags: String String'])
    """
    command = []
    inFlags = False
    flags = []
    for i in string.split(" "):
        if not inFlags and FLAG_REGEX.match(i):
            inFlags = True

        if not inFlags:
            command.append(i)
        else:
            flags.append(i)
    return (" ".join(command), " ".join(flags))
