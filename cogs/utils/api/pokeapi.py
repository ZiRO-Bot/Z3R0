import asyncio
import aiohttp
import json

API_URL = "https://pokeapi.co/api/v2/"


class PokeAPI:
    def __init__(self, session=None):
        self.cache = {}
        self.session = session or aiohttp.ClientSession()

    async def request(self, endpoint: str = "pokemon", query: str = "ditto"):
        """
        Get data from pokeapi.co

        Parameters
        ----------
        endpoint: str
            type of query can be either "pokemon", "type", "ability", etc
        query: str
            query can be pokemon, type or ability ID (or name for pokemon)
        """
        if (
            self.cache
            and endpoint.lower() in self.cache["endpoint"]
            and query.lower() in self.cache["query"]
        ):
            return self.cache["data"]

        async with self.session.get(API_URL + endpoint + "/" + query.lower()) as req:
            data = await req.text()
            self.cache = {
                "endpoint": endpoint.lower(),
                "query": query.lower(),
                "data": data,
            }
            return data

    async def get_pokemon_text(self, id = 1, prefered_lang: str = "en", prefered_ver=None):
        endpoint = "pokemon-species"
        try:
            entry = json.loads(await self.request(endpoint=endpoint, query=str(id)))
        except json.decoder.JSONDecodeError:
            entry = "Not Found"
        if "Not Found" not in entry:
            for ver in entry["flavor_text_entries"]:
                if ver["language"]["name"] == prefered_lang:
                    if prefered_ver and ver["version"]["name"] == prefered_ver:
                        return ver["flavor_text"]
                    elif not prefered_ver:
                        return ver["flavor_text"]
                    else:
                        return ver["flavor_text"]

    async def get_pokemon(self, pokemon: str = "ditto"):
        endpoint = "pokemon"
        try:
            poke_info = json.loads(await self.request(endpoint=endpoint, query=pokemon))
            entry = await self.get_pokemon_text(id=poke_info["id"], prefered_ver="ruby")
            poke_info = {
                "id": f"{poke_info['id']:0>3}",
                "name": poke_info["name"],
                "sprites": {"frontDefault": poke_info["sprites"]["front_default"]},
                "text": entry.replace("\n", " ").replace("\f", " ") if entry != "Not Found" else "",
                "types": [x["type"]["name"] for x in poke_info["types"]],
                "height": poke_info["height"],
                "weight": poke_info["weight"],
            }
        except json.decoder.JSONDecodeError:
            poke_info = {"Not Found"}
        if poke_info:
            return poke_info
        raise ConnectionError
