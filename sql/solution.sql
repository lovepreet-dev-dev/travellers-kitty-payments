-- =============================================================================
-- Travellers Kitty — "What is my next payment?"
-- Engine: SQLite 3 (dates stored as ISO-8601 TEXT, so string comparison = date
-- comparison). Every query is parameterised; nothing is concatenated.
--
-- Parameters:
--   :phone  traveller's phone number, e.g. '9800000001'
--   :today  "today" as YYYY-MM-DD. For this task it is always '2026-10-26' and is
--           passed in — no query calls date('now') / CURRENT_DATE.
--
-- Run the whole file in the sqlite3 CLI:
--   sqlite3 -header -column \
--     -cmd ".param set :phone \"'9800000001'\"" -cmd ".param set :today \"'2026-10-26'\"" \
--     :memory: < sql/solution.sql
--   (The inner quotes matter: without them the CLI evaluates 2026-10-26 as
--    arithmetic = 1990. Bound from code, the values are plain text.)
--
-- The API (api/app/queries.py) reads the "-- name: xxx" blocks from this file, so
-- this file is the single source of truth for every query the app uses.
--
-- Business rules / assumptions (also in README):
--   * paid(instalment)   = SUM(payments.amount) for that instalment (0 if none).
--   * unpaid(instalment) = amount - paid. An instalment is "open" if unpaid > 0.
--   * Over-payments are NOT carried forward to the next instalment. An over-paid
--     instalment is simply "not open" and is surfaced by Q3/Q4 for a human to
--     decide (refund vs. apply as credit). We never silently move money.
--   * overdue = due_date < :today (an instalment due today is not overdue yet).
--   * The "next" instalment of a booking is its earliest open instalment, which
--     may already be overdue (an overdue instalment is still the next to pay).
-- =============================================================================


-- -----------------------------------------------------------------------------
-- name: schema
-- -----------------------------------------------------------------------------
CREATE TABLE travellers  (id INT PRIMARY KEY, name TEXT, phone TEXT UNIQUE);
CREATE TABLE bookings    (id INT PRIMARY KEY, traveller_id INT, trip TEXT, departure_date DATE, total_amount INT);
CREATE TABLE instalments (id INT PRIMARY KEY, booking_id INT, due_date DATE, amount INT);
CREATE TABLE payments    (id INT PRIMARY KEY, instalment_id INT, amount INT, paid_at TIMESTAMP);

-- Q6 (part 2) — indexes I would add, and why:
--   * travellers(phone): already UNIQUE, so SQLite/Postgres create an index
--     automatically. Every traveller-facing query starts with an equality lookup
--     on phone, so this is the entry point and must never be a table scan.
--   * bookings(traveller_id): joins traveller -> their bookings.
--   * instalments(booking_id, due_date): joins booking -> instalments and lets
--     "earliest open instalment per booking" read instalments already in due-date
--     order.
--   * payments(instalment_id, paid_at): sums payments per instalment (Q1/Q2/Q3/Q5)
--     and lets the duplicate check (Q4) compare neighbouring payments of the same
--     instalment by time without scanning the whole table.
CREATE INDEX idx_bookings_traveller     ON bookings(traveller_id);
CREATE INDEX idx_instalments_booking_due ON instalments(booking_id, due_date);
CREATE INDEX idx_payments_instalment_at ON payments(instalment_id, paid_at);


-- -----------------------------------------------------------------------------
-- name: seed
-- -----------------------------------------------------------------------------
INSERT INTO travellers VALUES
(1,'Asha','9800000001'),(2,'Rohit','9800000002'),(3,'Meera','9800000003'),(4,'Neha','9800000004');
INSERT INTO bookings VALUES
(1,1,'Bali','2026-12-10',90000),(2,1,'Goa','2027-01-20',40000),(3,2,'Kerala','2026-11-25',60000),
(4,3,'Spiti','2027-02-05',30000),(5,4,'Jaipur','2026-11-15',20000);
INSERT INTO instalments VALUES
(1,1,'2026-10-10',30000),(2,1,'2026-11-10',30000),(3,1,'2026-12-01',30000),(4,2,'2026-11-10',20000),
(5,2,'2026-12-10',20000),(6,3,'2026-10-05',30000),(7,3,'2026-11-05',30000),(8,4,'2026-10-15',15000),
(9,4,'2026-12-20',15000),(10,5,'2026-10-01',20000);
INSERT INTO payments VALUES
(1,1,30000,'2026-10-09 10:00'),(2,2,15000,'2026-10-20 11:00'),(3,6,30000,'2026-10-04 09:00'),
(4,6,30000,'2026-10-04 09:05'),(5,10,20000,'2026-09-30 12:00');


