"""Collection of Object."""


import sqlite3


class Connection(sqlite3.Connection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.execute('pragma foreign_keys=1')


class CustomCommand:
    """Object for custom command."""

    __slots__ = (
        "id",
        "type",
        "name",
        "invokedName",
        "brief",
        "description",
        "help",
        "category",
        "content",
        "aliases",
        "url",
        "uses",
        "owner",
        "enabled",
    )

    def __init__(self, id, name, category, **kwargs):
        self.id = id
        # NOTE: Can be 'text' or 'imported'
        # - text: using text and not imported from pastebin/gist
        # - imported: imported from pastebin/gist
        self.type = kwargs.pop("type", "text")
        # Will always return None unless type == 'imported'
        self.url = kwargs.pop("url", None)

        self.name = name
        # Incase its invoked using its alias
        self.invokedName = kwargs.pop("invokedName", name)

        # TODO: Add "brief"
        self.brief = None
        self.description = kwargs.pop("description", None)
        self.help = self.description
        self.content = kwargs.pop("content", "NULL")
        self.category = category
        self.aliases = kwargs.pop("aliases", [])
        self.uses = kwargs.pop("uses", -1)
        self.owner = kwargs.pop("owner", None)
        self.enabled = kwargs.pop("enabled", True)

    def __str__(self):
        return self.name


