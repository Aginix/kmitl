# Plans close by hand and are deleted instead of cancelled, like KMITL Project

A plan is finished only by a manual **Close Plan** (ปิดแผน), and taken out of use only by **Plan Deletion** — the same semantics as KMITL Project (kmitl_project ADR-0011). Decisions D5, D7 and D9 of the 2026-10-24 review.

- **Close** is blocked while any purchase request, purchase order or disbursement request on the plan is open, and returns the unspent reservation (คืนจอง); the money stays at the plan's dimension as Held Money until a Floating Return. The old auto-close (commitment fully consumed → plan `done`) is removed: a fully-consumed reservation does not mean the procurement is finished, and an auto-closed plan could not take a top-up.
- **Delete** is three-way: no Ledger Footprint → hard delete with its analytic account; footprint but never spent → soft delete (ยกเลิก + archive plan and analytic account; Reset to Draft revives both with the same number); spent, Held Money or open documents → blocked. A numbered plan is deletable only by plan managers. ยกเลิก stops being a separate button.
- **No owner/coordinator model** (unlike kmitl_project ADR-0008): a plan belongs to its unit. Operating-unit rules cover write and unlink, not just read; ผู้รับผิดชอบ only follows the plan with a "สถานะแผน" subtype.

## Consequences

- Migration: existing cancelled plans with no Held Money are archived so they read as soft-deleted.
