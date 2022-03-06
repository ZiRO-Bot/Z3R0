import discord

from ..utils.other import utcnow
from .enums import Emojis


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
    def default(cls, ctx, timestamp=None, **kwargs):
        instance = cls.minimal(timestamp=timestamp or utcnow(), **kwargs)
        instance.set_footer(
            text="Requested by {}".format(ctx.author),
            icon_url=ctx.author.display_avatar.url,
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
