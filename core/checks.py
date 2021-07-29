from core.errors import NotInGuild  # type: ignore
from exts.utils.other import utcnow  # type: ignore
from discord.ext import commands


async def isMod(ctx):
    roleId = await ctx.bot.getGuildConfig(ctx.guild.id, "modRole", "guildRoles")
    role = ctx.guild.get_role(roleId)

    return role in ctx.author.roles or await check_guild_permissions(
        ctx, {"manage_guild": True}
    )


async def isModOrPerms(ctx, perms, check=all):
    return await isMod(ctx) or await check_guild_permissions(ctx, perms, check=check)


async def check_permissions(ctx, perms, *, check=all):
    is_owner = await ctx.bot.is_owner(ctx.author)
    if is_owner:
        return True

    resolved = ctx.channel.permissions_for(ctx.author)
    return check(
        getattr(resolved, name, None) == value for name, value in perms.items()
    )


def has_permissions(*, check=all, **perms):
    async def pred(ctx):
        return await check_permissions(ctx, perms, check=check)

    return commands.check(pred)


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


def has_guild_permissions(*, check=all, **perms):
    async def pred(ctx):
        return await check_guild_permissions(ctx, perms, check=check)

    return commands.check(pred)


# Is mod, is admin thingy


def guildOnly():
    def predicate(ctx):
        if not ctx.guild:
            raise NotInGuild from None
        return True

    return commands.check(predicate)


def is_botmaster():
    def predicate(ctx):
        return ctx.author.id in ctx.bot.master

    return commands.check(predicate)


def is_mod():
    async def pred(ctx):
        return await isMod(ctx)

    return commands.check(pred)


def is_admin():
    async def pred(ctx):
        return await check_guild_permissions(ctx, {"administrator": True})

    return commands.check(pred)


def mod_or_permissions(**perms):
    async def predicate(ctx):
        return await isModOrPerms(ctx, perms, check=any)

    return commands.check(predicate)


def admin_or_permissions(**perms):
    perms["administrator"] = True

    async def predicate(ctx):
        return await check_guild_permissions(ctx, perms, check=any)

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
