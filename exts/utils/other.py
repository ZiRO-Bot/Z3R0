from __future__ import division
from decimal import Decimal
from discord.ext import commands
from exts.utils.format import ZEmbed
from pyparsing import (
    Literal,
    Word,
    Group,
    Forward,
    alphas,
    alphanums,
    Regex,
    ParseException,
    CaselessKeyword,
    Suppress,
    delimitedList,
)
from typing import Union


import argparse
import datetime as dt
import discord
import json
import math
import operator


PHI = (1 + math.sqrt(5)) / 2


class NumericStringParser(object):
    """
    Most of this code comes from the fourFn.py pyparsing example by Paul McGuire

    http://pyparsing.wikispaces.com/file/view/fourFn.py
    http://pyparsing.wikispaces.com/message/view/home/15549426
    """

    def pushFirst(self, toks):
        self.exprStack.append(toks[0])

    def pushUMinus(self, toks):
        if toks and toks[0] == "-":
            self.exprStack.append("unary -")

    def __init__(self):
        """
        expop   :: '^' | '**'
        multop  :: '*' | '/' | '%'
        addop   :: '+' | '-'
        integer :: ['+' | '-'] '0'..'9'+
        atom    :: PI | E | real | fn '(' expr ')' | '(' expr ')'
        factor  :: atom [ expop factor ]*
        term    :: factor [ multop factor ]*
        expr    :: term [ addop term ]*
        """
        point = Literal(".")

        e = CaselessKeyword("E")
        pi = CaselessKeyword("PI")
        phi = CaselessKeyword("PHI")
        tau = CaselessKeyword("TAU")

        # fnumber = Combine(
        #     Word("+-" + nums, nums)
        #     + Optional(point + Optional(Word(nums)))
        #     + Optional(e + Word("+-" + nums, nums))
        # )
        fnumber = Regex(r"[+-]?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?")
        ident = Word(alphas, alphanums + "_$")

        plus, minus, mult, div, mod = map(Literal, "+-*/%")
        lpar, rpar = map(Suppress, "()")
        addop = plus | minus
        multop = mult | div | mod
        expop = Literal("^") | Literal("**")

        expr = Forward()
        expr_list = delimitedList(Group(expr))
        # add parse action that replaces the function identifier with a (name, number of args) tuple
        def insert_fn_argcount_tuple(t):
            fn = t.pop(0)
            num_args = len(t[0])
            t.insert(0, (fn, num_args))

        fn_call = (ident + lpar - Group(expr_list) + rpar).setParseAction(
            insert_fn_argcount_tuple
        )
        atom = (
            addop[...]
            + (
                (fn_call | pi | phi | e | tau | fnumber | ident).setParseAction(
                    self.pushFirst
                )
                | Group(lpar + expr + rpar)
            )
        ).setParseAction(self.pushUMinus)

        # by defining exponentiation as "atom [ ^ factor ]..." instead of
        # "atom [ ^ atom ]...", we get right-to-left exponents, instead of left-to-right
        # that is, 2^3^2 = 2^(3^2), not (2^3)^2.
        factor = Forward()
        factor <<= atom + (expop + factor).setParseAction(self.pushFirst)[...]
        term = factor + (multop + factor).setParseAction(self.pushFirst)[...]
        expr <<= term + (addop + term).setParseAction(self.pushFirst)[...]

        self.bnf = expr

        # map operator symbols to corresponding arithmetic operations
        epsilon = 1e-12
        self.opn = {
            "+": operator.add,
            "-": operator.sub,
            "*": operator.mul,
            "/": operator.truediv,
            "%": operator.mod,
            "^": operator.pow,
            "**": operator.pow,
        }
        self.fn = {
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "atan": math.atan,
            "exp": math.exp,
            "abs": abs,
            "trunc": int,
            "round": round,
            "sgn": lambda a: -1 if a < -epsilon else 1 if a > epsilon else 0,
            "sqrt": math.sqrt,
            "floor": math.floor,
            "fact": math.factorial,
            # functionsl with multiple arguments
            "multiply": lambda a, b: a * b,
            "hypot": math.hypot,
            # functions with a variable number of arguments
            "all": lambda *a: all(a),
        }

    def evaluateStack(self, s):
        op, num_args = s.pop(), 0
        if isinstance(op, tuple):
            op, num_args = op

        if op == "unary -":
            return -self.evaluateStack(s)
        if op in self.opn:
            op2 = self.evaluateStack(s)
            op1 = self.evaluateStack(s)
            return self.opn[op](op1, op2)
        elif op == "PI":
            return math.pi  # 3.1415926535
        elif op == "E":
            return math.e  # 2.718281828
        elif op == "PHI":
            return PHI
        elif op == "TAU":
            return math.tau
        elif op in self.fn:
            # note: args are pushed onto the stack in reverse order
            args = reversed([self.evaluateStack(s) for _ in range(num_args)])
            return self.fn[op](*args)
        elif op[0].isalpha():
            return 0
        else:
            return Decimal(op)

    def eval(self, num_string, parseAll=True):
        self.exprStack = []
        results = self.bnf.parseString(num_string, parseAll)
        val = self.evaluateStack(self.exprStack[:])
        return val


