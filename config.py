# API and HTTP settings
TIMEOUT = 30
MAX_CONCURRENT_REQUESTS = 5
RATE_LIMIT_DELAY = 0.5  # in seconds

# URLs
SELLERS_PAGE_URL = "https://bdvtrading.com/top-sellers/"
STORE_SEARCH_BASE = "https://bdvtrading.com/store"

# HTTP Headers and Cookies for requests
HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en,he;q=0.9",
    "DNT": "1",
    "Priority": "u=1, i",
    "Sec-CH-UA": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
}
