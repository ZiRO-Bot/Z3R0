import asyncio
import datetime
import discord
import json
import logging

from discord.ext import commands

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

