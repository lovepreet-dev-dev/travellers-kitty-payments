import { API_URL, REQUEST_TIMEOUT_MS, TODAY } from './config';

export type PaymentItem = {
  booking: string;
  amount: number;
  due_date: string;
  overdue: boolean;
};

// Only "ok" carries amounts/dates. Every other outcome carries no data at all,
// so the UI has nothing old or made-up that it could accidentally render.
export type NextPaymentResult =
  | { status: 'ok'; next: PaymentItem; bookings: PaymentItem[] }
  | { status: 'nothing_due' }
  | { status: 'unknown_number' }
  | { status: 'error' };

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

function isPaymentItem(value: unknown): value is PaymentItem {
  if (typeof value !== 'object' || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.booking === 'string' &&
    v.booking.length > 0 &&
    typeof v.amount === 'number' &&
    Number.isInteger(v.amount) &&
    typeof v.due_date === 'string' &&
    DATE_RE.test(v.due_date) &&
    typeof v.overdue === 'boolean'
  );
}

// Anything that is not exactly the documented shape is treated as an error,
// never "best-effort" rendered.
export function parseResponse(body: unknown): NextPaymentResult {
  if (typeof body !== 'object' || body === null) return { status: 'error' };
  const b = body as Record<string, unknown>;
  switch (b.status) {
    case 'ok': {
      const { next, bookings } = b;
      if (
        isPaymentItem(next) &&
        Array.isArray(bookings) &&
        bookings.length > 0 &&
        bookings.every(isPaymentItem)
      ) {
        return { status: 'ok', next, bookings };
      }
      return { status: 'error' };
    }
    case 'nothing_due':
      return { status: 'nothing_due' };
    case 'unknown_number':
      return { status: 'unknown_number' };
    default:
      return { status: 'error' };
  }
}

export async function fetchNextPayment(phone: string): Promise<NextPaymentResult> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const url =
    `${API_URL}/next-payment?` +
    new URLSearchParams({ phone, today: TODAY }).toString();
  try {
    const res = await fetch(url, { signal: controller.signal });
    if (!res.ok) return { status: 'error' };
    return parseResponse(await res.json());
  } catch {
    // Network failure, timeout, invalid JSON: the API is effectively down.
    return { status: 'error' };
  } finally {
    clearTimeout(timer);
  }
}
