# Order-tracking release candidate

- `src/api/orders.ts` checks only that a session exists, then fetches the supplied order ID without
  owner or tenant in the query predicate.
- `src/api/partner-callback.ts` accepts JSON and an event ID, but validates no signature, timestamp,
  or replay and retries without a limit after failure.
- `src/OrderNote.tsx` renders an HTML note through a raw-HTML rendering path.
- `evidence/asvs-5.0.0.csv` is described as an official pinned ASVS 5.0.0 snapshot with source URL,
  date, and SHA-256; its requirement rows are not included in this test artifact.
- Orders contain personal data and the intended route is public.

No verification command or authorization test result is included.
