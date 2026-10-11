"""Create (or recreate) the empty tables from db/schema.sql.

schema.sql drops every table first, so this wipes existing data. Prompts for
confirmation when the database already holds rows, unless -y is passed.
"""

import argparse
import sys

from dbfile import DATABASE, SCHEMA, connect, has_tables, row_count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-y", "--yes", action="store_true", help="Recreate without prompting.")
    args = parser.parse_args()

    db = connect()
    if not args.yes and has_tables(db) and row_count(db):
        answer = input(f"{DATABASE} has data. Drop and recreate every table? [y/N] ")
        if answer.strip().lower() not in ("y", "yes"):
            print("Cancelled.")
            sys.exit(1)
    db.executescript(SCHEMA.read_text(encoding="utf-8"))
    db.close()
    print(f"Created tables in {DATABASE}")


if __name__ == "__main__":
    main()
