"""Load the demo data into the database.

Creates the tables first if they are missing. Refuses to run when the tables
already hold rows; pass --reset to clear them and reseed.

--dataset overwatch also books every desk for an Overwatch match in the
current (or next) time block.
"""

import argparse
import sys

from esports.database import (
    DATASETS,
    clear,
    connect,
    create_tables,
    database_target,
    has_tables,
    row_count,
    seed,
    table_counts,
)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reset", action="store_true", help="Delete existing rows before seeding.")
    parser.add_argument(
        "--dataset",
        choices=["default", *DATASETS],
        default="default",
        help="Scenario to load on top of the demo data.",
    )
    args = parser.parse_args(argv)

    db = connect()
    if not has_tables(db):
        create_tables(db)
        print(f"Created tables in {database_target()}")
    elif row_count(db):
        if not args.reset:
            print(
                f"{database_target()} already has data. Run with --reset to replace it, or run scripts/clear.py first.",
                file=sys.stderr,
            )
            sys.exit(1)
        clear(db)
        print("Cleared existing rows")

    seed(db, args.dataset)
    for table, count in table_counts(db).items():
        print(f"  {table}: {count}")
    db.close()
    print(f"Seeded {database_target()} ({args.dataset})")


if __name__ == "__main__":
    main()
