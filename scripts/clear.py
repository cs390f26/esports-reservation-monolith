"""Delete every row from the database but keep the tables.

Pass --reservations to delete only bookings and keep the inventory.
Prompts for confirmation unless -y is passed.
"""

import argparse
import sys

from dbfile import DATABASE, TABLES, connect, has_tables


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-y", "--yes", action="store_true", help="Delete without prompting.")
    parser.add_argument(
        "--reservations",
        action="store_true",
        help="Delete only reservations; keep spaces, computers, and equipment.",
    )
    args = parser.parse_args()

    db = connect()
    if not has_tables(db):
        print(f"{DATABASE} has no tables. Run scripts/init_db.py first.", file=sys.stderr)
        sys.exit(1)

    tables = TABLES[:2] if args.reservations else TABLES
    if not args.yes:
        answer = input(f"Delete all rows from {', '.join(tables)} in {DATABASE}? [y/N] ")
        if answer.strip().lower() not in ("y", "yes"):
            print("Cancelled.")
            sys.exit(1)

    for table in tables:
        deleted = db.execute(f"DELETE FROM {table}").rowcount
        print(f"  {table}: deleted {deleted}")
    db.commit()
    db.close()
    print(f"Cleared {DATABASE}")


if __name__ == "__main__":
    main()
