"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import discord
from discord.utils import MISSING

from ...core import flags
from ...core.context import Context
from ...core.embed import ZEmbed
from ...core.guild import GuildWrapper
from ...utils.format import separateStringFlags
from . import _views


async def handleGreetingConfig(
    ctx: Context,
    type: str,
    *,
    arguments=MISSING,
    message: str = None,
    raw: bool = False,
    disable: bool = False,
    channel: discord.TextChannel = None,
):
    """Handle welcome and farewell configuration."""
    guild: GuildWrapper | None = ctx.guild
    if not guild:
        raise RuntimeError

    changeMsg = False

    if arguments is None:
        # TODO - Revisit once more input introduced to modals
        # TODO - Timeout + disable the button
        defMsg = await ctx.bot.getGuildConfig(guild.id, f"{type}Msg")

        await ctx.try_reply(
            "This feature currently not yet available on Mobile!\n"
            "If you're on Mobile, please do `{}{} "
            "[message] [options]` instead".format(ctx.clean_prefix, type),
            view=_views.OpenGreetingModal(ctx, type, defMsg, owner=ctx.author),
        )
        return
    elif arguments is not MISSING:
        message, args = separateStringFlags(arguments)

        parsed = await flags.GreetingFlags.convert(ctx, args)

        # Parsed value from flags
        disable = parsed.disable
        raw = parsed.raw
        channel = parsed.channel
        message = " ".join([message.strip()] + parsed.messages).strip()

    if not raw and not disable and message:
        changeMsg = True

    e = ZEmbed.success(
        title=("Welcome" if type == "welcome" else "Farewell") + " config has been updated",
    )

    if disable is True:
        await ctx.bot.setGuildConfig(guild.id, f"{type}Ch", None, "GuildChannels")
        e.add_field(name="Status", value="`Disabled`")
        return await ctx.try_reply(embed=e)

    if raw is True:
        message = await ctx.bot.getGuildConfig(guild.id, f"{type}Msg")
        return await ctx.try_reply(discord.utils.escape_markdown(str(message)))

    if changeMsg:
        await ctx.bot.setGuildConfig(guild.id, f"{type}Msg", message)
        e.add_field(name="Message", value=message, inline=False)

    if channel is not None:
        await ctx.bot.setGuildConfig(guild.id, f"{type}Ch", channel.id, "GuildChannels")
        e.add_field(name="Channel", value=channel.mention)

    return await ctx.try_reply(embed=e)
