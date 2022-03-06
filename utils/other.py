from __future__ import annotations, division

import datetime as dt
import json
import math
import operator
import os
import uuid
from decimal import Decimal
from html.parser import HTMLParser
from typing import Any, Dict, Optional, Tuple

import discord
from pyparsing import (
    CaselessKeyword,
    Forward,
    Group,
    Literal,
    Regex,
    Suppress,
    Word,
    alphanums,
    alphas,
    delimitedList,
)
from tortoise.functions import Max

from core import db


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
        # point = Literal(".")

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

        fn_call = (ident + lpar - Group(expr_list) + rpar).setParseAction(insert_fn_argcount_tuple)
        atom = (
            addop[...]
            + ((fn_call | pi | phi | e | tau | fnumber | ident).setParseAction(self.pushFirst) | Group(lpar + expr + rpar))
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
        self.bnf.parseString(num_string, parseAll)
        val = self.evaluateStack(self.exprStack[:])
        return val


async def reactsToMessage(message: discord.Message, reactions: list = []):
    """Simple loop to react to a message."""
    for reaction in reactions:
        try:
            await message.add_reaction(reaction)
        except discord.Forbidden:
            # Don't have perms to do reaction
            continue


class JSON(dict):
    __slots__ = ("filename", "data")

    def __init__(self, filename: str, default: Dict[Any, Any] = {}) -> None:
        self.filename: str = filename

        data: Dict[Any, Any] = default or {}

        try:
            f = open(filename, "r")
            data = json.loads(f.read())
        except FileNotFoundError:
            with open(filename, "w+") as f:
                json.dump(data, f, indent=4)

        super().__init__(data)

    def __repl__(self):
        return f"<JSON: data={self.items}>"

    def dump(self, indent: int = 4, **kwargs):
        temp = "{}-{}.tmp".format(uuid.uuid4(), self.filename)
        with open(temp, "w") as tmp:
            json.dump(self.copy(), tmp, indent=indent, **kwargs)

        os.replace(temp, self.filename)
        return True


class Blacklist(JSON):
    def __init__(self, filename: str = "blacklist.json"):
        super().__init__(filename)

    @property
    def guilds(self):
        return self.get("guilds", [])

    @property
    def users(self):
        return self.get("users", [])

    def __repl__(self):
        return f"<Blacklist: guilds={self.guilds} users={self.users}>"

    def append(self, key: Any, value: Any, **kwargs) -> Any:
        val: list = self.get(key, [])
        val.append(value)
        self.update({key: val})

        self.dump(**kwargs)
        return value

    def remove(self, key: Any, value: Any, **kwargs) -> Any:
        val: list = self.get(key, [])
        val.remove(value)
        self.update({key: val})

        self.dump(**kwargs)
        return value


def utcnow():
    # utcnow but timezone aware
    return dt.datetime.now(dt.timezone.utc)


def parseCodeBlock(string: str) -> Tuple[str, str]:
    # Removes ```py\n```
    if string.startswith("```") and string.endswith("```"):
        LString = string[3:-3].split("\n")
        if LString[0].endswith(" "):
            lang = "py"
            code = LString
        else:
            lang = LString[0]
            code = LString[1:]
        return lang, "\n".join(code)

    # Removes `foo`
    return "py", string.strip("` \n")


def boolFromString(string: str) -> bool:
    lowered = string.lower()
    if lowered in ("yes", "y", "true", "t", "1", "enable", "on"):
        return True
    elif lowered in ("no", "n", "false", "f", "0", "disable", "off"):
        return False
    raise ValueError("Invalid Input")


MORSE_CODE_DICT = {
    "A": ".-",
    "B": "-...",
    "C": "-.-.",
    "D": "-..",
    "E": ".",
    "F": "..-.",
    "G": "--.",
    "H": "....",
    "I": "..",
    "J": ".---",
    "K": "-.-",
    "L": ".-..",
    "M": "--",
    "N": "-.",
    "O": "---",
    "P": ".--.",
    "Q": "--.-",
    "R": ".-.",
    "S": "...",
    "T": "-",
    "U": "..-",
    "V": "...-",
    "W": ".--",
    "X": "-..-",
    "Y": "-.--",
    "Z": "--..",
    "1": ".----",
    "2": "..---",
    "3": "...--",
    "4": "....-",
    "5": ".....",
    "6": "-....",
    "7": "--...",
    "8": "---..",
    "9": "----.",
    "0": "-----",
    ".": ".-.-.-",
    ", ": "--..--",
    "?": "..--..",
    "'": ".----.",
    "!": "-.-.--",
    "/": "-..-.",
    "-": "-....-",
    "@": ".--.-.",
    "(": "-.--.",
    ")": "-.--.-",
    " ": "/",
}


def encodeMorse(msg):
    morse = ""
    for letter in msg:
        morse += MORSE_CODE_DICT[letter.upper()] + " "
    return morse


def decodeMorse(msg):
    msg = msg.replace("/ ", " ") + " "
    temp = ""
    decoded = ""
    for code in msg:
        if code not in [".", "-", "/", " "] and code.upper() in list(MORSE_CODE_DICT.keys()):
            return None
        if code != " ":
            i = 0
            temp += code
        else:
            i += 1  # type: ignore
            if i == 2:
                decoded += " "
            else:
                decoded += list(MORSE_CODE_DICT.keys())[list(MORSE_CODE_DICT.values()).index(temp)]
                temp = ""
    return decoded


async def doCaselog(
    bot,
    *,
    guildId: int,
    type: str,
    modId: int,
    targetId: int,
    reason: str,
) -> Optional[int]:
    q = await db.CaseLog.filter(guild_id=guildId).annotate(caseNum=Max("caseId")).first()
    caseNum = (q.caseNum or 0) + 1  # type: ignore

    if caseNum:
        await db.CaseLog.create(
            caseId=caseNum,
            guild_id=guildId,
            type=type,
            modId=modId,
            targetId=targetId,
            reason=reason,
            createdAt=utcnow(),
        )
        return int(caseNum)


TAG_IN_MD = {
    "a": "",
    "b": "**",
    "br": "\n",
}

TAG_ALIASES = {
    "bold": "b",
}


class Markdownify(HTMLParser):
    result = ""

    def feed(self, feed: str) -> str:
        self.result = ""
        super().feed(feed)
        return self.result

    def parse_md(self, tag):
        tag = TAG_ALIASES.get(tag, tag)
        return TAG_IN_MD.get(tag, tag)

    def handle_tag(self, tag):
        self.result += self.parse_md(tag)

    def handle_starttag(self, tag, attrs):
        self.handle_tag(tag)

    def handle_endtag(self, tag):
        self.handle_tag(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_tag(tag)

    def handle_data(self, data):
        self.result += data


async def authorOrReferenced(ctx):
    if ref := ctx.replied_reference:
        # Get referenced message author
        # if user reply to a message while doing this command
        return ref.cached_message.author if ref.cached_message else (await ctx.fetch_message(ref.message_id)).author
    return ctx.author


def isNsfw(channel) -> bool:
    try:
        return channel.is_nsfw()
    except AttributeError:  # Mark DMs as NSFW channel
        return isinstance(channel, discord.DMChannel)


async def getGuildRole(bot, guildId: int, roleType: str):
    return await bot.getGuildConfig(guildId, roleType, "GuildRoles")


async def setGuildRole(bot, guildId: int, roleType: str, roleId: Optional[int]):
    return await bot.setGuildConfig(guildId, roleType, roleId, "GuildRoles")


if __name__ == "__main__":
    # For testing
    # print(encodeMorse("test 123"))
    # print(decodeMorse("... --- ..."))
    test = JSON("test.json")
    test["test"] = "hello"
    print(test)
    test.dump()
