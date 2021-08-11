from typing import Optional

from discord import Interaction
from discord.ui import View

from core.context import Context


class ZView(View):
    """Base class for ziBot's view"""

    def __init__(
        self, ctx: Optional[Context] = None, *, ownerOnly: bool = True, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.context: Optional[Context] = ctx
        self._ownerOnly: bool = ownerOnly

    async def interaction_check(self, interaction: Interaction) -> bool:
        ctx = self.context
        if not ctx or not self._ownerOnly:
            return True

        # Prevent other user other than interaction owner using this interaction
        owner = ctx.author
        if interaction.user.id != owner.id:
            await interaction.response.send_message(
                f"This interaction belongs to {owner.mention}", ephemeral=True
            )
            return False
        return True
