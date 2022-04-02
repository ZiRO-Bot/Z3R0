from discord.ext import commands

from core.errors import (
    DefaultError,
    MissingAdminPrivilege,
    MissingModPrivilege,
    SilentError,
)
from utils.other import getGuildRole, utcnow


def has_guild_permissions(**perms):
    async def predicate(ctx):
        orig = commands.has_guild_permissions(**perms).predicate
        try:
            isMaster = ctx.author.id in ctx.bot.owner_ids
        except AttributeError:
            isMaster = False
        return isMaster or await orig(ctx)

    return commands.check(predicate)


# Is mod, is admin thingy


def is_botmaster():
    def predicate(ctx):
        return ctx.author.id in ctx.bot.owner_ids

    return commands.check(predicate)


def is_mod():
    # Moderator is a member that either have manage_guild or mod role
    async def predicate(ctx):
        try:
            roleId = await getGuildRole(ctx.bot, ctx.guild.id, "modRole")
            role = ctx.guild.get_role(roleId)
            isMod = role in ctx.author.roles
        except AttributeError:
            isMod = False

        if not isMod:
            try:
                isMod = await has_guild_permissions(manage_guild=True).predicate(ctx)
            except commands.MissingPermissions:
                raise MissingModPrivilege from None

        return isMod

    return commands.check(predicate)


def mod_or_permissions(**perms):
    async def predicate(ctx):
        try:
            orig = await is_mod().predicate(ctx)
        except MissingModPrivilege:
            orig = False

        try:
            permCheck = await has_guild_permissions(**perms).predicate(ctx)
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
            return await has_guild_permissions(administrator=True).predicate(ctx)
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
            permCheck = await has_guild_permissions(**perms).predicate(ctx)
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


def exlusive(*guildIds) -> bool:
    def predicate(ctx) -> bool:
        if ctx.guild.id not in guildIds:
            raise SilentError("Exclusive command")
        return True

    return commands.check(predicate)