async def reactsToMessage(message: discord.Message, reactions: list = []):
    """Simple loop to react to a message."""
    for reaction in reactions:
        try:
            await message.add_reaction(reaction)
        except:
            # Probably don't have perms to do reaction
            continue


async def logAction(bot, actionType: str, *args, **kwargs):
    """For case log (ban, kick, possibly warn) and purgatory."""
    e = ZEmbed(timestamp=dt.datetime.now(dt.timezone.utc))

    if actionType.startswith("msg"):
        if actionType == "msgEdit":
            before, after = args

            guildId = before.guild.id

            e.title = "Edited Message"

            e.set_author(name=before.author, icon_url=before.author.avatar_url)

            e.add_field(
                name="Before",
                value=before.content[:1020] + " ..."
                if len(before.content) > 1024
                else before.content,
            )
            e.add_field(
                name="After",
                value=after.content[:1020] + " ..."
                if len(after.content) > 1024
                else after.content,
            )

            if before.embeds:
                data = before.embeds[0]
                if data.type == "image" and not self.is_url_spoiler(
                    before.content, data.url
                ):
                    e.set_image(url=data.url)

            if before.attachments:
                _file = before.attachments[0]
                spoiler = _file.is_spoiler()
                if not spoiler and _file.url.lower().endswith(
                    ("png", "jpeg", "jpg", "gif", "webp")
                ):
                    e.set_image(url=_file.url)
                elif spoiler:
                    e.add_field(
                        name="📎 Attachment",
                        value=f"||[{_file.filename}]({_file.url})||",
                        inline=False,
                    )
                else:
                    e.add_field(
                        name="📎 Attachment",
                        value=f"[{_file.filename}]({_file.url})",
                        inline=False,
                    )

        if actionType == "msgDel":
            (message,) = args

            guildId = message.guild.id

            e.title = "Deleted Message"

            e.set_author(name=message.author, icon_url=message.author.avatar_url)

            e.description = (
                message.content[:1020] + " ..."
                if len(message.content) > 1024
                else message.content
            )

        logCh = bot.get_channel(await bot.getGuildConfig(guildId, "purgatoryCh"))
        if not logCh:
            return

        return await logCh.send(embed=e)


class ArgumentError(commands.CommandError):
    """Error class for ArgumentParser"""

    def __init__(self, message):
        super().__init__(discord.escape_mentions(message))


class ArgumentParser(argparse.ArgumentParser):
    """Argument parser that don't exit on error"""

    def __init__(self, *args, add_help=False, **kwargs):
        super().__init__(*args, add_help=add_help, **kwargs)

    def error(self, message):
        raise ArgumentError(message)


class Blacklist:
    __slots__ = ("filename", "guilds", "users")

    def __init__(self, filename: str = "blacklist.json"):
        self.filename = filename

        data = {}

        try:
            f = open(filename, "r")
            data = json.loads(f.read())
        except FileNotFoundError:
            with open(filename, "w+") as f:
                json.dump(data, f, indent=4)

        self.guilds = data.get("guilds", [])
        self.users = data.get("users", [])

    def __repl__(self):
        return f"<Blacklist: guilds:{self.guilds} users:{self.users}>"

    def dump(self, indent: int = 4, **kwargs):
        temp = "{}-{}.tmp".format(uuid.uuid4(), self.filename)
        data = {"guilds": self.guilds, "users": self.users}
        with open(temp, "w") as tmp:
            json.dump(data.copy(), tmp, indent=indent, **kwargs)

        os.replace(temp, self.filename)
        return True

    def append(self, key: str, value: int, **kwargs):
        """Add users/guilds to the blacklist"""
        _type = getattr(self, key)
        if value in _type:
            return

        _type.append(value)

        self.dump(**kwargs)
        return value

    def remove(self, key: str, value: int, **kwargs):
        _type = getattr(self, key)
        if value not in _type:
            return

        _type.remove(value)

        self.dump(**kwargs)
        return value


if __name__ == "__main__":
    # For testing
    print(NumericStringParser().eval("63**57") > 2147483647)
