"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from discord import Locale
from discord.app_commands import TranslationContext, Translator, locale_str
from fluent.runtime import FluentBundle
from fluent.syntax import FluentParser
from fluent.syntax.ast import Resource


if TYPE_CHECKING:
    from .bot import ziBot


class Localization:
    """
    Object that handles i18n, powered by Project Fluent.

    The documentation is kinda bad, I don't know if they have some sort of
    convention to do things, but this is how I prefer doing it since passing
    list of locales a bit confusing.

    Usage
    =====
    To use it you just need to import 'localization' or this script itself:
    'from core.i18n import _format as _' or 'from core.i18n import localization'

    Then either use _() or use localization.format() function.
    """

    __initialized: bool = False

    root: Path = Path("src/main/locale")
    useIsolating: bool = False
    defaultLocale: Locale = Locale.american_english
    currentLocale: Locale | None = None
    _locales: frozenset[str] = frozenset(p.name for p in root.iterdir() if p.name.endswith("ftl"))
    bundles: dict[Locale, FluentBundle] = {}

    if TYPE_CHECKING:
        _defaultResource: Resource

    @classmethod
    async def init(cls, defaultLocale: Locale = Locale.american_english, useIsolating: bool = False) -> Localization:
        self = cls()

        self.useIsolating = useIsolating

        if self.defaultLocale != defaultLocale:
            self.defaultLocale = defaultLocale

        self.bundles = {}

        try:
            self._defaultResource = await self._getResource(self.defaultLocale)
        except FileNotFoundError:
            raise RuntimeError("Default locale not found!")

        self.__initialized = True
        return self

    def __getattr__(self, name: str) -> Any:
        if not self.__initialized:
            raise RuntimeError("Localization is not initialized properly!")
        return super().__getattribute__(name)

    @property
    def locales(self) -> frozenset[str]:
        return frozenset(i.rstrip(".ftl") for i in self._locales)

    def set(self, locale: Locale | None = None) -> None:
        self.currentLocale = locale

    async def _bundle(self, locale: Locale) -> FluentBundle:
        if str(locale) not in self.locales:
            return await self._bundle(self.defaultLocale)

        if locale in self.bundles:
            return self.bundles[locale]

        bundle = FluentBundle([str(locale)], use_isolating=self.useIsolating)
        if locale != self.defaultLocale:
            bundle.add_resource(await self._getResource(locale))
        bundle.add_resource(self._defaultResource)
        self.bundles[locale] = bundle
        return bundle

    async def get(self, keyword: locale_str, locale: Locale) -> str:
        msgId = keyword.message

        bundle = await self._bundle(locale)
        if not bundle.has_message(msgId):
            return msgId

        msg = bundle.get_message(msgId)
        if not msg.value:
            return msgId

        val, _ = bundle.format_pattern(msg.value, keyword.extras)
        return cast(str, val)

    async def format(self, msgId: locale_str, locale: Locale | None = None) -> str:
        return await self.get(msgId, locale or self.currentLocale or self.defaultLocale)

    async def _getResource(self, locale: Locale) -> Resource:
        with Path(self.root, f"{locale.value}.ftl").open(encoding="utf8") as fp:
            file = await asyncio.to_thread(fp.read)
            resource = FluentParser().parse(file)
        return resource


class FluentTranslator(Translator):
    def __init__(self, bot: ziBot):
        self.bot: ziBot = bot

    async def translate(self, string: locale_str, locale: Locale, context: TranslationContext) -> str:
        return await self.bot.i18n.format(string, locale=locale)


if __name__ == "__main__":

    async def testParallel():
        import time

        localization = await Localization.init()
        _T = locale_str

        async def test1():
            while time.time() <= start_time:
                pass

            localization.set(Locale.american_english)
            print(await localization.format(_T("var", name="Z3R0 1-1")))
            localization.set(Locale.indonesian)
            print(await localization.format(_T("var", name="Z3R0 1-2")))

        async def test2():
            while time.time() <= start_time:
                pass

            localization.set(Locale.indonesian)
            print(await localization.format(_T("var", name="Z3R0 2-1")))
            localization.set(Locale.american_english)
            print(await localization.format(_T("var", name="Z3R0 2-2")))

        start_time = time.time() + 20
        await asyncio.gather(test1(), test2())

    async def testLocale():
        localization = await Localization.init()
        _T = locale_str

        print(await localization.format(_T("var", name="Z3R0 1-1")))
        localization.set(Locale.indonesian)
        print(await localization.format(_T("var", name="Z3R0 1-1")))
        localization.set(Locale.japanese)  # Doesn't exists
        print(await localization.format(_T("var", name="Z3R0 1-1")))

    asyncio.run(testParallel())
    print()
    asyncio.run(testLocale())
