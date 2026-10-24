# Plans close by hand and are deleted instead of cancelled, like KMITL Project

A plan is finished only by a manual **Close Plan** (ปิดแผน), and taken out of use only by **Plan Deletion** — the same semantics as KMITL Project (kmitl_project ADR-0011). Decisions D5, D7 and D9 of the 2026-10-24 review.

- **Close** is a plan-manager act, only from อยู่ในระหว่างดำเนินการ (`in_progress`) — a plan that never raised a purchase request is deleted, not closed. It is blocked while any purchase request, purchase order or disbursement request on the plan is open, and returns the unspent reservation (คืนจอง); the money stays at the plan's dimension as Held Money until a Floating Return. The old auto-close (commitment fully consumed → plan `done`) is removed: a fully-consumed reservation does not mean the procurement is finished, and an auto-closed plan could not take a top-up.
- **Delete** is three-way: no Ledger Footprint → hard delete with its analytic account; footprint but never spent → soft delete (ยกเลิก + archive plan and analytic account; Reset to Draft revives both with the same number); spent, Held Money or open documents → blocked. A numbered plan is deletable only by plan managers; Reset to Draft (which also revives a soft-deleted plan) is a plan-manager act too. ยกเลิก stops being a separate button.
- **Floating Return** (โอนคืนงบลอย) is the way out of Held Money, so it ships with this decision rather than waiting for the rest of ADR-0006: a Budget User returns the plan's money from the plan form, in any state, as a transfer that posts at once and releases the unobligated reservation in the same move.
- **No owner/coordinator model** (unlike kmitl_project ADR-0008): a plan belongs to its unit. ผู้รับผิดชอบ (`responsible_id`) only follows the plan with a "สถานะแผน" subtype. Operating-unit rules should cover write and unlink, not just read — **deferred** to a follow-up (2026-10-24): every cross-unit writer of a plan (purchase requests, transfers, appropriations) must sudo first.

## Consequences

- Migration: existing cancelled plans with no Held Money are archived so they read as soft-deleted (`procurement_plan` 16.0.1.4.0 archives every cancelled plan; `procurement_plan_budget` 16.0.1.2.0 re-activates those still holding money).
- Open documents: a purchase request not done/rejected/cancelled, a purchase order not done/cancelled, a disbursement request not paid/cleared/cancelled.
