# --- Test
test = Hello World!
var = Hello, { $name }!

# --- Terms
-channel =
    { $case ->
        [uppercase] Channel
        *[lowercase] channel
    }
-status =
    { $case ->
        [uppercase] Status
        *[lowercase] status
    }
-disabled =
    { $case ->
        [uppercase] Disabled
        *[lowercase] disabled
    }
-modlog =
    { $case ->
        [uppercase] Modlog
        *[lowercase] modlog
    }
-purgatory =
    { $case ->
        [uppercase] Purgatory
        *[lowercase] purgatory
    }

# --- Admin
# - Welcome
welcome = welcome
welcome-desc = Set welcome message and/or { -channel }
welcome-arg-channel = { -channel(case: "uppercase") } where welcome messages will be sent
welcome-arg-raw = Get current welcome message in raw mode (Useful for editing, other options is ignored when used!)
welcome-arg-disable = Disable welcome event
welcome-arg-message = Message that will be sent to the welcome { -channel }
# - Farewell
farewell = farewell
farewell-desc = Set farewell message and/or { -channel }
farewell-arg-channel = { -channel(case: "uppercase") } where farewell messages will be sent
farewell-arg-raw = Get current farewell message in raw mode (Useful for editing, other options is ignored when used!)
farewell-arg-disable = Disable farewell event
farewell-arg-message = Message that will be sent to the farewell { -channel }
# - Modlog
modlog = modlog
modlog-desc = Set modlog { -channel }
modlog-arg-channel = { -channel(case: "uppercase") } where modlogs will be sent
modlog-arg-disable = Disable modlog
# - Purgatory
purgatory = purgatory
purgatory-desc = Set purgatory { -channel }
purgatory-arg-channel = { -channel(case: "uppercase") } where deleted/edited messages will be sent
purgatory-arg-disable = Disable purgatory
# - Log (Modlog and Purgatory)
log-updated-title =
    { $type ->
        [modlog] { -modlog(case: "uppercase" }
        *[other] { -purgatory(case: "uppercase") }
    } config has been updated
log-updated-field-channel = { -channel(case: "uppercase") }
log-updated-field-status = { -status(case: "uppercase") }
log-updated-field-status-disabled = { -disabled(case: "uppercase") }
# config
log-config-title =
    { $guildName }'s { $type ->
        [modlog] { -modlog }
        *[other] { -purgatory }
    } current configuration
log-config-field-channel = { -channel(case: "uppercase") }
log-config-field-status = { -status(case: "uppercase") }
log-config-field-status-disabled = { -disabled(case: "uppercase") }
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
announcement-desc = Set announcement { -channel }
announcement-arg-channel = { -channel(case: "uppercase") } where announcements will be sent

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
weather = weather
weather-desc = Get current weather for specific city
color = color
color-desc = Get color information from hex value
jisho = jisho
jisho-desc = Get japanese text/word
serverinfo = serverinfo
serverinfo-desc = Get guild's information
spotify-desc = Show what song a member listening to in Spotify
pypi-desc = Get information of a python project from pypi

# --- Meta
source = source
source-desc = Get link to my source code
about = about
about-desc = Information about me
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

ping = ping
ping-desc = Get bot's response time
invite = invite
invite-desc = Get bot's invite link

# - Other
success = Success
loading = Loading...

# - Error
error-generic = Something went wrong!

# --- NSFW
hentai = hentai
hentai-desc = Get hentai images from nekos.fun

# --- Timer
time = time
time-desc = Get current time

# --- Utilities
calc = calc
calc-desc = Simple math evaluator
morse = morse
morse-desc = Encode a text into morse code
unmorse = unmorse
unmorse-desc = Decode a morse code
search = search
search-desc = Search the Internet
realurl = realurl
realurl-desc = Get shorten url's real url. No more rick roll!
realurl-arg-shorten-url = shorten-url
