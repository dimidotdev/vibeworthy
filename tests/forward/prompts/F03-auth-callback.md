Use $vibeworthy. Read `skill/vibeworthy/SKILL.md` completely and load only the directly linked
resources needed for this request. Respond to the request as you would to the user. Do not evaluate
your own response and do not modify files.

Review this public release candidate for order tracking. Authenticated users fetch orders by ID and a
partner sends status-change callbacks. Orders contain personal data. I need to know which risks and
verifications are in scope before launch.

Starting artifact:

- `src/api/orders.ts` checks only that a session exists, then fetches the supplied order ID without
  owner or tenant in the query predicate.
- `src/api/partner-callback.ts` accepts JSON and `eventId`, but validates no signature, timestamp, or
  replay and retries without a limit after failure.
- `src/OrderNote.tsx` renders `noteHtml` through `dangerouslySetInnerHTML`.
- `evidence/asvs-5.0.0.csv` is an official pinned ASVS 5.0.0 snapshot with source URL, date, and
  SHA-256, but its individual rows are not reproduced in this prompt.

Do not invent ASVS IDs that you cannot inspect. Give an evidence-based release recommendation.
