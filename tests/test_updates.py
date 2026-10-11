import pytest


def test_update_space(client):
    response = client.patch("/spaces/1", json={"space_name": "  Main Stage  ", "is_active": False})
    assert response.status_code == 200
    assert response.get_json()["space_name"] == "Main Stage"
    assert response.get_json()["is_active"] is False
    assert client.get("/inventory").get_json()["spaces"][0]["space_name"] == "Main Stage"


def test_update_space_blank_description_becomes_null(client):
    response = client.patch("/spaces/1", json={"description": "   "})
    assert response.get_json()["description"] is None


def test_update_computer(client):
    response = client.patch("/computers/1", json={"hostname": "NEW-01", "specs": "RTX 5090", "status": "OFFLINE"})
    assert response.status_code == 200
    assert response.get_json() == {
        "computer_id": 1,
        "space_id": 1,
        "hostname": "NEW-01",
        "specs": "RTX 5090",
        "status": "OFFLINE",
    }


def test_update_equipment(client):
    response = client.patch(
        "/equipment/1",
        json={"item_name": "Headset A", "category": "HEADSET", "serial_number": None, "status": "MAINTENANCE"},
    )
    assert response.status_code == 200
    assert response.get_json() == {
        "equipment_id": 1,
        "item_name": "Headset A",
        "category": "HEADSET",
        "serial_number": None,
        "status": "MAINTENANCE",
    }


@pytest.mark.parametrize("path", ["/spaces/1", "/computers/1", "/equipment/1"])
def test_empty_update_is_rejected(client, path):
    for body in ({}, None):
        response = client.patch(path, json=body)
        assert response.status_code == 400
        assert response.get_json()["code"] == "EMPTY_UPDATE"


@pytest.mark.parametrize(
    "path, field",
    [("/spaces/1", "space_id"), ("/computers/1", "space_id"), ("/equipment/1", "equipment_id")],
)
def test_unknown_field_is_rejected(client, path, field):
    response = client.patch(path, json={field: 2})
    assert response.status_code == 400
    assert response.get_json() == {
        "code": "UNKNOWN_FIELD",
        "message": f"Field cannot be updated: {field}.",
        "field": field,
    }


@pytest.mark.parametrize(
    "path, body, field",
    [
        ("/spaces/1", {"space_name": ""}, "space_name"),
        ("/spaces/1", {"space_name": 5}, "space_name"),
        ("/spaces/1", {"description": 5}, "description"),
        ("/spaces/1", {"is_active": "yes"}, "is_active"),
        ("/computers/1", {"hostname": "   "}, "hostname"),
        ("/computers/1", {"specs": ["fast"]}, "specs"),
        ("/computers/1", {"status": "BROKEN"}, "status"),
        ("/equipment/1", {"item_name": None}, "item_name"),
        ("/equipment/1", {"category": "MOUSE"}, "category"),
        ("/equipment/1", {"serial_number": 7}, "serial_number"),
        ("/equipment/1", {"status": "LOST"}, "status"),
    ],
)
def test_invalid_field_is_rejected(client, path, body, field):
    response = client.patch(path, json=body)
    assert response.status_code == 400
    assert response.get_json()["code"] == "INVALID_FIELD"
    assert response.get_json()["field"] == field


@pytest.mark.parametrize(
    "path, body, code",
    [
        ("/spaces/42", {"is_active": True}, "SPACE_NOT_FOUND"),
        ("/computers/42", {"status": "AVAILABLE"}, "COMPUTER_NOT_FOUND"),
        ("/equipment/42", {"status": "AVAILABLE"}, "EQUIPMENT_NOT_FOUND"),
    ],
)
def test_update_missing_resource(client, path, body, code):
    response = client.patch(path, json=body)
    assert response.status_code == 404
    assert response.get_json()["code"] == code
    assert response.get_json()["resource_ids"] == [42]


def test_deactivating_a_space_keeps_its_reservations(client, book):
    reservation = book(space_id=2).get_json()
    client.patch("/spaces/2", json={"is_active": False})
    response = client.get(f"/reservations/{reservation['reservation_id']}")
    assert response.get_json()["status"] == "CONFIRMED"
