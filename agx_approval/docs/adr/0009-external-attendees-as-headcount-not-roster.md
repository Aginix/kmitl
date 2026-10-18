# ADR-0009: External attendees are a headcount and a note, not a roster

## Status

Accepted

## Context

Every row of the plan's "รายชื่อบุคคลภายนอก" required a `res.partner`. Regular
users cannot create contacts, so requesters had to ask someone to create one,
with a name, ID number and bank account the approval stage never uses. When the
cost is settled by สำรองจ่าย or เงินยืม the recipient must be internal anyway, so
the external contact was never used.

## Decision

- **บุคคลภายนอก is no longer listed per person.** The plan records a headcount
  (`external_participant_count`) and a free-text description
  (`external_participant_note`).
- **นักศึกษา are still listed per person**, by picking a contact of the student
  partner type (`partner_type_kmitl.partner_type_student`).
  `participant_type` is now `internal` or `student`.
- **The "no participants" exception passes when the headcount is above zero.**
- **The actual-stage ผู้รับเงิน is unchanged.** It may be any contact. A
  direct-pay external payee without a contact is created by finance or the
  contact admin at that point, as for vendors.
- **Migration (16.0.1.7.0):** external rows whose contact is a student become
  student rows. All other external rows are folded into the count and the note
  (`ชื่อ — รายละเอียด`) and then deleted.

## Consequences

- **Hard to reverse.** The migration deletes the external rows; only the folded
  text survives, so the per-person roster cannot be rebuilt.
- **No per-person external data on the plan.** Contacts folded away no longer
  appear in the partner and employee smart-button counts, which key on
  `participant_ids.partner_id`.
- **The หนังสือ e-Saraban body reuses the PDF body**, so it shows the external
  line too.
