from discord.ext import commands

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


def has_guild_permissions(*, check=all, **perms):
    async def predicate(ctx):
        return await check_guild_permissions(ctx, perms, check=check)

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

        return role in ctx.author.roles or await has_guild_permissions(
            manage_guild=True
        ).predicate(ctx)

    return commands.check(predicate)


def mod_or_permissions(**perms):
    async def predicate(ctx):
        orig = await is_mod().predicate(ctx)
        return orig or await has_guild_permissions(**perms).predicate(ctx)

    return commands.check(predicate)


async def isMod(ctx):
    return await is_mod().predicate(ctx)


async def isModOrPerms(ctx, perms, check=all):
    return await mod_or_permissions(**perms).predicate(ctx)


def is_admin():
    async def predicate(ctx):
        return await has_guild_permissions(administrator=True).predicate(ctx)

    return commands.check(predicate)


def admin_or_permissions(**perms):
    async def predicate(ctx):
        orig = await is_admin().predicate(ctx)
        return orig or await has_guild_permissions(**perms, check=any).predicate(ctx)

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
