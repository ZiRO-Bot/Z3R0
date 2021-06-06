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
        "description",
        "category",
        "content",
        "aliases",
        "url",
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

        self.description = kwargs.pop("description", None) or "No description."
        self.content = kwargs.pop("content", "NULL")
        self.category = category
        self.aliases = kwargs.pop("aliases", [])

    def __str__(self):
        return self.name


