# Part 4 — WhatsApp assistant note

**No invented amounts or dates.** The assistant never writes an amount or date itself. It calls `/next-payment` with the sender's verified WhatsApp number (never a number typed in chat) and the "today" parameter. It fills a fixed template ("Your next payment for {booking} is ₹{amount}, due {due_date}") with the JSON values exactly as returned. If an LLM phrases the reply, it sees only that JSON. A post-check rejects any reply containing a number or date not in the JSON and falls back to the template. Only `status: "ok"` may mention money.

**Endpoint down** (error, timeout, bad JSON): "Sorry, I can't check your payment details right now. Please try again in a few minutes." No amount, no date, no cached value.

**Test before done:** replay every seeded traveller plus an outage through the bot. Assert each reply's amounts and dates match the API exactly, and the outage reply has none.
