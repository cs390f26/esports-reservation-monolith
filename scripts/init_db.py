"""Create (or recreate) the empty tables from the schema.

The schema drops every table first, so this wipes existing data. Prompts for
confirmation when the database already holds rows, unless -y is passed.
"""

import argparse
import sys

from esports.database import connect, create_tables, database_target, has_tables, row_count


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-y", "--yes", action="store_true", help="Recreate without prompting.")
    args = parser.parse_args(argv)

    db = connect()
    if not args.yes and has_tables(db) and row_count(db):
        answer = input(f"{database_target()} has data. Drop and recreate every table? [y/N] ")
        if answer.strip().lower() not in ("y", "yes"):
            print("Cancelled.")
            sys.exit(1)
    create_tables(db)
    db.close()
    print(f"Created tables in {database_target()}")


if __name__ == "__main__":
    main()
