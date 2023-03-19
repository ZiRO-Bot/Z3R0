"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import discord
import humanize
from discord.app_commands import locale_str as _
from discord.ext import commands

from ...core import checks
from ...core.context import Context
from ...core.embed import ZEmbed
from ...core.menus import ZMenuPagesView
from ...utils.format import cleanifyPrefix
from ...utils.other import utcnow
from ._help import CustomHelp
from ._pages import PrefixesPageSource
from .subcogs import MetaCustomCommands


if TYPE_CHECKING:
    from ...core.bot import ziBot


class Meta(MetaCustomCommands):
    """Bot-related commands."""

    icon = "🤖"
    cc = True

    def __init__(self, bot: ziBot):
        super().__init__(bot)

        # Custom help command stuff
        # help command's attribute
        attributes = dict(
            name="help",
            aliases=("?",),
            usage="[category / command]",
            description="Get information of a command or category",
            help=(
                "\n\nYou can use `filters` flag to set priority.\n"
                "For example:\n`>help info filters: custom built-in`, "
                "will show custom commands first then built-in commands "
                "in **info** category\n`>help info filters: custom`, "
                "will **only** show custom commands in **info** category"
            ),
            extras=dict(
                example=(
                    "help info",
                    "? weather",
                    "help info filters: custom",
                ),
                flags={
                    ("filters", "filter", "filt"): (
                        "Filter command type (`custom` or `built-in`), also "
                        "work as priority system. (Only works on category)"
                    ),
                },
            ),
        )
        # Backup the old/original command incase this cog unloaded
        self._original_help_command = bot.help_command
        # Replace default help menu with custom one
        self.bot.help_command = CustomHelp(command_attrs=attributes)
        self.bot.help_command.cog = self

    @commands.hybrid_command(name=_("source"), description=_("source-desc"))
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def source(self, ctx):
        await ctx.try_reply("My source code: {}".format(self.bot.links["Source Code"]))

    @commands.hybrid_command(name=_("about"), aliases=("botinfo", "bi"), description=_("about-desc"))
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def about(self, ctx):
        # Z3R0 Banner
        f = discord.File("./assets/img/banner.png", filename="banner.png")

        e = ZEmbed.default(
            ctx,
            description=self.bot.description + "\n\nThis bot is licensed under **{}**.".format(ctx.bot.license),
        )
        e.set_author(name=ctx.bot.user.name, icon_url=ctx.bot.user.display_avatar.url)
        e.set_image(url="attachment://banner.png")
        e.add_field(name="Author", value=ctx.bot.author)
        e.add_field(
            name="Library",
            value="[`discord.py`](https://github.com/Rapptz/discord.py) - `v{}`".format(discord.__version__),
        )
        e.add_field(name="Version", value=ctx.bot.version)
        view = discord.ui.View()
        for k, v in ctx.bot.links.items():
            if k and v:
                view.add_item(discord.ui.Button(label=k, url=v))
        await ctx.try_reply(file=f, embed=e, view=view)

    @commands.hybrid_command(name=_("stats"), description=_("stats-desc"))
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def stats(self, ctx: Context):
        botUser: discord.ClientUser | None = ctx.bot.user
        if not botUser:
            return
        uptime = utcnow() - self.bot.uptime
        e = ZEmbed.default(ctx)
        e.set_author(name=await ctx.translate(_("stats-title", bot=botUser.name)), icon_url=botUser.display_avatar.url)
        e.add_field(name=await ctx.translate(_("stats-uptime-title")), value=humanize.precisedelta(uptime), inline=False)
        e.add_field(
            name=await ctx.translate(_("stats-command-title")),
            value=await ctx.translate(
                _(
                    "stats-command",
                    commandCount=sum(self.bot.commandUsage.values()),
                    customCommand=self.bot.customCommandUsage,
                )
            ),
            inline=False,
        )
        await ctx.try_reply(embed=e)

    @commands.group(
        aliases=("pref",),
        description="Manages bot's custom prefix",
        extras=dict(
            example=(
                "prefix add ?",
                "pref remove !",
            )
        ),
        invoke_without_command=True,
        with_app_command=False,
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def prefix(self, ctx):
        await ctx.try_invoke(self.prefList)

    @prefix.command(
        name="list",
        aliases=("ls",),
        description="Get all prefixes",
        exemple=("prefix ls", "pref list"),
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def prefList(self, ctx):
        prefixes = await ctx.guild.getPrefixes()
        menu = ZMenuPagesView(ctx, source=PrefixesPageSource(ctx, ["placeholder"] * 2 + prefixes))
        await menu.start()

    @prefix.command(
        name="add",
        aliases=("+",),
        description="Add a custom prefix",
        help='\n\nTips: Wrap prefix with quotation mark (`" "`) to add spaces to your prefix.',
        extras=dict(
            example=("prefix add ?", 'prefix + "please do "', "pref + z!"),
            perms={
                "bot": None,
                "user": "Moderator Role or Manage Guild",
            },
        ),
    )
    @checks.is_mod()
    async def prefAdd(self, ctx: Context, *prefix: str):
        _prefix = " ".join(prefix).lstrip()
        if not _prefix:
            return await ctx.error(_("prefix-empty"))

        try:
            await ctx.requireGuild().addPrefix(_prefix)
            await ctx.success(title=_("prefix-added", prefix=cleanifyPrefix(self.bot, _prefix)))
        except Exception as exc:
            await ctx.error(str(exc))

    @prefix.command(
        name="remove",
        aliases=("-", "rm"),
        description="Remove a custom prefix",
        help='\n\nTips: Wrap prefix with quotation mark (`" "`) if the prefix has spaces.',
        extras=dict(
            example=("prefix rm ?", 'prefix - "please do "', "pref remove z!"),
            perms={
                "bot": None,
                "user": "Moderator Role or Manage Guild",
            },
        ),
    )
    @checks.is_mod()
    async def prefRm(self, ctx: Context, *prefix: str):
        _prefix = " ".join(prefix).lstrip()
        if not _prefix:
            return await ctx.error(_("prefix-empty"))

        try:
            await ctx.requireGuild().rmPrefix(_prefix.lstrip())
            await ctx.success(title=_("prefix-removed", prefix=cleanifyPrefix(self.bot, _prefix)))
        except Exception as exc:
            await ctx.error(str(exc))

    @commands.hybrid_command(name=_("ping"), aliases=("p",), description=_("ping-desc"))
    async def ping(self, ctx):
        start = time.perf_counter()
        msgPing = 0

        e = ZEmbed.default(ctx, title="Pong!")

        botLatency = f"{round(self.bot.latency*1000)}ms" if not ctx.bot.config.test else "∞"

        e.add_field(
            name="<a:discordLoading:857138980192911381> | Websocket",
            value=botLatency,
        )

        msg = await ctx.try_reply(embed=e)

        if not ctx.bot.config.test:
            end = time.perf_counter()
            msgPing = (end - start) * 1000

        e.add_field(
            name="<a:typing:785053882664878100> | Typing",
            value=f"{round(msgPing)}ms",
            inline=False,
        )
        await msg.edit(embed=e)

    @commands.hybrid_command(name=_("invite"), description=_("invite-desc"))
    async def invite(self, ctx):
        botUser: discord.ClientUser = self.bot.user  # type: ignore
        clientId = botUser.id
        e = ZEmbed(
            title=f"Want to invite {botUser.name}?",
            description="[Invite with administrator permission]("
            + discord.utils.oauth_url(
                clientId,
                permissions=discord.Permissions(8),
            )
            + ")\n[Invite with necessary premissions (**recommended**)]("
            + discord.utils.oauth_url(
                clientId,
                permissions=discord.Permissions(4260883702),
            )
            + ")",
        )
        await ctx.try_reply(embed=e)
