import asyncio
import datetime
import discord

from discord.ext import commands

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def source(self, ctx):
        """Show link to ziBot's source code."""
        git_link = "https://github.com/null2264/ziBot"
        await ctx.send(f"ziBot's source code: \n {git_link}")

    @commands.command()
    async def serverinfo(self, ctx):
        """Show server information."""
        embed = discord.Embed(
                title=f"{ctx.guild.name} Information",
                colour=discord.Colour.orange()
                )
        # embed.set_author(name=f"{ctx.guild.name} Information")
        embed.add_field(name="Created on",value=f"{ctx.guild.created_at.date()}")
        embed.set_thumbnail(url=ctx.guild.icon_url)
        embed.add_field(name="Members",value=f"{ctx.guild.member_count}")
        embed.add_field(name="Owner",value=f"{ctx.guild.owner.mention}")
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(General(bot))

