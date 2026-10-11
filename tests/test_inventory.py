def test_root_redirects_to_overview(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/01-overview.html")


def test_ui_pages_are_served(client):
    pages = ("01-overview.html", "02-reservation.html", "03-space-details.html", "04-settings.html")
    for page in pages:
        # Static files are streamed; the with block closes the file afterwards.
        with client.get(f"/{page}") as response:
            assert response.status_code == 200, page
            assert b"app.js" in response.data
    for asset in ("app.js", "styles.css"):
        with client.get(f"/{asset}") as response:
            assert response.status_code == 200, asset


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_inventory_lists_everything(client):
    body = client.get("/inventory").get_json()
    assert [space["space_id"] for space in body["spaces"]] == [1, 2, 3, 4, 5, 6]
    assert len(body["computers"]) == 6
    assert len(body["equipment"]) == 5


def test_inventory_shapes_match_the_spec(client):
    body = client.get("/inventory").get_json()
    assert body["spaces"][0] == {
        "space_id": 1,
        "space_name": "Station 01 - Cyberhound Rig",
        "description": "PC gaming desk with a 240Hz monitor.",
        "is_active": True,
    }
    assert body["spaces"][5]["is_active"] is False
    assert set(body["computers"][0]) == {"computer_id", "space_id", "hostname", "specs", "status"}
    assert set(body["equipment"][0]) == {"equipment_id", "item_name", "category", "serial_number", "status"}


def test_list_endpoints(client):
    assert len(client.get("/spaces").get_json()) == 6
    assert len(client.get("/computers").get_json()) == 6
    assert len(client.get("/equipment").get_json()) == 5
