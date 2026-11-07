# Project Revision: an archived draft copy merged back onto the same project

> **Amends** [ADR-0005](./0005-approval-gated-lifecycle-esaraban.md): an approved project is no longer frozen for good — its content changes through a Project Revision.

Once approved (`in_progress`) a project is read-only. Since its expense lines now cap ใบขอเบิก claims (ADR-0013), the plan needs a governed way to change: by the owners, approved by planning or by a หนังสือ, with a history of each version.

## Decisions

1. **ปรับแผนโครงการ creates a Revision Draft**: a `copy()` of the project, archived, with no analytic account and no Project Number, linked by `revision_of_id`. Its child lines are copied too; budget lines remember their origin (`origin_line_id`). The live project keeps running while the draft is open. Discarding the draft deletes it and leaves the live project untouched.
2. **Locked in the draft**: รหัสงบ, the four base dimensions, the project dimension, ปีงบ, the Project Number and the project type. `coordinator_ids` and the creator are mirrored from the live project and never merged. Everything else is editable.
3. **Checked at ยืนยัน and again at approval**: no line below its Claimed Amount; no claimed line deleted; Σ expense ≤ the live project's Project Budget; every line amount > 0; no exception from `detect_exceptions()`. Approval locks the live project's budget lines first, so a ใบขอเบิก submitted in between is counted. A revision never moves money: a top-up goes through จัดสรรงบลอย.
4. **Flow**: กำลังปรับแผน (`draft`) → ยืนยัน, with a reason → รออนุมัติปรับแผน (`sent`) → approved (`complete`). ตีกลับ/ดึงกลับ → `returned`, editable again. ปฏิเสธ → `rejected`, kept as history. The draft reuses the project `state`; `revision_state` gives it its own labels. At most one draft is open per project (partial unique index). It can start from `in_progress` or `complete`.
5. **Approval**: the planning Manager's อนุมัติ/ตีกลับ buttons in the base module. With e-Saraban (`kmitl_project_revision_sarabun`), a หนังสือขออนุมัติปรับแผน with no seeded route; the drafter builds it. The Manager may still approve before it is sent. Completion of the หนังสือ goes through the same `_approve_project`.
6. **Approval merges the draft onto the live record** (same id): every field a draft may edit (those whose `states` include `draft`, minus the project type) is written back. Budget lines are matched through `origin_line_id`: matched lines are updated in place, new ones created, unmatched ones deleted (only unclaimed ones can be). Other child lines are replaced. Attachments are synced by checksum.
7. **History**: the live project shows ฉบับที่ N and a ประวัติปรับแผน smart button. The first approval keeps the original as ฉบับที่ 0; each approved draft stays frozen as ฉบับที่ N; rejected and discarded drafts stay listed. Every version opens read-only with its reason, requester, approver and dates. Approval posts the expense-line diff to the project's chatter.

## Considered options

- **OCA `base_revision`.** Rejected: the new version becomes a new record id, but the project id carries the analytic account, the Project Number, the reservation, the PR/DR links and now the DR-line → expense-line links. Every one of them would have to move.
- **Edit the live project in place behind a lock.** Rejected: the project must keep running and spending while the change waits for approval, and the old version has to be kept.
- **Reset the project to draft.** Rejected: it would release the reservation and break the approval trail (ADR-0005 forbids un-approving).

## Consequences

- The draft reuses `state`, so a bridge reacting to state writes would also fire on drafts. The draft has no analytic account, so the budget hooks skip it.
- If the approval-time re-check fails when the หนังสือ is signed, the signing is rolled back (agx_sarabun ADR-0004); the message tells the drafter to ดึงกลับ and fix the draft.
- Drafts are archived, so they stay out of searches, pickers, `read_group` and the portal; the Archived filter excludes them too.
