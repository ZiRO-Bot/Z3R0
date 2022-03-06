"""Collection of Object."""


# import sqlite3


# class Connection(sqlite3.Connection):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.execute("pragma journal_mode=wal")
#         self.execute("pragma foreign_keys=ON")
#         self.isolation_level = None
#         self.row_factory = sqlite3.Row
