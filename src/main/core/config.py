from __future__ import annotations

from typing import Any


class Config:
    """A class that holds the bot's configuration"""

    __slots__ = (
        "token",
        "defaultPrefix",
        "botMasters",
        "issueChannel",
        "openWeatherToken",
        "author",
        "links",
        "databaseUrl",
        "_tortoiseConfig",
        "internalApiHost",
    )

    def __init__(
        self,
        token: str,
        databaseUrl: str,
        defaultPrefix: str | None = None,
        botMasters: list[str] | None = None,
        issueChannel: str | None = None,
        openWeatherToken: str | None = None,
        author: str | None = None,
        links: dict[str, str] | None = None,
        tortoiseConfig: dict[str, Any] | None = None,
        internalApiHost: str | None = None,
    ):
        self.token = token
        self.defaultPrefix = defaultPrefix or ">"
        self.botMasters: tuple[int, ...] = tuple([int(master) for master in botMasters or []])
        self.issueChannel = issueChannel
        self.openWeatherToken = openWeatherToken
        self.author = author
        self.links = links
        self.databaseUrl = databaseUrl
        self._tortoiseConfig = tortoiseConfig
        self.internalApiHost = internalApiHost or "127.0.0.1:2264"

    @property
    def tortoiseConfig(self):
        return self._tortoiseConfig or {
            "connections": {"default": self.databaseUrl},
            "apps": {
                "models": {
                    "models": ["src.main.core.db", "aerich.models"],
                    "default_connection": "default",
                },
            },
        }
