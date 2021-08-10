from discord.ext import commands

from core.errors import MissingAdminPrivilege, MissingModPrivilege
from utils.other import utcnow


async def check_permissions(ctx, perms, *, check=all):
    is_owner = await ctx.bot.is_owner(ctx.author)
    if is_owner:
        return True

    resolved = ctx.channel.permissions_for(ctx.author)
    return check(
        getattr(resolved, name, None) == value for name, value in perms.items()
    )


def has_permissions(*, check=all, **perms):
    async def predicate(ctx):
        return await check_permissions(ctx, perms, check=check)

    return commands.check(predicate)


async def check_guild_permissions(ctx, perms, *, check=all):
    is_owner = await ctx.bot.is_owner(ctx.author)
    if is_owner:
        return True

    if ctx.guild is None:
        return False

    resolved = ctx.author.guild_permissions
    return check(
        getattr(resolved, name, None) == value for name, value in perms.items()
    )


def has_guild_permissions(**perms):
    async def predicate(ctx):
        orig = commands.has_guild_permissions(**perms).predicate
        return ctx.author.id in ctx.bot.master or await orig(ctx)

    return commands.check(predicate)


# Is mod, is admin thingy


def is_botmaster():
    def predicate(ctx):
        return ctx.author.id in ctx.bot.master

    return commands.check(predicate)


def is_mod():
    async def predicate(ctx):
        roleId = await ctx.bot.getGuildConfig(ctx.guild.id, "modRole", "guildRoles")
        role = ctx.guild.get_role(roleId)

        try:
            check = await has_guild_permissions(manage_guild=True).predicate(ctx)
        except commands.MissingPermissions:
            raise MissingModPrivilege from None

        return role in ctx.author.roles or check

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
            raise MissingModPrivilege(err.missing_permissions) from None

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
        return ctx.author.id == 518154918276628490

    return commands.check(predicate)


def isAprilFool():
    def predicate(ctx):
        today = utcnow()
        return today.day == 1 and today.month == 5

    return commands.check(predicate)
