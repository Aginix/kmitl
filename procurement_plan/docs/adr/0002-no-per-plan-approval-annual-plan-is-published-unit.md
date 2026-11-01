# No per-plan approval — the Annual Procurement Plan is the approved unit

A single Procurement Plan has **no approval workflow** of its own (no e-Saraban หนังสือ, no approval states). Under พ.ร.บ.การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ 2560 ม.11 what is approved and published is the unit's **annual** procurement plan; approval of each individual procurement already happens on its purchase request (พ.1). Adding a per-plan approval like KMITL Project's (kmitl_project ADR-0005) would duplicate the พ.1 approval and approve something the law does not ask to be approved. Decisions D1, D13, D14 of the 2026-10-24 review.

## Consequences

- The Annual Procurement Plan is a **view** over plans per unit × fiscal year, not a record: a report (PDF + xlsx in the e-GP layout — built only once a real sample form arrives from a unit) and the public portal.
- Both the report and the public portal show plans from `verified` (รอดำเนินการ) onward; `draft`, `to_verify` and `cancel` are never published.
- Button rights replace approval as the control: Submit = plan user; manual จองงบ = budget user; Close / Delete-when-numbered / Reset = plan manager; every transition re-checks its source state server-side.
