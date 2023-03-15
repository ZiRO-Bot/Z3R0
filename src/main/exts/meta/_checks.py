"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

from discord.ext import commands

from ...core import checks
from ...core.context import Context
from ...core.guild import CCMode
from ._custom_command import checks
from ._errors import CCommandNoPerm


def hasCCPriviledge():
    async def predicate(ctx: Context):
        """Check for custom command's modes."""
        # 0: Only mods,
        # 1: Partial (Can add but only able to manage their own command),
        # 2: Full (Anarchy mode)
        mode = await ctx.requireGuild().getCCMode()
        isMod = await checks.isMod(ctx)
        hasPriviledge = isMod if mode == CCMode.MOD_ONLY else True
        if not hasPriviledge:
            raise CCommandNoPerm
        return hasPriviledge

    return commands.check(predicate)
