"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

searchQuery = """
    query(
        $name: String
        $format: MediaFormat
        $page: Int
        $perPage: Int=5
        $type: MediaType
    ) {
        Page(perPage:$perPage, page:$page) {
            pageInfo{hasNextPage, currentPage, lastPage}
            media(search:$name, type:$type, format:$format){
                type
                id
                format
                title {
                    romaji
                    english
                }
                episodes
                chapters
                duration
                status
                startDate {
                    year
                    month
                    day
                }
                endDate {
                    year
                    month
                    day
                }
                genres
                coverImage {
                    large
                }
                bannerImage
                description
                averageScore
                studios { nodes { name } }
                seasonYear
                externalLinks {
                    site
                    url
                }
                isAdult
                siteUrl
            }
        }
    }
"""
