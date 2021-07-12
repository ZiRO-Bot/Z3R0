import datetime as dt
import discord
import re


from core.objects import CustomCommand
from discord.ext import commands
from exts.utils.other import utcnow
from typing import Union


class ZEmbed(discord.Embed):
    def __init__(self, color=0x3DB4FF, fields=(), field_inline=False, **kwargs):
        super().__init__(color=color, **kwargs)
        for n, v in fields:
            self.add_field(name=n, value=v, inline=field_inline)

    @classmethod
    def default(cls, ctx, timestamp=None, **kwargs):
        instance = cls(timestamp=timestamp or utcnow(), **kwargs)
        instance.set_footer(
            text="Requested by {}".format(ctx.author), icon_url=ctx.author.avatar_url
        )
        return instance

    @classmethod
    def error(
        cls,
        emoji="<:error:783265883228340245>",
        title="Error",
        color=discord.Color.red(),
        **kwargs,
    ):
        return cls(title="{} {}".format(emoji, title), color=color, **kwargs)

    @classmethod
    def success(
        cls,
        emoji="<:ok:864033138832703498>",
        title="Success",
        color=discord.Color.green(),
        **kwargs,
    ):
        return cls(title="{} {}".format(emoji, title), color=color, **kwargs)

    @classmethod
    def loading(
        cls,
        emoji="<a:loading:776255339716673566>",
        title="Loading...",
        **kwargs,
    ):
        return cls(title="{} {}".format(emoji, title), **kwargs)


async def logAction(bot, actionType: str, *args, **kwargs):
    """For case log (ban, kick, possibly warn) and purgatory."""
    e = ZEmbed(timestamp=utcnow())

    if actionType.startswith("msg"):
        if actionType == "msgEdit":
            before, after = args

            guildId = before.guild.id

            e.title = "Edited Message"

            e.set_author(name=before.author, icon_url=before.author.avatar_url)

            e.add_field(
                name="Before",
                value=before.content[:1020] + " ..."
                if len(before.content) > 1024
                else before.content,
            )
            e.add_field(
                name="After",
                value=after.content[:1020] + " ..."
                if len(after.content) > 1024
                else after.content,
            )

            if before.embeds:
                data = before.embeds[0]
                if data.type == "image" and not self.is_url_spoiler(
                    before.content, data.url
                ):
                    e.set_image(url=data.url)

            if before.attachments:
                _file = before.attachments[0]
                spoiler = _file.is_spoiler()
                if not spoiler and _file.url.lower().endswith(
                    ("png", "jpeg", "jpg", "gif", "webp")
                ):
                    e.set_image(url=_file.url)
                elif spoiler:
                    e.add_field(
                        name="📎 Attachment",
                        value=f"||[{_file.filename}]({_file.url})||",
                        inline=False,
                    )
                else:
                    e.add_field(
                        name="📎 Attachment",
                        value=f"[{_file.filename}]({_file.url})",
                        inline=False,
                    )

        if actionType == "msgDel":
            (message,) = args

            guildId = message.guild.id

            e.title = "Deleted Message"

            e.set_author(name=message.author, icon_url=message.author.avatar_url)

            e.description = (
                message.content[:1020] + " ..."
                if len(message.content) > 1024
                else message.content
            )

        logCh = bot.get_channel(await bot.getGuildConfig(guildId, "purgatoryCh"))
        if not logCh:
            return

        return await logCh.send(embed=e)


def formatCmdParams(command):
    if isinstance(command, CustomCommand):
        return ""

    if command.name == "help":
        return "[category|command]"

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
        if not parent.signature or parent.invoke_without_command:
            entries.append(parent.name)
        else:
            entries.append(parent.name + " " + formatCmdParams(parent))
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


def formatDiscordDT(dt: Union[dt.datetime, float], style: str = None) -> str:
    # Format datetime using new timestamp formatting
    try:
        ts = int(dt.timestamp())
    except AttributeError:
        # Incase dt is a unix timestamp
        ts = int(dt)
    return f"<t:{ts}:{style}>" if style else f"<t:{ts}>"


def formatDateTime(datetime):
    return datetime.strftime("%A, %d %b %Y • %H:%M:%S %Z")


def formatName(name: str):
    return name.strip().lower().replace(" ", "-")


class CMDName(commands.Converter):
    async def convert(self, ctx, argument: str):
        return formatName(argument)


def cleanifyPrefix(bot, prefix):
    """Cleanify prefix (similar to context.clean_prefix)"""
    pattern = re.compile(r"<@!?{}>".format(bot.user.id))
    return pattern.sub("@{}".format(bot.user.display_name.replace("\\", r"\\")), prefix)