-- -----------------------------------------------------------------------------
-- name: find_traveller
-- Q6 helper: does this phone belong to a traveller? Used by the API only to pick
-- between "unknown_number" and "nothing_due". Returns the id only — never name,
-- phone or anything else. Unknown phone -> 0 rows.
-- -----------------------------------------------------------------------------
SELECT t.id
FROM travellers t
WHERE t.phone = :phone;


-- -----------------------------------------------------------------------------
-- name: next_unpaid_per_booking
-- Q1: for one phone, the next unpaid instalment of EACH booking, with the amount
-- still unpaid, the due date and whether it is overdue on :today.
-- Bookings that are fully paid return no row. Unknown phone -> 0 rows (the
-- traveller filter is an INNER JOIN, so there is nothing to join to).
-- Ordered the same way as Q2 so the first row is the overall next payment.
-- -----------------------------------------------------------------------------
WITH open_instalments AS (
    SELECT b.id                              AS booking_id,
           b.trip                            AS booking,
           b.departure_date,
           i.id                              AS instalment_id,
           i.due_date,
           i.amount - COALESCE(SUM(p.amount), 0) AS unpaid
    FROM travellers t
    JOIN bookings    b ON b.traveller_id = t.id
    JOIN instalments i ON i.booking_id   = b.id
    LEFT JOIN payments p ON p.instalment_id = i.id
    WHERE t.phone = :phone
    GROUP BY i.id
    HAVING unpaid > 0
),
ranked AS (
    SELECT o.*,
           ROW_NUMBER() OVER (PARTITION BY o.booking_id
                              ORDER BY o.due_date, o.instalment_id) AS rn
    FROM open_instalments o
)
SELECT booking,
       unpaid                                   AS amount,
       due_date,
       CASE WHEN due_date < :today THEN 1 ELSE 0 END AS overdue
FROM ranked
WHERE rn = 1
ORDER BY due_date, departure_date, booking_id;


-- -----------------------------------------------------------------------------
-- name: next_payment
-- Q2: for one phone, the SINGLE next payment across all bookings.
-- Earliest due date wins; on a tie, the booking with the earlier departure date
-- wins; booking id is a final tie-breaker so the answer is always deterministic.
-- (For Asha: Bali and Goa are both due 2026-11-10 -> Bali departs first -> Bali.)
-- -----------------------------------------------------------------------------
WITH open_instalments AS (
    SELECT b.id                              AS booking_id,
           b.trip                            AS booking,
           b.departure_date,
           i.id                              AS instalment_id,
           i.due_date,
           i.amount - COALESCE(SUM(p.amount), 0) AS unpaid
    FROM travellers t
    JOIN bookings    b ON b.traveller_id = t.id
    JOIN instalments i ON i.booking_id   = b.id
    LEFT JOIN payments p ON p.instalment_id = i.id
    WHERE t.phone = :phone
    GROUP BY i.id
    HAVING unpaid > 0
)
SELECT booking,
       unpaid                                   AS amount,
       due_date,
       CASE WHEN due_date < :today THEN 1 ELSE 0 END AS overdue
FROM open_instalments
ORDER BY due_date, departure_date, booking_id, instalment_id
LIMIT 1;


-- -----------------------------------------------------------------------------
-- name: payment_mismatches
-- Q3: instalments where the total paid differs from the amount — partially paid
-- or over-paid. Instalments with no payment at all are simply "unpaid", not a
-- mismatch, so they are excluded. (Admin query: no phone/today parameters.)
-- Expected on the seed data: #2 Bali partial (15000 of 30000),
--                            #6 Kerala over-paid (60000 of 30000).
-- -----------------------------------------------------------------------------
SELECT i.id                       AS instalment_id,
       b.trip                     AS booking,
       i.due_date,
       i.amount,
       SUM(p.amount)              AS total_paid,
       SUM(p.amount) - i.amount   AS difference,
       CASE WHEN SUM(p.amount) < i.amount THEN 'partial' ELSE 'overpaid' END AS kind
FROM instalments i
JOIN bookings b ON b.id = i.booking_id
JOIN payments p ON p.instalment_id = i.id
GROUP BY i.id
HAVING SUM(p.amount) <> i.amount
ORDER BY i.id;


