import aiohttp
import asyncio
import cogs.utils.api.anilist_query as query
import difflib
import json
import re

from ..formatting import pformat
from discord.ext import menus


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
                raise ValueError("AniList: " + str(_json['errors'][0]['message']))
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

    async def fetch_id(self, url: str, _type_: str = None) -> int:
        """
        Get id from url.
        """
        # If url is an ID, just return it
        try:
            _id_ = int(url)
            return _id_
        except ValueError:
            pass
    
        # regex for AniList and MyAnimeList
        regexAL = r"/anilist\.co\/anime\/(.\d*)/"
        regexMAL = r"/myanimelist\.net\/anime\/(.\d*)"

        # if AL link then return the id
        match = re.search(regexAL, url)
        if match:
            return int(match.group(1))
    
        # if MAL link get the id, find AL id out of MAL id then return the AL id
        match = re.search(regexMAL, url)
        if not match:
            _id_ = await self.fetch_id_with_name(url, _type_)
            return int(_id_["Media"]["id"])
    
        # getting ID from MAL ID
        q = await self.request(
            "query($malId: Int){Media(idMal:$malId){id}}", {"malId": match.group(1)}
        )
        if not q:
            raise ValueError("Anime not found!")
        return int(q["data"]["Media"]["id"])
    
    async def get_anime(self, keyword: str, page: int, amount: int = 1, _format: str = None):
        """
        Get anime from anilist, was called `search_ani`

        keyword: str -> Name/ID of an anime.
        _format: str   -> MediaFormat, format of the anime, MOVIE, TV Show, etc. [-]
        page: int    -> Number of selected page.
        amount: int  -> Anime per page. (default: 1)
        
        [-] -> Only for `>anime search` or `query.animeInfo`
        """
        _id = None
        try:
            _id = int(keyword)
        except ValueError:
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

