import discord

from discord.ext import commands
from TagScriptEngine import Interpreter, adapter
from TagScriptEngine.interface import Block
from typing import Optional
import random


class DiscordGuildBlock(Block):
    def __init__(
        self, guild: discord.Guild, context: discord.ext.commands.Context = None
    ):
        self.guild = guild
        self.context = context

    def will_accept(self, ctx: Interpreter.Context) -> bool:
        dec = ctx.verb.declaration.lower()
        return any([dec == "server", dec == "guild"])

    def process(self, ctx: Interpreter.Context) -> Optional[str]:
        if ctx.verb.parameter is None:
            return str(self.guild.name)

        param = ctx.verb.parameter.lower()

        if param == "bots":
            return str(len([x for x in self.guild.members if x.bot]))

        if param == "humans":
            return str(len([x for x in self.guild.members if not x.bot]))

        if param == "random":
            return str(random.choice(self.guild.members))

        # supported parameters
        supported = [
            "id",
            "name",
            "humans",
            "owner",
            "roles",
            "channels",
        ]

        _len_only = [
            "members",
            "roles",
            "channels",
        ]

        _format = "{0.%s}"
        _len_format = "{len(0.%s)}"
        # if parameter provided is not supported it will use name by default
        final = (_format if param not in _len_only else _len_format) % (
            param if param in supported else "name"
        )
        final = final.format(self.guild)
        return final


class DiscordMemberBlock(Block):
    def __init__(self, member: discord.Member, context: commands.Context = None):
        self.member = member
        self.context = context

    def will_accept(self, ctx: Interpreter.Context) -> bool:
        dec = ctx.verb.declaration.lower()
        return any([dec == "user", dec == "mention"])

    def process(self, ctx: Interpreter.Context) -> Optional[str]:
        if ctx.verb.declaration.lower() == "mention":
            return self.member.mention

        if ctx.verb.parameter is None:
            return str(self.member.name)

        param = ctx.verb.parameter.lower()

        if param == "proper":
            return str(self.member)

        # supported parameters
        supported = [
            "id",
            "nick",
            "name",
            "mention",
        ]

        _format = "{0.%s}"
        # if parameter provided is not supported it will use name by default
        final = _format % (param if param in supported else "name")
        final = final.format(self.member)
        return final


class RandomBlock(Block):
    def will_accept(self, ctx: Interpreter.Context) -> bool:
        dec = ctx.verb.declaration.lower()
        return any([dec == "random", dec == "#", dec == "rand"])

    def weighted_random(self, pairs, seed=None):
        total = sum(pair[0] for pair in pairs)
        if seed:
            random.seed(seed)
        r = random.randint(1, total)
        for (weight, value) in pairs:
            r -= weight
            if r <= 0:
                return value

    def process(self, ctx: Interpreter.Context) -> Optional[str]:
        if ctx.verb.payload is None:
            return None
        spl = []
        if "~" in ctx.verb.payload:
            spl = ctx.verb.payload.split("~")
        else:
            spl = ctx.verb.payload.split(",")

        tmp, spl = spl, []
        for i in tmp:
            pre = i.split("|")

            # Convert weight to int if possible
            try:
                pre[0] = int(pre[0])
                if pre[0] < 0 and len(pre) > 1:
                    pre[0] = None
            except ValueError:
                if len(pre) > 1:
                    pre[0] = None

            if len(pre) > 1 and isinstance(pre[0], int):
                spl.append((pre[0], str(pre[1])))
            elif len(pre) > 1:
                spl.append((1, str(i)))
            else:
                spl.append((1, str(pre[0])))

        random.seed(ctx.verb.parameter)

        result = self.weighted_random(spl, ctx.verb.parameter)
        return result
