// Where the API lives. On a physical phone "localhost" is the phone itself, so
// set EXPO_PUBLIC_API_URL to your computer's LAN address (see README).
export const API_URL = (process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');

// "Today" is a parameter for this task, never the device clock.
export const TODAY = process.env.EXPO_PUBLIC_TODAY ?? '2026-10-26';

// After this long with no answer we treat the API as down.
export const REQUEST_TIMEOUT_MS = 8000;
