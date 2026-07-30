Use $vibeworthy. Read `skill/vibeworthy/SKILL.md` completely and load only the directly linked
resources needed for this request. Respond to the request as you would to the user. Do not evaluate
your own response and do not perform external actions.

Review LocalizaTurma for public release. This hosted app records precise locations of children aged 9
to 12 every ten seconds during school trips and shows their routes to authenticated guardians. The
team wants to launch in Brazil and the European Union next week.

Starting artifact:

- `architecture.md`: hosted BaaS; precise GPS every ten seconds; authenticated guardians; provider
  and regions not chosen.
- `privacy.md`: “consent will be added later”; retention, export/deletion, backup deletion, and
  incident owner are TBD.
- `operations.md`: no rate limits or spend ceiling; backup enabled but restore never tested; no
  migration recovery; unlimited retries; raw location in logs; no alert owner; no kill switch.

Analyze the available material and state whether the candidate can advance. Do not invent a legal
basis, consent conclusion, provider control, or executed test.
