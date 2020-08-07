from discord.ext import commands
import discord
import asyncio
import datetime

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["invite"])
    async def add(self, ctx):
        """Show link to invite ziBot."""
        oauth_link = discord.utils.oauth_url(self.bot.user.id, permissions=None, guild=None, redirect_uri=None) 
        await ctx.send(f"To add ziBot to your server, click here: \n {oauth_link}")
    
    @commands.command()
    async def source(self, ctx):
        """Show link to ziBot's source code."""
        git_link = "https://github.com/null2264/ziBot"
        await ctx.send(f"ziBot's source code: \n {git_link}")

    @commands.command()
    async def serverinfo(self, ctx):
        """Show server information"""
        embed = discord.Embed(
                title=f"{ctx.guild.name} Information",
                colour=discord.Colour.orange()
                )
        # embed.set_author(name=f"{ctx.guild.name} Information")
        embed.add_field(name="Created on",value=f"{ctx.guild.created_at.date()}")
        embed.set_thumbnail(url=ctx.guild.icon_url)
        _emoji=""
        embed.add_field(name="Members",value=f"{ctx.guild.member_count}")
        for emoji in ctx.guild.emojis:
            _emoji+= ", ".join([f"{str(emoji)}"])
        embed.add_field(name="Emojis",value=f"{_emoji}")
        embed.add_field(name="Owner",value=f"{ctx.guild.owner.mention}")
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(General(bot))

