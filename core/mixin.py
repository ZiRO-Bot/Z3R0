class CogMixin:
    """Mixin for Cogs/Exts."""
    def __init__(self, bot):
        self.bot = bot

    @property
    def db(self):
        return self.bot.db
