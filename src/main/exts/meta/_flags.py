"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import List

from discord.ext import commands

from ...core.flags import StringAndFlags


class HelpFlags(StringAndFlags, case_insensitive=True):
    filters: List[str] = commands.flag(name="filter", aliases=["filters", "filt"], default=[])


class CmdManagerFlags(StringAndFlags, case_insensitive=True):
    built_in: bool = commands.flag(name="built-in", default=False)
    custom: bool = False
    category: bool = commands.flag(aliases=["cat"], default=False)
