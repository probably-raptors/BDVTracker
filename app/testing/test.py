import os
import requests
import time
import json
import random

# -- Config
CACHE_DIR = "cache/global_pages"
os.makedirs(CACHE_DIR, exist_ok=True)

BASE_URL = "https://bdvtrading.com/mtg/"
PARAMS_TEMPLATE = (
    "game_type=1&card_name=&set_name=&card_type=&subtype=&oracle_text=&"
    "card_language=&rarity=&foil=&min_price=&max_price=&in_stock=on&page={}"
)

COOKIES = {
    "csrftoken": "...",
    "sessionid": "...",
    "_ga": "...",
    "messages": "...",
    "_ga_EGM8VK13RC": "...",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://bdvtrading.com/mtg/",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}


# -- Throttle settings
def polite_sleep(base=1.2, jitter=0.8):
    time.sleep(base + random.uniform(0, jitter))


# -- Cache helpers
def cache_file_path(page):
    return os.path.join(CACHE_DIR, f"page_{page}.json")


def is_cached(page):
    return os.path.exists(cache_file_path(page))


def save_cache(page, data):
    with open(cache_file_path(page), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_cache(page):
    with open(cache_file_path(page), "r", encoding="utf-8") as f:
        return json.load(f)


# -- Main logic
def scrape_all_cards(start_page=1, max_pages=1000):
    page = start_page
    total = 0

    while page <= max_pages:
        print(f"🔎 Page {page}...")

        if is_cached(page):
            print(f"📦 Using cached page {page}")
            data = load_cache(page)
        else:
            url = BASE_URL + "?" + PARAMS_TEMPLATE.format(page)
            response = requests.get(url, headers=HEADERS, cookies=COOKIES)

            if response.status_code == 429:
                print("🚫 Rate limited — sleeping 10s")
                time.sleep(10)
                continue

            response.raise_for_status()
            data = response.json()

            save_cache(page, data)
            polite_sleep()

        results = data.get("results", [])
        if not results:
            print("✅ No more listings — done.")
            break

        print(f"   🧾 {len(results)} cards found.")
        total += len(results)
        page += 1

    print(f"\n🎯 Total cards scraped: {total}")


if __name__ == "__main__":
    scrape_all_cards()
