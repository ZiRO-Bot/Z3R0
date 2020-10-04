import asyncio
import bot
import datetime
import discord
import logging
import time

from aiogoogletrans import Translator
from discord.ext import commands
from utilities.formatting import realtime

translator = Translator()


class Utils(commands.Cog, name="utils"):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("discord")

    def get_disabled(self, ctx):
        self.bot.c.execute(
            "SELECT disabled_cmds FROM settings WHERE (id=?)", (str(ctx.guild.id),)
        )
        disabled = self.bot.c.fetchone()
        try:
            disabled_cmds = disabled[0].split(",")
        except AttributeError:
            disabled_cmds = []

        return disabled_cmds

    def get_mods_only(self, ctx):
        self.bot.c.execute(
            "SELECT mods_only FROM settings WHERE (id=?)", (str(ctx.guild.id),)
        )
        mods = self.bot.c.fetchone()
        try:
            mods_only = mods[0].split(",")
        except AttributeError:
            mods_only = []

        return mods_only

    async def bot_check(self, ctx):
        """
        Global checks, owner bypass all checks
        """
        if not ctx.guild:
            return True

        is_owner = await ctx.bot.is_owner(ctx.author)
        if is_owner:
            return True

        disabled_cmds = self.get_disabled(ctx)
        if disabled_cmds:
            if ctx.command.root_parent in disabled_cmds:
                return False
            if ctx.command.qualified_name in disabled_cmds:
                return False

        mods_only = self.get_mods_only(ctx)
        if mods_only and not ctx.author.guild_permissions.manage_channels:
            if ctx.command.root_parent in mods_only:
                return False
            if ctx.command.qualified_name in mods_only:
                return False

        return True

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        msg_id = payload.message_id
        if msg_id == 746645838586970152:
            guild_id = payload.guild_id
            guild = discord.utils.find(lambda g: g.id == guild_id, self.bot.guilds)
            role = None
            if payload.emoji.name == "🖥️":
                role = discord.utils.get(guild.roles, name="Computer Nerd")
            elif payload.emoji.name == "🇦":
                role = discord.utils.get(guild.roles, name="Weeb")
            elif payload.emoji.name == "🇸":
                role = discord.utils.get(guild.roles, name="Speedrunner")

            if role:
                member = discord.utils.find(
                    lambda m: m.id == payload.user_id, guild.members
                )
                if member:
                    await member.add_roles(role)
                else:
                    print("Member not found")
            else:
                print("Role not found")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        msg_id = payload.message_id
        if msg_id == 746645838586970152:
            guild_id = payload.guild_id
            guild = discord.utils.find(lambda g: g.id == guild_id, self.bot.guilds)
            role = None
            if payload.emoji.name == "🖥️":
                role = discord.utils.get(guild.roles, name="Computer Nerd")
            elif payload.emoji.name == "🇦":
                role = discord.utils.get(guild.roles, name="Weeb")
            elif payload.emoji.name == "🇸":
                role = discord.utils.get(guild.roles, name="Speedrunner")

            if role:
                member = discord.utils.find(
                    lambda m: m.id == payload.user_id, guild.members
                )
                if member:
                    await member.remove_roles(role)
                else:
                    print("Member not found")
            else:
                print("Role not found")

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author == self.bot.user:
            return

        self.bot.c.execute(
            "SELECT purge_ch FROM servers WHERE id=?", (str(message.guild.id),)
        )
        purgatory_ch = self.bot.c.fetchall()[0][0]
        if not purgatory_ch:
            return
        purgatory_ch = self.bot.get_channel(purgatory_ch)

        msg = f"**Deleted Message** in {message.channel.mention}"

        embed = discord.Embed(
            description=message.content,
            timestamp=message.created_at,
            colour=discord.Colour.red(),
        )
        embed.set_author(
            name=f"{message.author.name}#{message.author.discriminator}",
            icon_url=message.author.avatar_url,
        )
        if message.attachments:
            _file = message.attachments[0]
            spoiler = _file.is_spoiler()
            if not spoiler and _file.url.lower().endswith(
                ("png", "jpeg", "jpg", "gif", "webp")
            ):
                embed.set_image(url=_file.url)
            elif spoiler:
                embed.add_field(
                    name="📎 Attachment",
                    value=f"||[{_file.filename}]({_file.url})||",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="📎 Attachment",
                    value=f"[{_file.filename}]({_file.url})",
                    inline=False,
                )
        embed.set_footer(text=message.id)
        await purgatory_ch.send(msg, embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.content == after.content:
            return
        message = before

        self.bot.c.execute(
            "SELECT purge_ch FROM servers WHERE id=?", (str(message.guild.id),)
        )
        purgatory_ch = self.bot.c.fetchall()[0][0]
        if not purgatory_ch:
            return
        purgatory_ch = self.bot.get_channel(purgatory_ch)

        msg = f"**Edited Message** in {message.channel.mention}"

        embed = discord.Embed(colour=discord.Colour.red(), timestamp=after.edited_at)
        embed.set_author(
            name=f"{message.author.name}#{message.author.discriminator}",
            icon_url=message.author.avatar_url,
        )
        embed.add_field(
            name="**Original Message**", value=message.content or "\u200b", inline=False
        )
        embed.add_field(name="**New Message**", value=after.content, inline=False)
        if message.attachments:
            _file = message.attachments[0]
            spoiler = _file.is_spoiler()
            if not spoiler and _file.url.lower().endswith(
                ("png", "jpeg", "jpg", "gif", "webp")
            ):
                embed.set_image(url=_file.url)
            elif spoiler:
                embed.add_field(
                    name="📎 Attachment",
                    value=f"||[{_file.filename}]({_file.url})||",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="📎 Attachment",
                    value=f"[{_file.filename}]({_file.url})",
                    inline=False,
                )
        embed.set_footer(text=after.id)
        await purgatory_ch.send(msg, embed=embed)

    @commands.command(aliases=["p"])
    async def ping(self, ctx):
        """Tell the ping of the bot to the discord servers."""
        start = time.perf_counter()
        e = discord.Embed(
            title="Ping",
            description="**API Latency** = Time it takes to recive data from the discord API\n**Response Time** = Time it took send this response to your message\n**Bot Latency** = Time needed to send/edit messages",
            timestamp=ctx.message.created_at,
            colour=discord.Colour(0xFFFFF0),
        )
        e.add_field(name="API Latency", value=f"{round(self.bot.latency*1000)}ms")
        e.set_footer(
            text=f"Requested by {ctx.message.author.name}#{ctx.message.author.discriminator}"
        )
        msg = await ctx.send(embed=e)
        end = time.perf_counter()
        msg_ping = (end - start) * 1000
        e.add_field(
            name="Response Time",
            value=f"{round((msg.created_at - ctx.message.created_at).total_seconds()/1000, 4)}ms",
        )
        e.add_field(name="Bot Latency", value=f"{round(msg_ping)}ms")
        await msg.edit(embed=e)

    @commands.command(
        aliases=["trans"], brief="Translate a text.", usage="(language) (text)"
    )
    async def translate(self, ctx, lang, *txt):
        """Translate a text.\n\
           **Example**
           ``>translate ja Hello World``"""
        if not txt:
            await ctx.send("You need to specify the text you want to translate!")
        abbv = {"jp": "ja"}
        if lang in abbv:
            lang = abbv[lang]
        translation = await translator.translate(" ".join(txt), dest=lang)
        # remove spaces from <@![ID]>
        translated = str(translation.text).replace("<@! ", "<@!")
        translated = str(translated).replace("<@ ", "<@")
        translated = str(translated).replace("<# ", "<#")
        embed = discord.Embed(timestamp=ctx.message.created_at)
        embed.set_author(
            name="Google Translate", icon_url="https://translate.google.com/favicon.ico"
        )
        embed.add_field(
            name=f"Source [{translation.src}]", value=translation.origin, inline=False
        )
        embed.add_field(
            name=f"Translated [{translation.dest}]", value=translated, inline=False
        )
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Utils(bot))
