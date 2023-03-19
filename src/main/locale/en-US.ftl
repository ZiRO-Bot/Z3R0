# --- Test
test = Hello World!
var = Hello, { $name }!

# --- Admin
welcome = welcome
welcome-desc = Set welcome message and/or channel
farewell = farewell
farewell-desc = Set farewell message and/or channel
modlog = modlog
modlog-desc = Set modlog channel
purgatory = purgatory
purgatory-desc = Set purgatory channel
role = role
role-desc = Manage guild's role
role-create = create
role-create-desc = Create a new role
role-set = set
role-set-desc = Turn regular role into special role
role-types = types
role-types-desc = Show all special role types
announcement = announcement
announcement-desc = Set announcement channel

# --- Info
color = color
color-desc = Get color information from hex value

# --- Meta
stats = stats
stats-desc = Information about my stats
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
