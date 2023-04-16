"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import discord

from ...core.context import Context
from ...core.embed import ZEmbed
from ...core.guild import GuildWrapper
from . import _views
from ._flags import GreetingFlags


async def handleGreetingConfig(
    ctx: Context,
    type: str,
    *,
    arguments: GreetingFlags | None = None,
):
    """Handle welcome and farewell configuration."""
    guild: GuildWrapper | None = ctx.guild
    if not guild:
        raise RuntimeError

    # App commands doesn't turn arguments into None for some reason
    try:
        arguments.string  # type: ignore
    except AttributeError:
        arguments = None

    changeMsg = False

    if not arguments:
        # TODO - Revisit once more input introduced to modals
        defMsg = await guild.getConfig(f"{type}Msg") or "No message is set"
        currentChannel = await guild.getConfig(f"{type}Ch")

        e = ZEmbed.default(ctx)
        e.title = f"{guild.name}'s {type.title()} Configuration"
        e.add_field(name="Channel", value=f"<#{currentChannel}>" if currentChannel else "`Disabled`", inline=False)
        e.add_field(name="Message", value=defMsg, inline=False)
        e.add_field(name="Raw Message", value=discord.utils.escape_markdown(defMsg), inline=False)

        v = _views.OpenGreetingModal(ctx, type, owner=ctx.author)
        v.message = await ctx.tryReply(
            view=v,
            embed=e,
        )
        return
    else:
        parsed = arguments

        disable = parsed.disable
        raw = parsed.raw
        channel = parsed.channel
        message = (str(parsed.string).strip() + parsed.message.strip()).strip()

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
        message = await guild.getConfig(f"{type}Msg")
        return await ctx.try_reply(discord.utils.escape_markdown(str(message)))

    if changeMsg:
        await ctx.bot.setGuildConfig(guild.id, f"{type}Msg", message)
        e.add_field(name="Message", value=message, inline=False)

    if channel is not None:
        await ctx.bot.setGuildConfig(guild.id, f"{type}Ch", channel.id, "GuildChannels")
        e.add_field(name="Channel", value=channel.mention)

    return await ctx.try_reply(embed=e)
