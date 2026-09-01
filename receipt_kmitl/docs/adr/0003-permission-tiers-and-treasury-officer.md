# Permission model: viewer/user/manager tiers + a separate Treasury Officer

Security is split across **two axes**. A hierarchical **tier** (a single dropdown)
governs how much a person can do; an orthogonal **Treasury Officer** checkbox
governs the one action that must be segregated — posting the accounting entries.

## Tiers (dropdown, each implies the one below)

- **Viewer** — read-only on receipts, remittances, payment methods.
- **User** (เจ้าหน้าที่หน่วยงาน) — create/edit/confirm/cancel receipts; create/edit/
  submit/detach/cancel remittances. **Cannot** post accounting.
- **Manager** — adds all configuration (payment methods, walk-in partner, exception
  rules). Implies Treasury Officer.

All tiers can open the app; menu visibility differs (root menu → Viewer;
Configuration menu → Manager).

## Treasury Officer (separate checkbox, implies User)

Only a Treasury Officer may move a remittance to `done`, which creates one
`account.move` per receipt. It therefore **implies `account.group_account_invoice`**
so the entries are created by the real acting user — `_create_move()` is **not**
sudo'd. This is the department-vs-treasury segregation of duties: a User submits,
a Treasury Officer receives and posts. It is a capability, not a seniority level,
so it is not part of the tier dropdown (a User either has the treasury hat or not).

## Consequences

- **Which records** a Treasury Officer sees is still an Operating Unit matter
  (ADR-0001), not this group — treasury staff typically also hold the
  "access all OUs" group.
- Users must select income accounts on receipt lines, so **read on
  `account.account` is granted at the Viewer tier** (regular internal users cannot
  read it otherwise). No other accounting rights leak to non-treasury users.
- The receipt's `move_id` / Accounting page is **hidden from anyone without the
  Treasury Officer group**, so a User opening a posted receipt never hits an
  `account.move` access error.
