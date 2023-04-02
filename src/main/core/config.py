"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

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
        "test",
        "zmqPorts",
        "useAerich",
        "destUrl",
        "isDataMigration",
    )

    def __init__(
        self,
        token: str,
        databaseUrl: str | None = None,
        defaultPrefix: str | None = None,
        botMasters: list[str] | None = None,
        issueChannel: str | None = None,
        openWeatherToken: str | None = None,
        author: str | None = None,
        links: dict[str, str] | None = None,
        tortoiseConfig: dict[str, Any] | None = None,
        internalApiHost: str | None = None,
        test: bool = False,
        zmqPorts: dict[str, int] | None = None,
        destUrl: str | None = None,
        isDataMigration: bool = False,
    ):
        self.token = token
        self.defaultPrefix = defaultPrefix or ">"
        self.botMasters: tuple[int, ...] = tuple([int(master) for master in botMasters or []])
        self.issueChannel = issueChannel
        self.openWeatherToken = openWeatherToken
        self.author = author
        self.links = links
        self.databaseUrl = databaseUrl or "sqlite://data/database.db"
        self.destUrl = destUrl
        self.isDataMigration = isDataMigration
        self._tortoiseConfig = tortoiseConfig
        self.internalApiHost = internalApiHost or "127.0.0.1:2264"
        self.test = test
        self.zmqPorts = zmqPorts or {}

    @property
    def tortoiseConfig(self):
        mainModel = "main.core.db"
        if not self.test:
            mainModel = "src." + mainModel

        ret = self._tortoiseConfig
        if not ret:
            ret = {
                "connections": {
                    "default": self.databaseUrl,
                },
                "apps": {
                    "models": {
                        "models": [mainModel, "aerich.models"],
                        "default_connection": "default",
                    },
                },
                "use_tz": True,  # d.py 2.0 is tz-aware
                "timezone": "UTC",
            }

        if self.destUrl and not self.test and self.isDataMigration:
            ret["connections"]["dest"] = self.destUrl

        return ret
