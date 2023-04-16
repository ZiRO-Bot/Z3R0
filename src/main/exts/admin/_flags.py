"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

from contextlib import suppress
from typing import Literal

import discord
from discord.ext import commands

from ...core.context import Context
from ...core.flags import StringAndFlags
from ...utils.format import separateStringFlags


class LogFlags(StringAndFlags):
    channel: discord.TextChannel | None = commands.flag(name="channel", aliases=["ch"], default=None)
    disable: bool | None = None

    @classmethod
    async def convert(cls, ctx: Context, arguments: str) -> LogFlags:
        self: LogFlags = await super().convert(ctx, arguments)  # type: ignore

        if not self.string:
            return self

        _channel = self.string
        if _channel:
            channel: discord.abc.MessageableChannel | None = await commands.TextChannelConverter().convert(ctx, _channel)
        else:
            channel = None

        self.channel = channel

        return self


# Also includes aliases
ROLE_TYPES = {
    "member": "autoRole",  # Role that automatically given upon joining a guild
    "default": "autoRole",
    "moderator": "modRole",
    "mod": "modRole",
    "muted": "mutedRole",
    "mute": "mutedRole",
    "regular": "",
}

SpecialRoleLiterals = Literal[tuple([i for i in ROLE_TYPES.keys() if i != "regular"])]
RoleLiterals = Literal[tuple(ROLE_TYPES)]


class RoleCreateFlags(StringAndFlags, case_insensitive=True):
    name: str = commands.flag(name="name", description="Role name")
    type_: RoleLiterals = commands.flag(
        name="type", default="regular", description="Role type (run `/role types` for type list)"
    )

    @classmethod
    async def convert(cls, ctx: Context, arguments: str) -> RoleCreateFlags:
        try:
            self: RoleCreateFlags = await super().convert(ctx, arguments)  # type: ignore
        except commands.MissingRequiredFlag as e:
            if e.flag.name == "name":
                string, args = separateStringFlags(arguments)
                args += f" name:{string}"
                return await super().convert(ctx, args)  # type: ignore
            raise e

        if not self.string:
            return self

        self.name = f"{self.string.strip()} {self.name.strip()}"
        return self


class RoleSetFlags(StringAndFlags, case_insensitive=True):
    role: discord.Role = commands.flag(name="role", description="Role you want the type to be changed")
    type_: SpecialRoleLiterals = commands.flag(name="type", description="Role type (run `/role types` for type list)")

    @classmethod
    async def convert(cls, ctx: Context, arguments: str) -> RoleSetFlags:
        try:
            self: RoleSetFlags = await super().convert(ctx, arguments)  # type: ignore
        except commands.MissingRequiredFlag as e:
            if e.flag.name == "role":
                string, args = separateStringFlags(arguments)
                args += f" role:{string}"
                return await super().convert(ctx, args)  # type: ignore
            raise e

        if not self.string:
            return self

        with suppress(commands.RoleNotFound):
            self.role = await commands.RoleConverter().convert(ctx, self.string)  # type: ignore

        return self


# TODO: Ditch flags for greetings, it breaks TagScript handler
class GreetingFlags(StringAndFlags, case_insensitive=True):
    message: str = commands.flag(name="message", aliases=["msg"], default="")
    channel: discord.TextChannel | None = commands.flag(name="channel", aliases=["ch"], default=None)
    raw: bool = False
    disable: bool = False
