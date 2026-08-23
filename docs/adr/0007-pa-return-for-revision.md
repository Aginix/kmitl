# ตีกลับ/แก้ไข: cross-model PA→PR return with `pending_pr` park, full PA resync on revive, and soft-void sarabun

Once a พจ.1 (PA) is auto-created off a Sarabun-approved พ.1 (PR)
([ADR-0005]), the only prior negative-path options were:

- **Cancel** (`_action_do_cancel`) — cascades PA + PR to `cancelled`;
  the พจ.1 number is voided; downstream flow is dead.
- **Sarabun-approver ตีกลับ** — lands PA in `sarabun_returned`;
  the correction is on PA fields only (the PR is untouched).

Neither covers a common real case: the requester (or PA drafter) realises
the underlying **พ.1 data is wrong** (bad title/lines/tax/vendor), needs to
revise it, and does **not** want to burn the พจ.1 number or force a fresh
Sarabun request from scratch. God Mode ([ADR-0006]) does not help either —
its scope is post-approval PA-only surgical edits, not a PR revision.

**Decision.** Introduce a scoped negative-path transition **"ตีกลับ/แก้ไข"**
(keep-number PA-to-PR return) that spans the PA and PR boundaries in one
click, and revives cleanly when the PR flow re-completes.

Lifecycle effect, one click, one wizard (mandatory reason only):

- **PA** → new state `pending_pr` (parked; `name` retained).
- **PR** → `to_submit` (budget commitment intact).
- **PR's active sarabun** → soft-voided (`state='cancelled'` via `sudo`,
  register number **kept**).
- **Redirect** to the PR form.

On the revive path — when the same PR's sarabun re-completes and
`_transition_after_sarabun_approve` runs on the PR:

- If an existing PA is `pending_pr`, **write
  `_prepare_approval_sync_vals()` onto it** (all PA-copied fields refreshed
  from the current PR — see below), then flip state to `draft`.
- The `sarabun.document` is re-used via `_restart_chain` + `state=draft`
  (invoked from the PR's `action_submit_to_sarabun` override, which
  short-circuits to `_resume_returned_sarabun` when
  `can_resume_returned_sarabun` is True). Same document, same registered
  number.

Two deliberate contradictions with prior ADRs, documented so a future
reader is not surprised:

- **Against [ADR-0004] "PA copied but free to diverge":** the revive
  **overwrites** every PA-own field (`title`, `description`,
  `procurement_type_id`, `procurement_method_id`, `account_fiscal_year_id`,
  `payment_type`, `partner_id`, `vat_included`, `tax_id`, `line_ids`) with
  the PR's current values. Divergence made on the PA (e.g. a vendor
  change, or a God-Mode header edit) is **discarded** at revive. The
  framing is: a ตีกลับ/แก้ไข is a **restart**, not a tweak — the PR is
  authoritative for the fresh cycle. Only immutable identity fields
  (`request_id`, `date_start`, `origin`, `state`, `validation_status`) are
  omitted from the resync.
- **Against [agx_sarabun ADR-0006] "cancelled = terminal + voided
  number":** the soft-void writes `state='cancelled'` without calling
  `_void_register`, so the register number stays `used` and the doc is
  later un-cancelled by `_restart_chain + state=draft`. A real
  `action_recall` cancel and a soft-void look identical when inspecting
  only the `state` field. The register-number consistency is preserved
  (never revive a doc whose number has been voided).

Naming choice — the parked PA state is `pending_pr`, not a bare `returned`:

- `returned` is already reserved in `purchase_request_approval_disbursement`
  (a different domain — return-for-disbursement-correction). Reusing it
  would collide.
- `pending_pr` says the same thing more precisely for the reader: "the PA
  is waiting on the PR to be revised and re-sent". Statusbar hides it
  (`statusbar_visible` list unchanged).

## Considered options

- **Cancel + start over (status quo before this ADR)** — rejected.
  Voids the พจ.1 number, kills downstream artefacts, forces a fresh
  Sarabun cycle for what is often a title/line/tax typo.
- **Extend God Mode to allow PR-side edits** — rejected. God Mode is a
  **PA-side surgical** correction while the PA holds a live `to_approve`
  or `approved` state ([ADR-0006]); crossing model boundaries and
  reopening the PR is out of its charter.
- **Keep the earlier three-mode wizard** (keep-number, new-number,
  cancel-all) — rejected during grilling. New-number is redundant with
  cancel-then-recreate; cancel-all overlaps the existing Cancel button.
  Simpler UI: one action, one field (reason).
- **Reset sarabun to `draft` immediately at wizard confirm (single-step
  revive)** — rejected. It hides a heavy operation (`_restart_chain` on
  the originator step under `sudo`) behind a modal close. The two-step
  flow (park now → user clicks the same "Create Sarabun" button to revive
  on the PR form) puts the revive under a visible, deliberate user action.
- **Add a new dedicated "ส่งเรื่องสารบรรณ" resume button on the PR** —
  tried, rejected. It duplicated the Create Sarabun UX. The final
  approach overrides `action_submit_to_sarabun` on `purchase.request`:
  if `can_resume_returned_sarabun` is True → revive; else → super (fresh
  doc). One button, right behaviour by context.

## Consequences

- **The base `_prepare_approval_vals` becomes the single source of truth
  for both create and resync.** A new helper
  `_prepare_approval_sync_vals` derives from it by dropping identity
  fields and turning `line_ids` into `[(5, 0, 0)] + [(0, 0, {...})]`.
  Downstream modules that extend `_prepare_approval_vals` participate in
  the resync automatically — usually the right thing; if a field must
  survive across ตีกลับ, it should not be sourced from `_prepare_approval_vals`
  in the first place.
- **Origin-driven sarabun fields (`subject`, `sender_department_id`)** are
  re-sourced from the (edited) PR when `_resume_returned_sarabun` writes
  `state='draft'` back to the document, so a title change on the PR is
  reflected on the หนังสือ header on the revived cycle.
- **`button_create_approval` exists-check filters out `state='cancelled'`
  PAs.** Necessary so a Cancel → later re-send flow can spawn a fresh PA;
  a PA parked in `pending_pr` continues to gate creation as before.
- **`_transition_after_sarabun_approve` behaviour is now polymorphic**:
  no PA → create; PA in `pending_pr` → resync + flip to `draft`; PA in
  any other non-cancelled state → **no-op** (defensive; not expected in
  normal flow).
- **Known limitations, accepted:**
  - The revive picks the latest cancelled sarabun by `id`. Edge case
    (multi-cancelled history from a prior real `action_recall`) picks the
    wrong doc. Real-world rare because a real recall requires
    `not has_signed`.
  - A PA in `draft` no longer has a direct Cancel button. Cancelling
    such a PA outright requires: ตีกลับ/แก้ไข first (PA → `pending_pr`,
    PR → `to_submit`), then Cancel from the PR side; the PA stays
    orphaned in `pending_pr` unless cleaned up by an admin. Future
    iteration may auto-cascade PA `pending_pr` → `cancelled` when the PR
    cancels.
- **Reinforces [ADR-0005]** on the state-split direction (new negative-
  path states live in their own key; drawio v2 remains the reference for
  positive-path lifecycle). **Amends the divergence guarantee of
  [ADR-0004]** for this one path.

[ADR-0004]: 0004-pa-owns-copied-data.md
[ADR-0005]: 0005-post-sarabun-state-split.md
[ADR-0006]: 0006-pa-godmode-edit.md
[agx_sarabun ADR-0006]: ../../agx_sarabun/docs/adr/0006-recall-split-pullback-vs-cancel-send.md
