"""GET /next-payment?phone=...&today=YYYY-MM-DD

Answers "what is my next payment?" using only the database:
  * Q1 (next_unpaid_per_booking) -> "bookings"
  * Q2 (next_payment)            -> "next"
Every amount and date in the response comes straight from those query rows.
"today" is always taken from the request; the server never reads the clock.
"""

import logging
import re
import sqlite3
from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .db import connect_readonly, init_db
from .queries import query

log = logging.getLogger("kitty")

PHONE_RE = re.compile(r"^\+?\d{6,15}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()  # builds api/data/kitty.db from sql/solution.sql on first run
    yield


app = FastAPI(title="Travellers Kitty — next payment", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"]
)


def respond(status: str, http_code: int = 200, next_=None, bookings=None) -> JSONResponse:
    return JSONResponse(
        status_code=http_code,
        content={"status": status, "next": next_, "bookings": bookings or []},
    )


def to_item(row: sqlite3.Row) -> dict:
    return {
        "booking": row["booking"],
        "amount": row["amount"],
        "due_date": row["due_date"],
        "overdue": bool(row["overdue"]),
    }


def is_valid_date(value: str) -> bool:
    if not DATE_RE.match(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


@app.get("/next-payment")
def next_payment(phone: str | None = None, today: str | None = None):
    phone = (phone or "").strip()
    today = (today or "").strip()
    if not phone or not is_valid_date(today):
        # Bad request: say nothing about any traveller.
        return respond("error", 400)

    # A value that cannot be a phone number cannot match a traveller. Answer
    # exactly like any other unknown number, without touching the DB.
    if not PHONE_RE.match(phone):
        return respond("unknown_number")

    params = {"phone": phone, "today": today}
    try:
        conn = connect_readonly()
        try:
            conn.execute("BEGIN")  # one snapshot for all three reads
            if conn.execute(query("find_traveller"), params).fetchone() is None:
                return respond("unknown_number")
            bookings = [to_item(r) for r in conn.execute(query("next_unpaid_per_booking"), params)]
            next_row = conn.execute(query("next_payment"), params).fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        log.exception("database error")
        return respond("error", 503)

    if next_row is None:
        return respond("nothing_due")
    return respond("ok", next_=to_item(next_row), bookings=bookings)


@app.get("/health")
def health():
    return {"status": "ok"}
