# --- Test
test = Hello World!
var = Hello, { $name }!

# --- Slash
stats = stats
stats-desc = Information about my stats

# --- Meta
stats-title = { $bot }'s stats
stats-uptime-title = 🕙 | Uptime

stats-command-title = <:terminal:852787866554859591> | Command Usage (This session)
stats-command =
    { $commandCount ->
        [one] { $commandCount } command
       *[other] { $commandCount } commands
    } ({ $customCommand ->
        [one] { $customCommand } custom command
       *[other] { $customCommand } custom commands
    })

prefix-empty = Prefix can't be empty!
prefix-added = Prefix `{ $prefix }` has been added!
prefix-removed = Prefix `{ $prefix }` has been removed!

# - Other
success = Success
loading = Loading...

# - Error
error-generic = Something went wrong!
