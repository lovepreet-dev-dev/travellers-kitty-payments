"""Direct tests of every query in sql/solution.sql (Q1–Q6)."""

import sqlite3

import pytest

from app.queries import query
from conftest import ASHA, MEERA, NEHA, ROHIT, TODAY, UNKNOWN


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.executescript(query("schema"))
    c.executescript(query("seed"))
    yield c
    c.close()


def run(conn, name, **params):
    return conn.execute(query(name), params).fetchall()


def test_q1_next_unpaid_per_booking(conn):
    assert run(conn, "next_unpaid_per_booking", phone=ASHA, today=TODAY) == [
        ("Bali", 15000, "2026-11-10", 0),
        ("Goa", 20000, "2026-11-10", 0),
    ]
    assert run(conn, "next_unpaid_per_booking", phone=MEERA, today=TODAY) == [
        ("Spiti", 15000, "2026-10-15", 1),
    ]
    assert run(conn, "next_unpaid_per_booking", phone=NEHA, today=TODAY) == []


def test_q2_single_next_payment_with_tie_break(conn):
    assert run(conn, "next_payment", phone=ASHA, today=TODAY) == [
        ("Bali", 15000, "2026-11-10", 0),
    ]
    assert run(conn, "next_payment", phone=ROHIT, today=TODAY) == [
        ("Kerala", 30000, "2026-11-05", 0),
    ]


def test_q2_tie_break_is_by_departure_not_by_insert_order(conn):
    # Make Goa depart before Bali: Goa must now win the 2026-11-10 tie.
    conn.execute("UPDATE bookings SET departure_date = '2026-11-30' WHERE trip = 'Goa'")
    assert run(conn, "next_payment", phone=ASHA, today=TODAY) == [
        ("Goa", 20000, "2026-11-10", 0),
    ]


def test_q3_partial_and_overpaid_instalments(conn):
    rows = run(conn, "payment_mismatches")
    assert [(r[0], r[1], r[3], r[4], r[6]) for r in rows] == [
        (2, "Bali", 30000, 15000, "partial"),
        (6, "Kerala", 30000, 60000, "overpaid"),
    ]


def test_q4_duplicate_payments_within_10_minutes(conn):
    assert run(conn, "duplicate_payments") == [
        (6, 3, 4, 30000, "2026-10-04 09:00", "2026-10-04 09:05", 5),
    ]


def test_q4_ignores_payments_more_than_10_minutes_apart(conn):
    conn.execute("UPDATE payments SET paid_at = '2026-10-04 09:11' WHERE id = 4")
    assert run(conn, "duplicate_payments") == []
    conn.execute("UPDATE payments SET paid_at = '2026-10-04 09:10' WHERE id = 4")
    assert len(run(conn, "duplicate_payments")) == 1  # exactly 10 min counts


def test_q5_overdue_balance(conn):
    assert run(conn, "overdue_balance", phone=MEERA, today=TODAY) == [("Meera", 15000)]
    assert run(conn, "overdue_balance", phone=ASHA, today=TODAY) == [("Asha", 0)]
    assert run(conn, "overdue_balance_all", today=TODAY) == [("Meera", 15000)]
    # On 2026-11-11 Asha's Bali (15000 left) and Goa (20000) are overdue too.
    assert run(conn, "overdue_balance", phone=ASHA, today="2026-11-11") == [("Asha", 35000)]


def test_q6_unknown_number_returns_no_rows_anywhere(conn):
    for name in ["find_traveller", "next_unpaid_per_booking", "next_payment", "overdue_balance"]:
        assert run(conn, name, phone=UNKNOWN, today=TODAY) == [], name
