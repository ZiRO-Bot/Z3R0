class CogMixin:
    """Mixin for Cogs/Exts."""
    def __init__(self, bot):
        self.bot = bot
        self.db = self.bot.db
