from discord import Interaction
from discord.ui import View


class ZView(View):
    """Base class for ziBot's view"""

    def __init__(self, owner=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.owner = owner

    async def interaction_check(self, interaction: Interaction) -> bool:
        owner = self.owner
        if not owner:
            return True

        # Prevent other user other than interaction owner using this interaction
        if interaction.user.id != owner.id:
            await interaction.response.send_message(
                f"This interaction belongs to {owner.mention}", ephemeral=True
            )
            return False
        return True
