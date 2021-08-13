from typing import Any

from discord import Interaction
from discord.ui import View


class ZView(View):
    """Base class for ziBot's view"""

    def __init__(self, owner=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.owner = owner

    async def on_check_failed(self, interaction: Interaction, *args, **kwargs) -> Any:
        """Just incase i need to replace failed check response"""
        if owner := self.owner:
            await interaction.response.send_message(
                f"This interaction belongs to {owner.mention}", ephemeral=True
            )

    async def interaction_check(self, interaction: Interaction) -> bool:
        owner = self.owner
        if not owner:
            return True

        # Prevent other user other than interaction owner using this interaction
        if interaction.user.id != owner.id:
            await self.on_check_failed(interaction)
            return False
        return True
