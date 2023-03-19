# --- Test
test = Hello World!
var = Hello, { $name }!

# --- Admin
# - Welcome
welcome = welcome
welcome-desc = Set welcome message and/or channel
welcome-arg-channel = Channel where welcome messages will be sent
welcome-arg-raw = Get current welcome message in raw mode (Useful for editing, other options is ignored when used!)
welcome-arg-disable = Disable welcome event
welcome-arg-message = Message that will be sent to the welcome channel
# - Farewell
farewell = farewell
farewell-desc = Set farewell message and/or channel
farewell-arg-channel = Channel where farewell messages will be sent
farewell-arg-raw = Get current farewell message in raw mode (Useful for editing, other options is ignored when used!)
farewell-arg-disable = Disable farewell event
farewell-arg-message = Message that will be sent to the farewell channel
# - Modlog
modlog = modlog
modlog-desc = Set modlog channel
modlog-arg-channel = Channel where modlogs will be sent
modlog-arg-disable = Disable modlog
# - Purgatory
purgatory = purgatory
purgatory-desc = Set purgatory channel
purgatory-arg-channel = Channel where deleted/edited messages will be sent
purgatory-arg-disable = Disable purgatory
# - Role
role = role
role-desc = Manage guild's role
role-create = create
role-create-desc = Create a new role
role-set = set
role-set-desc = Turn regular role into special role
role-types = types
role-types-desc = Show all special role types
# - Announcement
announcement = announcement
announcement-desc = Set announcement channel
announcement-arg-channel = Channel where announcements will be sent

# --- AniList
# - Anime
anime-desc = Get an anime's information
anime-search = search
anime-search-desc = Search for an anime on AniList
anime-search-arg-name = The anime's name
anime-search-arg-format = The anime's format
anime-random = random
anime-random-desc = Get a random anime
# - Manga
manga-desc = Get a manga's information
manga-search = search
manga-search-desc = Search for a manga on AniList
manga-search-arg-name = The manga's name
manga-search-arg-format = The manga's format
manga-random = random
manga-random-desc = Get a random manga

# --- Fun
meme = meme
meme-desc = Get random meme from reddit
findseed = findseed
findseed-desc = Get your Minecraft seed's eye count
httpcat = httpcat
httpcat-desc = Get http status code with cat in it
pp = pp
pp-desc = Show your pp size
isimpostor = isimpostor
isimpostor-desc = Check if you're an impostor or a crewmate
dadjokes = dadjokes
dadjokes-desc = Get random dad jokes
rps = rps
rps-desc = Rock Paper Scissors with the bot
flip = flip
flip-desc = Flip a Coin
barter = barter
barter-desc = Barter with Minecraft's Piglins

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
