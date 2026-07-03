"""
Seed Script — populates DynamoDB with Massy Caribbean supply chain data.
Usage: python data/seed.py --region us-east-1 --env dev
"""

import boto3, json, uuid, random, argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal

random.seed(42)

LOCATIONS = [
    {"location_id": "WH-POS-001",  "name": "Port of Spain Warehouse",    "island": "Trinidad", "type": "warehouse", "lat": Decimal("10.6549"), "lon": Decimal("-61.5019")},
    {"location_id": "STR-POS-001", "name": "Massy Stores Long Circular", "island": "Trinidad", "type": "store",     "lat": Decimal("10.6572"), "lon": Decimal("-61.5209")},
    {"location_id": "STR-SFD-001", "name": "Massy Stores San Fernando",  "island": "Trinidad", "type": "store",     "lat": Decimal("10.2756"), "lon": Decimal("-61.4637")},
    {"location_id": "STR-CHG-001", "name": "Massy Stores Chaguanas",     "island": "Trinidad", "type": "store",     "lat": Decimal("10.5167"), "lon": Decimal("-61.4000")},
    {"location_id": "STR-SCR-001", "name": "Massy Stores Scarborough",   "island": "Tobago",   "type": "store",     "lat": Decimal("11.1839"), "lon": Decimal("-60.7329")},
    {"location_id": "WH-BGI-001",  "name": "Bridgetown Distribution Hub","island": "Barbados", "type": "warehouse", "lat": Decimal("13.0969"), "lon": Decimal("-59.6145")},
    {"location_id": "STR-BGI-001", "name": "Massy Stores Wildey",        "island": "Barbados", "type": "store",     "lat": Decimal("13.0940"), "lon": Decimal("-59.5960")},
    {"location_id": "STR-GEO-001", "name": "Massy Stores Georgetown",    "island": "Guyana",   "type": "store",     "lat": Decimal("6.8013"),  "lon": Decimal("-58.1551")},
    {"location_id": "STR-CAS-001", "name": "Massy Stores Castries",      "island": "St. Lucia","type": "store",     "lat": Decimal("14.0101"), "lon": Decimal("-60.9875")},
]

SKUS = [
    ("RICE-5KG",       "Rice 5kg",         45, 5.50),
    ("FLOUR-2KG",      "Flour 2kg",        38, 3.25),
    ("COOKING-OIL-1L", "Cooking Oil 1L",   52, 8.75),
    ("SUGAR-1KG",      "Sugar 1kg",        42, 2.95),
    ("CHICKEN-WHOLE",  "Whole Chicken",    30, 42.00),
    ("BEEF-MINCE",     "Beef Mince",       25, 38.50),
    ("PEAS-TIN",       "Pigeon Peas Tin",  28, 4.20),
    ("BREAD-WHITE",    "White Bread",      60, 6.00),
    ("MILK-1L",        "Milk 1L",          48, 7.25),
    ("COLA-2L",        "Cola 2L",          35, 9.50),
    ("DETERGENT-1L",   "Detergent 1L",     20, 18.00),
    ("SUGAR-1KG",      "Sugar 1kg",        42, 2.95),
    ("BUTTER-250G",    "Butter 250g",      18, 14.50),
    ("WATER-6PK",      "Water 6-Pack",     25, 12.00),
    ("BEER-6PK",       "Beer 6-Pack",      18, 45.00),
]

BASKETS = [
    ["RICE-5KG", "CHICKEN-WHOLE", "COOKING-OIL-1L", "PEAS-TIN"],
    ["FLOUR-2KG", "SUGAR-1KG", "BUTTER-250G", "MILK-1L"],
    ["BREAD-WHITE", "MILK-1L", "BUTTER-250G"],
    ["BEEF-MINCE", "COOKING-OIL-1L", "RICE-5KG"],
    ["DETERGENT-1L", "WATER-6PK", "COLA-2L"],
    ["RICE-5KG", "FLOUR-2KG", "SUGAR-1KG", "COOKING-OIL-1L"],
]


def seed_locations(table):
    print("Seeding locations...")
    with table.batch_writer() as batch:
        for loc in LOCATIONS:
            batch.put_item(Item=loc)
    print(f"  ✓ {len(LOCATIONS)} locations")


def seed_inventory(table):
    print("Seeding inventory...")
    count = 0
    now = datetime.now(timezone.utc).isoformat()
    seen = set()
    for sku_id, name, daily_sales, price in SKUS:
        if sku_id in seen:
            continue
        seen.add(sku_id)
        for loc in LOCATIONS:
            table.put_item(Item={
                "sku_id": sku_id,
                "location_id": loc["location_id"],
                "name": name,
                "units_on_hand": random.randint(max(10, daily_sales * 2), daily_sales * 15),
                "avg_daily_sales": Decimal(str(daily_sales)),
                "price_ttd": Decimal(str(price)),
                "last_updated": now
            })
            count += 1
    print(f"  ✓ {count} inventory records")


def seed_orders(table):
    print("Seeding orders (60 days)...")
    count = 0
    for loc in LOCATIONS:
        if loc["type"] != "store":
            continue
        with table.batch_writer() as batch:
            for day_offset in range(60):
                order_date = (datetime.now(timezone.utc) - timedelta(days=day_offset)).strftime("%Y-%m-%d")
                for _ in range(random.randint(20, 60)):
                    basket = random.choice(BASKETS).copy()
                    extras = [s[0] for s in random.choices(SKUS, k=random.randint(0, 2))]
                    items = list(set(basket + extras))
                    total = sum(next((s[3] for s in SKUS if s[0] == sku), 0) * random.randint(1, 5) for sku in items)
                    batch.put_item(Item={
                        "order_id": str(uuid.uuid4()),
                        "location_id": loc["location_id"],
                        "created_at": order_date,
                        "items": items,
                        "total_ttd": Decimal(str(round(total, 2)))
                    })
                    count += 1
    print(f"  ✓ {count} orders")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--region",  default="us-east-1")
    parser.add_argument("--env",     default="dev")
    parser.add_argument("--project", default="massy-agent")
    args = parser.parse_args()

    db = boto3.resource("dynamodb", region_name=args.region)
    p  = args.project

    seed_locations(db.Table(f"{p}-locations"))
    seed_inventory(db.Table(f"{p}-inventory"))
    seed_orders(db.Table(f"{p}-orders"))

    print("\n✅ Seed complete.")


if __name__ == "__main__":
    main()