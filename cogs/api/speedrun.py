import asyncio
import aiohttp
import json
import urllib.parse


class Pagination:
    def __init__(self, data):
        """
        Object for `data.pagination`
        """
        self.offset = data["offset"]
        self.max = data["max"]
        self.size = data["size"]
        self.hasNextPage = False
        for i in data["links"]:
            if i["rel"] == "next":
                self.hasNextPage = True

    def __str__(self):
        return "{} -> [size={}, max={}, hasNextPage={}]".format(self.offset, self.size, self.max, self.hasNextPage)


class Asset:
    def __init__(self, data):
        """
        Object for `asset`
        """
        self.url = data["uri"]
        self.uri = self.url
        self.height = data["height"]
        self.width = data["width"]

    def __str__(self):
        return self.url

    def __repr__(self):
        return "<{} ({}x{})>".format(self.url, self.height, self.width)


class Game:
    def __init__(self, data, embeds=[], embedded=False):
        """
        Object for `/games/`
        """
        self.rawData = data
        gameData = self.rawData["data"][0] if not embedded else self.rawData

        self.id = gameData["id"]
        self.name = gameData["names"]["international"]
        self.nameInt = self.name
        self.nameJapan = gameData["names"]["japanese"]
        self.nameTwitch = gameData["names"]["twitch"]
        self.abbreviation = gameData["abbreviation"]
        self.weblink = gameData["weblink"]
        self.releaseYear = gameData["released"]
        self.releaseDate = gameData["release-date"]
        self.assets = {asset: Asset(gameData["assets"][asset]) for asset in gameData["assets"] if gameData["assets"][asset]}

        # Stuff that overwritten by embeds
        self.moderators = gameData["moderators"]
        self.platforms = gameData["platforms"]

        if not embedded:
            self.page = Pagination(data["pagination"])
            if "levels" in embeds:
                self.levels = [Level(lev, embedded=True) for lev in gameData["levels"]["data"]]
            if "categories" in embeds:
                self.categories = [Category(cat, embedded=True) for cat in gameData["categories"]["data"]]
            if "moderators" in embeds:
                self.moderators = [Runner(mod, embedded=True) for mod in self.moderators["data"]]
            if "platforms" in embeds:
                self.platforms = [Platform(platform, embedded=True) for platform in self.platforms["data"]] 

    def __str__(self):
        return self.name


class Runner:
    def __init__(self, data, embedded=False):
        """
        Object for Runner (`moderator`, `player`, `user`)
        """
        self.rawData = data
        runnerData = self.rawData["data"][0] if not embedded else self.rawData
        self.id = data["id"]
        self.name = runnerData["names"]["international"]
        self.nameInt = self.name
        self.nameJapan = runnerData["names"]["japanese"]
        self.weblink = runnerData["weblink"]

    def __str__(self):
        return self.name


class Platform:
    def __init__(self, data, embedded=False):
        """
        Object for `platform`
        """
        self.rawData = data
        platformData = self.rawData["data"] if not embedded else self.rawData
        self.id = platformData["id"]
        self.name = platformData["name"]
        self.releaseYear = platformData["released"]

    def __str__(self):
        return self.name


class Category:
    def __init__(self, data, embedded=False):
        """
        Object for category
        """
        self.rawData = data
        categoryData = self.rawData["data"][0] if not embedded else self.rawData
        self.id = categoryData["id"]
        self.name = categoryData["name"]
        self.weblink = categoryData["weblink"]
        self.type = categoryData["type"]
        self.rules = categoryData["rules"]
    
    def __str__(self):
        return self.name


class Level:
    def __init__(self, data, embedded=False):
        """
        Object for `level` (individual levels)
        """
        self.rawData = data
        levelData = self.rawData["data"][0] if not embedded else self.rawData
        self.id = levelData["id"]
        self.name = levelData["name"]
        self.weblink = levelData["weblink"]
    
    def __str__(self):
        return self.name


class SpeedrunPy:
    def __init__(self, session = aiohttp.ClientSession()):
        """
        Wrapper for speedrun.com's API
        """
        self.session = session
        self.baseUrl = "https://www.speedrun.com/api/v1"
    
    async def get(self, _type: str, query: str):
        """
        Get data from speedrun.com api

        Parameters
        ----------
        _type
            Type of request (example: `/games/{query}`)
        query
            Query for a request (example: `/games/mcbe` or `/games?name=Minecraft: Bedrock Edition`)
        """
        async with self.session.get(self.baseUrl + _type + query) as res:
            return json.loads(await res.text())

    async def get_game(self, name: str="", page: int=0, perPage: int=100, embeds: list=[]):
        """
        Get game data from speedrun.com api

        Parameters
        ----------
        name
            Name/Abbreviation of the game
        page
            Page count
        perPage
            Game per page
        embeds
            SRC's Embeds
        """
        availableEmbeds = (
            "levels",
            "categories",
            "moderators",
            "gametypes",
            "platforms",
            "regions",
            "genres",
            "engines",
            "developers",
            "publishers",
            "variables",
        )
        params = {"name": name, "embed": ",".join([e for e in embeds if e in availableEmbeds])}
        query = urllib.parse.urlencode(params)
        return Game(await self.get("/games", "?{}".format(query)), embeds=embeds)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    src = SpeedrunPy()
    # res = await src.get_game("Super Mario Sunshine", embeds=["platforms"])
    game = loop.run_until_complete(src.get_game("Super Mario Sunshine", embeds=["levels"]))
    print(game.assets)
    print(game.levels[0].name)
