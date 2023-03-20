"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Collection

import discord
from discord.app_commands import locale_str

from ..utils.other import utcnow
from .enums import Emojis


if TYPE_CHECKING:
    from ..core.context import Context


class Field:
    def __init__(self, name: locale_str | str, value: locale_str | str, inline: bool = False):
        self.name: locale_str | str = name
        self.value: locale_str | str = value
        self.inline: bool = inline


class ZEmbed(discord.Embed):
    def __init__(self, color=0x3DB4FF, fields: Collection[Field] = list(), fieldInline=False, **kwargs):
        super().__init__(color=color, **kwargs)
        for field in fields:
            self.add_field(name=field.name, value=field.value, inline=field.inline or fieldInline)

    # TODO: Not yet "usable", just an idea for now
    @classmethod
    async def asyncBuild(cls, context: Context, fields: Collection[Field] = list(), **kwargs):
        instance = cls(**kwargs)
        for field in fields:
            name = await context.maybeTranslate(field.name)
            value = await context.maybeTranslate(field.value)
            instance.add_field(name=name, value=value, inline=field.inline or kwargs.get("fieldInline", False))

    @classmethod
    def minimal(cls, timestamp=None, **kwargs):
        instance = cls(timestamp=timestamp or utcnow(), **kwargs)
        return instance

    @classmethod
    def default(cls, context: discord.Interaction | Context, timestamp=None, **kwargs):
        """Shortcut to build embeds"""
        try:
            author = context.author  # type: ignore
        except AttributeError:
            author = context.user  # type: ignore

        instance = cls.minimal(timestamp=timestamp or utcnow(), **kwargs)
        instance.set_footer(
            text="Requested by {}".format(author),
            icon_url=author.display_avatar.url,
        )
        return instance

    # TODO: Not yet "usable", just an idea for now
    @classmethod
    async def asyncDefault(
        cls, context: Context | discord.Interaction, *, title: locale_str | str, timestamp=None, **kwargs
    ) -> ZEmbed:
        """|coro|

        Shortcut to build embed faster that support i18n
        """
        if isinstance(title, locale_str):
            title = await context.translate(title) or title.message
        instance = cls.default(context, title=title, timestamp=timestamp, **kwargs)
        return instance

    @classmethod
    def error(
        cls,
        *,
        emoji: str = Emojis.error,
        title: str = "Error",
        color: discord.Color = None,
        **kwargs,
    ):
        return cls(
            title="{} {}".format(emoji, title),
            color=color or discord.Color.red(),
            **kwargs,
        )

    @classmethod
    def success(
        cls,
        *,
        emoji: str = Emojis.ok,
        title: str = "Success",
        color: discord.Color = None,
        **kwargs,
    ):
        return cls(
            title="{} {}".format(emoji, title),
            color=color or discord.Color.green(),
            **kwargs,
        )

    @classmethod
    def loading(
        cls,
        *,
        emoji: str = Emojis.loading,
        title: str = "Loading...",
        **kwargs,
    ):
        return cls(title="{} {}".format(emoji, title), **kwargs)
