"""Load db/sampledata.sql into the database.

Creates the tables first if they are missing. Refuses to run when the tables
already hold rows; pass --reset to clear them and reseed.

--dataset overwatch also books every desk for an Overwatch match in the
current (or next) time block.
"""

import argparse
import sys

from dbfile import DATABASE, DATASETS, SAMPLE_DATA, SCHEMA, TABLES, connect, has_tables, row_count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reset", action="store_true", help="Delete existing rows before seeding.")
    parser.add_argument(
        "--dataset",
        choices=["default", *DATASETS],
        default="default",
        help="Scenario to load on top of the demo data.",
    )
    args = parser.parse_args()

    db = connect()
    if not has_tables(db):
        db.executescript(SCHEMA.read_text(encoding="utf-8"))
        print(f"Created tables in {DATABASE}")
    elif row_count(db):
        if not args.reset:
            print(
                f"{DATABASE} already has data. Run with --reset to replace it, "
                "or run scripts/clear.py first.",
                file=sys.stderr,
            )
            sys.exit(1)
        for table in TABLES:
            db.execute(f"DELETE FROM {table}")
        print("Cleared existing rows")

    db.executescript(SAMPLE_DATA.read_text(encoding="utf-8"))
    if args.dataset != "default":
        db.executescript(DATASETS[args.dataset].read_text(encoding="utf-8"))
    for table in reversed(TABLES):
        count = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count}")
    db.close()
    print(f"Seeded {DATABASE} ({args.dataset})")


if __name__ == "__main__":
    main()