-- -----------------------------------------------------------------------------
-- name: duplicate_payments
-- Q4: duplicate payments — same instalment, same amount, paid within 10 minutes
-- of each other (inclusive). Returned as pairs; p1.id < p2.id so each pair
-- appears once. The later payment of each pair is the likely duplicate.
-- (Admin query: no phone/today parameters.)
-- Expected on the seed data: payments 3 & 4 on instalment #6, 5 minutes apart.
-- -----------------------------------------------------------------------------
SELECT p1.instalment_id,
       p1.id         AS first_payment_id,
       p2.id         AS duplicate_payment_id,
       p1.amount,
       p1.paid_at    AS first_paid_at,
       p2.paid_at    AS duplicate_paid_at,
       ABS(CAST(strftime('%s', p2.paid_at) AS INT)
         - CAST(strftime('%s', p1.paid_at) AS INT)) / 60 AS minutes_apart
FROM payments p1
JOIN payments p2
  ON  p2.instalment_id = p1.instalment_id
  AND p2.amount        = p1.amount
  AND p2.id            > p1.id
-- Whole seconds, not julianday(): julianday is a float and makes exactly
-- 10 minutes come out as 10.0000001 -> wrongly excluded.
WHERE ABS(CAST(strftime('%s', p2.paid_at) AS INT)
        - CAST(strftime('%s', p1.paid_at) AS INT)) <= 10 * 60
ORDER BY p1.instalment_id, p1.id;


-- -----------------------------------------------------------------------------
-- name: overdue_balance
-- Q5: overdue balance for the traveller with :phone on :today — instalments due
-- strictly before :today that are not fully paid, counting only the unpaid part
-- (a partial payment reduces the balance). Over-paid instalments contribute 0,
-- never a negative number.
-- Returns one row for a known traveller (0 if nothing is overdue) and 0 rows for
-- an unknown phone: GROUP BY t.id is what guarantees that — an aggregate without
-- GROUP BY would return one row of NULLs even when nothing matched (Q6).
-- Expected: Meera 15000 (Spiti, due 2026-10-15), everyone else 0.
-- -----------------------------------------------------------------------------
WITH instalment_balance AS (
    SELECT t.id                              AS traveller_id,
           t.name,
           i.due_date,
           i.amount - COALESCE(SUM(p.amount), 0) AS unpaid
    FROM travellers t
    LEFT JOIN bookings    b ON b.traveller_id = t.id
    LEFT JOIN instalments i ON i.booking_id   = b.id
    LEFT JOIN payments    p ON p.instalment_id = i.id
    WHERE t.phone = :phone
    GROUP BY t.id, i.id
)
SELECT name,
       COALESCE(SUM(CASE WHEN due_date < :today AND unpaid > 0 THEN unpaid END), 0)
           AS overdue_balance
FROM instalment_balance
GROUP BY traveller_id;


-- -----------------------------------------------------------------------------
-- name: overdue_balance_all
-- Q5 (admin variant, "per traveller"): the same rule for every traveller who
-- has an overdue balance, given only :today. No phone, so this must never be
-- exposed to a traveller-facing channel.
-- -----------------------------------------------------------------------------
WITH instalment_balance AS (
    SELECT b.traveller_id,
           i.due_date,
           i.amount - COALESCE(SUM(p.amount), 0) AS unpaid
    FROM bookings b
    JOIN instalments i ON i.booking_id = b.id
    LEFT JOIN payments p ON p.instalment_id = i.id
    GROUP BY i.id
)
SELECT t.name,
       SUM(ib.unpaid) AS overdue_balance
FROM instalment_balance ib
JOIN travellers t ON t.id = ib.traveller_id
WHERE ib.due_date < :today
  AND ib.unpaid > 0
GROUP BY t.id
ORDER BY overdue_balance DESC, t.id;


-- -----------------------------------------------------------------------------
-- Q6: an unknown phone number returns no rows and reveals nothing.
-- How every phone-scoped query above guarantees it:
--   1. The phone is the only way in: every query starts FROM travellers WHERE
--      t.phone = :phone, compared by exact equality as a bound parameter — so a
--      value like  ' OR 1=1 --  is just a phone number that matches nothing.
--   2. Bookings/instalments are reached only through that traveller (joins), so
--      no other traveller's rows can leak in.
--   3. Aggregates are GROUPed BY the traveller, so "no traveller" means
--      "no group" means 0 rows — not one row of NULLs/zeros (see Q5).
--   4. Queries return only what the screen needs (trip, amount, due date,
--      overdue) — no name, phone, ids or totals of anyone.
--   5. The API answers an unknown number with {"status":"unknown_number"} and
--      no data, identical whatever the number is.
-- Proof — run Q1, Q2 and Q5 with a number that does not exist: each returns 0 rows.
-- (The indexes I would add are documented next to the schema at the top.)
-- -----------------------------------------------------------------------------
