from datetime import date, datetime, timedelta

from flask import Flask, g, jsonify, redirect, request

from esports.database import DatabaseError, IntegrityError, connect

START_HOURS = (10, 12, 14, 16, 18, 20)
COMPUTER_STATUSES = ("AVAILABLE", "IN_USE", "MAINTENANCE", "OFFLINE")
EQUIPMENT_STATUSES = COMPUTER_STATUSES
EQUIPMENT_CATEGORIES = ("HEADSET", "CONTROLLER")

# The UI in static/ is served from the site root, next to the API.
app = Flask(__name__, static_url_path="")


def now():
    """The lounge's local time. Tests replace this to control the clock."""
    return datetime.now()


def get_db():
    if "db" not in g:
        g.db = connect()
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def error(status, code, message, **extra):
    body = {"code": code, "message": message}
    body.update({key: value for key, value in extra.items() if value is not None})
    return jsonify(body), status


def parse_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def block_times(day, start_hour):
    start = datetime(day.year, day.month, day.day, start_hour)
    return start, start + timedelta(hours=2)


def db_time(value):
    return value.strftime("%Y-%m-%d %H:%M:%S")


def iso_time(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%S")
    return str(value).replace(" ", "T")


def space_json(row):
    return {
        "space_id": row["space_id"],
        "space_name": row["space_name"],
        "description": row["description"],
        "is_active": bool(row["is_active"]),
    }


def computer_json(row):
    return {
        "computer_id": row["computer_id"],
        "space_id": row["space_id"],
        "hostname": row["hostname"],
        "specs": row["specs"],
        "status": row["status"],
    }


def equipment_json(row):
    return {
        "equipment_id": row["equipment_id"],
        "item_name": row["item_name"],
        "category": row["category"],
        "serial_number": row["serial_number"],
        "status": row["status"],
    }


def reservation_json(db, row):
    equipment_ids = [
        r["equipment_id"]
        for r in db.execute(
            "SELECT equipment_id FROM ReservationEquipment WHERE reservation_id = %s ORDER BY equipment_id",
            (row["reservation_id"],),
        )
    ]
    return {
        "reservation_id": row["reservation_id"],
        "user_id": row["user_name"],
        "space_id": row["space_id"],
        "equipment_ids": equipment_ids,
        "start_time": iso_time(row["start_time"]),
        "end_time": iso_time(row["end_time"]),
        "status": row["status"],
        "created_at": iso_time(row["created_at"]),
    }


def available_space_ids(db, start):
    return [
        r["space_id"]
        for r in db.execute(
            """SELECT space_id FROM Spaces
               WHERE is_active = 1 AND space_id NOT IN (
                 SELECT space_id FROM Reservations
                 WHERE status = 'CONFIRMED' AND start_time = %s)
               ORDER BY space_id""",
            (db_time(start),),
        )
    ]


def available_equipment_ids(db, start):
    return [
        r["equipment_id"]
        for r in db.execute(
            """SELECT equipment_id FROM Equipment
               WHERE status != 'MAINTENANCE' AND status != 'OFFLINE' AND equipment_id NOT IN (
                 SELECT re.equipment_id FROM ReservationEquipment re
                 JOIN Reservations r ON r.reservation_id = re.reservation_id
                 WHERE r.status = 'CONFIRMED' AND r.start_time = %s)
               ORDER BY equipment_id""",
            (db_time(start),),
        )
    ]


def block_payload(db, day, hour, current):
    start, end = block_times(day, hour)
    return {
        "date": day.isoformat(),
        "start_hour": hour,
        "end_hour": hour + 2,
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "in_progress": start <= current < end,
        "space_ids": available_space_ids(db, start),
        "equipment_ids": available_equipment_ids(db, start),
    }


def current_or_next(current):
    day = current.date()
    for hour in START_HOURS:
        _start, end = block_times(day, hour)
        if current < end:
            return day, hour
    return day + timedelta(days=1), START_HOURS[0]


def text_field(value, field):
    if not isinstance(value, str) or not value.strip():
        return None, error(400, "INVALID_FIELD", f"{field} must be text.", field=field)
    return value.strip(), None


def optional_text(value, field):
    if value is None:
        return None, None
    if not isinstance(value, str):
        return None, error(400, "INVALID_FIELD", f"{field} must be text.", field=field)
    return (value.strip() or None), None


def read_patch(allowed):
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or not body:
        return None, error(400, "EMPTY_UPDATE", "Include at least one field to update.")
    unknown = next((key for key in body if key not in allowed), None)
    if unknown:
        return None, error(400, "UNKNOWN_FIELD", f"Field cannot be updated: {unknown}.", field=unknown)
    return body, None


def apply_update(db, table, id_column, row_id, fields):
    assignments = ", ".join(f"{name} = %s" for name in fields)
    db.execute(
        f"UPDATE {table} SET {assignments} WHERE {id_column} = %s",
        (*fields.values(), row_id),
    )


@app.get("/")
def index():
    return redirect("/01-overview.html")


@app.get("/health")
def health():
    get_db().execute("SELECT 1 FROM Spaces LIMIT 1")
    return jsonify(status="ok")


@app.get("/inventory")
def inventory():
    db = get_db()
    return jsonify(
        spaces=[space_json(row) for row in db.execute("SELECT * FROM Spaces ORDER BY space_id")],
        computers=[computer_json(row) for row in db.execute("SELECT * FROM Computers ORDER BY computer_id")],
        equipment=[equipment_json(row) for row in db.execute("SELECT * FROM Equipment ORDER BY equipment_id")],
    )


@app.get("/spaces")
def list_spaces():
    rows = get_db().execute("SELECT * FROM Spaces ORDER BY space_id")
    return jsonify([space_json(row) for row in rows])


@app.patch("/spaces/<int:space_id>")
def update_space(space_id):
    body, failure = read_patch(("space_name", "description", "is_active"))
    if failure:
        return failure
    fields = {}
    if "space_name" in body:
        value, failure = text_field(body["space_name"], "space_name")
        if failure:
            return failure
        fields["space_name"] = value
    if "description" in body:
        value, failure = optional_text(body["description"], "description")
        if failure:
            return failure
        fields["description"] = value
    if "is_active" in body:
        if not isinstance(body["is_active"], bool):
            return error(400, "INVALID_FIELD", "is_active must be true or false.", field="is_active")
        fields["is_active"] = body["is_active"]
    db = get_db()
    row = db.execute("SELECT * FROM Spaces WHERE space_id = %s", (space_id,)).fetchone()
    if row is None:
        return error(404, "SPACE_NOT_FOUND", f"Space {space_id} does not exist.", resource_ids=[space_id])
    if fields:
        apply_update(db, "Spaces", "space_id", space_id, fields)
        row = db.execute("SELECT * FROM Spaces WHERE space_id = %s", (space_id,)).fetchone()
    return jsonify(space_json(row))


@app.get("/computers")
def list_computers():
    rows = get_db().execute("SELECT * FROM Computers ORDER BY computer_id")
    return jsonify([computer_json(row) for row in rows])


@app.patch("/computers/<int:computer_id>")
def update_computer(computer_id):
    body, failure = read_patch(("hostname", "specs", "status"))
    if failure:
        return failure
    fields = {}
    if "hostname" in body:
        value, failure = text_field(body["hostname"], "hostname")
        if failure:
            return failure
        fields["hostname"] = value
    if "specs" in body:
        value, failure = optional_text(body["specs"], "specs")
        if failure:
            return failure
        fields["specs"] = value
    if "status" in body:
        if body["status"] not in COMPUTER_STATUSES:
            return error(
                400,
                "INVALID_FIELD",
                "status must be one of AVAILABLE, IN_USE, MAINTENANCE, OFFLINE.",
                field="status",
            )
        fields["status"] = body["status"]
    db = get_db()
    row = db.execute("SELECT * FROM Computers WHERE computer_id = %s", (computer_id,)).fetchone()
    if row is None:
        return error(
            404,
            "COMPUTER_NOT_FOUND",
            f"Computer {computer_id} does not exist.",
            resource_ids=[computer_id],
        )
    if fields:
        apply_update(db, "Computers", "computer_id", computer_id, fields)
        row = db.execute("SELECT * FROM Computers WHERE computer_id = %s", (computer_id,)).fetchone()
    return jsonify(computer_json(row))


@app.get("/equipment")
def list_equipment():
    rows = get_db().execute("SELECT * FROM Equipment ORDER BY equipment_id")
    return jsonify([equipment_json(row) for row in rows])


@app.patch("/equipment/<int:equipment_id>")
def update_equipment(equipment_id):
    body, failure = read_patch(("item_name", "category", "serial_number", "status"))
    if failure:
        return failure
    fields = {}
    if "item_name" in body:
        value, failure = text_field(body["item_name"], "item_name")
        if failure:
            return failure
        fields["item_name"] = value
    if "category" in body:
        if body["category"] not in EQUIPMENT_CATEGORIES:
            return error(400, "INVALID_FIELD", "category must be one of HEADSET, CONTROLLER.", field="category")
        fields["category"] = body["category"]
    if "serial_number" in body:
        value, failure = optional_text(body["serial_number"], "serial_number")
        if failure:
            return failure
        fields["serial_number"] = value
    if "status" in body:
        if body["status"] not in EQUIPMENT_STATUSES:
            return error(
                400,
                "INVALID_FIELD",
                "status must be one of AVAILABLE, IN_USE, MAINTENANCE, OFFLINE.",
                field="status",
            )
        fields["status"] = body["status"]
    db = get_db()
    row = db.execute("SELECT * FROM Equipment WHERE equipment_id = %s", (equipment_id,)).fetchone()
    if row is None:
        return error(
            404,
            "EQUIPMENT_NOT_FOUND",
            f"Equipment {equipment_id} does not exist.",
            resource_ids=[equipment_id],
        )
    if fields:
        apply_update(db, "Equipment", "equipment_id", equipment_id, fields)
        row = db.execute("SELECT * FROM Equipment WHERE equipment_id = %s", (equipment_id,)).fetchone()
    return jsonify(equipment_json(row))


@app.get("/availability")
def availability():
    unknown = next((key for key in request.args if key not in {"date", "start_hour"}), None)
    if unknown:
        return error(400, "UNKNOWN_PARAMETER", f"Unknown query parameter: {unknown}.", field=unknown)
    raw_date = request.args.get("date")
    raw_hour = request.args.get("start_hour")
    if raw_hour is not None and raw_date is None:
        return error(400, "MISSING_DATE", "Include date when filtering by start_hour.", field="date")
    current = now()
    db = get_db()
    if raw_date is None:
        day, hour = current_or_next(current)
        return jsonify([block_payload(db, day, hour, current)])
    day = parse_date(raw_date)
    if day is None:
        return error(400, "INVALID_DATE", "date must be a calendar date in YYYY-MM-DD format.", field="date")
    if raw_hour is None:
        return jsonify([block_payload(db, day, hour, current) for hour in START_HOURS])
    try:
        hour = int(raw_hour)
    except ValueError:
        hour = None
    if hour not in START_HOURS:
        return error(400, "INVALID_TIME_BLOCK", "Choose one of the available time blocks.", field="start_hour")
    return jsonify([block_payload(db, day, hour, current)])


@app.get("/reservations")
def list_reservations():
    sql = "SELECT * FROM Reservations WHERE 1 = 1"
    params = []
    if "user_id" in request.args:
        sql += " AND user_name = %s"
        params.append(request.args["user_id"])
    if "space_id" in request.args:
        space_id = request.args.get("space_id", type=int)
        if space_id is None or space_id < 1:
            return error(400, "INVALID_FILTER", "Check the reservation filters and try again.")
        sql += " AND space_id = %s"
        params.append(space_id)
    if "active_only" in request.args:
        flag = request.args["active_only"].lower()
        if flag not in ("true", "false"):
            return error(400, "INVALID_PARAMETER", "active_only must be true or false.", field="active_only")
        if flag == "true":
            current = db_time(now())
            sql += " AND status = 'CONFIRMED' AND start_time <= %s AND end_time > %s"
            params.extend([current, current])
    sql += " ORDER BY created_at DESC"
    db = get_db()
    return jsonify([reservation_json(db, row) for row in db.execute(sql, params).fetchall()])


@app.post("/reservations")
def create_reservation():
    body = request.get_json(silent=True) or {}
    user_id = body.get("user_id")
    space_id = body.get("space_id")
    equipment_ids = body.get("equipment_ids", [])
    day = parse_date(body.get("date"))
    hour = body.get("start_hour")

    valid_space = isinstance(space_id, int) and not isinstance(space_id, bool)
    if not isinstance(user_id, str) or not user_id or not valid_space or day is None:
        return error(400, "INVALID_REQUEST", "Check the reservation details and try again.")
    if hour not in START_HOURS:
        return error(400, "INVALID_TIME_BLOCK", "Choose one of the available time blocks.")
    if not isinstance(equipment_ids, list) or len(set(equipment_ids)) != len(equipment_ids):
        return error(400, "INVALID_REQUEST", "Check the reservation details and try again.")

    start, end = block_times(day, hour)
    if start <= now():
        return error(400, "BLOCK_STARTED", "Choose a time block that has not started yet.")

    db = get_db()
    # Lock the space (and any equipment) before checking, so two requests cannot
    # both pass the availability checks for the same block.
    db.begin()
    try:
        space = db.execute(
            "SELECT is_active FROM Spaces WHERE space_id = %s FOR UPDATE",
            (space_id,),
        ).fetchone()
        if space is None:
            db.rollback()
            return error(404, "SPACE_NOT_FOUND", "That space could not be found.")
        if not space["is_active"]:
            db.rollback()
            return error(409, "SPACE_INACTIVE", "This space is not open for reservations. Choose another space.")

        for equipment_id in equipment_ids:
            locked = db.execute(
                "SELECT 1 FROM Equipment WHERE equipment_id = %s FOR UPDATE",
                (equipment_id,),
            ).fetchone()
            if locked is None:
                db.rollback()
                return error(404, "EQUIPMENT_NOT_FOUND", "That equipment item could not be found.")

        booked_space = db.execute(
            "SELECT 1 FROM Reservations WHERE space_id = %s AND start_time = %s AND status = 'CONFIRMED'",
            (space_id, db_time(start)),
        ).fetchone()
        if booked_space:
            db.rollback()
            return error(
                409,
                "SPACE_BOOKED",
                "This space is already booked during your selected time. Choose another space or time.",
            )

        if equipment_ids:
            placeholders = ", ".join(["%s"] * len(equipment_ids))
            booked_item = db.execute(
                f"""SELECT 1 FROM ReservationEquipment re
                    JOIN Reservations r ON r.reservation_id = re.reservation_id
                    WHERE r.status = 'CONFIRMED' AND r.start_time = %s
                      AND re.equipment_id IN ({placeholders})""",
                (db_time(start), *equipment_ids),
            ).fetchone()
            if booked_item:
                db.rollback()
                return error(409, "EQUIPMENT_UNAVAILABLE", "This equipment is unavailable during your selected time.")

        cursor = db.execute(
            """INSERT INTO Reservations (user_name, space_id, start_time, end_time, status, created_at)
               VALUES (%s, %s, %s, %s, 'CONFIRMED', %s)""",
            (user_id, space_id, db_time(start), db_time(end), db_time(now())),
        )
        reservation_id = cursor.lastrowid
        if equipment_ids:
            db.executemany(
                "INSERT INTO ReservationEquipment (reservation_id, equipment_id) VALUES (%s, %s)",
                [(reservation_id, item_id) for item_id in equipment_ids],
            )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if exc.args and exc.args[0] == 1062 and "one_confirmed_booking_per_space" in str(exc):
            return error(
                409,
                "SPACE_BOOKED",
                "This space is already booked during your selected time. Choose another space or time.",
            )
        return error(500, "RESERVATION_FAILED", "We couldn't complete your reservation. Please try again.")
    except DatabaseError:
        db.rollback()
        return error(500, "RESERVATION_FAILED", "We couldn't complete your reservation. Please try again.")

    row = db.execute("SELECT * FROM Reservations WHERE reservation_id = %s", (reservation_id,)).fetchone()
    return jsonify(reservation_json(db, row)), 201


@app.get("/reservations/<int:reservation_id>")
def get_reservation(reservation_id):
    db = get_db()
    row = db.execute("SELECT * FROM Reservations WHERE reservation_id = %s", (reservation_id,)).fetchone()
    if row is None:
        return error(404, "RESERVATION_NOT_FOUND", "That reservation could not be found.")
    return jsonify(reservation_json(db, row))


@app.post("/reservations/<int:reservation_id>/cancel")
def cancel_reservation(reservation_id):
    db = get_db()
    row = db.execute("SELECT * FROM Reservations WHERE reservation_id = %s", (reservation_id,)).fetchone()
    if row is None:
        return error(404, "RESERVATION_NOT_FOUND", "That reservation could not be found.")
    if row["status"] != "CANCELLED":
        if datetime.fromisoformat(str(row["end_time"]).replace(" ", "T")) <= now():
            return error(409, "BOOKING_ENDED", "This reservation has already ended.")
        db.execute("UPDATE Reservations SET status = 'CANCELLED' WHERE reservation_id = %s", (reservation_id,))
        row = db.execute("SELECT * FROM Reservations WHERE reservation_id = %s", (reservation_id,)).fetchone()
    return jsonify(reservation_json(db, row))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
