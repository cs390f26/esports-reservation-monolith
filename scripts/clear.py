"""Delete every row from the database but keep the tables.

Pass --reservations to delete only bookings and keep the inventory.
Prompts for confirmation unless -y is passed.
"""

import argparse
import sys

from esports.database import RESERVATION_TABLES, TABLES, clear, connect, database_path, has_tables


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-y", "--yes", action="store_true", help="Delete without prompting.")
    parser.add_argument(
        "--reservations",
        action="store_true",
        help="Delete only reservations; keep spaces, computers, and equipment.",
    )
    args = parser.parse_args(argv)

    db = connect()
    if not has_tables(db):
        print(f"{database_path()} has no tables. Run scripts/init_db.py first.", file=sys.stderr)
        sys.exit(1)

    tables = RESERVATION_TABLES if args.reservations else TABLES
    if not args.yes:
        answer = input(f"Delete all rows from {', '.join(tables)} in {database_path()}? [y/N] ")
        if answer.strip().lower() not in ("y", "yes"):
            print("Cancelled.")
            sys.exit(1)

    for table, deleted in clear(db, args.reservations).items():
        print(f"  {table}: deleted {deleted}")
    db.close()
    print(f"Cleared {database_path()}")


if __name__ == "__main__":
    main()
