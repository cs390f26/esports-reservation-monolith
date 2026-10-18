from datetime import datetime

import pytest

from conftest import TODAY, TOMORROW
from esports import database


def test_create_reservation(book):
    response = book(user_id="  alex  ", space_id=2, equipment_ids=[1, 3], start_hour=10)
    assert response.status_code == 201
    body = response.get_json()
    assert body["reservation_id"] >= 1
    assert body["user_id"] == "  alex  "
    assert body["space_id"] == 2
    assert body["equipment_ids"] == [1, 3]
    assert body["start_time"] == f"{TOMORROW}T10:00:00"
    assert body["end_time"] == f"{TOMORROW}T12:00:00"
    assert body["status"] == "CONFIRMED"
    assert body["created_at"] == "2030-01-15T13:00:00"


def test_equipment_is_optional(book):
    assert book().get_json()["equipment_ids"] == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"user_id": ""},
        {"user_id": 7},
        {"space_id": "1"},
        {"space_id": True},
        {"date": "someday"},
        {"equipment_ids": "1"},
        {"equipment_ids": [1, 1]},
    ],
)
def test_invalid_request(book, overrides):
    response = book(**overrides)
    assert response.status_code == 400
    assert response.get_json()["code"] == "INVALID_REQUEST"


def test_missing_body(client):
    response = client.post("/reservations")
    assert response.status_code == 400
    assert response.get_json()["code"] == "INVALID_REQUEST"


@pytest.mark.parametrize("hour", [9, 11, 22, "10", None])
def test_invalid_time_block(book, hour):
    response = book(start_hour=hour)
    assert response.status_code == 400
    assert response.get_json()["code"] == "INVALID_TIME_BLOCK"


@pytest.mark.parametrize("hour", [10, 12])
def test_block_that_started_is_rejected(book, hour):
    # The clock is 13:00, so 10:00 is over and 12:00 is in progress.
    response = book(date=TODAY, start_hour=hour)
    assert response.status_code == 400
    assert response.get_json()["code"] == "BLOCK_STARTED"


def test_later_block_today_is_allowed(book):
    assert book(date=TODAY, start_hour=14).status_code == 201


def test_missing_space(book):
    response = book(space_id=42)
    assert response.status_code == 404
    assert response.get_json()["code"] == "SPACE_NOT_FOUND"


def test_missing_equipment(book):
    response = book(equipment_ids=[1, 42])
    assert response.status_code == 404
    assert response.get_json()["code"] == "EQUIPMENT_NOT_FOUND"


def test_inactive_space(book):
    response = book(space_id=6)
    assert response.status_code == 409
    assert response.get_json()["code"] == "SPACE_INACTIVE"


def test_space_already_booked(book):
    assert book().status_code == 201
    response = book(user_id="someone else")
    assert response.status_code == 409
    assert response.get_json()["code"] == "SPACE_BOOKED"


def test_equipment_already_booked(book):
    assert book(space_id=1, equipment_ids=[2]).status_code == 201
    response = book(space_id=2, equipment_ids=[1, 2])
    assert response.status_code == 409
    assert response.get_json()["code"] == "EQUIPMENT_UNAVAILABLE"


def test_back_to_back_blocks_are_allowed(book):
    assert book(equipment_ids=[1], start_hour=14).status_code == 201
    assert book(equipment_ids=[1], start_hour=16).status_code == 201


def test_rebooking_a_cancelled_slot(client, book):
    first = book().get_json()
    client.post(f"/reservations/{first['reservation_id']}/cancel")
    assert book(user_id="next in line").status_code == 201


def test_conflict_leaves_no_partial_booking(client, book):
    book(space_id=1, equipment_ids=[2])
    book(space_id=2, equipment_ids=[1, 2])
    assert [r["space_id"] for r in client.get("/reservations").get_json()] == [1]


def test_list_reservations_newest_first_with_filters(client, book, clock):
    book(user_id="alex", space_id=1)
    clock.set(datetime(2030, 1, 15, 13, 5))
    book(user_id="sam", space_id=2)
    clock.set(datetime(2030, 1, 15, 13, 10))
    book(user_id="alex", space_id=3)

    assert [r["space_id"] for r in client.get("/reservations").get_json()] == [3, 2, 1]
    assert [r["space_id"] for r in client.get("/reservations?user_id=alex").get_json()] == [3, 1]
    assert [r["user_id"] for r in client.get("/reservations?space_id=2").get_json()] == ["sam"]


@pytest.mark.parametrize("space_id", ["abc", "0"])
def test_invalid_space_filter(client, space_id):
    response = client.get(f"/reservations?space_id={space_id}")
    assert response.status_code == 400
    assert response.get_json()["code"] == "INVALID_FILTER"


def test_active_only(client, book, clock):
    in_progress = book(start_hour=14).get_json()
    later = book(start_hour=18).get_json()
    clock.set(datetime(2030, 1, 16, 15, 0))

    active = client.get("/reservations?active_only=true").get_json()
    assert [r["reservation_id"] for r in active] == [in_progress["reservation_id"]]
    everything = client.get("/reservations?active_only=false").get_json()
    assert {r["reservation_id"] for r in everything} == {in_progress["reservation_id"], later["reservation_id"]}


def test_active_only_must_be_boolean(client):
    response = client.get("/reservations?active_only=yes")
    assert response.status_code == 400
    assert response.get_json()["code"] == "INVALID_PARAMETER"


def test_get_reservation(client, book):
    created = book(equipment_ids=[4]).get_json()
    response = client.get(f"/reservations/{created['reservation_id']}")
    assert response.status_code == 200
    assert response.get_json() == created


def test_get_missing_reservation(client):
    response = client.get("/reservations/999")
    assert response.status_code == 404
    assert response.get_json()["code"] == "RESERVATION_NOT_FOUND"


def test_cancel_reservation(client, book):
    created = book().get_json()
    response = client.post(f"/reservations/{created['reservation_id']}/cancel")
    assert response.status_code == 200
    assert response.get_json()["status"] == "CANCELLED"
    # Cancelling again is harmless.
    again = client.post(f"/reservations/{created['reservation_id']}/cancel")
    assert again.status_code == 200
    assert again.get_json()["status"] == "CANCELLED"


def test_cancel_missing_reservation(client):
    response = client.post("/reservations/999/cancel")
    assert response.status_code == 404
    assert response.get_json()["code"] == "RESERVATION_NOT_FOUND"


def test_cannot_cancel_after_the_block_ends(client, book, clock):
    created = book(start_hour=14).get_json()
    clock.set(datetime(2030, 1, 16, 16, 0))
    response = client.post(f"/reservations/{created['reservation_id']}/cancel")
    assert response.status_code == 409
    assert response.get_json()["code"] == "BOOKING_ENDED"


def test_database_error_returns_500_and_saves_nothing(client, book, inventory_db):
    # Make the equipment link insert fail after the reservation row is written.
    db = database.connect()
    db.execute("SET GLOBAL log_bin_trust_function_creators = 1")
    db.execute(
        """CREATE TRIGGER fail_links BEFORE INSERT ON ReservationEquipment
           FOR EACH ROW
           SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'disk on fire'"""
    )
    db.close()

    response = book(equipment_ids=[1])
    assert response.status_code == 500
    assert response.get_json()["code"] == "RESERVATION_FAILED"
    assert client.get("/reservations").get_json() == []
