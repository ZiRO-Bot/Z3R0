import discord

from discord.ext import tasks, commands


class Pingloop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # self.handle_schedule.start()

    def cog_unload(self):
        self.handle_schedule.cancel()

    @tasks.loop(seconds=3)
    async def handle_schedule(self, channel: discord.TextChannel):
        if channel.guild.id != 747984453585993808:
            self.handle_schedule.cancel()
            return
        await channel.send("@everyone")

    @commands.command()
    async def start_pingloop(self, ctx, channel: discord.TextChannel):
        if channel.guild.id != 747984453585993808:
            return
        if self.handle_schedule.is_running():
            return
        self.handle_schedule.start()
        await ctx.send(f"Pingloop started by {ctx.message.author.mention}.")

    @commands.command()
    async def stop_pingloop(self, ctx):
        if not self.handle_schedule.is_running():
            return
        self.handle_schedule.cancel()
        await ctx.send(f"Pingloop started by {ctx.message.author.mention}.")


def setup(bot):
    bot.add_cog(Pingloop(bot))
