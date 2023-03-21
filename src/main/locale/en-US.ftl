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
-error =
    { $case ->
       *[uppercase] Error
        [lowercase] error
        [capital] ERROR
    }
-error-title-prefix = { -error(case: "capital") }:
-success =
    { $case ->
       *[uppercase] Success
        [lowercase] success
        [capital] SUCCESS
    }
-success-title-prefix = { -success(case: "capital") }:

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
role-types-title = Role Types
role-types-desc = Show all special role types
role-types-list = Available role type: { $roleTypes }
role-types-footer = This list also includes aliases! (e.g. 'mod' -> 'moderator')
# role action
role-mute-updated = Mute role has been set to { $roleName }
role-mute-updated-with-reason = Mute role has been set to { $roleName } by { $creatorName }
role-created = { -success-title-prefix } Role has been created
role-modified = { -success-title-prefix } Role has been modified
role-properties =
    {"**"}Name{"**"}: { $roleName }
    {"**"}Type{"**"}: `{ $roleType }`
    {"**"}ID{"**"}: `{ $roleId }`
role-manage-failed-reason = Invalid role type!
# - Announcement
announcement = announcement
announcement-desc = Set announcement { -channel }
announcement-arg-channel = { -channel(case: "uppercase") } where announcements will be sent
announcement-updated = Announcement { -channel } has been updated
announcement-updated-channel = **{ -channel(case: "uppercase") }**: { $channelMention }

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
anilist-search-name-empty =
    You need to specify the name of the { $type ->
       *[ANIME] anime
        [MANGA] manga
    }!
anilist-search-no-result = No { $type } called `{ $name }` found.
anilist-search-no-result-title = { -error-title-prefix } No result
anilist-hidden-description =
    {"... **"}+{ $count }{"**"} hidden
    (click { $emoji } to read more)
anilist-format = Format
anilist-duration = Duration
anilist-episodes = Episode
anilist-chapters = Chapters
anilist-status = Status
anilist-date-start = Start Date
anilist-date-end = End Date
anilist-genres = Genres
anilist-unknown = Unknown
anilist-streaming-sites = Streaming Sites

# --- Fun
meme = meme
meme-desc = Get random meme from reddit
meme-score = Score
meme-comments = Comments
findseed = findseed
findseed-desc = Get your Minecraft seed's eye count
findseed-result = findseed - Your seed is a { $eyeCount ->
        [one] **{ $eyeCount }** eye
       *[other] **{ $eyeCount }** eyes
    }
findseed-result-classic = <@{ $userId }> -> Your seed is a { $eyeCount ->
        [one] **{ $eyeCount }** eye
       *[other] **{ $eyeCount }** eyes
    }
httpcat = httpcat
httpcat-desc = Get http status code with cat in it
pp = pp
pp-desc = Show your pp size
pp-result = Your pp looks like this:
isimpostor = isimpostor
isimpostor-desc = Check if you're an impostor or a crewmate
isimpostor-impostor-count-set = Impostor count has been set to `1`
isimpostor-result-impostor = { $user }, you're an impostor!
isimpostor-result-crewmate = { $user }, you're a crewmate!
dadjokes = dadjokes
dadjokes-desc = Get random dad jokes
rps = rps
rps-desc = Rock Paper Scissors with the bot
rps-rock = Rock wins!
rps-paper = Paper wins!
rps-scissors = Scissors wins!
rps-noob = Noob wins!
rps-tie = It's a Tie!
rps-result =
    You choose ***{ $userChoice }***. I chose ***{ $botChoice }***.
    { $result }
flip = flip
flip-desc = Flip a Coin
flip-result = You got { $side }!
barter = barter
barter-desc = Barter with Minecraft's Piglins
barter-result-title = Bartering with { $goldCount ->
        [one] { $goldCount } gold
       *[other] { $goldCount } golds
    }
barter-result = You got:

    { $barterResult }

# --- Info
weather = weather
weather-desc = Get current weather for specific city
weather-api-error = { -error-title-prefix } OpenWeather's API Key is not set! Please contact the bot owner to solve this issue.
weather-temperature = Temperature
weather-temperature-feel = Feels like { $tempFeels }°C, { $detail }
weather-humidity = Humidity
weather-wind = Wind
color = color
color-desc = Get color information from hex value
color-error = { -error-title-prefix } Invalid color value!
color-title = Information on #{ $hexValue }
color-hex = Hex
color-rgb = RGB
jisho = jisho
jisho-desc = Get japanese text/word
jisho-error = Sorry, couldn't find any words matching `{ $words }`
serverinfo = serverinfo
serverinfo-desc = Get guild's information
serverinfo-properties-title = General
serverinfo-properties =
    {"**"}Name{"**"}: { $guildName }
    {"**"}ID{"**"}: `{ $guildId }`
    {"**"}Created At{"**"}: { $createdAt } ({ $createdAtRelative })
    {"**"}Owner{"**"}: { $guildOwner } / { $ownerMention }
    {"**"}Owner ID{"**"}: { $ownerId }
serverinfo-stats-title = Stats
serverinfo-stats =
    {"**"}Categories{"**"}: { $categoryCount }
    {"**"}Channels{"**"}: { $channelCount }
    { $otherChannels }
    {"**"}Member Count{"**"}: { $memberCount } ({ $humanCount } humans | { $botCount} bots)
    { $memberStatus }
    {"**"}Boosts{"**"}: { $boostCount } (Lv. { $boostLevel })
    {"**"}Role Count{"**"}: { $roleCount }
serverinfo-settings-title = Settings
serverinfo-settings =
    {"**"}Verification Level{"**"}: `{ $verificationLevel }`
    {"**"}Two-Factor Auth{"**"}: { $mfaLevel ->
        [one] On
       *[other] Off
    }
spotify-desc = Show what song a member listening to in Spotify
spotify-error = { $user } is not listening to Spotify!
spotify-artist = Artist
spotify-album = Album
spotify-duration = Duration
pypi-desc = Get information of a python project from pypi
pypi-error-title = 404 - Page Not Found
pypi-error = We looked everywhere but couldn't find that project
pypi-author-title = Author Info
pypi-author =
    {"**"}Name{"**"}: { $author }
    {"**"}Email{"**"}: { $authorEmail }
pypi-package-title = Package Info
pypi-package =
    {"**"}Version{"**"}: `{ $version }`
    {"**"}License{"**"}: { $license }
    {"**"}Keywords{"**"}: { $keywords }
pypi-links-title = Links
pypi-links =
    {"["}Home Page{"]"}({ $homePage })
    {"["}Project Link{"]"}({ $projectUrl })
    {"["}Release Link{"]"}({ $releaseUrl })
    {"["}Download Link{"]"}({ $downloadUrl })

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
success = { -success }
loading = Loading...
no-description = No description
unknown = Unknown
not-provided = Not provided
not-specified = Not specified

# - Error
error-generic = { -error-title-prefix } Something went wrong!

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
