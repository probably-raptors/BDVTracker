import ijson
import os
import asyncio
import uuid
from app.db import AsyncSessionLocal
from app.models import Card
from sqlalchemy import text
from tqdm import tqdm
import json

BULK_DATA_PATH = "app/cache/scryfall/all-cards.json"  # Path to the downloaded JSON


async def upsert_bulk_data():
    # Check if file exists
    if not os.path.exists(BULK_DATA_PATH):
        print(f"❌ File does not exist: {BULK_DATA_PATH}")
        return

    with open(BULK_DATA_PATH, "r", encoding="utf-8") as f:
        print(f"✅ File opened: {BULK_DATA_PATH}")

        async with AsyncSessionLocal() as session:
            parser = ijson.items(f, "item")
            total_cards = 0
            batch_size = 500  # Number of records to insert in one batch
            batch = []
            failed_inserts = 0

            progress_bar = tqdm(parser, desc="Processing cards", unit="card")
            for card in progress_bar:
                total_cards += 1
                progress_bar.set_postfix({"Processed": total_cards})
                try:
                    scryfall_id_str = card.get("id")
                    if not scryfall_id_str:
                        continue
                    card_values = {
                        "scryfall_id": uuid.UUID(scryfall_id_str),
                        "name": card.get("name"),
                        "set_name": card.get("set_name"),
                        "image_url": card.get("image_uris", {}).get("large"),
                        "mana_cost": card.get("mana_cost"),
                        "mana_value": card.get("cmc"),
                        # Split the "type_line" to get the first part before " — " then split into a list.
                        "types": (
                            card.get("type_line", "").split(" — ")[0].split()
                            if card.get("type_line")
                            else []
                        ),
                        "power": card.get("power"),
                        "toughness": card.get("toughness"),
                    }
                except Exception as e:
                    print(f"Error processing card: {e}")
                    continue

                # Append the values (as a Python dict) to the batch; do not convert to JSON string.
                batch.append(card_values)

                if len(batch) >= batch_size:
                    sql = """
                    INSERT INTO cards (scryfall_id, name, set_name, image_url, mana_cost, mana_value, types, power, toughness)
                    VALUES (:scryfall_id, :name, :set_name, :image_url, :mana_cost, :mana_value, :types, :power, :toughness)
                    ON CONFLICT (scryfall_id) DO UPDATE
                    SET name = EXCLUDED.name,
                        set_name = EXCLUDED.set_name,
                        image_url = EXCLUDED.image_url,
                        mana_cost = EXCLUDED.mana_cost,
                        mana_value = EXCLUDED.mana_value,
                        types = EXCLUDED.types,
                        power = EXCLUDED.power,
                        toughness = EXCLUDED.toughness;
                    """
                    try:
                        result = await session.execute(text(sql), batch)
                        await session.commit()
                        print(
                            f"Processed {total_cards} cards, {result.rowcount} rows affected."
                        )
                    except Exception as e:
                        print(f"Error during bulk upsert: {e}")
                        await session.rollback()  # Roll back on error
                        failed_inserts += 1
                    batch = []  # Reset the batch after insertion

            if batch:
                sql = """
                INSERT INTO cards (scryfall_id, name, set_name, image_url, mana_cost, mana_value, types, power, toughness)
                VALUES (:scryfall_id, :name, :set_name, :image_url, :mana_cost, :mana_value, :types, :power, :toughness)
                ON CONFLICT (scryfall_id) DO UPDATE
                SET name = EXCLUDED.name,
                    set_name = EXCLUDED.set_name,
                    image_url = EXCLUDED.image_url,
                    mana_cost = EXCLUDED.mana_cost,
                    mana_value = EXCLUDED.mana_value,
                    types = EXCLUDED.types,
                    power = EXCLUDED.power,
                    toughness = EXCLUDED.toughness;
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
                    failed_inserts += 1

            print(
                f"✅ Bulk upsert of {total_cards} cards completed. Failed inserts: {failed_inserts}"
            )


if __name__ == "__main__":
    asyncio.run(upsert_bulk_data())
