import asyncio
import datetime
import discord
import json
import logging
import re

from discord.ext import commands
from pytz import timezone

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('discord')

    @commands.command(usage="(language) (code)",
                      brief="Compile code")
    async def compile(self, ctx, language=None, *, code=None):
        """Compile code from a variety of programming languages, powered by <https://wandbox.org/>\n\
           **Example**
           ``>compile python print('Hello World')``"""
        
        compilers = {
                "bash": "bash",
                "c":"gcc-head-c",
                "c#":"dotnetcore-head",
                "coffeescript": "coffescript-head",
                "cpp": "gcc-head",
                "elixir": "elixir-head",
                "go": "go-head",	
                "java": "openjdk-head",
                "javascript":"nodejs-head",
                "lua": "lua-5.3.4",
                "perl": "perl-head",
                "php": "php-head",
                "python":"cpython-3.8.0",
                "ruby": "ruby-head",
                "rust": "rust-head",
                "sql": "sqlite-head",
                "swift": "swift-5.0.1",
                "typescript":"typescript-3.5.1",
                "vim-script": "vim-head"
                }
        if not language:
            await ctx.send(f"```json\n{json.dumps(compilers, indent=4)}```")
        if not code:
            await ctx.send("No code found")
            return
        try:
            compiler = compilers[language.lower()]
        except KeyError:
            await ctx.send("Language not found")
            return
        body = {
                "compiler": compiler,
                "code": code,
                "save": True
                }
        head = {
                "Content-Type":"application/json"
                }
        async with ctx.typing():
            async with self.bot.session.post("https://wandbox.org/api/compile.json", headers=head, data=json.dumps(body)) as r:
                #r = requests.post("https://wandbox.org/api/compile.json", headers=head, data=json.dumps(body))
                try:
                    response = json.loads(await r.text())
                    #await ctx.send(f"```json\n{json.dumps(response, indent=4)}```")
                    self.logger.info(f"json\n{json.dumps(response, indent=4)}")
                except json.decoder.JSONDecodeError:
                    self.logger.error(f"json\n{r.text}")
                    await ctx.send(f"```json\n{r.text}```")
                
                try:
                    embed=discord.Embed(title="Compiled code")
                    embed.add_field(name="Output", value=f'```{response["program_message"]}```', inline=False)
                    embed.add_field(name="Exit code", value=response["status"], inline=True)
                    embed.add_field(name="Link", value=f"[Permalink]({response['url']})", inline=True)
                    await ctx.send(embed=embed)
                except KeyError:
                    self.logger.error(f"json\n{json.dumps(response, indent=4)}")
                    await ctx.send(f"```json\n{json.dumps(response, indent=4)}```")

    @commands.command()
    async def source(self, ctx):
        """Show link to ziBot's source code."""
        git_link = "https://github.com/null2264/ziBot"
        await ctx.send(f"ziBot's source code: \n {git_link}")

    @commands.command(aliases=['ui'], usage="[member]")
    async def userinfo(self, ctx, *, user: discord.Member=None):
        if not user:
            user = ctx.message.author
        def stat(x):
            return {
                'offline': '<:status_offline:747799247243575469>',
                'idle': '<:status_idle:747799258316668948>',
                'dnd': '<:status_dnd:747799292592259204>',
                'online': '<:status_online:747799234828435587>',
                'streaming': '<:status_streaming:747799228054765599>'
                }.get(str(x), "None")
        def badge(x):
            return {
                "UserFlags.hypesquad_balance" : "<:balance:747802468586356736>",
                "UserFlags.hypesquad_brilliance" : "<:brilliance:747802490241810443>",
                "UserFlags.hypesquad_bravery" : "<:bravery:747802479533490238>",
                "UserFlags.bug_hunter" : "<:bughunter:747802510663745628>",
                "UserFlags.booster" : "<:booster:747802502677659668>",
                "UserFlags.hypesquad" : "<:hypesquad:747802519085776917>",
                "UserFlags.partner" : "<:partner:747802528594526218>",
                "UserFlags.owner" : "<:owner:747802537402564758>",
                "UserFlags.staff" : "<:stafftools:747802548391379064>",
                "UserFlags.early_supporter" : "<:earlysupport:747802555689730150>",
                "UserFlags.verified" : "<:verified:747802457798869084>",
                "UserFlags.verified_bot" : "<:verified:747802457798869084>"
                }.get(x, "🚫")
        badges = []
        for x in list(user.public_flags.all()):
            x = str(x)
            print(x)
            badges.append(badge(x))
        roles = [x.mention for x in user.roles]
        ignored_role = ["<@&645074407244562444>", "<@&745481731133669476>"]
        for i in ignored_role:
            try:
                roles.remove(i)
            except ValueError:
                print("Role not found, skipped")
        jakarta = timezone('Asia/Jakarta')

        embed = discord.Embed(description=f"{stat(user.status)}({user.status})", 
                              colour=user.colour,
                              timestamp=ctx.message.created_at)
        embed.set_author(name=f"{user.name}#{user.discriminator}", icon_url=user.avatar_url)
        embed.set_thumbnail(url=user.avatar_url)
        embed.add_field(name="Guild name", value=user.display_name)
        embed.add_field(name="Badges",value=" ".join(badges) if badges else "No badge.")
        embed.add_field(name="Created on", value=user.created_at.replace(
            tzinfo=timezone('UTC')).astimezone(jakarta).strftime("%a, %#d %B %Y, %H:%M WIB"), inline=False)
        embed.add_field(name="Joined on", value=user.joined_at.replace(
            tzinfo=timezone('UTC')).astimezone(jakarta).strftime("%a, %#d %B %Y, %H:%M WIB"), inline=False)
        embed.add_field(name=f"Roles ({len(roles)})",
                        value=", ".join(roles))
        embed.set_footer(text=f"ID: {user.id}")
        await ctx.send(embed=embed)

    @commands.command(aliases=['si'])
    async def serverinfo(self, ctx):
        """Show server information."""
        embed = discord.Embed(
                title=f"About {ctx.guild.name}",
                colour=discord.Colour(0xFFFFF0)
                )
        roles = [x.mention for x in ctx.guild.roles]
        ignored_role = ["<@&645074407244562444>", "<@&745481731133669476>"]
        for i in ignored_role:
            try:
                roles.remove(i)
            except ValueError:
                print("Role not found, skipped")
        width = 3
        
        boosters = [x.mention for x in ctx.guild.premium_subscribers]

        embed.add_field(name="Owner",value=f"{ctx.guild.owner.mention}",inline=False)
        embed.add_field(name="Created on",value=f"{ctx.guild.created_at.date()}")
        embed.add_field(name="Region",value=f"``{ctx.guild.region}``")
        embed.set_thumbnail(url=ctx.guild.icon_url)
        embed.add_field(name="Verification Level",
                        value=f"{ctx.guild.verification_level}".title())
        embed.add_field(name="Channels",value="<:categories:747750884577902653>"
                                              + f" {len(ctx.guild.categories)}\n"
                                              + "<:text_channel:747744994101690408>"
                                              + f" {len(ctx.guild.text_channels)}\n"
                                              + "<:voice_channel:747745006697185333>"
                                              + f" {len(ctx.guild.voice_channels)}")
        embed.add_field(name="Members",value=f"{ctx.guild.member_count}")
        if len(boosters) < 5:
            embed.add_field(name=f"Boosters ({len(boosters)})",
                            value=",\n".join(", ".join(boosters[i:i+width]) 
                                    for i in range(0, len(boosters), width)) 
                                    if boosters 
                                    else 'No booster.')
        else:
            embed.add_field(name=f"Boosters ({len(boosters)})",
                            value=len(boosters))
        embed.add_field(name=f"Roles ({len(roles)})",
                        value=", ".join(roles))
        embed.set_footer(text=f"ID: {ctx.guild.id}")
        await ctx.send(embed=embed)

    @commands.command()
    async def info(self, ctx):
        embed = discord.Embed(
                title="About ziBot",
                description="ziBot is an open source bot, \n\
                             a fork of mcbeDiscordBot",
                colour=discord.Colour(0xFFFFF0)
                )
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.add_field(name="Author", value="ZiRO2264#4572")
        embed.add_field(name="Links", value="[Github](https://github.com/null2264/ziBot)")
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(General(bot))

