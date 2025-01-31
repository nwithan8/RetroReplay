import argparse
from datetime import datetime, timedelta
import os
import time
from urllib3.util.retry import Retry

from plexapi.server import PlexServer
import requests
from requests.adapters import HTTPAdapter
from tmdbapis import TMDbAPIs
import yaml

# Constants
MDBLIST_BASE_URL = "https://api.mdblist.com"
CONFIG_FILE = os.getenv("CONFIG_FILE", default='config.yml')

def run():
    # Record start time
    start_time = datetime.now()

    # Load configuration
    with open(CONFIG_FILE, 'r') as file:
        config = yaml.safe_load(file)

    # Initialize TMDb client
    tmdb_config = config['tmdb']
    tmdb = TMDbAPIs(tmdb_config['api_key'], v4_access_token=tmdb_config.get('authenticated_token') or tmdb_config.get('access_token'))

    if not tmdb_config.get('authenticated_token'):
        print("No authenticated token found. Starting TMDb authentication.")
        print(tmdb.v4_authenticate())
        input("Navigate to the URL and then hit enter when Authenticated")
        tmdb.v4_approved()
        tmdb_config['authenticated_token'] = tmdb.v4_access_token
        with open(CONFIG_FILE, "w") as f:
            yaml.dump(config, f)
        print("Authenticated token saved to config.yml")
    else:
        print("Authenticated token loaded from file.")


    # Initialize Plex client
    plex = PlexServer(config['plex']['url'], config['plex']['token'])


    def make_request_with_retry(url, method="POST", data=None, headers=None):
        """Makes a request with retry policy for 5xx errors, supporting GET and POST."""

        retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504], allowed_methods=["GET", "POST"])
        adapter = HTTPAdapter(max_retries=retries)
        http = requests.Session()
        http.mount("https://", adapter)

        try:
            if method.upper() == "POST":
                response = http.post(url, data=data, headers=headers)
            elif method.upper() == "GET":
                response = http.get(url, params=data, headers=headers)
            else:
                raise ValueError("Invalid HTTP method. Must be 'GET' or 'POST'.")

            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Request failed after multiple retries: {e}")
            return None


    def should_include_media(mdblist_type, tmdb_id, imdb_min_rating, imdb_min_votes):
        """Determines if media should be included based on IMDb ratings."""

        headers = {'Content-Type': 'application/json'}
        url = f'{MDBLIST_BASE_URL}/tmdb/{mdblist_type}/{tmdb_id}?apikey={config["mdblist"]["api_key"]}'
        response = make_request_with_retry(url, method="GET", headers=headers)

        if not response:
            return False

        imdb_rating = next((r for r in response.get('ratings', []) if r["source"] == "imdb"), None)

        if not imdb_rating:
            return False

        score = imdb_rating.get('score')
        votes = imdb_rating.get('votes')

        if score is None or votes is None:
            return False

        return score >= imdb_min_rating or votes >= imdb_min_votes # Modified condition to OR

    # Check MDBList API limits (only once)
    limits = make_request_with_retry(f'{MDBLIST_BASE_URL}/user?apikey={config["mdblist"]["api_key"]}', method="GET", headers={'Content-Type': 'application/json'})
    print(f'MDBList API limits = {limits}')


    for library_name, library_config in config["libraries"].items():
        print(f"\n============================\nWorking on library {library_name}")

        today = datetime.now()
        date_range_type = library_config.get("range", "day")  # Default to "day"

        if date_range_type == 'week':
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
        elif date_range_type == 'month':
            start_date = today.replace(day=1)
            end_date = (start_date.replace(month=start_date.month + 1, day=1) - timedelta(days=1)) if start_date.month < 12 else start_date.replace(day=31)
        else: # Day or other invalid value
            start_date = today
            end_date = today

        print(f'Date range: {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}')

        candidate_date_ranges = []
        for year in range(library_config["starting_year"], today.year + 1): # Use today.year
            year_start = datetime(year, start_date.month, start_date.day)
            year_end = datetime(year, end_date.month, end_date.day)

            if year_start <= year_end:
                candidate_date_ranges.append((year_start.strftime('%Y-%m-%d'), year_end.strftime('%Y-%m-%d')))

        plex_library = plex.library.section(library_name)
        media_type = plex_library.type  # Use plex_library.type directly

        mdblist_type = 'show' if media_type == 'show' else 'movie'
        tmdb_type = "tv" if media_type == 'show' else "movie"


        tmdb_list = tmdb.list(library_config["tmdb_list_id"])
        print(f'Clearing list {library_config["tmdb_list_id"]}')
        tmdb_list.clear()

        for search_start, search_end in candidate_date_ranges:
            print(f'\nSearching between {search_start} and {search_end}')
            search_results = plex_library.search(filters={"originallyAvailableAt>>": [search_start], "originallyAvailableAt<<": [search_end]})
            print(f'Found {len(search_results)} items in range')

            tmdb_payload = []
            for item in search_results:  # More descriptive variable name
                for guid in item.guids:
                    if guid.id.startswith("tmdb://"):
                        tmdb_id = guid.id[7:]
                        if should_include_media(mdblist_type, tmdb_id, library_config["imdb_min_rating"], library_config["imdb_min_votes"]):
                            tmdb_payload.append((tmdb_id, tmdb_type))

            tmdb_list.add_items(items=tmdb_payload)
            print(f'Added {len(tmdb_payload)} items to list {library_config["tmdb_list_id"]}')

    # Calculate and print elapsed time
    end_time = datetime.now()
    elapsed_time = end_time - start_time

    hours, remainder = divmod(int(elapsed_time.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)

    print(f"\nScript execution time: {hours} hours, {minutes} minutes, {seconds} seconds")


parser = argparse.ArgumentParser()
parser.add_argument("--run", action="store_true")
parser.parse_args()
args = parser.parse_args()

if args.run is True:
    run()
else:
    run_at = os.getenv("RUN_AT", default="02:00")
    dtime_24hour = time.strptime(run_at, "%H:%M")
    dtime_12hour = time.strftime( "%I:%M %p", dtime_24hour )
    print(f"It's {time.strftime('%I:%M %p')}. Waiting for next run at {str(dtime_12hour)}")
    while True:
        if run_at == time.strftime('%I:%M %p'):
            run()
            print(f"It's {time.strftime('%I:%M %p')}. Waiting for next run at {str(dtime_12hour)}")
            time.sleep(60)
        else:
            time.sleep(20)
