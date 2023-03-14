"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from typing import Any, cast

import discord
from fluent.runtime import FluentBundle
from fluent.syntax import FluentParser
from fluent.syntax.ast import Resource


class Localization:
    def __init__(self, defaultLocale: discord.Locale = discord.Locale.american_english):
        self.defaultLocale: discord.Locale = defaultLocale
        self.root = Path("src/main/locale")
        self._defaultResource: Resource = self._getResource(defaultLocale)
        self.bundles: dict[discord.Locale, Any] = {}

        self._bundle(defaultLocale)

    def _bundle(self, locale: discord.Locale):
        if locale in self.bundles:
            return self.bundles[locale]

        bundle = FluentBundle([str(locale)])
        with suppress(FileNotFoundError):
            bundle.add_resource(self._getResource(locale))
        bundle.add_resource(self._defaultResource)
        self.bundles[locale] = bundle
        return bundle

    def get(self, msgId: str, locale: discord.Locale, args: dict[str, Any] | None = None) -> str:
        bundle = self._bundle(locale)
        if not bundle.has_message(msgId):
            return msgId

        msg = bundle.get_message(msgId)
        if not msg.value:
            return msgId

        val, _ = bundle.format_pattern(msg.value, args)
        return cast(str, val)

    def format(self, msgId: str, locale: discord.Locale | None = None) -> str:
        return self.get(msgId, locale or self.defaultLocale)

    def _getResource(self, locale: discord.Locale) -> Resource:
        with Path(self.root, f"{locale.value}.ftl").open() as fp:
            resource = FluentParser().parse(fp.read())
        return resource


test = Localization()
print(test.format("test"))
print(test.format("test", discord.Locale.japanese))
print(test.format("test", discord.Locale.indonesian))
