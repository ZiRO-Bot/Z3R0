"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import TagScriptEngine as tse
from discord.ext import commands

from ....core.mixin import CogMixin
from ....utils import tseBlocks
from ....utils.cache import CacheListProperty, CacheUniqueViolation


if TYPE_CHECKING:
    from core.bot import ziBot


class MetaCustomCommands(commands.Cog, CogMixin):
    """Meta subcog for custom commands"""

    # TODO - Complete this

    def __init__(self, bot: ziBot):
        super().__init__(bot)

        # Cache for disabled commands
        self.bot.cache.add(
            "disabled",
            cls=CacheListProperty,
            unique=True,
        )

        # TSE stuff
        blocks = [
            tse.AssignmentBlock(),
            tse.EmbedBlock(),
            tse.LooseVariableGetterBlock(),
            tse.RedirectBlock(),
            tse.RequireBlock(),
            tseBlocks.RandomBlock(),
            tseBlocks.ReactBlock(),
            tseBlocks.ReactUBlock(),
            tseBlocks.SilentBlock(),
        ]
        self.engine = tse.Interpreter(blocks)
