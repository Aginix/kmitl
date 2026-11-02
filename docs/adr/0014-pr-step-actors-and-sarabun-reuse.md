# พ.1: who presses each button, step-back from รออนุมัติ, and the หนังสือ is reused

## Status

Accepted. Narrows [ADR-0010](0010-pr-split-verify-and-budget-commit-direct-entry.md)'s
"the requester's ดึงกลับ (Reset) goes to `draft`" and replaces the PR's Resend-to-Sarabun.

## Context

Before this ADR, the requester side of a พ.1 had no clear owner. Anyone in PR User could
submit. Cancel was open to every PR User: All Documents at almost every state. ดึงกลับ
was keyed on `requested_by` or the PR manager, and at `to_approve` only the manager could
press it. Anyone could press สร้างหนังสือ. A PR returned by Sarabun could only be re-sent
as-is or cancelled. Sarabun's ดึงกลับ (แก้ไข) moved the PR to `returned`, and its
ยกเลิกการส่ง cancelled the PR but left the ใบจอง live.

## Decision

- **Three requester-side roles:**
  - **ผู้จัดทำ** is the PR's `user_id`.
  - **ธุรการ** is the PR's `create_uid`, and may be the same person as the ผู้จัดทำ.
  - **พัสดุ** is anyone in `purchase.group_purchase_user`.
- **Before the budget is reserved, the requester side belongs to the ผู้จัดทำ alone:**
  - ส่งคำขอ from `draft`.
  - ยกเลิก, and only from `draft`.
  - ดึงกลับ → `draft` from `to_verify` and `to_verify_budget`.
- **From `to_approve` on, ผู้จัดทำ / ธุรการ / พัสดุ may act:**
  - สร้างหนังสือ.
  - ดึงกลับ → `draft`.
  - ตีกลับ → `to_verify_budget`, with a reason.
  - ดึงกลับ → `draft` from `returned`. This replaces Resend-to-Sarabun.
- **The ผู้จองงบประมาณ พ.1 may ดึงกลับ `to_approve` → `to_verify_budget`.** Both ways back
  to `to_verify_budget` keep the ใบจอง live and clear the committer's stamp, so pressing
  ยืนยันงบประมาณ again re-advances on the same ใบจอง.
- **Cancel exists only at `draft` before Sarabun.** A PR at `to_verify` … `returned` must
  first be pulled back to draft. Cancel after approval (`in_progress`, `in_egp`,
  `in_approval`) is unchanged.
- **The หนังสือ outlives a pull-back.** สร้างหนังสือ reopens the PR's live หนังสือ (`draft`
  or `returned`) instead of creating a new one, so a PR returned by Sarabun walks the
  normal path again and is re-sent on the same หนังสือ. The หนังสือ can only be sent while
  the PR is at `to_approve`, and the PR's circulating callback raises otherwise.
  Only that หนังสือ's sender can edit and send it, so another team member pressing
  สร้างหนังสือ gets an error naming the sender instead of a second หนังสือ.
- **Sarabun ดึงกลับ (แก้ไข) puts the PR back at `to_approve`, not `returned`.** The sender
  edits the หนังสือ and re-sends it. An admin Reset from any other PR state keeps the
  ตีกลับ handling.
- **Pulling back or cancelling releases the ใบจอง as superuser**, after the step check,
  because ผู้จัดทำ / ธุรการ / พัสดุ hold no budget rights. This is the same pattern as Reserve.
- **Every cancel path releases the ใบจอง.** The release moved from `button_cancel`, which
  only opens the reason wizard, to `_action_do_cancel`. This covers Sarabun's ยกเลิกการส่ง,
  and dismissing the wizard no longer cancels the ใบจอง.
- **All checks also run in Python.** Superuser mode passes, as in ADR-0010.

## Consequences

- PR managers lose their override on ดึงกลับ at `to_verify` / `to_verify_budget` /
  `to_approve`.
- พัสดุ act at `to_approve` / `returned` through the PR's normal access rules. A Purchase
  User with no access to the PR still cannot open it.
- While a PR is back in `draft`, its returned หนังสือ stays visible as รอการแก้ไขเอกสาร.
