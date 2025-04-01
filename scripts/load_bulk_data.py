import ijson
import os
import asyncio
from app.db import AsyncSessionLocal
from app.models import ScryfallCard
from sqlalchemy import text

BULK_DATA_PATH = "app/cache/scryfall/all-cards.json"  # Path to the downloaded JSON


# This function will handle the upsert into the database
async def upsert_bulk_data():
    # Check if file exists
    if not os.path.exists(BULK_DATA_PATH):
        print(f"❌ File does not exist: {BULK_DATA_PATH}")
        return

    # Open the JSON file for streaming parsing
    with open(BULK_DATA_PATH, "r", encoding="utf-8") as f:
        print(f"✅ File opened: {BULK_DATA_PATH}")

        # Initialize the session for database transactions
        async with AsyncSessionLocal() as session:
            # Parse the JSON file incrementally
            parser = ijson.items(f, "item")
            total_cards = 0
            batch_size = 500  # Number of records to insert in one batch
            batch = []

            # Loop through each card in the stream
            for card in parser:
                total_cards += 1
                print(f"Processing card {total_cards}: {card.get('name')}")

                # Prepare data for insertion
                card_values = {
                    "scryfall_id": card.get("id"),
                    "name": card.get("name"),
                    "set_name": card.get("set_name"),
                    "image_url": card.get("image_uris", {}).get("large", None),
                    "mana_cost": card.get("mana_cost"),
                    "mana_value": card.get("cmc"),
                    # Ensure types is a list of strings, defaulting to empty list if not available
                    "types": (
                        card.get("type_line", "").split(" — ")[0].split()
                        if card.get("type_line")
                        else []
                    ),
                    # Ensure legality is a list of strings, defaulting to empty list if not available
                    "legality": (
                        [
                            fmt
                            for fmt, status in card.get("legalities", {}).items()
                            if status == "legal"
                        ]
                        if card.get("legalities")
                        else []
                    ),
                    "power": card.get("power"),
                    "toughness": card.get("toughness"),
                }

                # Make sure that types and legality are JSON arrays (list of strings)
                if isinstance(
                    card_values["types"], str
                ):  # if types is somehow a string, convert to a list
                    card_values["types"] = [card_values["types"]]

                if isinstance(
                    card_values["legality"], str
                ):  # if legality is a string, convert to a list
                    card_values["legality"] = [card_values["legality"]]

                batch.append(card_values)

                # Once the batch reaches the defined size, insert into the database
                if len(batch) >= batch_size:
                    sql = """
                    INSERT INTO scryfall_cards (scryfall_id, name, set_name, image_url, mana_cost, mana_value, types, power, toughness, legality)
                    VALUES (:scryfall_id, :name, :set_name, :image_url, :mana_cost, :mana_value, :types, :power, :toughness, :legality)
                    ON CONFLICT (scryfall_id) DO UPDATE
                    SET name = EXCLUDED.name,
                        set_name = EXCLUDED.set_name,
                        image_url = EXCLUDED.image_url,
                        mana_cost = EXCLUDED.mana_cost,
                        mana_value = EXCLUDED.mana_value,
                        types = EXCLUDED.types,
                        power = EXCLUDED.power,
                        toughness = EXCLUDED.toughness,
                        legality = EXCLUDED.legality;
                    """
                    try:
                        result = await session.execute(text(sql), batch)
                        await session.commit()
                        print(
                            f"Processed {total_cards} cards, {result.rowcount} rows affected."
                        )
                    except Exception as e:
                        print(f"Error during bulk upsert: {e}")
                        await session.rollback()  # Ensure we don't keep partial results
                    batch = []  # Reset the batch after insertion

            # If there are any remaining records in the batch, insert them
            if batch:
                sql = """
                INSERT INTO scryfall_cards (scryfall_id, name, set_name, image_url, mana_cost, mana_value, types, power, toughness, legality)
                VALUES (:scryfall_id, :name, :set_name, :image_url, :mana_cost, :mana_value, :types, :power, :toughness, :legality)
                ON CONFLICT (scryfall_id) DO UPDATE
                SET name = EXCLUDED.name,
                    set_name = EXCLUDED.set_name,
                    image_url = EXCLUDED.image_url,
                    mana_cost = EXCLUDED.mana_cost,
                    mana_value = EXCLUDED.mana_value,
                    types = EXCLUDED.types,
                    power = EXCLUDED.power,
                    toughness = EXCLUDED.toughness,
                    legality = EXCLUDED.legality;
                """
                try:
                    result = await session.execute(text(sql), batch)
                    await session.commit()
                    print(
                        f"Processed {total_cards} cards, {result.rowcount} rows affected."
                    )
                except Exception as e:
                    print(f"Error during bulk upsert: {e}")
                    await session.rollback()

            print(f"✅ Bulk upsert of {total_cards} cards completed.")


# Run the bulk data upsert
if __name__ == "__main__":
    asyncio.run(upsert_bulk_data())
