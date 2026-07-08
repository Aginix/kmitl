# Work Acceptance Portal Review

Committee review of a Work Acceptance (`work.acceptance`) from a token-secured portal page, with the review Todo delivered through the unified [Todos](../mail_activity_todo/CONTEXT.md) inbox. The portal route lets a committee member act without backend rights; the Todo gives them a single place to see the work waiting on them.

## Language

**Work Acceptance (WA, ตรวจรับ)**:
The `work.acceptance` document, the receiving check that closes out part of a PO. The thing being reviewed.
_Avoid_: Goods Receipt (that's `stock.picking`).

**Committee Member (กรรมการตรวจรับ)**:
A row of `work.acceptance.committee` listed on a WA. The person who must accept / reject / record absence for that WA. Identified by `employee_id`; must have `employee_id.user_id` set, otherwise the WA cannot be sent for review (`request_validation` raises). One committee member is one Todo recipient.
_Avoid_: Approver (that's the PA manager, see [Procurement Plan](../procurement_plan/CONTEXT.md)), Reviewer.

**Committee Token**:
The `access_token` on `work.acceptance.committee` (inherited from `portal.mixin`). Identifies *which* committee member is opening the portal, so the page shows their own accept/reject controls and records their decision against the right row. Different from the WA's own `access_token`, which only authorises reading the document.
_Avoid_: confusing with `wa_token` (the WA's access_token re-used in a PO portal URL).

**WA Portal Link**:
A URL of the form `/wa/view/<wa_id>?access_token=<wa_token>&committee_token=<committee_token>`. The page committee members open to review a WA — accept/reject buttons are gated on the committee_token. Reached from a [smart button](./docs/adr/0003-portal-links-as-smart-buttons.md) on the WA backend form (visible only when the current user is on the committee); the Todo's primary "Open Source" action lands the user on that form.

**PO Portal Link**:
A URL of the form `/purchase/view/<po_id>?access_token=<po_token>&wa_token=<wa_token>`. The supporting purchase order page a viewer of the WA can open to see what is being accepted against. Reached from a [smart button](./docs/adr/0003-portal-links-as-smart-buttons.md) on the WA backend form (visible when the WA has a linked PO).

**Review Todo**:
A `mail.activity` of type `mail_activity_type_wa_review`, category Approval — one per (committee user, WA). Scheduled when `request_validation()` runs; closed by `activity_feedback` when that committee member sets their `status`; unlinked (no log entry) when the WA returns to draft or the committee member is removed.
_Avoid_: Inbox entry (the standalone `work.acceptance.inbox` model and its systray were removed in [ADR-0001](./docs/adr/0001-committee-notification-via-mail-activity-todo.md); the term should disappear with the model).
