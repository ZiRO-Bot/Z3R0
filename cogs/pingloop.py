import asyncio
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
        channel_ids = [748437426325815297, 749867701144387605, 750000260302241943,
                       750000287447515196, 750000429835747388, 750000463008497694,
                       750000477508468897, 750000671100764203]
        for _id in channel_ids:
            await asyncio.sleep(1)
            ch = self.bot.get_channel(_id)
            await ch.send("@everyone")

def setup(bot):
    bot.add_cog(Everyone(bot))
