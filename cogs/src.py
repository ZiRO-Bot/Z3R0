import aiohttp
import json

from discord.ext import commands

class SRC(commands.Cog, name="src"):
    def __init__(self, bot):
        self.bot = bot
        self.API_URL = "https://www.speedrun.com/api/v1/"
        self.session = self.bot.session
    
    async def get(self, _type, **kwargs):
        async with self.session.get(self.API_URL + _type, **kwargs) as url:
            data = json.loads(await url.text())
        return data
    
    async def get_cats(self, game_id):
        data = await self.get(f"games/{game_id}/categories")
        print(data['data'])
        # return data['data'][0]


    async def get_game(self, game):
        """Get game data without abbreviation."""
        data = await self.get("games", params={'name': game})
        return data['data'][0]

    @commands.group()
    async def worldrecord(self, ctx):
        """Get worldrecords from speedrun.com."""
        pass

    @commands.command()
    async def lb(self, ctx, game):
        data = await self.get_game(game)
        await self.get_cats(data['id'])
        # await ctx.send(data['names']['international'])
        pass
        
def setup(bot):
    bot.add_cog(SRC(bot))
