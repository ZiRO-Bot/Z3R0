"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import datetime as dt
from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING, Collection

import discord
from discord.app_commands import locale_str

from ..utils import utcnow
from .enums import Emojis


_ = locale_str


if TYPE_CHECKING:
    from ..core.context import Context


@dataclass
class Field:
    name: locale_str | str
    value: locale_str | str
    inline: bool = False


@dataclass
class Footer:
    text: locale_str | str
    iconUrl: str | None = None


class ZEmbedBuilder:
    """Async-first Embed Builder"""

    def __init__(
        self,
        title: locale_str | str | None = None,
        description: locale_str | str | None = None,
        colour: discord.Colour | int | None = None,
        timestamp: dt.datetime | None = None,
        fields: list[Field] = None,
        fieldInline: bool = False,
        emoji: str | None = None,
    ):
        self.author: locale_str | str | None = None
        self.authorUrl: str | None = None
        self.authorIcon: str | None = None
        self.title: locale_str | str | None = title
        self.emoji: str | None = emoji
        self.description: locale_str | str | None = description
        self.colour: discord.Colour | int = colour or 0x3DB4FF
        self.timestamp: dt.datetime | None = timestamp
        if fields:  # avoid ZEmbedBuilder.fields from being singleton
            self.setFields(fields)
        self.fieldInline: bool = fieldInline
        self.imageUrl: str | None = None
        self.footer: Footer | None = None

    @classmethod
    def default(cls, context: Context | discord.Interaction, timestamp: dt.datetime | None = None, **kwargs):
        """Default template"""
        if isinstance(context, Context):
            author = context.author
        else:
            author = context.user

        instance = cls(timestamp=timestamp or utcnow(), **kwargs)
        instance.requesterToFooter(author)
        return instance

    @classmethod
    def error(
        cls,
        *,
        emoji: str = Emojis.error,
        title: locale_str | str = _("error"),
        colour: discord.Colour = None,
        **kwargs,
    ):
        """Embed Template for Error Message"""
        return cls(
            title=title,
            colour=colour or discord.Colour.red(),
            emoji=emoji,
            **kwargs,
        )

    @classmethod
    def success(
        cls,
        *,
        emoji: str = Emojis.ok,
        title: locale_str | str = _("success"),
        colour: discord.Colour = None,
        **kwargs,
    ):
        """Embed Template for Success Message"""
        return cls(
            title=title,
            colour=colour or discord.Colour.green(),
            emoji=emoji,
            **kwargs,
        )

    @classmethod
    def loading(
        cls,
        *,
        emoji: str = Emojis.loading,
        title: locale_str | str = _("loading"),
        colour: discord.Colour | int = None,
        **kwargs,
    ):
        """Embed Template for Loading"""
        return cls(
            title=title,
            colour=colour or discord.Colour.green(),
            emoji=emoji,
            **kwargs,
        )

    def setAuthor(self, *, name: locale_str | str, url: str | None = None, iconUrl: str | None = None) -> ZEmbedBuilder:
        self.author = name
        self.authorUrl = url
        self.authorIcon = iconUrl
        return self

    def setImage(self, url: str) -> ZEmbedBuilder:
        self.imageUrl = url
        return self

    def requesterToFooter(self, author: discord.User | discord.Member) -> ZEmbedBuilder:
        return self.setFooter(locale_str("requested-by", user=str(author)), author.display_avatar.url)

    def setFooter(self, text: locale_str | str, iconUrl: str | None = None) -> ZEmbedBuilder:
        self.footer = Footer(text, iconUrl)
        return self

    def setFields(self, fields: list[Field]) -> ZEmbedBuilder:
        self.fields = fields
        return self

    def addField(self, name: locale_str | str, value: locale_str | str, inline: bool = False) -> ZEmbedBuilder:
        field = Field(name, value, inline)

        try:
            self.fields.append(field)
        except AttributeError:
            self.setFields([field])
        return self

    async def build(
        self, context: Context, *, cls=discord.Embed, autoGenerateDT: bool = False, addRequester: bool = True
    ) -> discord.Embed:
        kwargs = {}

        if self.title:
            title = await context.maybeTranslate(self.title)
            if self.emoji:
                title = f"{self.emoji} {title}"
            kwargs["title"] = title

        if self.description:
            kwargs["description"] = await context.maybeTranslate(self.description)

        ts = self.timestamp
        if not ts and autoGenerateDT:
            ts = utcnow()
        if ts:
            kwargs["timestamp"] = ts

        if self.colour:
            kwargs["colour"] = self.colour

        instance: discord.Embed = cls(**kwargs)

        if self.author:
            instance.set_author(name=await context.maybeTranslate(self.author), icon_url=self.authorIcon, url=self.authorUrl)

        with suppress(AttributeError):
            for field in self.fields:
                name = await context.maybeTranslate(field.name)
                value = await context.maybeTranslate(field.value)
                instance.add_field(name=name, value=value, inline=field.inline or self.fieldInline)

        if self.imageUrl:
            instance.set_image(url=self.imageUrl)

        if not self.footer and addRequester:
            self.requesterToFooter(context.author)

        if self.footer:
            instance.set_footer(text=await context.maybeTranslate(self.footer.text), icon_url=self.footer.iconUrl)

        return instance


class ZEmbed(discord.Embed):
    def __init__(self, color=0x3DB4FF, fields: Collection[Field] = list(), fieldInline=False, **kwargs):
        super().__init__(color=color, **kwargs)
        for field in fields:
            self.add_field(name=field.name, value=field.value, inline=field.inline or fieldInline)

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
        colour: discord.Colour | int = None,
        **kwargs,
    ):
        return cls(title="{} {}".format(emoji, title), color=colour, **kwargs)
