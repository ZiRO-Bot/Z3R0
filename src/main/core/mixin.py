"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .bot import ziBot


class CogMixin:
    """Mixin for Cogs/Exts."""

    icon = "❓"
    cc = False

    def __init__(self, bot: ziBot) -> None:
        self.bot: ziBot = bot

    # @property
    # def db(self) -> Database:
    #     return self.bot.db
