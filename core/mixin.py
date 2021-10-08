from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from core.bot import ziBot


class CogMixin:
    """Mixin for Cogs/Exts."""

    icon = "❓"
    cc = False

    def __init__(self, bot: ziBot) -> None:
        self.bot: ziBot = bot

    # @property
    # def db(self) -> Database:
    #     return self.bot.db
