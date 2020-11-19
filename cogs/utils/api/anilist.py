import aiohttp
import asyncio
import cogs.utils.api.anilist_query as query
import difflib
import json
import re

from ..formatting import pformat
from discord.ext import menus

class AniListException(Exception):
    """Base exception class for AniList"""
    pass

class AnimeNotFound(AniListException):
    def __init__(self, message: str = "Anime not found!"):
        self.message = message
        super().__init__(self.message)

class AniList:
    def __init__(self, session = None):
        self.api_url = "https://graphql.anilist.co"
        self.session = session or aiohttp.ClientSession()
        # All known anime format (MediaFormat)
        self.format = {
            "anime": [
                "tv",
                "tv_short",
                "movie",
                "special",
                "ova",
                "ona",
                "music",
            ],
            "manga": [
                "manga",
                "novel",
                "one_shot",
            ],
        }

    async def request(self, query: str, variables: str):
        """
        Request data from anilist.
        """
        if not query:
            return None
        async with self.session.post(
            self.api_url, json={
                "query": query,
                "variables": variables
            }
        ) as req:
            _json = json.loads(await req.text())
            if "errors" in _json:
                raise AnimeNotFound
            else:
                return _json
    
    async def fetch_id_with_name(self, name: str, _type_: str = None) -> dict:
        """Get id from name."""
        var = {"name": name}
        if _type_:
            var['atype'] = _type_.upper()
        q = await self.request(
            "query($name:String" + (",$atype:MediaFormat" if _type_ else "") + "){Media(search:$name,type:ANIME" + (",format:$atype" if _type_ else "") + "){id}}",
            var,
        )
        if "data" in q:
            return q['data']
        return None

    async def fetch_id(self, url: str) -> int:
        """
        Get id from url.
        """
        # If url is an ID, just return it
        try:
            _id = int(url)
            q = await self.request(
                "query($mediaId: Int){Media(id:$mediaId){id}}", {"mediaId": _id}
            )
            if q:
                return _id
            return None
        except ValueError:
            pass
    
        # regex for AniList and MyAnimeList
        regexAL = r"/anilist\.co\/anime\/(.\d*)/?"
        regexMAL = r"/myanimelist\.net\/anime\/(.\d*)/?"

        # if AL link then return the id
        match = re.search(regexAL, str(url))
        if match:
            return int(match.group(1))
    
        # if MAL link get the id, find AL id out of MAL id then return the AL id
        match = re.search(regexMAL, str(url))
        if not match:
            return None
        #     _id_ = await self.fetch_id_with_name(url, _type_)
        #     return int(_id_["Media"]["id"])
    
        # getting ID from MAL ID
        q = await self.request(
            "query($malId: Int){Media(idMal:$malId){id}}", {"malId": match.group(1)}
        )
        if not q:
            return None
            # raise ValueError("Anime not found!")
        return int(q["data"]["Media"]["id"])
    
    async def get_basic_info(self, _id):
        """
        Get basic information an anime, such as title, id, and cover

        Parameter
        ---------
        _id
            ID of an anime
        """
        checked_id = await self.fetch_id(_id)
        q = await self.request(query.animeInfo, {"mediaId": checked_id})
        return q["data"]

    async def get_anime(self, keyword: str, page: int, amount: int = 1, _format: str = None):
        """
        Get anime from anilist, was called `search_ani`

        Parameter
        ---------
        keyword: str
            Name/ID of an anime.
        _format: str
            MediaFormat, format of the anime, MOVIE, TV Show, etc. [-]
        page: int
            Number of selected page.
        amount: int
            Anime per page. (default: 1)
        
        Note
        ----
        [-] -> Only for `>anime search` or `query.animeInfo`
        """
        _id = None
        try:
            _id = await self.fetch_id(keyword)
        except AnimeNotFound:
            pass
        
        if _id:
            checked_id = await self.fetch_id(_id)
            q = await self.request(query.animeInfo, {"mediaId": checked_id})
            # maybe it's not id afterall?
            if not q:
                pass
            return q["data"]

        var = {"name": keyword, "page": page, "amount": amount}
        # Add aniformat if _type is not empty/None
        if _format:
            var["aniformat"] = str(difflib.get_close_matches(pformat(_format), self.format["anime"])[0]).upper()
        q = await self.request(query.searchAni, var)
        if not q:
            return
        return q["data"]

