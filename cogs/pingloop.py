import discord

from discord.ext import tasks, commands

class Everyone(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.handle_schedule.start()

    def cog_unload(self):
        self.handle_schedule.cancel()

    @tasks.loop(seconds=3)
    async def handle_schedule(self):
        channel = self.bot.get_channel(748437426325815297)
        await channel.send("@everyone")

def setup(bot):
    bot.add_cog(Everyone(bot))
