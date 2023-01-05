from tortoise import fields
from tortoise.models import Model


""" - WARNING: BREAKING CHANGES -----
- Due to how tortoise works, relation fields will have automatically use
  snake_case, for e.g.:

    guild.id -> commandsLookup.guild_id

- Rename commands_lookup -> commandsLookup to be more consistent

- Datetime columns now uses DatetimeField, which translated to:
  MySQL = DateTime, PostgreSQL = DateTime, SQLite = NUMERIC (timestamp)

  And will actually returns datetime.datetime instead of timestamp (no need to
  do datetime.fromtimestamp) when fetched.

  NOTE: Old datetime (which saved as timestamp) will need to be converted to
  new format in order to get the correct timezone, unless your server's time is
  set to UTC

----- Less breaking changes -----
- Every table now have id column, tortoise require every table to have
  atleast 1 primary key

- Timer's JSON column now uses JSONField from Tortoise,
  which translated to: MySQL = JSON, PostgreSQL = JsonB, SQLite = TEXT
"""


class Guilds(Model):
    id = fields.BigIntField(pk=True, generated=False)


class ContainsGuildId:
    # guild_id
    guild = fields.ForeignKeyField("models.Guilds", to_field="id")


class Timer(Model):
    id = fields.BigIntField(pk=True)
    event = fields.TextField()
    extra = fields.JSONField()  # {"args": ..., "kwargs": ...}
    expires = fields.DatetimeField()
    created = fields.DatetimeField()
    owner = fields.BigIntField(pk=False, generated=False)


class Commands(Model):
    id = fields.BigIntField(pk=True)
    type = fields.TextField()
    name = fields.TextField()
    category = fields.TextField(default="unsorted")
    description = fields.TextField(null=True)
    content = fields.TextField()
    url = fields.TextField(null=True)
    uses = fields.BigIntField(pk=False, generated=False, default=0)
    ownerId = fields.BigIntField(pk=False, generated=False)
    createdAt = fields.DatetimeField()
    visibility = fields.BooleanField(default=False)  # public or private
    enabled = fields.BooleanField(default=True)


class CommandsLookup(ContainsGuildId, Model):
    # cmd_id
    cmd = fields.ForeignKeyField("models.Commands", related_name="cmd", to_field="id")
    name = fields.TextField()  # alias name

    class Meta:
        table = "commandsLookup"


class Disabled(ContainsGuildId, Model):
    command = fields.TextField()


class Prefixes(ContainsGuildId, Model):
    prefix = fields.TextField()


class GuildConfigs(ContainsGuildId, Model):
    ccMode = fields.IntField(pk=False, generated=False, default=0)
    tagMode = fields.IntField(pk=False, generated=False, default=0)  # currently unused
    welcomeMsg = fields.TextField(null=True)
    farewellMsg = fields.TextField(null=True)

    class Meta:
        table = "guildConfigs"


class GuildChannels(ContainsGuildId, Model):
    welcomeCh = fields.BigIntField(pk=False, generated=False, null=True)
    farewellCh = fields.BigIntField(pk=False, generated=False, null=True)
    modlogCh = fields.BigIntField(pk=False, generated=False, null=True)
    purgatoryCh = fields.BigIntField(pk=False, generated=False, null=True)
    announcementCh = fields.BigIntField(pk=False, generated=False, null=True)

    class Meta:
        table = "guildChannels"


class GuildRoles(ContainsGuildId, Model):
    modRole = fields.BigIntField(pk=False, generated=False, null=True)
    mutedRole = fields.BigIntField(pk=False, generated=False, null=True)
    autoRole = fields.BigIntField(pk=False, generated=False, null=True)

    class Meta:
        table = "guildRoles"


class GuildMutes(ContainsGuildId, Model):
    mutedId = fields.BigIntField(pk=False, generated=False)

    class Meta:
        table = "guildMutes"


class CaseLog(ContainsGuildId, Model):
    caseId = fields.BigIntField(pk=False, generated=False)
    type = fields.TextField()
    modId = fields.BigIntField(pk=False, generated=False)
    targetId = fields.BigIntField(pk=False, generated=False)
    reason = fields.TextField()
    createdAt = fields.DatetimeField()

    class Meta:
        table = "caseLog"
