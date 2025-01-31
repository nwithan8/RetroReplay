# RetroReplay

Highlight your Plex media that originally aired in the past during the current week or month.

![](https://i.imgur.com/akwExaK.png)

To be used with Kometa.

Inspired by https://github.com/InsertDisc/pattrmm.

## How to use

Create `config.yml`:

```
libraries:
  Movies:
    imdb_min_rating: 70
    imdb_min_votes: 50000
    range: week  # can be "day", "week", "month
    starting_year: 1990
    tmdb_list_id: 12345  # Create a list in your profile then copy the ID here
  TV Shows:
    imdb_min_rating: 70
    imdb_min_votes: 50000
    range: week  # can be "day", "week", "month
    starting_year: 2000
    tmdb_list_id: 12345  # Create a list in your profile then copy the ID here
mdblist:
  api_key: abc123  # Required
plex:
  token: abc123  # Required
  url: https://1234.com  # Required
tmdb:
  access_token: reallylongstring  # Get from https://www.themoviedb.org/settings/api
  api_key: abc123  # Get from https://www.themoviedb.org/settings/api
```
