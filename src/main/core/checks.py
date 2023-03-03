"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

from contextlib import suppress

from discord.ext import commands

from ..utils.other import getGuildRole, utcnow
from .errors import (
    DefaultError,
    MissingAdminPrivilege,
    MissingModPrivilege,
    SilentError,
)


# TODO: Re-organize, also make it hybrid


def hasGuildPermissions(**perms):
    async def predicate(ctx):
        orig = commands.has_guild_permissions(**perms).predicate
        try:
            isMaster = ctx.author.id in ctx.bot.owner_ids
        except AttributeError:
            isMaster = False
        return isMaster or await orig(ctx)

    return commands.check(predicate)


# Is mod, is admin thingy


def botMasterOnly():
    def predicate(ctx):
        return ctx.author.id in ctx.bot.owner_ids

    return commands.check(predicate)


# NOTE: Deprecated, use botMasterOnly() instead
is_botmaster = botMasterOnly


# TODO
def botManagerOnly():
    async def predicate(ctx):
        try:
            roleId = await getGuildRole(ctx.bot, ctx.guild.id, "botManagerRole")
            role = ctx.guild.get_role(roleId)
            isManager = role in ctx.author.roles
        except AttributeError:
            isManager = False

        return isManager

    return commands.check(predicate)


def modOnly(**perms):
    async def predicate(ctx):
        if ctx.bot.config.test:
            return True

        # Check if user is in a guild first
        await commands.guild_only().predicate(ctx)

        try:
            roleId = await getGuildRole(ctx.bot, ctx.guild.id, "modRole")
            role = ctx.guild.get_role(roleId)
            isMod = role in ctx.author.roles
        except AttributeError:
            isMod = False

        # Mod role bypass every moderation permission checks
        if isMod:
            return isMod

        # If no permissions is specified, then only people with mod roles can use this
        if not perms:
            raise MissingModPrivilege

        try:
            return await hasGuildPermissions(**perms).predicate(ctx)
        except commands.MissingPermissions as err:
            raise MissingModPrivilege(err.missing_permissions) from None

    return commands.check(predicate)


# NOTE: Deprecated, use modOnly() instead
def is_mod():
    # Moderator is a member that either have manage_guild or mod role
    async def predicate(ctx):
        if ctx.bot.config.test:
            return True

        try:
            roleId = await getGuildRole(ctx.bot, ctx.guild.id, "modRole")
            role = ctx.guild.get_role(roleId)
            isMod = role in ctx.author.roles
        except AttributeError:
            isMod = False

        if not isMod:
            try:
                isMod = await hasGuildPermissions(manage_guild=True).predicate(ctx)
            except commands.MissingPermissions:
                raise MissingModPrivilege from None

        return isMod

    return commands.check(predicate)


# NOTE: Deprecated, use modOnly() instead
def mod_or_permissions(**perms):
    async def predicate(ctx):
        try:
            orig = await is_mod().predicate(ctx)
        except MissingModPrivilege:
            orig = False

        try:
            permCheck = await hasGuildPermissions(**perms).predicate(ctx)
        except commands.MissingPermissions as err:
            if not orig:
                raise MissingModPrivilege(err.missing_permissions) from None
            permCheck = False

        return orig or permCheck

    return commands.check(predicate)


async def isMod(ctx):
    return await is_mod().predicate(ctx)


async def isModOrPerms(ctx, perms, check=all):
    return await mod_or_permissions(**perms).predicate(ctx)


def is_admin():
    async def predicate(ctx):
        try:
            return await hasGuildPermissions(administrator=True).predicate(ctx)
        except commands.MissingPermissions:
            raise MissingAdminPrivilege from None

    return commands.check(predicate)


def admin_or_permissions(**perms):
    async def predicate(ctx):
        try:
            orig = await is_admin().predicate(ctx)
        except MissingAdminPrivilege:
            orig = False

        try:
            permCheck = await hasGuildPermissions(**perms).predicate(ctx)
        except commands.MissingPermissions as err:
            raise MissingModPrivilege(err.missing_permissions) from None

        return orig or permCheck

    return commands.check(predicate)


def isRafael():
    def predicate(ctx):
        if not (ctx.author.id == 518154918276628490):
            raise SilentError("Only Rafael can use this command")
        return True

    return commands.check(predicate)


def isAprilFool():
    def predicate(ctx):
        today = utcnow()
        if not (today.day == 1 and today.month == 4):
            raise DefaultError("Not April Fools yet!")
        return True

    return commands.check(predicate)


def exlusive(*guildIds):
    def predicate(ctx) -> bool:
        if ctx.guild.id not in guildIds:
            raise SilentError("Exclusive command")
        return True

    return commands.check(predicate)
