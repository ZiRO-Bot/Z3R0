from random import choice
from typing import Optional

from discord import Guild, Member, TextChannel

from ..interface import Adapter
from ..utils import escape_content
from ..verb import Verb


__all__ = (
    "AttributeAdapter",
    "MemberAdapter",
    "ChannelAdapter",
    "GuildAdapter",
)


class AttributeAdapter(Adapter):
    def __init__(self, base):
        self.object = base
        created_at = getattr(base, "created_at", None)
        self._attributes = {
            "id": base.id,
            "created_at": created_at or "N/A",
            "timestamp": int(created_at.timestamp() if created_at else 0),
            "name": getattr(base, "name", str(base)),
        }
        self._methods = {}
        self.update_attributes()
        self.update_methods()

    def __repr__(self):
        return f"<{type(self).__qualname__} object={self.object!r}>"

    def update_attributes(self):
        pass

    def update_methods(self):
        pass

    def get_value(self, ctx: Verb) -> Optional[str]:
        should_escape = False

        if ctx.parameter is None:
            return_value = str(self.object)
        else:
            try:
                value = self._attributes[ctx.parameter]
            except KeyError:
                if method := self._methods.get(ctx.parameter):
                    value = method()
                else:
                    return

            if isinstance(value, tuple):
                value, should_escape = value

            return_value = str(value) if value is not None else None

        return escape_content(return_value) if should_escape else return_value


class MemberAdapter(AttributeAdapter):
    """
    The ``{author}`` block with no parameters returns the tag invoker's full username
    and discriminator, but passing the attributes listed below to the block payload
    will return that attribute instead.

    **Aliases:** ``user``

    **Usage:** ``{author([attribute])``

    **Payload:** None

    **Parameter:** attribute, None

    Attributes
    ----------
    id
        The author's Discord ID.
    name
        The author's username.
    nick
        The author's nickname, if they have one, else their username.
    avatar
        A link to the author's avatar, which can be used in embeds.
    discriminator
        The author's discriminator.
    created_at
        The author's account creation date.
    timestamp
        The author's account creation date as a UTC timestamp.
    joined_at
        The date the author joined the server.
    mention
        A formatted text that pings the author.
    bot
        Whether or not the author is a bot.
    color
        The author's top role's color as a hex code.
    """

    def update_attributes(self):
        member: Member = self.object
        additional_attributes = {
            "color": member.colour,
            "colour": member.colour,
            "nick": member.display_name,
            "avatar": (member.display_avatar.url, False),
            "discriminator": member.discriminator,
            "joined_at": getattr(member, "joined_at", member.created_at),
            "mention": member.mention,
            "bot": member.bot,
        }
        self._attributes.update(additional_attributes)


class ChannelAdapter(AttributeAdapter):
    """
    The ``{channel}`` block with no parameters returns the channel's full name
    but passing the attributes listed below to the block payload
    will return that attribute instead.

    **Usage:** ``{channel([attribute])``

    **Payload:** None

    **Parameter:** attribute, None

    Attributes
    ----------
    id
        The channel's ID.
    name
        The channel's name.
    created_at
        The channel's creation date.
    timestamp
        The channel's creation date as a UTC timestamp.
    nsfw
        Whether the channel is nsfw.
    mention
        A formatted text that pings the channel.
    topic
        The channel's topic.
    """

    def update_attributes(self):
        if isinstance(self.object, TextChannel):
            additional_attributes = {
                "nsfw": self.object.nsfw,
                "mention": self.object.mention,
                "topic": self.object.topic or None,
            }
            self._attributes.update(additional_attributes)


class GuildAdapter(AttributeAdapter):
    """
    The ``{server}`` block with no parameters returns the server's name
    but passing the attributes listed below to the block payload
    will return that attribute instead.

    **Aliases:** ``guild``

    **Usage:** ``{server([attribute])``

    **Payload:** None

    **Parameter:** attribute, None

    Attributes
    ----------
    id
        The server's ID.
    name
        The server's name.
    icon
        A link to the server's icon, which can be used in embeds.
    created_at
        The server's creation date.
    timestamp
        The server's creation date as a UTC timestamp.
    member_count
        The server's member count.
    bots
        The number of bots in the server.
    humans
        The number of humans in the server.
    description
        The server's description if one is set, or "No description".
    channels
        The number of channels in the server.
    roles
        The number of roles in the server.
    owner
        The server's owner.
    random
        A random member from the server.
    randomonline
        A random online member from the server.
    randomoffline
        A random offline member from the server.
    """

    def update_attributes(self):
        guild: Guild = self.object
        bots = 0
        humans = 0
        for m in guild.members:
            if m.bot:
                bots += 1
            else:
                humans += 1
        additional_attributes = {
            "icon": (getattr(guild.icon, "url", "https://cdn.discordapp.com/embed/avatars/1.png"), False),
            "member_count": guild.member_count,
            "members": guild.member_count,
            "bots": bots,
            "humans": humans,
            "description": guild.description or "No description.",
            "channels": len(guild.channels),
            "roles": len(guild.roles),
            "owner": guild.owner,
        }
        self._attributes.update(additional_attributes)

    def update_methods(self):
        additional_methods = {
            "random": self.random_member,
            "randomonline": self.random_online_member,
            "randomoffline": self.random_offline_member,
        }
        self._methods.update(additional_methods)

    def get_member_list(self, status: str = None):
        if not status:
            member_list = self.object.members
        else:
            member_list = [m for m in self.object.members if str(m.status) == status]

        return member_list

    def random_member(self):
        members = self.get_member_list()
        return choice(members)

    def random_online_member(self):
        members = self.get_member_list("online")
        return choice(members)

    def random_offline_member(self):
        members = self.get_member_list("offline")
        return choice(members)
