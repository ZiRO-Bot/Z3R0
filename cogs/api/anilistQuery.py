"""
List of query for anilist API

Retrieved from 3.0.R branch
"""

scheduleQuery = """
query($page: Int = 0, $amount: Int = 50, $watched: [Int!]!, $nextDay: Int!) {
  Page(page: $page, perPage: $amount) {
    pageInfo {
      currentPage
      hasNextPage
    }
    airingSchedules(notYetAired: true, mediaId_in: $watched, sort: TIME, airingAt_lesser: $nextDay) {
      media {
        id
        siteUrl
        format
        duration
        episodes
        title {
          romaji
        }
        coverImage {
          large
          color
        }
        externalLinks {
          site
          url
        }
        studios(isMain: true) {
          edges {
            isMain
            node {
              name
            }
          }
        }
        isAdult
      }
      episode
      airingAt
      timeUntilAiring
      id
    }
  }
}
"""

searchAni = """
query($name:String,$aniformat:MediaFormat,$page:Int,$amount:Int=5){
    Page(perPage:$amount,page:$page){
        pageInfo{hasNextPage, currentPage, lastPage}
        media(search:$name,type:ANIME,format:$aniformat){
            id,
            format,
            title {
                romaji, 
                english
            }, 
            episodes, 
            duration,
            status, 
            startDate {
                year, 
                month, 
                day
            }, 
            endDate {
                year, 
                month, 
                day
            }, 
            genres, 
            coverImage {
                large
            }, 
            bannerImage,
            description, 
            averageScore, 
            studios{nodes{name}}, 
            seasonYear, 
            externalLinks {
                site, 
                url
            },
            isAdult
        }
    } 
}
"""

animeBasicInfo = """
query($mediaId: Int){
    Media(id:$mediaId, type:ANIME){
        id,
        format,
        title {romaji},
        coverImage {large},
        isAdult
    }
}
"""

animeInfo = """
query($mediaId: Int){
    Media(id:$mediaId, type:ANIME){
        id,
        format,
        title {
            romaji, 
            english
        }, 
        episodes, 
        duration,
        status, 
        startDate {
            year, 
            month, 
            day
        }, 
        endDate {
            year, 
            month, 
            day
        }, 
        genres, 
        coverImage {
            large
        }, 
        bannerImage,
        description, 
        averageScore, 
        studios{nodes{name}}, 
        seasonYear, 
        externalLinks {
            site, 
            url
        },
        isAdult
    }
}
"""

# Backwards compatibility
generalQ = animeInfo

listQ = """
query($page: Int = 0, $amount: Int = 50, $mediaId: [Int!]!) {
  Page(page: $page, perPage: $amount) {
    pageInfo {
      currentPage
      hasNextPage
    }
    media(id_in: $mediaId, type:ANIME){
        id,
        title {
            romaji,
            english
        },
        siteUrl,
        nextAiringEpisode {
            episode,
            airingAt,
            timeUntilAiring
        }
    }
  }
}
"""

defaultWithGenre = """
query($title:String,$genre:MediaFormat,$page:Int,$amount:Int=5){
    Page(perPage:$amount,page:$page){
        pageInfo{hasNextPage, currentPage, lastPage}
        media(search:$title,type:ANIME,format:$genre){
            id,
            format,
            title {
                romaji, 
                english
            }, 
            episodes, 
            duration,
            status, 
            startDate {
                year, 
                month, 
                day
            }, 
            endDate {
                year, 
                month, 
                day
            }, 
            genres, 
            coverImage {
                large
            }, 
            bannerImage,
            description, 
            averageScore, 
            studios{nodes{name}}, 
            seasonYear, 
            externalLinks {
                site, 
                url
            },
            isAdult
        }
    } 
}
"""

default = """
query($title:String,$page:Int,$amount:Int=5){
    Page(perPage:$amount,page:$page){
        pageInfo{hasNextPage, currentPage, lastPage}
        media(search:$title,type:ANIME){
            id,
            format,
            title {
                romaji, 
                english
            }, 
            episodes, 
            duration,
            status, 
            startDate {
                year, 
                month, 
                day
            }, 
            endDate {
                year, 
                month, 
                day
            }, 
            genres, 
            coverImage {
                large
            }, 
            bannerImage,
            description, 
            averageScore, 
            studios{nodes{name}}, 
            seasonYear, 
            externalLinks {
                site, 
                url
            },
            isAdult
        }
    } 
}
"""
