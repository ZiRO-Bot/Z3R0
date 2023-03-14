"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import builtins
from contextlib import suppress
from pathlib import Path
from typing import Any, cast

import discord
from fluent.runtime import FluentBundle
from fluent.syntax import FluentParser
from fluent.syntax.ast import Resource


class Localization:
    """
    Object that handles i18n, powered by Project Fluent.

    The documentation is kinda bad, I don't know if they have some sort of
    convention to do things, but this is how I prefer doing it since passing
    list of locales a bit confusing.

    Usage
    =====
    To use it you just need to import 'localization' or this script itself:
    'from core import i18n' or 'from core.i18n import localization'

    Then either use localization.format() or use _() function.
    """

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

    def get(self, msgId: str, locale: discord.Locale, args: dict[str, Any] = {}) -> str:
        bundle = self._bundle(locale)
        if not bundle.has_message(msgId):
            return msgId

        msg = bundle.get_message(msgId)
        if not msg.value:
            return msgId

        val, _ = bundle.format_pattern(msg.value, args)
        return cast(str, val)

    def format(self, msgId: str, locale: discord.Locale | None = None, **kwargs) -> str:
        return self.get(msgId, locale or self.defaultLocale, kwargs)

    def _getResource(self, locale: discord.Locale) -> Resource:
        with Path(self.root, f"{locale.value}.ftl").open() as fp:
            resource = FluentParser().parse(fp.read())
        return resource


localization = Localization()
builtins._ = localization.format  # type: ignore

if __name__ == "__main__":
    print(localization.format("test"))
    print(localization.format("test", discord.Locale.japanese))
    print(localization.format("test", discord.Locale.indonesian))
    print(localization.format("var"))
    print(localization.format("var", discord.Locale.japanese, name="Z3R0"))
    print(localization.format("var", discord.Locale.indonesian, name="Z3R0"))
