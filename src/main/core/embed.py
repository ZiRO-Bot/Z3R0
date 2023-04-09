"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Union

import discord

from ..utils import utcnow
from .enums import Emojis


if TYPE_CHECKING:
    from ..core.context import Context


class ZEmbed(discord.Embed):
    def __init__(self, color=0x3DB4FF, fields=(), field_inline=False, **kwargs):
        super().__init__(color=color, **kwargs)
        for n, v in fields:
            self.add_field(name=n, value=v, inline=field_inline)

    @classmethod
    def minimal(cls, timestamp=None, **kwargs):
        instance = cls(timestamp=timestamp or utcnow(), **kwargs)
        return instance

    @classmethod
    def default(cls, context: Union[discord.Interaction, Context], timestamp=None, **kwargs):
        try:
            author = context.author
        except AttributeError:
            author = context.user

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
        emoji=Emojis.error,
        title="Error",
        color=None,
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
        emoji=Emojis.ok,
        title="Success",
        color=None,
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
        emoji=Emojis.loading,
        title="Loading...",
        **kwargs,
    ):
        return cls(title="{} {}".format(emoji, title), **kwargs)
