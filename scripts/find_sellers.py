import asyncio
import httpx
from bs4 import BeautifulSoup
from app.db import AsyncSessionLocal
from app.models import Seller
from sqlalchemy import select
from tqdm import tqdm

from config import (
    SELLERS_PAGE_URL,
    TIMEOUT,
    RATE_LIMIT_DELAY
)

SESSION = httpx.AsyncClient()


async def fetch_sellers():
    """Fetch the seller page, extract sellers' names and URLs, and handle pagination."""
    sellers = []
    page_number = 1
    has_more_pages = True

    while has_more_pages:
        try:
            print(f"Fetching sellers from page {page_number}...")
            response = await SESSION.get(
                f"{SELLERS_PAGE_URL}?page={page_number}", timeout=TIMEOUT
            )
            response.raise_for_status()  # Raise an error for bad responses

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract seller names from <div class="seller-content">
            seller_elements = soup.find_all("div", class_="seller-content")
            print(
                f"Found {len(seller_elements)} seller elements on page {page_number}."
            )
            for seller in seller_elements:
                seller_name_tag = seller.find("h5")
                if seller_name_tag:
                    seller_name = seller_name_tag.get_text(strip=True)
                    # Construct store URL based on seller name (spaces replaced by hyphens)
                    store_url = (
                        f"https://bdvtrading.com/store/{seller_name.replace(' ', '-')}"
                    )
                    sellers.append({"name": seller_name, "store_url": store_url})
                else:
                    print(f"Error: Missing name for seller: {seller}. Skipping.")

            print(
                f"Total sellers collected so far: {len(sellers)} on page {page_number}."
            )

            # Check if there's another page using the pagination block
            pagination = soup.find("ul", class_="pagination")
            next_page_button = (
                pagination.find("a", string=lambda t: t and t.strip().lower() == "next")
                if pagination
                else None
            )
            if next_page_button:
                page_number += 1  # Next page exists, move to the next one
            else:
                has_more_pages = False  # No next page, stop the loop

            await asyncio.sleep(RATE_LIMIT_DELAY)  # Asynchronous rate limiting

        except httpx.RequestError as e:
            print(f"Error fetching seller list: {e}")
            with open("error_log.txt", "a") as f:
                f.write(f"Error fetching seller list: {e}\n")
            has_more_pages = False
        except Exception as e:
            print(f"Unexpected error: {e}")
            with open("error_log.txt", "a") as f:
                f.write(f"Unexpected error: {e}\n")
            has_more_pages = False

    # Once we have all the sellers, upsert them into the database
    await upsert_sellers_into_db(sellers)


async def upsert_sellers_into_db(sellers):
    """Upsert the sellers into the sellers table by checking for existing records."""
    async with AsyncSessionLocal() as session:
        for seller in sellers:
            # Check if a seller with the same name already exists
            result = await session.execute(
                select(Seller).filter_by(name=seller["name"])
            )
            existing_seller = result.scalars().first()
            if existing_seller:
                # Optionally update the store_url if it has changed
                if existing_seller.store_url != seller["store_url"]:
                    existing_seller.store_url = seller["store_url"]
            else:
                # If the seller does not exist, add a new record
                db_seller = Seller(name=seller["name"], store_url=seller["store_url"])
                session.add(db_seller)
        await session.commit()
        print(f"Upserted {len(sellers)} sellers into the database.")


async def main():
    """Main function to fetch sellers."""
    await fetch_sellers()


if __name__ == "__main__":
    asyncio.run(main())
