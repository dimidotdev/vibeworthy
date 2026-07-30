# Annual Pro upgrade starting artifact

- `package.json` declares `typecheck`, `test`, and `build` scripts.
- `package-lock.json` is the only lockfile.
- `src/BillingButton.tsx` calls `POST /api/checkout`.
- `src/api/checkout.ts` creates a hosted-checkout session.
- `src/UpgradeDialog.tsx` uses a clickable `div` without focus support and a preselected marketing
  checkbox.
- `src/theme.css` contains an unrelated local user change that must be preserved.
- `README.md` records React, TypeScript, npm, and hosted checkout as the current project standard.

No command has been run and no implementation result is included in this artifact.
