import asyncio
import httpx
import json
import os
from bs4 import BeautifulSoup
from datetime import datetime
from sqlalchemy import select, text
from app.db import AsyncSessionLocal
from app.models import Seller, Card

from config import (
    TIMEOUT,
    MAX_CONCURRENT_REQUESTS,
    HEADERS
)


async def fetch_store_page(seller_name, store_url, page):
    """Submit a search request for a seller's store and return the JSON response."""
    search_url = (
        f"{store_url}/search/json/?"
        f"page={page}&game_type=Magic%20the%20Gathering&search=&set_name_search=&min_price=&max_price="
        f"&sort_by_price=&sort_new_to_old=&condition=&foil=&rarity=&special_editions="
    )
    # Set Referer dynamically
    headers = HEADERS.copy()
    headers["Referer"] = store_url + "/"

    async with httpx.AsyncClient(
        timeout=TIMEOUT, headers=headers
    ) as client:
        response = await client.get(search_url)
        response.raise_for_status()
        return response.json()


def parse_listing_html(html):
    """Parse the HTML (from the 'html' key) and extract listing details."""
    soup = BeautifulSoup(html, "html.parser")
    listings = []
    product_cards = soup.find_all(
        "div", class_="product-card"
    )  # adjust selector as needed
    for card in product_cards:
        try:
            card_link = card.find("a", class_="card-link")
            card_name = card_link.get_text(strip=True) if card_link else None
            detail_url = (
                card_link["href"] if card_link and card_link.has_attr("href") else None
            )

            quantity_span = card.find(
                "span", id=lambda x: x and x.startswith("product-quantity-")
            )
            bdv_listing_id = None
            if quantity_span and "id" in quantity_span.attrs:
                id_parts = quantity_span["id"].split("-")
                if id_parts and len(id_parts) >= 3:
                    bdv_listing_id = int(id_parts[-1])

            price_div = card.find("div", class_="price")
            price_text = price_div.get_text(strip=True) if price_div else ""
            price = float(price_text.replace("$", "")) if price_text else None

            quantity_text = quantity_span.get_text(strip=True) if quantity_span else "0"
            quantity = int(quantity_text)

            condition_div = card.find("div", class_="condition")
            condition = condition_div.get_text(strip=True) if condition_div else "N/A"

            language_div = card.find("div", class_="language")
            language = "unknown"
            if language_div:
                flag_icon = language_div.find("i")
                if flag_icon and flag_icon.has_attr("class"):
                    for cls in flag_icon["class"]:
                        if cls.startswith("flag-icon-"):
                            language = cls.replace("flag-icon-", "")
                            break

            listings.append(
                {
                    "bdv_listing_id": bdv_listing_id,
                    "card_name": card_name,
                    "detail_url": detail_url,
                    "price": price,
                    "quantity": quantity,
                    "condition": condition,
                    "language": language,
                    "foil": False,  # Default to False unless specified otherwise
                }
            )
        except Exception as e:
            print(f"Error parsing a product card: {e}")
    return listings


def has_next_page(pagination_html):
    """Parse pagination HTML and return True if a 'Next' link exists."""
    soup = BeautifulSoup(pagination_html, "html.parser")
    next_link = soup.find("a", string=lambda s: s and s.strip().lower() == "next")
    return next_link is not None


async def process_store_for_seller(seller, semaphore):
    """
    For a given seller, paginate through the search results,
    extract listing details, and upsert listings into the database.
    """
    seller_name = seller["name"]
    store_url = seller["store_url"]
    page = 1
    all_listings = []

    while True:
        async with semaphore:
            try:
                print(f"Fetching {seller_name} page {page}...")
                json_response = await fetch_store_page(seller_name, store_url, page)
            except Exception as e:
                print(f"Error fetching {seller_name} page {page}: {e}")
                break

        # Save raw JSON response for debugging
        log_path = os.path.join(
            "app/cache/sellers", f"{seller_name}_page_{page}_response.json"
        )
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(json_response, f, ensure_ascii=False, indent=4)
        print(f"Saved raw response for {seller_name} page {page}.")

        html_content = json_response.get("html", "")
        pagination_html = json_response.get("pagination_html", "")
        listings = parse_listing_html(html_content)
        if listings:
            print(f"Found {len(listings)} listings on {seller_name} page {page}.")
            all_listings.extend(listings)
        else:
            print(f"No listings found on {seller_name} page {page}.")
            break

        if has_next_page(pagination_html):
            page += 1
        else:
            break

    if all_listings:
        await upsert_listings(seller_name, all_listings)
    else:
        print(f"No listings to insert for {seller_name}.")


async def get_card_by_name(card_name):
    """Retrieve the card object from the database by name."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Card).filter_by(name=card_name))
        return result.scalars().first()


async def upsert_listings(seller_name, listings):
    """Upsert listings into the database."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Seller).filter_by(name=seller_name))
        seller_obj = result.scalars().first()
        if not seller_obj:
            print(f"Seller {seller_name} not found in the database.")
            return

        batch = []
        for listing in listings:
            card = await get_card_by_name(listing["card_name"])
            if not card:
                print(f"Card '{listing['card_name']}' not found; skipping listing.")
                continue
            batch.append(
                {
                    "bdv_listing_id": listing["bdv_listing_id"],
                    "seller_id": seller_obj.id,
                    "card_id": card.id,
                    "price": listing["price"],
                    "quantity": listing["quantity"],
                    "condition": listing["condition"],
                    "foil": listing["foil"],
                    "language": listing["language"],
                    "last_seen": datetime.utcnow(),
                }
            )

        if not batch:
            print(f"No valid listings to insert for {seller_name}.")
            return

        sql = """
        INSERT INTO listings (bdv_listing_id, seller_id, card_id, price, quantity, condition, foil, language, last_seen)
        VALUES (:bdv_listing_id, :seller_id, :card_id, :price, :quantity, :condition, :foil, :language, :last_seen)
        ON CONFLICT (bdv_listing_id) DO UPDATE
        SET price = EXCLUDED.price,
            quantity = EXCLUDED.quantity,
            condition = EXCLUDED.condition,
            foil = EXCLUDED.foil,
            language = EXCLUDED.language,
            last_seen = EXCLUDED.last_seen;
        """
        try:
            result = await session.execute(text(sql), batch)
            await session.commit()
            print(f"Upserted {result.rowcount} listings for seller {seller_name}.")
        except Exception as e:
            print(f"Error during listings upsert for {seller_name}: {e}")
            await session.rollback()


async def main():
    # Retrieve sellers from the database.
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Seller))
        sellers = [
            {"name": s.name, "store_url": s.store_url} for s in result.scalars().all()
        ]

    # Create a semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    tasks = [
        asyncio.create_task(process_store_for_seller(seller, semaphore))
        for seller in sellers
    ]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
