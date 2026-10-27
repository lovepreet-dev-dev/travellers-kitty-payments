"""API tests for GET /next-payment. All use today = 2026-10-26."""

import json
import sqlite3

from conftest import ASHA, MEERA, NEHA, ROHIT, UNKNOWN

EMPTY = {"next": None, "bookings": []}


def test_tie_on_due_date_goes_to_earlier_departure(get):
    # Bali and Goa are both due 2026-11-10; Bali departs 2026-12-10, Goa 2027-01-20.
    res = get(ASHA)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["next"] == {
        "booking": "Bali", "amount": 15000, "due_date": "2026-11-10", "overdue": False,
    }
    assert body["bookings"] == [
        {"booking": "Bali", "amount": 15000, "due_date": "2026-11-10", "overdue": False},
        {"booking": "Goa", "amount": 20000, "due_date": "2026-11-10", "overdue": False},
    ]


def test_partial_payment_shows_only_the_unpaid_part(get):
    # Bali instalment #2 is 30000 with 15000 paid -> 15000 still due, not 30000.
    assert get(ASHA).json()["next"]["amount"] == 15000


def test_overdue_instalment_is_flagged(get):
    body = get(MEERA).json()
    assert body["status"] == "ok"
    assert body["next"] == {
        "booking": "Spiti", "amount": 15000, "due_date": "2026-10-15", "overdue": True,
    }
    assert body["bookings"] == [body["next"]]


def test_nothing_due_traveller(get):
    res = get(NEHA)
    assert res.status_code == 200
    assert res.json() == {"status": "nothing_due", **EMPTY}


def test_unknown_number_reveals_nothing(get):
    res = get(UNKNOWN)
    assert res.status_code == 200
    assert res.json() == {"status": "unknown_number", **EMPTY}


def test_duplicate_payment_is_not_carried_to_next_instalment(get):
    # Kerala #6 was paid twice (60000 for 30000). That excess is a refund/credit
    # decision for a human, so #7 (30000, 2026-11-05) is still due in full.
    body = get(ROHIT).json()
    assert body["status"] == "ok"
    assert body["next"] == {
        "booking": "Kerala", "amount": 30000, "due_date": "2026-11-05", "overdue": False,
    }


def test_today_comes_from_the_parameter_not_the_clock(get):
    # Same traveller, different "today": overdue flips. Proves no system date.
    assert get(ASHA, today="2026-11-10").json()["next"]["overdue"] is False  # due today
    assert get(ASHA, today="2026-11-11").json()["next"]["overdue"] is True
    assert get(MEERA, today="2026-10-01").json()["next"]["overdue"] is False


def test_response_contains_only_this_travellers_data(get):
    body = get(ASHA).json()
    text = json.dumps(body)
    for other in ["Kerala", "Spiti", "Jaipur", "Rohit", "Meera", "Neha", "9800000002"]:
        assert other not in text
    assert set(body) == {"status", "next", "bookings"}
    for item in body["bookings"]:
        assert set(item) == {"booking", "amount", "due_date", "overdue"}


def test_sql_injection_is_just_an_unknown_number(get):
    for evil in ["' OR '1'='1", "9800000001' --", "9800000001 OR 1=1"]:
        assert get(evil).json() == {"status": "unknown_number", **EMPTY}


def test_missing_or_invalid_today_is_an_error(get):
    for today in [None, "", "26-10-2026", "2026-13-01", "2026-02-30", "today"]:
        res = get(ASHA, today=today)
        assert res.status_code == 400
        assert res.json() == {"status": "error", **EMPTY}


def test_missing_phone_is_an_error(get):
    res = get(None)
    assert res.status_code == 400
    assert res.json() == {"status": "error", **EMPTY}


def test_database_unavailable_returns_error_and_no_data(get, db_file, monkeypatch):
    monkeypatch.setenv("KITTY_DB_PATH", str(db_file.parent / "missing.db"))
    res = get(ASHA)
    assert res.status_code == 503
    assert res.json() == {"status": "error", **EMPTY}


def test_corrupt_database_returns_error_and_no_data(get, db_file):
    db_file.write_bytes(b"this is not a sqlite database")
    res = get(ASHA)
    assert res.status_code == 503
    assert res.json() == {"status": "error", **EMPTY}


def test_api_cannot_write_to_the_database(db_file):
    from app.db import connect_readonly

    conn = connect_readonly(db_file)
    try:
        conn.execute("DELETE FROM payments")
        raise AssertionError("write should have failed")
    except sqlite3.OperationalError as exc:
        assert "readonly" in str(exc)
    finally:
        conn.close()
