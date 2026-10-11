from datetime import datetime

import pytest

from conftest import TODAY, TOMORROW

ACTIVE_SPACES = [1, 2, 3, 4, 5]
WORKING_EQUIPMENT = [1, 2, 3, 4]  # equipment 5 is in maintenance


def test_no_parameters_returns_the_block_in_progress(client):
    blocks = client.get("/availability").get_json()
    assert blocks == [
        {
            "date": TODAY,
            "start_hour": 12,
            "end_hour": 14,
            "start_time": f"{TODAY}T12:00:00",
            "end_time": f"{TODAY}T14:00:00",
            "in_progress": True,
            "space_ids": ACTIVE_SPACES,
            "equipment_ids": WORKING_EQUIPMENT,
        }
    ]


def test_before_opening_returns_todays_first_block(client, clock):
    clock.set(datetime(2030, 1, 15, 8, 30))
    block = client.get("/availability").get_json()[0]
    assert (block["date"], block["start_hour"], block["in_progress"]) == (TODAY, 10, False)


def test_after_closing_returns_tomorrows_first_block(client, clock):
    clock.set(datetime(2030, 1, 15, 22, 0))
    block = client.get("/availability").get_json()[0]
    assert (block["date"], block["start_hour"], block["in_progress"]) == (TOMORROW, 10, False)


def test_date_returns_all_six_blocks_in_order(client):
    blocks = client.get(f"/availability?date={TOMORROW}").get_json()
    assert [block["start_hour"] for block in blocks] == [10, 12, 14, 16, 18, 20]
    assert [block["end_hour"] for block in blocks] == [12, 14, 16, 18, 20, 22]
    assert not any(block["in_progress"] for block in blocks)


def test_date_and_start_hour_returns_one_block(client):
    blocks = client.get(f"/availability?date={TOMORROW}&start_hour=16").get_json()
    assert len(blocks) == 1
    assert blocks[0]["start_time"] == f"{TOMORROW}T16:00:00"


def test_booked_space_and_equipment_are_not_free(client, book):
    book(space_id=3, equipment_ids=[2], start_hour=18)
    block = client.get(f"/availability?date={TOMORROW}&start_hour=18").get_json()[0]
    assert 3 not in block["space_ids"]
    assert 2 not in block["equipment_ids"]
    other = client.get(f"/availability?date={TOMORROW}&start_hour=16").get_json()[0]
    assert other["space_ids"] == ACTIVE_SPACES


def test_cancelled_booking_frees_the_space(client, book):
    reservation = book(space_id=3, start_hour=18).get_json()
    client.post(f"/reservations/{reservation['reservation_id']}/cancel")
    block = client.get(f"/availability?date={TOMORROW}&start_hour=18").get_json()[0]
    assert 3 in block["space_ids"]


def test_inactive_space_is_never_free(client):
    client.patch("/spaces/1", json={"is_active": False})
    block = client.get(f"/availability?date={TOMORROW}&start_hour=10").get_json()[0]
    assert 1 not in block["space_ids"]


@pytest.mark.parametrize(
    "query, code, field",
    [
        ("sort=asc", "UNKNOWN_PARAMETER", "sort"),
        ("start_hour=10", "MISSING_DATE", "date"),
        ("date=2030-02-30", "INVALID_DATE", "date"),
        ("date=tomorrow", "INVALID_DATE", "date"),
        (f"date={TOMORROW}&start_hour=11", "INVALID_TIME_BLOCK", "start_hour"),
        (f"date={TOMORROW}&start_hour=noon", "INVALID_TIME_BLOCK", "start_hour"),
    ],
)
def test_invalid_queries(client, query, code, field):
    response = client.get(f"/availability?{query}")
    assert response.status_code == 400
    assert response.get_json()["code"] == code
    assert response.get_json()["field"] == field
