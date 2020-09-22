import aiohttp
import discord
import json

from discord.ext import commands
from utilities.formatting import pformat, realtime


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
        categories = {}
        data = await self.get(f"games/{game_id}/categories")
        data = data["data"]
        for category in data:
            if category["type"] == "per-game":
                categories[pformat(category["name"])] = {
                    "id": category["id"],
                    "name": category["name"],
                }
        return categories

    async def get_subcats(self, game_id, category):
        catdict = await self.get_cats(game_id)
        cat_id = catdict[pformat(category)]["id"]
        data = await self.get(f"games/{game_id}/variables")
        data = data["data"]
        subcategory = {}
        for i in data:
            if i["category"] == cat_id and i["is-subcategory"]:
                subcategory[i["name"]] = i["id"]
            if (
                not i["category"]
                and i["is-subcategory"]
                and i["scope"]["type"] == "full-game"
            ):
                subcategory[i["name"]] = i["id"]
        print(subcategory)

    async def get_game(self, game):
        """Get game data without abbreviation."""
        data = await self.get(f"games/{game}")
        bulk = False
        try:
            data = data["data"]
        except:
            # If data is empty try getting it from abbv or name
            data = await self.get(f"games?abbreviation={game}")
            data = data["data"]
            bulk = True
            if not data:
                data = await self.get("games", params={"name": game})
                data = data["data"]
                bulk = True
        game_info = []

        if bulk:
            for i in range(len(data) - 1):
                game_info.append(
                    {
                        "id": data[i]["id"],
                        "name": data[i]["names"]["international"],
                    }
                )
        else:
            game_info.append(
                {
                    "id": data["id"],
                    "name": data["names"]["international"],
                }
            )
        return game_info

    @commands.group()
    async def mcbe(self, ctx):
        """Get mcbe run informations from speedrun.com."""
        pass

    @commands.command()
    async def lb(self, ctx, game, category):
        data = await self.get_game(game)
        await self.get_subcats(data[0]["id"], category)
        # await ctx.send(data['names']['international'])
        pass

    @commands.command()
    async def categories(self, ctx, game):
        game = await self.get_game(game)
        game = game[0]
        catdict = await self.get_cats(game["id"])
        e = discord.Embed(title=f"{game['name']} Categories")
        for i in catdict:
            e.add_field(
                name=catdict[i]["name"], value=pformat(catdict[i]["name"]), inline=False
            )
        await ctx.send(embed=e)


def setup(bot):
    bot.add_cog(SRC(bot))
