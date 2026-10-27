def test_health_returns_ok(client):
    response = client.get("/api/health/")

    assert response.status_code == 200
    assert response.data == {"status": "ok"}


def test_schema_loads(client):
    response = client.get("/api/schema/")

    assert response.status_code == 200


def test_docs_page_loads(client):
    response = client.get("/api/docs/")

    assert response.status_code == 200
