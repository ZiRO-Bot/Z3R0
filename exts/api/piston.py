import asyncio


from aiohttp import ClientSession
from exts.utils.cache import ExpiringDict


class PistonOutput:
    def __init__(self, data):
        self.rawData = data

        # Always return None unless there's invalid value
        self.message = data.get("message", None)

        self.language = data.get("language", None)
        self.version = data.get("version", None)

        runData = data.get("run", {})
        self.stdout = runData.get("stdout", None)
        self.stderr = runData.get("stderr", None)
        self.code = runData.get("code", None)
        self.output = runData.get("output", None)


DEFAULT_SERVER = "https://emkc.org"


class Piston:
    def __init__(
        self, server: str = "https://emkc.org", loop=None, session: ClientSession = None
    ) -> None:
        self.session: ClientSession = session or ClientSession()
        self.baseUrl: str = server + (
            "/api/v2/piston" if server == DEFAULT_SERVER else "/api/v2"
        )
        # Max age: 86400 seconds (24 hour)
        self.languages: ExpiringDict = ExpiringDict(maxAgeSeconds=86400)

    async def getAvailableLanguages(self):
        # Check if any cache expired
        self.languages.verifyCache()

        if not self.languages:
            async with self.session.get(f"{self.baseUrl}/runtimes") as response:
                runtimes = await response.json()
            for runtime in runtimes:
                language = runtime["language"]
                self.languages[language] = language
                for alias in runtime["aliases"]:
                    self.languages[alias] = language

        return self.languages

    async def run(self, language, source, args=None, stdin=None):
        # languages = await self.getAvailableLanguages()
        # if language not in language:
        #     return

        data = {
            "language": language,
            "version": "*",
            "files": [{"content": source}],
            "args": args,
            "stdin": stdin or "",
            "log": 0,
        }
        async with self.session.post(
            f"{self.baseUrl}/execute",
            # headers=headers,
            json=data,
        ) as response:
            r = await response.json()
            return PistonOutput(r)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    piston = Piston(loop=loop)
    data = loop.run_until_complete(piston.run("py", "print('Hello World!')"))
    print(data.message)
