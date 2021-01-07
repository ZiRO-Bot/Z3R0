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

class Utils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('discord')
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        msg_id = payload.message_id
        if msg_id == 746645838586970152:
            guild_id = payload.guild_id
            guild = discord.utils.find(lambda g: g.id == guild_id, self.bot.guilds)
            role = None 
            if payload.emoji.name == "🖥️":
                role = discord.utils.get(guild.roles, name='Computer Nerd')
            elif payload.emoji.name == '🇦':
                role = discord.utils.get(guild.roles, name='Weeb')
            elif payload.emoji.name == '🇸':
                role = discord.utils.get(guild.roles, name='Speedrunner')
            
            if role:
                member = discord.utils.find(lambda m: m.id == payload.user_id, guild.members)
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
                role = discord.utils.get(guild.roles, name='Computer Nerd')
            elif payload.emoji.name == '🇦':
                role = discord.utils.get(guild.roles, name='Weeb')
            elif payload.emoji.name == '🇸':
                role = discord.utils.get(guild.roles, name='Speedrunner')
            
            if role:
                member = discord.utils.find(lambda m: m.id == payload.user_id, guild.members)
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
        purgatory_ch = self.bot.get_channel(
                                            int(self.bot.config[
                                                str(message.guild.id)][
                                                    "purge_ch"]
                                               )
                                            )
        embed = discord.Embed(title = "Deleted Message",
                colour = discord.Colour.red())
        embed.add_field(name="User", value=f"{message.author.mention}")
        embed.add_field(name="Channel", value=f"{message.channel.mention}")
        if not message.content:
            msg = "None"
        else:
            msg = message.content
        embed.add_field(name="Message", value=f"{msg}", inline=False)
        await purgatory_ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.content == after.content:
            return
        message = before
        purgatory_ch = self.bot.get_channel(
                                            int(self.bot.config[
                                                str(message.guild.id)][
                                                    "purge_ch"]
                                               )
                                            )
        embed = discord.Embed(title = "Edited Message",
                colour = discord.Colour.red())
        embed.add_field(name="User", value=f"{message.author.mention}")
        embed.add_field(name="Channel", value=f"{message.channel.mention}")
        if not message.content:
            b_msg = "None"
        else:
            b_msg = message.content
        if not after.content:
            a_msg = "None"
        else:
            a_msg = after.content
        embed.add_field(name="Before", value=f"{b_msg}", inline=False)
        embed.add_field(name="After", value=f"{a_msg}", inline=False)
        await purgatory_ch.send(embed=embed)

    @commands.command(aliases=['p'])
    async def ping(self, ctx):
        """Tell the ping of the bot to the discord servers."""
        await ctx.send(f'Pong! {round(self.bot.latency*1000)}ms')
    
    @commands.command(aliases=['trans'], brief="Translate a text.", usage="(language) (text)")
    async def translate(self, ctx, lang, *txt):
        """Translate a text.\n\
           **Example**
           ``>translate ja Hello World``"""
        if not txt:
            await ctx.send('You need to specify the text you want to translate!')
        abbv = {"jp": "ja"} 
        if lang in abbv:
            lang=abbv[lang]
        translation = await translator.translate(" ".join(txt), dest=lang)
        # remove spaces from <@![ID]>
        translated = str(translation.text).replace("<@! ", "<@!")
        translated = str(translated).replace("<@ ", "<@")
        translated = str(translated).replace("<# ", "<#")
        embed = discord.Embed(timestamp=ctx.message.created_at)
        embed.set_author(name="Google Translate",
                         icon_url="https://translate.google.com/favicon.ico")
        embed.add_field(name=f"Source [{translation.src}]", 
                        value=translation.origin, inline=False)
        embed.add_field(name=f"Translated [{translation.dest}]", 
                        value=translated, inline=False)
        await ctx.send(embed=embed)

    @commands.command(aliases=['up'])
    async def uptime(self, ctx):
        """Tell the ping of the bot to the discord servers."""
        await ctx.send('ziBot has been online for'
                       + f' {realtime(int(time.time() - bot.start_time))}')

def setup(bot):
    bot.add_cog(Utils(bot))

