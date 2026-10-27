import pytest
from fastapi.testclient import TestClient

from app.db import init_db
from app.main import app

TODAY = "2026-10-26"

ASHA = "9800000001"   # Bali + Goa, tie on 2026-11-10, Bali partly paid
ROHIT = "9800000002"  # Kerala, first instalment paid twice (duplicate)
MEERA = "9800000003"  # Spiti, instalment overdue since 2026-10-15
NEHA = "9800000004"   # Jaipur, fully paid -> nothing due
UNKNOWN = "9999999999"


@pytest.fixture()
def db_file(tmp_path, monkeypatch):
    path = tmp_path / "kitty.db"
    monkeypatch.setenv("KITTY_DB_PATH", str(path))
    init_db(path)
    return path


@pytest.fixture()
def client(db_file):
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def get(client):
    def _get(phone, today=TODAY):
        params = {}
        if phone is not None:
            params["phone"] = phone
        if today is not None:
            params["today"] = today
        return client.get("/next-payment", params=params)

    return _get
