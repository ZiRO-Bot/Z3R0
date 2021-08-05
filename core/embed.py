import discord

from utils.other import utcnow


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
            text="Requested by {}".format(ctx.author), icon_url=ctx.author.avatar.url
        )
        return instance

    @classmethod
    def error(
        cls,
        *,
        emoji="<:error:783265883228340245>",
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
        emoji="<:ok:864033138832703498>",
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
        emoji="<a:loading:776255339716673566>",
        title="Loading...",
        **kwargs,
    ):
        return cls(title="{} {}".format(emoji, title), **kwargs)
