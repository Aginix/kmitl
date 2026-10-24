# disbursement_wc: Implementation Plan (สถานี for the ใบขอเบิก)

> **Status:** design settled, nothing built. The only code in the tree is `work_center/`
> from PR #1510, unmerged, still implementing the superseded ADR-0001.
> `disbursement_wc/` holds only its glossary and ADR-0001. This plan is for an
> implementer who **did not sit in the 21-question design interview**. It turns the
> settled decisions into 13 stacked PRs. None of them merges into `16.0` until the
> product owner (PO) accepts a pilot on a **copy of the local snapshot DB
> `snapshot-2610220031`**. The shared UAT DB is not touched at any point. **No test in
> this plan has been run** (CLAUDE.md: tests run only when the user asks).
>
> **Authoritative sources (read first, they win on any conflict):**
>
> - `disbursement_wc/CONTEXT.md`: the station glossary. Use its terms exactly and honour
>   every _Avoid_.
> - `disbursement_wc/docs/adr/0001-the-route-is-the-only-control.md`: ordering is
>   recorded, not enforced.
> - `work_center/docs/adr/0002-a-work-center-is-a-station.md`: supersedes `work_center`
>   ADR-0001.
> - `disbursement/CONTEXT.md` (its banner marks the retiring terms) and
>   `disbursement/docs/adr/0001..0004`.
> - The settled decisions D1-D19 (§0.4). This plan works inside them. Where it extends
>   or amends one, §8 says so and names the PO sign-off it needs.

---

## 0. Status, scope and authoritative sources

### 0.1 Who this is for

This plan is for a developer, or an agent, who builds the PRs below without having been
in the design interview. Read the sources above, then §1 and §2, before opening any PR.
Every PR in §3 lists its own files, tests, checks and risks, so it can be built and
reviewed alone.

### 0.2 Scope

- **In scope:**
  - rewrite `work_center` into a generic station engine;
  - collapse the DR state to `draft / submitted / signed / in_progress / done / cancel`;
  - add the money axis ขั้นการชำระ (`settlement_stage`);
  - replace `READONLY_STATES` with `can_edit_*` flags;
  - split each act into its capability module;
  - plug the DR into the engine (`disbursement_wc`);
  - update every dependent that reads the old states.
- **Pilot:** runs on a copy of `snapshot-2610220031`, cloned with the
  `odoo-real-db-test` recipe. In-flight DRs are cancelled and finished DRs are mapped by
  an odoo-shell snippet (§3 PR6 and PR11). Nothing touches UAT.
- **No migrations.** The DB is pre-prod and its schema is disposable. Data intent goes
  into runtime code. One-off fixes go into `.context/` odoo-shell snippets. `.context/`
  is git-excluded (`.git/info/exclude`), so it lives only in this workspace: attach the
  snippets to the PR description (PR6 and PR11) so the next person has them.
- **Merge rule (D18):** no PR in this plan merges into `16.0` before the PO accepts the
  pilot. Deploys rebuild the image by re-cloning branch heads, so any merge reaches UAT.
  After acceptance, PR1-PR12 merge in stack order in one window, and the `.context`
  snippets run on UAT in that same window. PR6 on its own must never merge: it would
  leave DRs stuck at `signed`, leave orphan state values, and lose the payment-audit
  Todos.

### 0.3 Fate of PR #1510, and who must be told

- PR #1510 (`16.0-add-work_center`, author GitHub **@n3n**, Nonpawit Teerachetmongkol)
  is **rewritten in place** as PR1. It keeps the same branch and PR number and gets a
  new title. Its ADR-0001 stays as history, marked superseded.
- **Before any force-push**, comment on #1510 and wait for @n3n to acknowledge. The
  comment should say:
  - ADR-0001 (stamped owning unit) is superseded by ADR-0002 (station);
  - the branch will be force-pushed with the station engine;
  - the closed bridges in #1576 assume the owning unit and would have to be redone.

### 0.4 Settled decisions (do not re-litigate)

| #   | Decision                                                                                                                                                                                                                                                                                                                                                                                                                               |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | For the DR, a work center is a **สถานี**: a desk at the level of a step, not of a person. `ศูนย์งาน` is retired in UI and th.po.                                                                                                                                                                                                                                                                                                       |
| D2  | A station **is** a `work.center` record. The work_center core is rewritten into a generic station engine (ADR-0002) that reuses areas, counters, the kanban, the Unassigned card and rules.                                                                                                                                                                                                                                            |
| D3  | DR state becomes `draft, submitted, signed, in_progress, done, cancel`. Retired: `verified`, `approved`, `approval_state`, the two-approver step, the two OWL approver queues, `action_approve_batch`, `pipeline_status`, `display_status`, and `bills_posted / payment_audited / payment_authorized / paid / cleared`.                                                                                                                |
| D4  | The current station is one pointer field plus an append-only สมุดเยี่ยม (arrived, left, mover, act, override reason, frozen responsible set). The standard route is configuration, read live.                                                                                                                                                                                                                                          |
| D5  | At a station the user can press its acts, **ส่งต่อ** to the next station on the route, or **divert** to any station of the same area. After a divert, "next" = the station after the last on-route station visited.                                                                                                                                                                                                                    |
| D6  | A station declares **allowed** and **required** acts. Forward may skip a missing required act only with a mandatory reason, which is logged. Divert ignores required acts.                                                                                                                                                                                                                                                             |
| D7  | No hard ordering. Ordering guards written against state are **removed, not ported**. Only integrity checks stay.                                                                                                                                                                                                                                                                                                                       |
| D8  | The requester is not a station. Send-back to the maker leaves the circuit to `draft`. It is a different action from divert, and members of the station holding the DR can press it.                                                                                                                                                                                                                                                    |
| D9  | A corrected DR, resubmitted, re-enters at the **first station** without a new head signature.                                                                                                                                                                                                                                                                                                                                          |
| D10 | The **วงจร** runs from หมวดตรวจ to อนุมัติจ่าย. A station exists only where a person presses something **on the DR**.                                                                                                                                                                                                                                                                                                                  |
| D11 | **เสร็จสิ้น (`done`)** = forwarded out of the last station. It says nothing about money.                                                                                                                                                                                                                                                                                                                                               |
| D12 | **ขั้นการชำระ** `none → billed → settled → booked` is a stored compute derived from the bills and vouchers that exist. It walks back by itself. Guard the empty-recordset `all()` trap.                                                                                                                                                                                                                                                |
| D13 | Locks are `can_edit_*` computed booleans: (current station allows it) AND (`settlement_stage == 'none'`). `READONLY_STATES` and every `states=` are deleted. UI only. `_banking_editable` stays the one enforced lock.                                                                                                                                                                                                                 |
| D14 | Authority = the user holds the role AND is a member of the holding station. Membership narrows and never grants. A memberless station is open to all role holders. Forward, divert and send-back are for members of the current station.                                                                                                                                                                                               |
| D15 | On arrival the visit freezes who was responsible (members, or role holders if there are none). Who may act is decided live. An actor missing from the snapshot is evidence, not a breach.                                                                                                                                                                                                                                              |
| D16 | Modules split by **capability**; stations are **data**. `work_center` = engine. `disbursement_wc` = plugs the DR in. Act families: `disbursement_validation`, `disbursement_approver_director`, `disbursement_approver_rector`, `disbursement_budget` (consumes on its own act, plus a per-DR flag), and `disbursement_accounting` (= `disbursement_accounting_kmitl`). There are **no** `disbursement_wc_*` modules.                  |
| D17 | **Act registry:** capability modules declare acts in Python, and a sync step reflects them into records. No XML seeding of acts.                                                                                                                                                                                                                                                                                                       |
| D18 | No migration. The pilot runs on a copy of `snapshot-2610220031` with in-flight DRs cancelled. UAT is untouched until the pilot is accepted.                                                                                                                                                                                                                                                                                            |
| D19 | Defaults: entry is automatic at `signed`; one arrival Todo per responsible user, closed when the DR leaves; divert stays within one area; after `done`, money walking back leaves the DR `done` and sends a Todo to the station that last forwarded it; the signature block stays and each act stamps its own row; the `cancel` key stays; `disbursement_assignment_kmitl` keeps its name and assigns an officer **inside** a station. |

### 0.5 Repo rules that bind every PR

- **Naming.** Branch `16.0-{add|imp|fix}-{module}`. PR title
  `[16.0][TYPE] module: description`. Commit `[TYPE] module: description` with **no
  `Co-Authored-By` line**: CLAUDE.md takes precedence over the harness attribution.
- **Strings.** Code and UI source strings are English. Thai goes in `i18n/th.po`, edited
  by hand with `#:` lines. There is no `.pot` and CI is off, so `msgfmt -c` is the only
  mechanical check.
- **Tests.** Existing suites are **repaired in place**, never extended with new test
  files or new test methods. Only brand-new modules get a minimal `tests/`, and they are
  marked **never run**.
- **noupdate.** A field added to a `noupdate="1"` record never reaches an installed DB.
  Only admin-edited data (stations, route, counters) may be `noupdate="1"`.
- **Odoo 16 traps.**
  - `@api.depends` accumulates across overrides, so each override declares only what it
    adds.
  - Stored computes run lazily.
  - A list `_inherit` that adds a mixin needs an explicit `_name`.
  - `fields.Json` turns `[]` into `False`.
  - Call `invalidate_all()` before every `with_user()` probe.
  - A new stored column is stamped with its default on every existing row.
  - `required` is ignored on monetary and float fields.
  - A field repeated in one form takes its model-level modifiers from the **last** node.
- **Docs.** READMEs are hand-written, and the `oca-gen-addon-readme` pre-commit hook is
  SKIPped (it leaves a pandoc artifact). CONTEXT.md files are glossaries only. Write an
  ADR only for a hard-to-reverse, surprising trade-off.

---

## 1. What changes in one page

### 1.1 Module map, before and after

**The original 11-module plan from the interview:**

- `work_center`
- `disbursement_wc`
- four per-desk `disbursement_wc_*` station modules
- `disbursement_validation`
- `disbursement_approver_director`
- `disbursement_approver_rector`
- `disbursement_budget`
- `disbursement_accounting`

**Target shape: `work_center` plus six disbursement-side modules.**

| Module                           | Status                           | Role                                                                                                                                                                              |
| -------------------------------- | -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `work_center`                    | rewritten (PR1, #1510)           | Generic station engine: areas, stations, routes, the act registry, the visit log, the move engine, authority, arrival Todos, counters and the kanban. Knows nothing about the DR. |
| `disbursement_wc`                | new code (PR11), docs exist      | The only bridge between the DR and the engine: circuit entry and exit, resubmit, station-aware act and edit authority, the walk-back Todo, seeded area, stations and route.       |
| `disbursement_validation`        | new (PR8)                        | ตรวจสอบ act (`disbursement.validate`), with verifier stamps and the `verify` signature row.                                                                                       |
| `disbursement_approver_director` | new (PR9)                        | ผอ.กองคลัง act (`disbursement.approve_director`).                                                                                                                                 |
| `disbursement_approver_rector`   | new (PR10)                       | ผู้รับมอบอำนาจอธิการบดี act (`disbursement.approve_rector`).                                                                                                                      |
| `disbursement_budget`            | exists, reshaped (PR7)           | Budget-consume act (`disbursement.consume_budget`) and the `consumes_budget` flag.                                                                                                |
| `disbursement_accounting_kmitl`  | exists, reshaped (PR2, PR4, PR6) | `disbursement_accounting` of D16: create-bill act and the bill leg of ขั้นการชำระ.                                                                                                |

`disbursement_finance_kmitl` already exists and becomes the act family for ตรวจจ่าย /
อนุมัติจ่าย (`disbursement.audit_payment`, `disbursement.authorize_payment`). D16 does
not name it, so it is listed in §8 for confirmation.

**Why the four `disbursement_wc_*` modules do not exist:** a station is a `work.center`
record (D2, D16). Adding a desk means adding a record and, if it needs new behaviour, an
act in a capability module. A module per desk would hard-code configuration and break
"adding a station never needs a new act" (glossary, การกระทำ).

**Dependency rule:**

- Core `disbursement` never depends on `work_center`.
- Capability modules depend only on core, or on their money bridge.
- Only `disbursement_wc` and `disbursement_assignment_kmitl` (from PR12) pull in the
  engine.

### 1.2 DR state machine, before and after

**Before** (`disbursement` plus bridges, three tangled fields):

```
state:          draft → submitted → signed → verified → approved → bills_posted → payment_audited → payment_authorized → paid → cleared
                  ↑________ action_draft (from submitted/signed/verified/cancel)           (accounting)    (finance ……………………………………………………)
                any → cancel
approval_state: none → pending_finance → pending_rector → approved | rejected → (request again)
pipeline_status / display_status: stored mirrors of the above
locks: READONLY_STATES / states= (UI only)
```

**After** (two independent axes):

```
state (progress around the วงจร):
  draft ──action_submit──▶ submitted ──(Saraban completes) action_sign──▶ signed ──_on_signed──▶ in_progress @ station 1
    ▲                                                                                              │  ส่งต่อ / divert move the pointer
    │◀── send-back (Return wizard → action_draft) ◀────────────────────────────────────────────────┤
    │── resubmit (returned_for_edit) ─▶ signed ─_on_signed─▶ in_progress @ station 1 (no new head signature)
                                                                       ส่งต่อ out of the last station ─▶ done (เสร็จสิ้น)
  any not-done ──action_cancel──▶ cancel                         (signed persists only when no route is configured)

settlement_stage (ขั้นการชำระ, derived, never written):
  none ─(all active bills posted)─▶ billed ─(every payee has a live voucher and all are finance-paid)─▶ settled ─(all posted)─▶ booked
  walks back by itself (bill reset, voucher cancel, cheque bounce)

locks: can_edit_header / lines / attachments / dimensions / budget = station allows it AND settlement_stage == 'none' (UI only)
enforced lock: disbursement_payment_line._banking_editable (rekeyed to "no voucher yet")
```

### 1.3 What is retired

| Retired                                                                                                                  | Replaced by                                            | PR                                         |
| ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------ | ------------------------------------------ |
| `verified`, `approved` states                                                                                            | `in_progress` at a station, then `done`                | PR6                                        |
| `bills_posted`, `payment_audited`, `payment_authorized`, `paid`, `cleared`                                               | `settlement_stage` (money); the station (who holds it) | PR2 + PR6                                  |
| `approval_state`, `approval_reject_reason`, reject wizard, Request Approval Again                                        | divert, send-back and the สมุดเยี่ยม                   | PR6                                        |
| `pipeline_status`, `display_status`                                                                                      | `state` plus `settlement_stage`                        | PR2 + PR6                                  |
| OWL approver queues (`static/src/approval_queue/`), Approved history, Approver menus                                     | station kanban cards and counters                      | PR6 / PR11                                 |
| `action_approve_batch`                                                                                                   | none (a station-kanban batch press is out of scope)    | PR6                                        |
| Return-to-verification flow                                                                                              | divert to สถานีหมวดตรวจ                                | PR6                                        |
| `_on_final_approval` hook                                                                                                | the `disbursement.consume_budget` act                  | PR7                                        |
| `READONLY_STATES`, every `states=` on DR fields                                                                          | `can_edit_*` flags in view `attrs`                     | PR2                                        |
| `work_center_manual` ("Pinned"), the stamped and sticky pointer                                                          | a pointer moved only by the engine                     | PR1                                        |
| Activity types `dr_approve_finance`, `dr_approve_rector`, `dr_rejected`, `dr_reverify`, `dr_to_audit`, `dr_to_authorize` | one generic arrival Todo type                          | PR6 (XML); the snippet removes the DB rows |
| The word ศูนย์งาน in UI and th.po                                                                                        | สถานี                                                  | PR1                                        |

---

## 2. Data model

### 2.1 `work_center` (engine)

**`work.center` (reshaped).** `_description` becomes `"Station"`; the technical name
stays.

| Field                                                                                  | Type                                                                                                         | Purpose                                                                                                       |
| -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| `member_ids`                                                                           | M2m res.users (same `work_center_member_rel`)                                                                | **สมาชิกสถานี.** Narrows authority. Empty = open to role holders. Members move the DR.                        |
| `allowed_act_ids`                                                                      | M2m `work.center.act` (`work_center_allowed_act_rel`), domain `kind='act'`, `context={'active_test': False}` | Acts offered here.                                                                                            |
| `required_act_ids`                                                                     | M2m `work.center.act` (`work_center_required_act_rel`), domain `kind='act'`, `active_test False`             | Needed in **this visit** before forward. Must be a subset of allowed.                                         |
| `allowed_edit_ids`                                                                     | M2m `work.center.act` (`work_center_allowed_edit_rel`), domain `kind='edit'`, `active_test False`            | Which parts of the document may be edited here (feeds `can_edit_*`). These are not acts.                      |
| `area_model_ids`                                                                       | related `area_id.model_ids`                                                                                  | Domain helper.                                                                                                |
| `is_my_station`                                                                        | Boolean, non-stored, `_search_is_my_station`                                                                 | Member, or memberless and holding one of its role groups (template: `mail_activity_todo._search_is_my_todo`). |
| `operating_unit_id`, `is_unassigned`, `rule_ids`, `counter_data`, `company_id`, `code` | kept                                                                                                         | Helps reworded (§3 PR1).                                                                                      |

Constraints:

- required ⊆ allowed;
- every act's model is in `area_id.model_ids`;
- the Unassigned card has no acts, no edits and no members;
- **a real (non-Unassigned) station has at least one allowed act or one member**;
- `unlink` is refused with "archive it instead" while visits reference the station.

**`work.center.mixin` (reshaped).**

| Field                            | Type                                                                                                         | Purpose                                                                                        |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| `work_center_id`                 | M2o work.center, **plain stored**, `readonly=True`, `index`, `copy=False`, `tracking`, `ondelete='restrict'` | The pointer. Only `_work_center_move` writes it. No default, so nothing is stamped at install. |
| `work_center_visit_ids`          | O2m `work.center.visit` (`res_id`), readonly                                                                 | สมุดเยี่ยม. Odoo adds the `res_model` filter itself.                                           |
| `work_center_open_visit_id`      | M2o, non-stored                                                                                              | The visit with no departure.                                                                   |
| `work_center_next_id`            | M2o, non-stored                                                                                              | Live next station.                                                                             |
| `work_center_missing_act_ids`    | M2m, non-stored                                                                                              | Required, minus done in the open visit, minus not-applicable, minus dead or group-less acts.   |
| `work_center_can_move`           | Boolean, non-stored, `@api.depends_context('uid')`                                                           | Forward / divert / send-back visibility.                                                       |
| **retired** `work_center_manual` |                                                                                                              | An orphan column stays on dev DBs. Harmless; no migration.                                     |

All four non-stored computes declare real depends: `work_center_id`,
`work_center_visit_ids.departure_date`, `work_center_visit_ids.done_act_ids`, and
`state` where the consumer has one. Engine methods recompute from the open visit
directly and never trust the cached field (see the trap list).

**`work.center.act` (new): the act registry.**

| Field                     | Type                                    | Purpose                                                                                     |
| ------------------------- | --------------------------------------- | ------------------------------------------------------------------------------------------- |
| `code`                    | Char, required, SQL-unique              | Stable and module-agnostic, e.g. `disbursement.validate`.                                   |
| `name`                    | Char, translate                         | Filled in every installed language by the sync.                                             |
| `kind`                    | Selection `act` / `edit`                | `edit` entries are edit permissions. They can never be required, and they are not การกระทำ. |
| `model_id` / `model_name` | M2o ir.model (cascade) / related stored |                                                                                             |
| `group_id`                | M2o res.groups, `ondelete='set null'`   | The role. NULL = offered to nobody (see 2.4).                                               |
| `module`                  | Char                                    | Declaring module.                                                                           |
| `sequence`, `active`      |                                         | Archived when no longer declared; never deleted.                                            |

**`work.center.route` / `work.center.route.line` (new).**

| Model      | Field                          | Type                                                                   | Purpose                                                |
| ---------- | ------------------------------ | ---------------------------------------------------------------------- | ------------------------------------------------------ |
| route      | `name`                         | Char, translate                                                        |                                                        |
| route      | `area_id`                      | M2o area, required, `ondelete='cascade'`                               |                                                        |
| route      | `model_id`                     | M2o ir.model, **required, `ondelete='cascade'`**, domain = area models |                                                        |
| route      | `active`, `line_ids`           |                                                                        | One active route per model.                            |
| route.line | `route_id`                     | M2o, cascade                                                           |                                                        |
| route.line | `sequence`, `name` (translate) |                                                                        | `_order 'sequence, id'`                                |
| route.line | `work_center_ids`              | M2m work.center (`work_center_route_line_station_rel`)                 | Candidate stations. Rules pick when there are several. |

Constraints:

- the model inherits the mixin;
- candidates are not the Unassigned card and belong to `route.area_id`;
- a station appears at most once per route;
- never name this a "step" (glossary _Avoid_).

**`work.center.visit` (new): the สมุดเยี่ยม.** `_order 'id desc'`.

| Field                                               | Type                                                                          | Purpose                                                                                                         |
| --------------------------------------------------- | ----------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `res_model` / `res_id`                              | Char index / Many2oneReference index                                          | Polymorphic document link.                                                                                      |
| `document_display`                                  | Char, non-stored, computed under `sudo()` with `exists()`                     | Readable reference for auditors.                                                                                |
| `work_center_id`                                    | M2o, required, restrict                                                       | The station visited. The area's Unassigned card on a no-match placement.                                        |
| `area_id`                                           | related, stored                                                               |                                                                                                                 |
| `arrival_date`, `arrived_by_id`, `arrival_act`      | Datetime, M2o users, Selection `enter / resubmit / forward / divert`          |                                                                                                                 |
| `departure_date`, `departed_by_id`, `departure_act` | Datetime, M2o users, Selection `forward / divert / send_back / exit / cancel` | **Forward out of the last line is logged as `exit`.**                                                           |
| `departure_reason`                                  | Text                                                                          | Reason for a skip, divert or send-back.                                                                         |
| `done_act_ids`                                      | M2m act (`work_center_visit_done_act_rel`), `active_test False`               | Acts performed during this visit.                                                                               |
| `skipped_act_ids`                                   | M2m act (`work_center_visit_skipped_act_rel`), `active_test False`            | Required acts skipped with a reason.                                                                            |
| `not_applicable_act_ids`                            | M2m act (`work_center_visit_na_act_rel`), `active_test False`                 | Required acts the document declared not applicable (e.g. no budget), logged at departure.                       |
| `responsible_user_ids`                              | M2m res.users (`work_center_visit_responsible_rel`), `active_test False`      | Frozen on arrival (D15).                                                                                        |
| `responsible_source`                                | Selection `members / role / fallback`                                         | `fallback` only when the station has neither members nor active role holders (the Unassigned card in practice). |

Append-only: `write()` is refused unless context `work_center_moving` is set and the row
is still open, and even then only the departure fields and the three act m2ms may
change. `unlink()` is refused unless forced by the document's own `unlink()`
(`work_center_force_unlink`; pattern:
`base_state_leadtime/models/state_leadtime_log.py:54-60`).

**`work.center.move.wizard` (new, transient).** Fields:

- `res_model`, `res_id`, `mode` (`forward / divert / send_back`), `expected_station_id`;
- `allowed_target_ids` (computed M2m; the view uses domain
  `[('id','in',allowed_target_ids)]`);
- `target_id`, `missing_act_ids` (read-only), `needs_reason` (compute), `reason`.

The reason is checked server-side with `(reason or '').strip()`. Divert re-checks the
target server-side.

**Activity type** `work_center.mail_activity_station_arrival`:
`todo_category='execution'`, generic (no `res_model`), `noupdate="0"`.

### 2.2 Disbursement side

| Model / module                                           | Status          | Fields and seams                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| -------------------------------------------------------- | --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `disbursement.request` / `disbursement`                  | reshaped        | `state` selection with six keys (PR6). `settlement_stage` Selection `none/billed/settled/booked`, stored compute, index, tracking; base value `none` (PR2). `can_edit_header/lines/attachments/dimensions/budget`, non-stored, `depends_context('uid')` (PR2). Seams: `_disbursement_acts`, `_disbursement_act_applicable`, `_disbursement_act_offered`, `_disbursement_check_act`, `_disbursement_act_done`, `_disbursement_check_send_back`, `_on_signed`, `_can_edit_open` / `_can_edit_blocked`, `_settlement_snapshot` / `_settlement_check`, `_on_settlement_walked_back`, `_resolve_source_correction_todos`. Kept: `returned_for_edit`, `returned_to_source`, `return_source_reason`, `signature_ids`. |
| `disbursement.request` / `disbursement_wc`               | reshaped        | `_name='disbursement.request'` + `_inherit=['disbursement.request','work.center.mixin']`, so it gets every mixin field. Bridges `_disbursement_acts` into `_work_center_acts` and declares the five edit kinds. Station-aware act, edit and send-back authority. Circuit entry and exit. The walk-back Todo. Activity type `disbursement_wc.mail_activity_dr_money_walked_back` (`noupdate="0"`).                                                                                                                                                                                                                                                                                                              |
| `disbursement.request` / `disbursement_budget`           | reshaped        | `consumes_budget` Boolean, default True, tracking (PR7). `can_consume_budget`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `disbursement.request` / `disbursement_accounting_kmitl` | reshaped        | Bill leg of `settlement_stage`. `_on_bills_posted` seam. `can_create_bill`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `disbursement.request` / `disbursement_finance_kmitl`    | reshaped        | Voucher legs (`settled`, `booked`). `_vouchers_all_paid`. `can_audit_payment`, `can_authorize_payment`, `can_edit_payment_subject`. Stamps kept.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| act modules                                              | new             | Each carries its own stamp pair: `verifier_id/verify_date` (validation), `finance_approver_id/finance_approve_date` (director), `rector_approver_id/rector_approve_date` (rector). Each has a `can_*` flag.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `disbursement.request.signature`                         | reshaped        | Step keys unchanged (`verify`, `finance_approve`, `rector_approve` in core; `payment_audit`, `payment_authorize` in finance). `_stamp_signature` archives the previous active row of the same step. Rows are in plain chronological order.                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `disbursement.return.request.wizard`                     | reshaped        | `mode` retired; send-back only. ACL widened to `group_disbursement_user`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `disbursement.reject.wizard`                             | **retired**     |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `disbursement.assignment.rule`                           | reshaped (PR12) | `work_center_id` (no default). `user_id` domain = the station's members, or its role holders when it has none.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `advance.payment.usage.line`                             | reshaped (PR5)  | `disbursement_state` now related to `settlement_stage`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| **retired fields**                                       |                 | `approval_state`, `approval_reject_reason`, `pipeline_status`, `display_status`, `returned_to_verification`, `return_verification_reason`, and every late `selection_add` on `state`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |

### 2.3 Act registry and sync mechanism

**Declaration.** `@api.model _work_center_acts()` on the document model returns a list
of dicts:

```python
{"code": "disbursement.validate", "name": _lt("Validate"), "kind": "act",
 "group": "disbursement.group_disbursement_officer", "sequence": 10, "module": "disbursement_validation"}
```

- On the DR, capability modules extend core's `_disbursement_acts()` (which carries the
  same keys plus `states`, see 2.4).
- `disbursement_wc` forwards those into `_work_center_acts()`. Capability modules
  therefore never import the engine.

**Sync: `work.center.act._reflect_acts()`.**

1. For every non-abstract registry model that inherits `work.center.mixin`, read the
   declarations.
2. Search existing acts **with `active_test=False`**, upsert by `code`, and
   **unarchive** a re-declared code. Write only when something differs. Each act is
   written inside its own savepoint: a failure logs a warning and the loop moves on, so
   the registry load never aborts.
3. Resolve groups with `env.ref(..., raise_if_not_found=False)`. A missing group sets
   `group_id=False` and logs a warning.
4. Translate names for every installed language through a helper evaluated in the right
   frame:
   ```python
   self.with_context(lang=L)._act_label(name)   # def _act_label(self, label): return str(label)
   ```
   `_lt` resolves its language from the frame that calls `str()`, and inside the helper
   that frame's `self.env.lang == L`. Write the result with `update_field_translations`,
   the same pattern the Unassigned card uses at `work_center_area.py:88-95`.
5. Archive codes that are no longer declared. Never delete them: visits reference them
   as audit evidence.

**Trigger.** `_register_hook()` calls `super()`, then, only when
`self.pool.updated_modules` is non-empty, takes `pg_try_advisory_xact_lock` and runs
`_reflect_acts()` as SUPERUSER. Odoo's STEP 9 runs this after all data has loaded. There
are no xmlids for acts.

**Runtime robustness.** An uninstall reloads the registry with `updated_modules` empty,
so the sync is skipped. To survive that, the engine computes missing and offered acts
**only over codes currently returned by `_work_center_acts()`** (an in-memory set). An
act that is archived, no longer declared, or has a NULL `group_id` is never "missing"
and is offered to nobody.

**Manual sync.** The Settings > Stations > Acts list has a manager server action **Sync
acts**. It runs `env['work.center.act'].sudo()._reflect_acts()` after checking
`has_group('work_center.group_work_center_manager')`, because the ACL on acts is
read-only for everyone.

### 2.4 Authority (enforced in Python; button `groups=` is cosmetic)

- **Holding station.** `_work_center_holding_station()` returns the pointer, or, when
  the pointer is False and a visit is open, that visit's station (possibly the
  Unassigned card). Every area, authority and divert check reads this helper, never the
  raw pointer.
- **May act: `_work_center_user_may_act(user, act)`.** True when all of these hold:

  - `act.group_id` is set;
  - `act.group_id` is in `user.sudo().groups_id` (implied groups included);
  - the station has no members, or the user is a member.

  Members and groups are read through `sudo`, because the OU record rule can hide the
  station from the actor.

- **Offered: `_work_center_offers(code)`.** The holding station lists the code (in
  `allowed_act_ids`, or in `allowed_edit_ids` for `kind='edit'`) AND the code is live
  AND `_work_center_act_applies(code)` AND (`env.su` OR `may_act`).
  - **`env.su` bypasses only the role and membership half.** "The station allows it" is
    enforced even under su, unless the caller sets the explicit context
    `work_center_act_anywhere=True`. Only the pilot snippet uses that, for legacy
    placement.
- **May move: `_work_center_user_may_move(user)`.**
  - `responsible_source == 'fallback'` on the open visit (the Unassigned card, or a
    station with no members and no active role holders): only
    `work_center.group_work_center_manager`.
  - Station has members: only members.
  - Otherwise: holders of any of the station's act groups.
  - `env.su` passes, for the Saraban callback and for snippets.
  - **There is no manager override on a station that has members or role holders
    (D14).**
- **Responsible snapshot: `_work_center_responsible_users()`.** Returns
  `(users, source)`:

  - members → `members`;
  - else active, non-share holders of the allowed acts' groups → `role`;
  - else group managers → `fallback`.

  Acts are bound to specific roles, never `base.group_user`. Implied groups make a
  memberless station fan out to every disbursement manager and to admin/root, so pilot
  stations get explicit members.

- **DR acts: `_disbursement_check_act(code)`.**
  1. Raise `UserError` unless `state` is in the act's declared `states` (default
     `('signed','in_progress')`; `create_bill` also allows `done`, because money can
     walk back after done). **This state check is integrity and is not bypassed by su.**
  2. Raise `AccessError` without the role (su bypasses this half).
  3. With `disbursement_wc` and `state == 'in_progress'`, also run
     `_work_center_check_act(code)`.
- **Leaving the circuit.**
  - `action_draft` and `action_cancel` on an `in_progress` DR call
    `_disbursement_check_send_back()` (core: the officer role; with `disbursement_wc`:
    `_work_center_check_move()`); su bypasses.
  - The manager "Reset to draft" button is **not** shown for `in_progress` and not shown
    for `done`.

### 2.5 Record rules and ACLs

| Model                                | Access                                                                                            | Record rule                                                                                                                                         |
| ------------------------------------ | ------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `work.center`, area, counter         | user read, manager full (unchanged)                                                               | OU rule, manager-sees-all and multi-company rules kept.                                                                                             |
| `work.center.rule`                   | manager                                                                                           | none                                                                                                                                                |
| `work.center.route`, `.line`         | `base.group_user` read, manager full                                                              | none                                                                                                                                                |
| `work.center.act`                    | `base.group_user` read, manager read (code owns it)                                               | none                                                                                                                                                |
| `work.center.visit`                  | `base.group_user` **read only**; nobody creates, writes or unlinks (the engine writes under sudo) | none: a polymorphic `res_id` cannot be ruled. Accepted risk, §7. The Visit Log **menu** is manager-only; users see visits embedded in the document. |
| `work.center.move.wizard`            | `base.group_user` full                                                                            | none                                                                                                                                                |
| `disbursement.return.request.wizard` | widened to `group_disbursement_user`                                                              | authority checked in the method                                                                                                                     |
| `disbursement.reject.wizard`         | deleted                                                                                           |                                                                                                                                                     |
| `disbursement.assign.officer.wizard` | widened to `group_disbursement_user` (PR12)                                                       | membership checked in the method                                                                                                                    |

---

## 3. The PR sequence

### 3.0 Branch graph and how to build it

A **single linear stack**: each PR's GitHub base is the previous PR's branch, and
nothing merges until the pilot is accepted (§0.2).

```
16.0 (origin/16.0)
 └─ PR1  16.0-add-work_center                              (#1510, rewritten)
     └─ PR2  16.0-imp-disbursement-settlement_stage
         └─ PR3  16.0-imp-disbursement-act-seams
             └─ PR4  16.0-imp-disbursement_finance_kmitl-money-events
                 └─ PR5  16.0-imp-kmitl_project_disbursement-readers
                     └─ PR6  16.0-imp-disbursement-state-collapse
                         └─ PR7  16.0-imp-disbursement_budget-consume-act
                             └─ PR8  16.0-add-disbursement_validation
                                 └─ PR9  16.0-add-disbursement_approver_director
                                     └─ PR10 16.0-add-disbursement_approver_rector
                                         └─ PR11 16.0-add-disbursement_wc      ← existing branch, rebased here
                                             └─ PR12 16.0-imp-disbursement_assignment_kmitl-station   ← PO TRIAL GATE (PR1-PR12)
                                                 └─ PR13 16.0-imp-finance_kmitl_demo-stations          (after the trial)
pilot integration branch: 16.0-pilot-stations = PR12 head at trial time (never PR'd; tagged pilot-stations-<date>)
```

PR2-PR10 do not need `work_center`. They sit above PR1 only so the stack stays linear.
After acceptance they merge in order.

**Building it from today's tree.** `16.0-add-disbursement_wc` already sits on the
`16.0-add-work_center` head `92d3bc77`.

```bash
# 1. Move ADR-0002 (and ADR-0001's 'superseded' header) onto the work_center branch.
#    5f0ef4b3 also touches disbursement_wc/CONTEXT.md, which does not exist there, so take only the ADR files.
git checkout 16.0-add-work_center
git checkout 5f0ef4b3 -- work_center/docs/adr/
git commit -m "[ADD] work_center: ADR-0002 a work center is a station; supersede ADR-0001"
#    Skip bcc56539: PR1 rewrites work_center/CONTEXT.md entirely.
# 2. Build PR1 on this branch (after @n3n acknowledges, §0.3).
# 3. Create PR2..PR10 one on top of the other:
git checkout -b 16.0-imp-disbursement-settlement_stage 16.0-add-work_center   # and so on, each from the previous
# 4. Rebase the existing disbursement_wc branch (its glossary/ADR commits ride along) onto PR10:
git rebase --onto 16.0-add-disbursement_approver_rector 16.0-add-work_center@{1} 16.0-add-disbursement_wc
#    (use the pre-step-1 work_center head 92d3bc77 as the old base if the reflog entry differs)
#    Two replays need a hand: 5f0ef4b3 re-adds the ADR files step 1 already moved (identical
#    content, so it merges clean or empties out), and bcc56539 conflicts on work_center/CONTEXT.md,
#    which PR1 rewrote — keep PR1's version and take only its disbursement_wc/CONTEXT.md hunk.
# 5. When any PR in the middle changes, rebase everything above it in one go from the top branch:
git checkout 16.0-imp-disbursement_assignment_kmitl-station
git rebase --update-refs 16.0-<changed-branch>
git push --force-with-lease origin <every updated branch>
```

**Who rebases.** The implementer owns the whole stack and rebases downstream branches
after any upstream change. Expect conflicts in
`disbursement/models/disbursement_request.py` and `disbursement/i18n/th.po`, which PR2,
PR3, PR4, PR6 and PR8-PR10 all touch. Resolve them so that each branch stays installable
on its own. No merge commits inside the stack.

**Deploy and pilot install rule.** The act modules move stored fields out of core
(PR8-PR10). `-u disbursement` and `-i` of the act modules **must run in one command**,
or Odoo drops the columns and every historical stamp is lost (`ir_model.py`
`_process_end` keeps a field only if another xmlid claims it in the same run). The exact
pilot command is in §6.

---

### PR1: `work_center` station engine

- **Branch:** `16.0-add-work_center` (PR #1510, rewritten)
- **Title:**
  `[16.0][ADD] work_center: stations a document passes through (routes, visit log, acts)`
- **Modules:** `work_center`. Depends on: nothing (base `16.0`).
- **Goal:** replace the stamped owning unit (ADR-0001) with the generic station engine
  (ADR-0002) and prove it on the throwaway `test.work.center.doc`.
- **Installable after it:** yes. Nothing inherits `work.center.mixin` (the purchase
  bridges were closed in #1510 and #1576). The module is not installed on the snapshot.
  The only new dependency, `mail_activity_todo`, is installed there.

**Change list by file**

| File                                                                | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `__manifest__.py`                                                   | Summary: "Stations a document passes through: routes, visit log, acts, per-area overview". `depends`: `mail`, `operating_unit`, `mail_activity_todo`. Data order: security xml/csv → `data/mail_activity_type_data.xml` → `views/work_center_act_views.xml` → `views/work_center_route_views.xml` → `views/work_center_visit_views.xml` → `wizards/work_center_move_wizard_views.xml` → existing views → `views/work_center_menus.xml` last. Version stays `16.0.1.0.0` (unmerged).                                                                                                                                                                                                                 |
| `__init__.py`, `models/__init__.py`, `wizards/__init__.py` (new)    | Import `wizards`. Import `work_center_act`, `work_center_route` and `work_center_visit` before `work_center_mixin`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `models/work_center.py`                                             | Docstring: a station (ADR-0002). `_description="Station"`. Helps: `operating_unit_id` also filters divert targets; `member_ids` narrows (empty = open to role holders; members move documents); `is_unassigned` = "in-circuit documents that no rule placed at a station". Fields and constraints as in §2.1. `unlink` refuses while visits exist. `_counter_base_domain(model)`: for the Unassigned card, AND `env[model]._work_center_circuit_domain()`, used both in `_compute_counter_data` (L143-148) and in `action_open_counter` (L180-182); keep the Json-False guard. Helpers from §2.4, all reading through `sudo`.                                                                       |
| `models/work_center_area.py`                                        | Docstring and the L105 message say "station". Keep `_check_model_in_one_area`, Unassigned card creation with per-language names, and `unlink`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `models/work_center_mixin.py`                                       | Pointer: see §2.1. **Delete** `work_center_manual`, `_work_center_routing_fields`, `_work_center_is_routable`, `_compute_work_center_id`, `_work_center_stamp`, `_work_center_update_pin`, and the pin/stamp `create`/`write`. **Keep** `_valid_field_parameter` and `_check_work_center_id`. Guards: `create` raises when `vals.get('work_center_id')` is truthy without context `work_center_moving`; `write` raises only when the new value differs from any record's current pointer. `unlink` deletes the document's visits under `work_center_force_unlink`. Engine and act API: see the list below this table.                                                                               |
| `models/work_center_rule.py`                                        | Docstring: chooses which candidate station of a route line takes the document, evaluated on arrival at that line. Strings at L80, L88-90 and L97 say "station". Matching code unchanged.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `models/work_center_act.py` (new)                                   | §2.1 and §2.3.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `models/work_center_route.py` (new)                                 | §2.1 (`model_id` required + cascade).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `models/work_center_visit.py` (new)                                 | §2.1, with the append-only rules.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `wizards/work_center_move_wizard.py` + `_views.xml` (new)           | §2.1. `action_confirm` dispatches to `_work_center_forward` / `_divert` / `_send_back` with `expected_station`. Chatter bodies use `tools.plaintext2html(reason)`. One form, mode-dependent `attrs`, Confirm/Cancel footer.                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `data/mail_activity_type_data.xml` (new)                            | `<odoo noupdate="0">`: `mail_activity_station_arrival`, name "Arrived at your station", `todo_category` execution, icon `fa-inbox`, `delay_count` 0.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `security/ir.model.access.csv`, `security/work_center_security.xml` | ACLs as in §2.5. Category "Stations". Group "Station Administrator", comment "Configures stations, routes, acts, routing rules and overview counters." Reword the L22-26 comment. Keep the three record rules.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `views/work_center_views.xml`                                       | Placeholder "e.g. Verification Station". New "Acts" page with `allowed_act_ids`, `required_act_ids` (domain `[('id','in',allowed_act_ids)]`) and `allowed_edit_ids`, invisible on the Unassigned card. Member help. Filter `my_work_centers` → "My Stations", domain `['                                                                                                                                                                                                                                                                                                                                                                                                                            | ',('is_my_station','=',True),('is_unassigned','=',True)]`. Action "Stations". Kanban unchanged (keep `or []`). |
| `views/work_center_rule_views.xml`, `_counter_views.xml`            | "Station Routing Rules" with the new help (exact indentation, because the msgid must match); "Station Counters".                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `views/work_center_route_views.xml` (new)                           | Tree and form; editable `line_ids` (handle, name, `work_center_ids` many2many_tags with domain area = `parent.area_id` and not Unassigned); action.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `views/work_center_act_views.xml` (new)                             | Read-only tree (code, name, kind, model, group, module, active; a "missing role" decoration when `group_id` is empty). Action with `create=0 edit=0`. Manager server action "Sync acts" (§2.3).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `views/work_center_visit_views.xml` (new)                           | Default embeddable tree: station, arrived, arrival act, arrived by, left, departure act, departed by, reason, skipped acts, not-applicable acts, responsible tags. Read-only form. Search grouped by station and model. Manager action.                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `views/work_center_menus.xml`                                       | Root "Stations". Areas 10, Stations 20, Routes 25, Routing Rules 30, Counters 40, Acts 50, Visit Log 60. The new menus are manager-only.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `i18n/th.po`                                                        | §5.2.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `tests/test_work_center.py`                                         | Repair in place (below).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `README.rst`                                                        | Hand-written. How it works; configuration (areas, stations with members, allowed/required acts and editable parts, routes, rules, counters, read-only acts). Bridge recipe: list `_inherit` with explicit `_name`; declare `_work_center_acts`; call `_work_center_enter`; implement the hooks; embed the buttons and the visit tree; **add th.po entries for every mixin field under the consumer module's xmlid** (`<consumer>.field_<model>__work_center_id`, …), because Odoo 16 gives inherited fields the consumer's xmlid; under `tier.validation`, whitelist only `work_center_id`.                                                                                                         |
| `CONTEXT.md`                                                        | Rewrite as a generic glossary: สถานี, ระบบงาน, สมาชิกสถานี (narrows), Route / Route line (candidates + rule), ส่งต่อ / divert / send back, สมุดเยี่ยม, การกระทำ, editable part (not an act), ยังไม่มีสถานี, Counter. Drop Pinned.                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `docs/adr/0003-acts-are-declared-in-python-and-reflected.md` (new)  | Acts are code-declared and reflected; archived, never deleted; no xmlids; `kind='edit'` entries are permissions, not acts, and can never be required. **Declared exceptions needing PO sign-off (status "proposed" until signed):** (a) a required act a document declares not applicable is not "missing", and it is logged on the visit in `not_applicable_act_ids`; (b) the `fallback` responsible source and the manager move authority apply only where nobody else is responsible (the Unassigned card, or a station whose roles have no active holders). Rejected alternatives: XML seeding, `ir.model.fields.selection` (unreadable to `base.group_user`), `post_init_hook` (install only). |
| `CONTEXT-MAP.md` L165-167                                           | "สถานี: a desk a document passes through; routes, visit log, acts".                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `.context/work_center_refresh_unassigned_name.py` (new, local)      | Dev DBs that had the old module: rewrite the Unassigned cards' name translations through `_unassigned_name()`. Not needed on the snapshot.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |

**Engine methods on the mixin.** All moves go through `_work_center_move`.

- **`_work_center_route()`**: the active route for `self._name`.
- **`_work_center_resolve(line)`**:
  - candidates are active, not the Unassigned card, and OU-compatible (only when
    `self._work_center_ou_field in self._fields`);
  - one candidate → that station;
  - otherwise `work.center.rule._candidate_rules(self._name)` filtered to the
    candidates, then `_match()`;
  - no match → False.
- **`_work_center_next_line()`**: walk the visits ordered by **id** desc. The first
  visit whose station is on the live route gives the following line, or `None` (→ exit).
  With no on-route visit, return line 1.
- **`_work_center_enter(act='enter'|'resubmit')`**: always line 1, ignoring history
  (D9).
- **`_work_center_forward(reason=None, expected_station=None)`**:
  - refused while the holding station is the Unassigned card ("divert to a station");
  - missing = live, grouped, required acts − `done_act_ids` of the **open** visit − acts
    where `_work_center_act_applies` is False. The not-applicable ones are written to
    `not_applicable_act_ids` at departure;
  - if any act is missing, a stripped reason is mandatory and the missing acts go to
    `skipped_act_ids`;
  - next line `None` → departure `exit`.
- **`_work_center_divert(station, reason=None, expected_station=None)`**: the target
  must be in the holding station's area, the document's model, not the holding station,
  not Unassigned, and OU-compatible. Required acts are ignored.
- **`_work_center_send_back(reason)`**: reason mandatory;
  `_work_center_leave('send_back', reason)`, then `_work_center_on_send_back(reason)`.
- **`_work_center_leave(act, reason=None, expected_station=None)`**: **implemented as
  `_work_center_move(False, arrival_act=None, departure_act=act, reason=reason, expected_station=expected_station)`**.
  It therefore runs steps 1-4 below (closing the visit and the Todos, clearing the
  pointer) and skips 5-6. Idempotent when no visit is open.
- **`_work_center_move(station, arrival_act, departure_act, reason=None, skipped=None, expected_station=None)`**
  is the single writer. In order:
  1. if `expected_station` is given and differs from the holding station, raise "already
     moved";
  2. close the open visit (departure date, by, act, reason, skipped, not-applicable)
     under sudo and `work_center_moving`;
  3. `action_feedback` the mover's own arrival Todo only, and sudo-unlink the other
     arrival Todos of this document (`purchase_request_verifier._close_todos` pattern;
     never feedback the whole fan-out);
  4. write the pointer with sudo under `work_center_moving` (False when leaving, or when
     resolve gives no match);
  5. when `arrival_act` is set, open a new visit with the frozen
     `_work_center_responsible_users()` snapshot (station = the area's Unassigned card
     when resolve gave False);
  6. schedule one `mail_activity_station_arrival` per snapshot user (skipped when
     `activity_ids` is not in `_fields`);
  7. call the hooks `_work_center_on_departure(old_visit)`, then
     `_work_center_on_arrival(new_visit)` if a visit was opened, then
     `_work_center_on_exit()` when `departure_act == 'exit'`.
- **Act API:**
  - `_work_center_live_codes()`
  - `_work_center_offers(code)`, see §2.4
  - `_work_center_check_act(code)`: AccessError for missing role or membership;
    UserError "not allowed at this station"
  - `_work_center_act_done(code)`: append to the open visit's `done_act_ids` under sudo
    and the engine context
  - `_work_center_check_move()`
  - `_work_center_last_visit(departure_acts=('forward','exit'))`: latest **closed**
    visit with one of those departure acts, ordered by id desc
- **Hooks** (defaults are `[]`, `True` or no-op):
  - `_work_center_acts`
  - `_work_center_act_applies(code)`
  - `_work_center_circuit_domain`
  - `_work_center_on_arrival(visit)`
  - `_work_center_on_departure(visit)`
  - `_work_center_on_exit`
  - `_work_center_on_send_back(reason)`
- **Buttons:**
  - `action_work_center_forward()`: moves directly when nothing is missing, otherwise
    returns the wizard;
  - `action_work_center_divert()` and `action_work_center_send_back()`: always return
    the wizard;
  - all three read `expected_station` from the context.

**Existing tests to repair in place** (`work_center/tests/test_work_center.py`; the
method count stays the same; **NEVER RUN**):

- **Test model.**
  - Drop the `_work_center_routing_fields` override.
  - `_inherit` gains `mail.activity.mixin`; `state` gains `in_progress`.
  - Declare two acts on **existing groups that have xmlids**
    (`base.group_partner_manager`, `base.group_erp_manager`), because groups created in
    `setUpClass` have no xmlid for the declaration to reference.
  - Implement `_on_exit` and `_on_send_back` so they set the state.
- **setUpClass.**
  - Stations renamed สถานี…
  - Route: line 1 = `[wc_dept, wc_other]` (rules decide), line 2 = `wc_central`.
  - Explicit members on one station; two role users and one user without the role; a
    second area.
  - Call `env['work.center.act']._reflect_acts()` explicitly, because the hook ran
    before the test model existed.
- **Re-keyed through `_work_center_enter`:**
  - `test_routed_on_create`, `test_child_of_matches_sub_unit`, `test_ou_guard`,
    `test_central_matches_any_ou`, `test_sequence_priority`,
    `test_archived_work_center_ignored`;
  - `test_no_match`: pointer False plus an open visit on the Unassigned card; extended
    in place so a manager can divert it to a real station and a role user cannot.
- **`test_unassigned_card_not_assignable`:** a direct truthy write raises UserError; a
  write under the engine context still hits the ValidationError.
- **`test_counters`:** documents are entered first; the Unassigned count uses the
  circuit domain.
- **The eight owning-unit tests are rewritten in place** under new names, each covering
  one engine behaviour:

| Old method (deleted behaviour)            | Rewritten as                                                                                                                                                                                                                                                                                                                      |
| ----------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test_child_of_in_memory_preview`         | `test_forward_moves_to_next_line_and_exit_calls_hook`: departure `exit` on the last line.                                                                                                                                                                                                                                         |
| `test_draft_follows_rules`                | `test_divert_then_forward_rejoins_after_last_on_route_visit`: ordered by id.                                                                                                                                                                                                                                                      |
| `test_sticky_after_draft`                 | `test_divert_to_another_area_refused`                                                                                                                                                                                                                                                                                             |
| `test_stamped_when_leaving_draft_at_once` | `test_missing_required_act_needs_reason`: no reason raises; with a reason, `departure_reason` and `skipped_act_ids` are written.                                                                                                                                                                                                  |
| `test_manual_edit_after_draft_kept`       | `test_send_back_and_cancel_close_visit_todos_and_pointer`                                                                                                                                                                                                                                                                         |
| `test_manual_pick_in_draft_pins`          | `test_visit_is_append_only`: write and unlink raise.                                                                                                                                                                                                                                                                              |
| `test_writing_rule_result_does_not_pin`   | `test_membership_narrows_and_snapshot_freezes`: `invalidate_all()` before each `with_user`; a non-member role holder is refused; a member without the role is refused; a group-less act is refused; the snapshot survives a membership change; a memberless station snapshots role holders (`assertIn`, because admin is seated). |
| `test_clear_after_draft_stays_empty`      | `test_resubmit_enters_line_one_regardless_of_history`                                                                                                                                                                                                                                                                             |

- **Kept unchanged:** the area, rule, counter and delete tests.
- **Left unguarded by tests** (covered by §6 instead): act-sync idempotence, archive and
  unarchive; th_TH act names; a route edit changing "next" for a document in flight; a
  stale `expected_station` raising "already moved"; a whitespace-only wizard reason; the
  act sync after an uninstall.

**Minimal tests for new modules:** none (the module has a suite).

**Verify:**

- `python -m pyflakes work_center`; `xmllint --noout` on every changed XML;
  `msgfmt -c work_center/i18n/th.po`.
- `grep -rn 'work_center_manual\|_work_center_stamp\|_work_center_routing_fields\|_work_center_is_routable' work_center/`
  returns nothing.
- `grep -rn 'ศูนย์งาน' --include='*.po' --include='*.xml' --include='*.py' --include='*.rst' work_center/`
  returns nothing.
- Only if the user asks: on a throwaway snapshot copy, `-i work_center`. The Settings >
  Stations menus open, the Acts list is empty and read-only, and a second registry load
  writes nothing (check the log).

**Acceptance:**

- `work_center_id` changes only through `_work_center_move`.
- Every move closes exactly one visit. Every move **to a station** (enter, resubmit,
  forward, divert) opens exactly one. `exit`, `send_back` and `cancel` leave no open
  visit and the pointer False.
- "Next" after a divert is derived from the สมุดเยี่ยม by id.
- With members, non-member role holders are refused. Without members, role holders may
  act. Managers move only on `fallback` visits.
- su cannot perform an act the holding station does not allow.

**Risks:**

- If the `updated_modules` guard or the advisory lock is wrong, the sync writes on every
  worker start.
- Memberless stations fan Todos out to every implied role holder.
- The force-push rewrites @n3n's commits (§0.3).

---

### PR2: settlement*stage and can_edit*\* flags

- **Branch:** `16.0-imp-disbursement-settlement_stage`. **Title:**
  `[16.0][IMP] disbursement: settlement_stage money axis and can_edit_* field locks`
- **Modules:** `disbursement`, `disbursement_budget`, `disbursement_accounting_kmitl`,
  `disbursement_finance_kmitl`, `procurement_plan_disbursement`,
  `disbursement_assignment_kmitl`. Depends on: none logically; base PR1.
- **Goal:** add the two new DR axes next to the old workflow without changing behaviour.
  The lock still means "draft only" after this PR.
- **Placement note:** D16 lists the state collapse, `settlement_stage` and `can_edit_*`
  under `disbursement_wc`. This plan declares them in **core** with legs in the money
  bridges, because readers that depend only on `disbursement` or `disbursement_budget`
  (`kmitl_project_disbursement`, `procurement_plan_disbursement`,
  `agx_approval_disbursement`, `purchase_request_approval_disbursement`,
  `advance_payment_disbursement`) would crash at registry load if those fields existed
  only in `disbursement_wc`. `disbursement_wc` contributes only the station half of each
  compute. This **amends D16** and needs PO sign-off before PR2 (§8 item 1). It is
  recorded in a new `disbursement/docs/adr/0005-the-drs-two-axes-live-in-core.md`.
- **Installable after it:** yes. The old states, pipeline and display fields are
  untouched.

| File                                                                 | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `disbursement/models/disbursement_request.py`                        | `settlement_stage` Selection(`none` "Not Billed", `billed` "Billed", `settled` "Settled", `booked` "Booked"), `compute='_compute_settlement_stage'`, `store=True`, `index=True`, `readonly=True`, `copy=False`, `tracking=True`. The base compute (`@api.depends()`) sets `none`. Add `_SETTLEMENT_RANK`. Non-stored `can_edit_header/lines/attachments/dimensions/budget`, all from one `_compute_can_edit` with `@api.depends('state')` and `@api.depends_context('uid')`: `flag = rec._can_edit_open(kind) and not rec._can_edit_blocked(kind)`; base `_can_edit_open` = `state == 'draft'`, base `_can_edit_blocked` = False. A docstring tells bridges to extend with `super()` and declare only the depends they add. **Delete** `READONLY_STATES` (L37-50) and all 14 `states=READONLY_STATES` (L66, 78, 91, 103, 108, 117, 126, 134, 150, 316, 329, 341, 356, 373). Bump the version to `16.0.13.0.0`. |
| `disbursement/views/disbursement_request_views.xml`                  | Invisible nodes for the five flags and `settlement_stage`. Readonly attrs: `can_edit_header` on `date`, `payment_type`, `partner_type_id`, `note`, `account_fiscal_year_id` and **both** `user_id` nodes (the manager node gets explicit attrs; the non-manager node keeps `readonly="1"`, last-node trap). `can_edit_dimensions` on the four dimensions (L251-274, replacing `state != 'draft'`). `can_edit_lines` on `line_ids` (with `parent.can_edit_lines` in the inline tree where needed). `can_edit_attachments` on `attachment_ids`. `ignore_exception`: drop the dead `states="to_approve"` and set `invisible="1"`. `settlement_stage`: read-only badge on the form, optional tree column, filters `stage_billed / stage_settled / stage_booked`, group-by.                                                                                                                                         |
| `disbursement/docs/adr/0005-the-drs-two-axes-live-in-core.md` (new)  | The D16 amendment above, with the rejected alternative (everything in `disbursement_wc`, so every reader depends on the engine).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `disbursement/i18n/th.po`                                            | Add ขั้นการชำระ; ยังไม่ตั้งหนี้ / ตั้งหนี้แล้ว / จ่ายแล้ว / บันทึกบัญชีแล้ว; the filters, the group-by and the five flag labels (§5).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `disbursement_budget/models/disbursement_request.py`                 | Delete the `DisbursementRequestBase` import (L6-8) and `states=` on `budget_commitment_id` / `budget_account_id` (L37, L48) **in the same commit**. `_can_edit_blocked(kind)` = `super()` or (`kind in ('dimensions','budget')` and `budget_commitment_id`), with `@api.depends('budget_commitment_id')` only.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `disbursement_budget/views/disbursement_request_views.xml`           | L44-58: dimensions readonly `[('can_edit_dimensions','=',False)]`; `budget_account_id` and `budget_commitment_id` on `can_edit_budget`; keep `force_save="1"`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `disbursement_accounting_kmitl/models/disbursement_request.py`       | Override `_compute_settlement_stage` with `@api.depends('bill_ids','bill_ids.state')` only: `super()`; `active` = non-cancelled `bill_ids`; `billed` only when `active and all(b.state == 'posted')`. Read `bill_ids`, never `related_move_ids`, so cash-revenue handovers never count. `_can_edit_blocked`: `super()` or (`kind in ('lines','dimensions','budget')` and any non-cancelled bill, **draft included**). `init()`: `self.env.add_to_compute(self._fields['settlement_stage'], self.with_context(active_test=False).search([]))`, because the column was filled with `none` when core installed, before this override existed.                                                                                                                                                                                                                                                                     |
| `disbursement_finance_kmitl/models/disbursement_request.py`          | Extract `_vouchers_all_paid()` from `_try_hand_over_when_all_paid` (L576-603): `active` non-empty AND every payment line has a non-cancelled voucher AND all active vouchers have `finance_state == 'paid'`. Override `_compute_settlement_stage` with `@api.depends('payment_ids.state','payment_ids.finance_state','payment_line_ids.payment_id')` only: after `super()`, from `billed` → `settled` if `_vouchers_all_paid()`, → `booked` if in addition all active vouchers are posted. Same `init()` recompute.                                                                                                                                                                                                                                                                                                                                                                                            |
| `procurement_plan_disbursement/views/disbursement_request_views.xml` | L20-24: `['                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | ',('budget_commitment_id','!=',False),('can_edit_dimensions','=',False)]` plus an invisible flag node. |
| `disbursement_assignment_kmitl/models/disbursement_request.py`       | L37-41 comment: "assigned*to is not covered by any can_edit*\* flag on purpose".                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `disbursement_wc/README.rst` (written in PR11)                       | Records the deliberate narrowings of D13 (draft bills, the budget commitment) and points to §8 item 8.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |

**Existing tests to repair (NEVER RUN):**

- `disbursement_cash_revenue_handover/tests/test_cash_revenue_handover.py::test_posting_the_handover_leaves_the_request_alone`:
  also asserts `settlement_stage == 'none'`.
- `disbursement_finance_kmitl/tests/test_payment_workflow.py::test_the_request_crosses_when_the_last_voucher_is_cancelled`:
  also asserts the stage is not `settled` (the empty-set guard).

**Minimal tests for new modules:** none.

**Left unguarded** (covered in §6): no bills reads `none`; a bill reset walks back to
`none`; posted vouchers read `booked`.

**Verify:**

- pyflakes on the six modules; xmllint; `msgfmt -c`.
- `grep -rn 'READONLY_STATES\|states=' disbursement/models disbursement_budget/models`
  shows nothing on DR fields.
- Only if asked, on a snapshot clone: `-u disbursement`. The stage distribution compared
  with the **old state**:

  - `bills_posted`, `payment_audited`, `payment_authorized` → `billed` (or `settled`
    when every voucher is already finance-paid, an expected exception);
  - `paid` → `settled`;
  - `cleared` → `booked`;
  - every other state → `none`.

  A submitted DR stays fully read-only.

**Acceptance:**

- No `states=` remains on `disbursement.request` fields.
- `settlement_stage` is never written by hand.
- No bills, or only cancelled ones, reads `none`. All vouchers cancelled never reads
  `settled`.
- `disbursement_budget` loads without importing core's class.

**Risks:**

- The install-time recompute writes tracking messages on every DR.
- Every override must declare only its own depends.
- The `init()` recompute is required: without it, every finished DR reads `none`.

---

### PR3: act and circuit seams in core

- **Branch:** `16.0-imp-disbursement-act-seams`. **Title:**
  `[16.0][IMP] disbursement: generic seams for acts, authority, circuit entry and signature supersede`
- **Modules:** `disbursement`, `purchase_work_acceptance_disbursement`. Base PR2.
- **Goal:** capability-named seams that act modules and `disbursement_wc` plug into. The
  role and the circuit state are enforced in Python. A re-stamp supersedes the previous
  signature row. Behaviour is otherwise unchanged.
- **Installable after it:** yes. The new role checks match what the button `groups=`
  already allowed, and su fixtures bypass the role half.

| File                                                                          | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `disbursement/models/disbursement_request.py`                                 | `@api.model _disbursement_acts()` → list of dicts `{code, name (_lt), kind, group (xmlid), states (default ('signed','in_progress')), sequence, module}`. `_disbursement_act(code)`. `_disbursement_act_applicable(code)` → True. `_disbursement_act_offered(code)` = state in the act's states and `env.user` holds the group. `_disbursement_check_act(code)`: UserError when state is not in the act's states (**not bypassed by su**), then AccessError without the role unless `env.su`. `_disbursement_act_done(code)`: no-op. `_on_signed()`: no-op; context `disbursement_resubmit` marks a resubmit. `_disbursement_check_send_back()`: returns under su, otherwise requires the officer role. Core temporarily declares `disbursement.validate` (officer), `disbursement.approve_director` (`group_disbursement_finance_director`) and `disbursement.approve_rector` (`group_disbursement_rector_delegate`). `action_validate`, `action_approve_finance` and `action_approve` call `_disbursement_check_act(code)` first and `_disbursement_act_done(code)` last (state guards stay until PR6). `action_sign` calls `self._on_signed()` after writing `signed`. `_stamp_signature(step)` first archives any active row of the same step on this DR. |
| `disbursement/models/disbursement_return.py`, `disbursement_return_source.py` | `action_resubmit_verification`: after `state='signed'`, `self.with_context(disbursement_resubmit=True)._on_signed()`. `_action_return_for_edit` and `_return_to_source` call `_disbursement_check_send_back()`. Chatter bodies use `Markup(...) % reason` / `plaintext2html`, which fixes the HTML injection. Extract `_resolve_source_correction_todos()` from the `action_validate` override (L270-293); the override calls it until PR6.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `disbursement/models/disbursement_request_signature.py`, `docs/adr/0002-*.md` | L22-24 comment: "plain chronology; a re-stamp archives the previous row of its step". ADR superseding note on the archive rule. Step keys stay in core.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `disbursement/security/ir.model.access.csv`                                   | Row 14 (return wizard) → `group_disbursement_user`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `disbursement/wizards/disbursement_exception_confirm.py`                      | Call `action_draft()` only when the record's `state != 'draft'` (fixes an existing untested crash).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `purchase_work_acceptance_disbursement/models/disbursement_request.py`        | Move `wa_ids.is_disbursed=True` from the `action_sign` override (L61-70) into an `_on_signed` override, so resubmit sets it too. Keep the `action_draft` reset.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `disbursement/i18n/th.po`                                                     | The AccessError and "not in the circuit" messages. The three act names as `#. odoo-python` / `#: code:addons/disbursement/models/disbursement_request.py:0` / `#, python-format` entries. Re-escaped chatter msgids where the text changed.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |

**Existing tests to repair:**

- `disbursement/tests/test_signature_block.py`: the return-to-verification archive test
  (L240-255) is re-keyed to "re-stamping a step archives its previous row". NEVER RUN.

**Minimal tests for new modules:** none.

**Left unguarded:** AccessError over RPC for a non-officer. PR8 covers it in its new
suite.

**Verify:**

- pyflakes.
- grep shows every act method calls `_disbursement_check_act` and
  `_disbursement_act_done`.
- Only if asked: the old flow submit → sign → validate → approve ×2 behaves as today.

**Acceptance:**

- `action_approve_finance` over RPC without the director group raises AccessError.
- An act on a `draft` DR raises UserError, even under su.
- `action_sign` and `action_resubmit_verification` both pass through `_on_signed`.
- Re-stamping a step leaves exactly one active row for it.

**Risks:** `with_user` callers that relied on a missing group surface now.

---

### PR4: money side effects move to events

- **Branch:** `16.0-imp-disbursement_finance_kmitl-money-events`. **Title:**
  `[16.0][IMP] disbursement_finance_kmitl: money side effects hang on bill/payment events, not on DR state writes`
- **Modules:** `disbursement`, `disbursement_accounting_kmitl`,
  `disbursement_finance_kmitl`, `finance_kmitl` (ADR note only). Logical dependency PR2;
  base PR3.
- **Goal:** re-home, while the old states still exist, every side effect the collapse
  would otherwise kill silently.
- **Installable after it:** yes. The `bills_posted`, `paid` and `cleared` writes stay
  until PR6.

| File                                                                                             | Change                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `disbursement/models/disbursement_request.py`                                                    | `_settlement_snapshot()` → `{id: stage}`. `_settlement_check(before)`: flush `settlement_stage`, compare ranks, call `_on_settlement_walked_back(previous_stage)` per record whose rank dropped. Seam `_on_settlement_walked_back(previous_stage)`: no-op.                                                                                                                                                            |
| `disbursement_accounting_kmitl/models/disbursement_request.py`, `account_move.py`                | Seam `_on_bills_posted()`: no-op. `account.move._post`: after `super()`, call `_on_bills_posted()` on linked requests whose active bills are now all posted (`active and all`). New `button_draft` / `button_cancel` overrides: snapshot the stages of requests linked through `disbursement_request_id`, call `super()`, then `_settlement_check`. Reword the stale docstring at `accounting_kmitl_dashboard.py:13`. |
| `disbursement_finance_kmitl/models/disbursement_request.py`                                      | Move `_ensure_payment_lines()` from the `write()` `bills_posted` branch (L223-231) into an `_on_bills_posted()` override. It is idempotent (finance ADR-0003) and must never run inside a compute. `_hand_over` candidates: `settlement_stage == 'settled'` with no open TO_BOOK activity (the new idempotence key). `_try_hand_over_when_all_paid` uses `_vouchers_all_paid()`.                                      |
| `disbursement_finance_kmitl/models/account_move.py`                                              | L60-80: re-key the guard to `settlement_stage not in ('settled','booked')`. New `button_draft` / `button_cancel` overrides that snapshot and check requests linked through `payment_disbursement_request_id` (voucher entries), which the accounting override cannot see.                                                                                                                                             |
| `disbursement_finance_kmitl/models/account_payment.py`                                           | In `write` (when `finance_state` is in vals, which includes a cheque bounce writing `confirmed`), `action_cancel` and `unlink`: snapshot, `super()`, `_settlement_check`. Keep `_try_hand_over_requests` under sudo. Reword the L111 comment (`payment_authorized`).                                                                                                                                                  |
| `disbursement_finance_kmitl/models/disbursement_payment_line.py`                                 | `_banking_editable` (L278-295) → `not self.payment_id and self.request_id.state != 'cancel'`. Keep the `write()` guard (L297-317). New message "Banking coordinates are frozen once the payment voucher exists." plus a th.po python-format entry.                                                                                                                                                                    |
| `finance_kmitl/docs/adr/0006-*.md`, `0007-*.md`; `disbursement_finance_kmitl/docs/adr/0007-*.md` | "Superseded in part": the request's `settlement_stage` now walks back with the voucher.                                                                                                                                                                                                                                                                                                                               |

**Existing tests to repair (NEVER RUN):**
`disbursement_finance_kmitl/tests/test_payment_workflow.py` is re-read against the new
predicates. Assertions are unchanged:

- `test_the_request_is_not_handed_over_twice` now proves the open-activity key;
- `test_banking_coordinates_freeze_once_the_payment_exists`;
- `test_posting_waits_for_the_finance_office`.

**Minimal tests for new modules:** none.

**Verify:**

- pyflakes.
- grep shows the `write()` `bills_posted` branch keeps only the TO_AUDIT fan-out, and
  `_hand_over` filters on no state.
- Only if asked: posting a bill on an approved DR creates payment lines and the stage
  reads `billed`.

**Acceptance:**

- Payment lines appear when the bills post, whatever the DR state.
- Banking edits are refused exactly when a voucher exists.
- Resetting a posted bill, resetting a posted voucher entry, or bouncing a cheque calls
  `_on_settlement_walked_back` once per affected DR.

**Risks:**

- The old audit-to-authorize banking freeze window disappears (an ordering lock removed
  by D7).
- `test_cash_movement.py:346` is probably already red: baseline it against the
  merge-base before blaming this PR.

---

### PR5: readers move off state literals

- **Branch:** `16.0-imp-kmitl_project_disbursement-readers`. **Title:**
  `[16.0][IMP] kmitl_project_disbursement, procurement_plan_disbursement, agx_approval_disbursement, purchase_request_approval_disbursement, advance_payment_disbursement, purchase_order_disbursement, disbursement_operating_unit: key on settlement, budget and cancel facts`
  (multi-module title, precedent: commit `bcc56539`).
- **Modules:** the seven in the title. Logical dependency PR2; base PR4.
- **Goal:** every downstream reader of `verified`, `approved`, `bills_posted`,
  `payment_*`, `paid`, `cleared`, `pipeline_status` and `display_status` moves onto
  facts that outlive the collapse.
- **Installable after it:** yes. Every new key exists before and after PR6.

| File                                                                                                                                                                                      | Change                                                                                                                                                                                                                                                                                                                                                                           |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `kmitl_project_disbursement/models/kmitl_project.py`                                                                                                                                      | Replace the tuples (L3-10) with domain helpers. **settled:** `['                                                                                                                                                                                                                                                                                                                 | ',('state','=','cancel'),('settlement_stage','in',('settled','booked'))]`. **approved:** `[('state','!=','cancel'),('budget_consumed_amount','>',0)]`. **pending:** `[('state','!=','cancel'),('budget_consumed_amount','in',(0, False))]`(the column is NULL when budget was never consumed). Re-key L44-130. Do not port the old bug where`bills_posted`/`payment_audited` fell into no bucket. Keep the cancel-only domains. |
| `procurement_plan_disbursement/models/procurement_plan.py`, `CONTEXT.md`                                                                                                                  | Same mapping (L3-6, L47-90). CONTEXT L20-21: "once the budget act consumed it".                                                                                                                                                                                                                                                                                                  |
| `agx_approval_disbursement/models/approval_request.py`                                                                                                                                    | Delete `_DISBURSEMENT_NOT_BILLED_STATES` (L10-18). A DR counts as billed when it is not cancelled and (`budget_consumed_amount > 0` or `settlement_stage != 'none'`). Depends gain `.budget_consumed_amount` and `.settlement_stage`. `init()`: `add_to_compute` on stored `billing_status` for every record, because rewriting a compute does not refresh existing stored rows. |
| `purchase_request_approval_disbursement/models/purchase_request_approval.py`                                                                                                              | Replace `_DR_STATE_TO_BILLING_STATUS` (L143-160) with `_dr_billing_status(dr)`: `draft` → draft; `submitted`/`signed` → submitted; `cancel` → cancel; `settlement_stage == 'booked'` → done; else in_progress. Depends gain `disbursement_request_ids.settlement_stage`. Same `init()` recompute.                                                                                |
| `advance_payment_disbursement/models/advance_payment_usage_line.py`                                                                                                                       | L25-28: `related='disbursement_request_id.settlement_stage'`, string "Disbursement Settlement Stage". Must land before PR6.                                                                                                                                                                                                                                                      |
| `purchase_order_disbursement/views/disbursement_request_views.xml`                                                                                                                        | L48-54: a `state` badge (decorations for `in_progress`, `done` and `cancel`) plus a `settlement_stage` badge.                                                                                                                                                                                                                                                                    |
| `disbursement_operating_unit/views/disbursement_request_views.xml`                                                                                                                        | Delete the inherit of `disbursement.view_disbursement_request_approved_search` (L50-68).                                                                                                                                                                                                                                                                                         |
| th.po of `kmitl_project_disbursement`, `procurement_plan_disbursement`, `advance_payment_disbursement`; `agx_approval_disbursement/CONTEXT.md`, `docs/adr/0001*`; `CONTEXT-MAP.md` L82-86 | Stat buttons "ใบเบิกตัดงบแล้ว" / "ยอดตัดงบแล้ว", the new field label. Docs: "the DR stays at its station" replaces "kept as-is at signed".                                                                                                                                                                                                                                       |

**Existing tests to repair:** none (these modules have no suites). **Minimal tests:**
none. **Unguarded:** every change here; the stat buttons are checked in §6.

**Verify:**

- Grep for DR-specific accessors:
  `grep -rnE "disbursement_request_id\.state|disbursement_request_ids\.state|d\.state (not )?in|DISBURSEMENT_[A-Z_]*_STATES|pipeline_status|display_status|_DR_STATE_TO" kmitl_project_disbursement procurement_plan_disbursement agx_approval_disbursement purchase_request_approval_disbursement advance_payment_disbursement purchase_order_disbursement disbursement_operating_unit`.
- Expected legitimate residuals:
  - `purchase_request_approval_disbursement` `_disbursement_return_state = "approved"`
    (its own model's state);
  - `approval.request` state reads in `agx_approval_disbursement`;
  - `state == 'cancel'` / `!= 'cancel'` domains.
- Review the diffs by hand. Only if asked: compare stat-button counts before and after.

**Acceptance:** no reader outside `disbursement/` and the two money bridges names a
state value or field that PR6 deletes.

**Risks:** the `billing_status` recompute on `purchase.request.approval` and
`approval.request` (stored, tracked) posts a wave of chatter on the pilot.

---

### PR6: the state collapse

- **Branch:** `16.0-imp-disbursement-state-collapse`. **Title:**
  `[16.0][IMP] disbursement: collapse the DR state to draft/submitted/signed/in_progress/done/cancel`
- **Modules:** `disbursement`, `disbursement_accounting_kmitl`,
  `disbursement_finance_kmitl`, `disbursement_budget`, `disbursement_assignment_kmitl`,
  `disbursement_cash_movement_kmitl`, `disbursement_cash_revenue_handover`,
  `finance_kmitl_demo`, `accounting_kmitl_workflow`. Logical dependencies PR2-PR5; base
  PR5.
- **Goal:** the one change that cannot be split. Delete the retired states, fields,
  flows, queues and every ordering guard keyed on state (D7). In the same commit, change
  every module that would fail at load or view validation. The three approval acts and
  `_on_final_approval` stay in core, guard-free, until PR7-PR10, so every intermediate
  PR stays installable.
- **Installable after it:** yes. Without PR11, a DR goes draft → submitted → signed and
  stays there; every act is offered at `signed` to its role; billing and payment work.
  The TO_AUDIT / TO_AUTHORIZE fan-outs are gone until the arrival Todos arrive (PR11).
  **Do not pilot, and never merge, PR6 without PR11** (§0.2).

| File                                                                                                                                                     | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| -------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `disbursement/__manifest__.py`, `models/__init__.py`                                                                                                     | Version `16.0.14.0.0`, no `migrations/`. Remove `wizards/disbursement_reject_wizard_views.xml`, `views/disbursement_approval_queue_views.xml` and the whole `web.assets_backend` block (keep the frontend asset). Reword the L7-12 comment.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `disbursement/models/disbursement_request.py`                                                                                                            | `state` (L196-212): `draft`, `submitted`, `signed`, `in_progress` ("In Progress"), `done` ("Done"), `cancel`. **Delete:** the `DR_*_ACTIVITY` constants (L15-20); `pipeline_status`, `display_status`, `approval_state` and `approval_reject_reason` with their computes (L214-264, L288-290, L527-559); `action_approve_batch`, `action_open_reject_wizard`, `_action_reject` and `action_request_approval` (L783-900); `_schedule_approval_todo`, `_reset_verification` and `_reset_approval` (L936-983). **Acts** `action_validate`, `action_approve_finance` and `action_approve` keep only: `_disbursement_check_act`, their own stamps, `_stamp_signature(step)`, `_disbursement_act_done`. `action_approve` still calls `_on_final_approval()` until PR7. **New** non-stored `can_validate`, `can_approve_director`, `can_approve_rector` = `_disbursement_act_offered(code)`, `@api.depends('state')` + `@api.depends_context('uid')`. **`action_cancel`:** drop `_reset_approval()`; for `in_progress` records, call `_disbursement_check_send_back()`. **`action_draft`:** guard `state in ('submitted','signed','in_progress','cancel')` (new msgid; `done` excluded); for `in_progress` records call `_disbursement_check_send_back()`; archive every active signature row; clear the three stamp pairs (the act modules take this over in PR8-PR10).                                                                                                                                                                                                                                                                                          |
| `disbursement/models/disbursement_return.py`, `disbursement_return_source.py`                                                                            | **Delete:** `_ACT_REVERIFY_XMLID`; `returned_to_verification` / `return_verification_reason` (L37-48); `action_return_verification_open_wizard`; `_action_return_to_verification`; `_clear_returned_to_verification`; the `action_validate` / `action_draft` / `action_cancel` overrides (L121-203). The docstring describes send-back only. `_action_return_for_edit` guard: `state in ('signed','in_progress')`, msgid "Only a request in the circuit can be sent back.". `_return_to_source` guard: the same; chatter "stays at its station". `_apply_source_correction`: "Please continue.". Delete the `action_validate` override (L270-293), which contains an ordering raise; `action_validate` calls `_resolve_source_correction_todos()`. Update the docstrings at L30-44 and L157-163.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `disbursement/wizards/*`                                                                                                                                 | Delete `disbursement_reject_wizard.py`, its views and its import. `return_request_wizard`: drop `mode` and the verification branch; add a server-side `strip()` check on the reason. View: delete L9.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `disbursement/views/disbursement_request_views.xml`                                                                                                      | **Tree:** a state badge over the six values; delete `pipeline_status` and the redundant invisible `state`. **Header:** Validate and both Approve buttons on the `can_*` flags (keep `groups=`); delete the Reject buttons (L82-95), Request Approval Again (L96-103), the pipeline/display/approval_state nodes (L119-132) and both banners (L150-180). `action_draft` (keep the node, it is an anchor) is visible for `submitted, signed, cancel`, manager group: **not** `in_progress`. `action_cancel` is invisible only when `state == 'cancel'`. Exactly one `<field name="state" widget="statusbar" statusbar_visible="draft,submitted,signed,in_progress,done"/>`. **Search:** `pre_approval` → `open` (`state not in ('done','cancel')`); delete the verified/approved and pipeline filters (L490-524); add an `in_progress` filter and a state filter **named `done`** (the finance anchor survives, now meaning the circuit finished); keep the `signed`, `draft`, `submitted` and `state` group-by filters. **Action:** `search_default_open`; rewrite the literal Thai help.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `disbursement/views/disbursement_approval_queue_views.xml`, `static/src/approval_queue/`                                                                 | Delete.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `disbursement/views/disbursement_return_views.xml`, `security/ir.model.access.csv`, `data/mail_activity_type_data.xml`                                   | Return button: invisible unless state is in (`signed`, `in_progress`) and not `returned_to_source`; `groups="disbursement.group_disbursement_user"`. Delete the Return to Verification button (L25-32) and its filter (L58-62). Delete ACL rows 15-16. Delete `mail_activity_dr_reverify` / `_dr_approve_finance` / `_dr_approve_rector` / `_dr_rejected`; they are noupdate="1", so the snippet removes the DB rows.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `disbursement/i18n/th.po`                                                                                                                                | §5.3.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `disbursement/docs/adr/0001-*.md`                                                                                                                        | Status: "superseded by disbursement_wc ADR-0001". The glossary banner and rewrite of `disbursement/CONTEXT.md` happen in **PR11**: the banner commit `8b8afcd9` lives on the `disbursement_wc` branch.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `disbursement_accounting_kmitl/models/disbursement_request.py`, `account_move.py`, `accounting_kmitl_dashboard.py`                                       | Delete the state/pipeline/display `selection_add`s (L12-42), the pipeline/display compute overrides (L124-143) and the `_action_return_to_verification` override (L342-355). `_create_bill`: delete the `approved` guard and refuse on `cancel` (new msgid). `_disbursement_acts` adds `disbursement.create_bill` (`accounting_kmitl.group_accounting_kmitl_user`, states `('signed','in_progress','done')`). `action_create_bill`: check act → existing-bills integrity check → act_done. `can_create_bill` (`depends_context('uid')`, depends `state`, `bill_ids.state`) = offered and no non-cancelled bill. `action_post_bills`: drop the guard and the state write. `_post`: drop the `approved` filter and the `bills_posted` write. Dashboard card domain: `[('state','in',('signed','in_progress')),('settlement_stage','=','none'),('bill_ids','=',False)]`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `disbursement_accounting_kmitl/views/disbursement_request_views.xml`, `i18n/th.po`, `tests/test_dashboard_card.py`                                       | Delete the `display_status` xpath (L36-39) and the Return to Verification button (L51-56). Create Bill re-anchored to `//button[@name='action_draft']` `position="before"`, invisible `['                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | ',('can_create_bill','=',False),('bill_count','>',0)]`, groups kept. Action: `search_default_awaiting_bill`on a new filter with the card domain; rewrite the help. th.po per §5.3. Test L23 expects the new domain and also asserts that a DR with no bills reads`none`; `count == search_count` kept. |
| `disbursement_finance_kmitl/models/disbursement_request.py`, `account_move.py`                                                                           | **Delete:** the state/pipeline/display `selection_add`s (L46-94); `_compute_pipeline_status` (L187-207); the TO_AUDIT / TO_AUTHORIZE constants, fan-outs and the `write()` `bills_posted` branch. Keep `payment_subject_id`, TO_PAY, TO_BOOK and the group constants. **Acts:** `action_audit` = `disbursement.audit_payment` (AUDITOR_GROUP): check; **UserError "Post the bills first." when there is no posted active bill** (integrity); `_ensure_payment_lines`; `_check_payment_classification`; stamp; `_stamp_signature('payment_audit')`; act_done. `action_authorize` = `disbursement.authorize_payment` (AUTHORIZER_GROUP): check; stamp; signature; TO_PAY; `_try_create_payments`; act_done. Neither has a state guard or writes state. **Other methods:** `action_confirm_paid` drops the state guard and keeps the integrity checks; `_hand_over` drops the `paid` write; `action_submit_payments` guards on `settlement_stage == 'settled'`; `_payment_batch(single_method, predicate)` keeps the savepoints; `action_cancel` refuses when the stage is `settled` or `booked`; `_create_payments` deletes the L758 ordering guard and keeps the duplicate/partial/classification checks. **New flags** (`depends_context('uid')`, real depends): `can_audit_payment` = offered and a posted active bill exists; `can_authorize_payment` = offered; `can_edit_payment_subject` = audit offered and no active voucher. Rewrite the docstring (L20-42). `account_move.py` L84-99: drop the `paid` filter and the `cleared` write; keep `_reconcile_source_invoice_lines` and the TO_BOOK feedback when all active vouchers are posted.        |
| `disbursement_finance_kmitl/views/*.xml`, `data/mail_activity_type.xml`, `i18n/th.po`, `CONTEXT.md`, `docs/adr/0001-0005*`, `docs/adr/0006*`             | **Queues** (`disbursement_queue_views.xml`): the badge becomes `state` + `settlement_stage`; row and batch buttons use the `can_*` flags. Domains are integrity-only, with no stamp-order conditions: audit list `[('state','in',('signed','in_progress','done')),('payment_line_ids','!=',False)]`, renamed "Requests with Payment Lines"; authorize list `[('state','in',('signed','in_progress')),('payment_line_ids','!=',False),('payment_ids','=',False)]`, renamed "Requests without Vouchers"; book `[('settlement_stage','=','settled')]`. With `disbursement_wc` installed, **the station card is the desk's worklist** (§8 item 19). Reword the stale L20 comment (deleted approved tree). **Request views:** finance action domain `settlement_stage != 'none'`; the authorized history keeps only the stamp leg; delete the tree `display_status` xpath (L72-89) and the form statusbar xpath; the search inherit keeps `//filter[@name='done']`, swaps the state filters for settlement filters, and keeps Audited/Authorized by Me; Audit/Authorize buttons on the flags; Create Payment: `payment_authorizer_id` set and `payment_count == 0`; Confirm Paid: `settlement_stage == 'billed'` and `payment_count > 0` (still `base.group_no_one`); the Payment Execution page is invisible without `payment_line_ids`; the alert and `payment_subject_id` use `can_edit_payment_subject`; keep `force_save` on `paying_account_match`. **Data:** delete `mail_activity_dr_to_audit` / `_to_authorize` (the snippet removes the rows). th.po per §5.3. CONTEXT.md and ADRs 0001, 0002, 0003, 0004, 0005, 0006 get "superseded in part" notes. |
| `disbursement_finance_kmitl/tests/test_payment_workflow.py`                                                                                              | Delete L129. L156 asserts `settlement_stage == 'billed'`. Docstring reworded. `test_audit_authorize_forward` asserts the stamps and vouchers. `test_audit_requires_bills_posted` is re-keyed in place to "audit before any bill posted raises 'Post the bills first.'" (integrity). `test_authorize_requires_audited` is deleted (pure ordering). `test_pipeline_done_when_cleared` → "booked when every active voucher posted". `test_cancel_blocked…` drops L239. L401 / L489 assert the stamps. Hand-over tests: `payment_authorized` → stage `billed`, `paid` → `settled`. **Invert** `test_a_bounced_cheque…`: the stage walks back to `billed` and the state is unchanged.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `disbursement_budget/tests/test_final_approval_budget.py`, `models/disbursement_request.py`                                                              | Test: use `_make_signed_dr`; finance approve leaves consumption at 0; `action_approve` without a commitment raises UserError; drop the `verified` assertion. Model L223-224 comment: "after a divert back". `security/security.xml` comment untouched until PR7.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `disbursement_assignment_kmitl/...`                                                                                                                      | Interim, until PR12: `_assignment_auto_assign` filters `state in ('signed','in_progress')`; replace the `action_validate` override with a `_disbursement_act_done(code)` override that closes the Todo when `code == 'disbursement.validate'`; `action_apply_to_pending` domain `[('state','in',('signed','in_progress')),('assigned_to','=',False)]`; buttons invisible unless state is in (`signed`, `in_progress`). Tests: `test_validate_by_other_officer_closes_todo` drops the `verified` assertion; `test_manual_assign…` resets from `signed` (the factory stubs `_on_signed`).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `disbursement_cash_movement_kmitl/tests/test_cash_movement.py`, `disbursement_cash_revenue_handover/tests/…`, `models/account_move.py`, `docs/adr/0001*` | Delete the `request.state = 'approved'` fixtures (L120, L173); reword the docstrings ("a billed payment line"; "would count as billed"). L376-380 asserts the state is unchanged and the stage is `none`. ADR-0001 gets a "superseded in part" note.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `disbursement/tests/test_two_approver.py`, `test_return_verification.py`, `test_signature_block.py`                                                      | **`test_two_approver.py`:** keep the file, the class `TwoApproverCommon` and its import path; keep the officer/finance/rector users (the groups stay in core); drop the activity refs (L63-67); `_make_verified_dr` → `_make_signed_dr` (no `signed` assertion); `_patch_final_approval` → `_patch_circuit_entry` = `patch.object(type(self.DR), '_on_signed')`; delete the `TestTwoApprover` workflow tests (L102-170) (the rector suite in PR10 inverts `test_cannot_skip_finance_step`); keep `test_cancel_resets_approval` without L176. **`test_return_verification.py`:** delete `_make_verified_dr` and the four return-to-verification / wizard-mode tests; `_make_signed_dr` asserts `state in ('signed','in_progress')`; send-back and resubmit run under `_patch_circuit_entry`. **`test_signature_block.py`:** `_approve_fully` stamps directly with `dr.with_user(u)._stamp_signature(step)` in the asserted order; delete the reject-round test.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `finance_kmitl_demo/hooks.py`, `accounting_kmitl_workflow/models/account_move.py`, `CONTEXT-MAP.md`                                                      | Demo: docstrings and logs say stage "billed"; `_approve_dr` keeps calling the core acts under su. Workflow L83 docstring: drop the `display_status` reference. CONTEXT-MAP L103-107: finance = audit/authorize acts plus ขั้นการชำระ.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `.context/disbursement-station-pilot.py` (new, local)                                                                                                    | **Section A**, run with the old code: `action_cancel` every DR in `submitted / signed / verified / approved` with no posted bill (reverses budget, cancels draft bills); print the rest. Before cancelling, post one plain chatter note per DR that summarises its `approval_state` tracking values, because deleting the field cascades away `mail.tracking.value` rows. **Section B** is completed in PR11.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |

**Existing tests repaired (NEVER RUN):** the nine files above.

**Minimal tests for new modules:** none.

**Left unguarded:** cancel/draft authority for `in_progress` DRs (PR11's suite covers
it); the finance queue domains; the demo.

**Verify:**

- Run
  `grep -rnE "approval_state|pipeline_status|display_status|bills_posted|payment_audited|payment_authorized|READONLY_STATES|_reset_approval|action_approve_batch|action_request_approval|_action_return_to_verification|approval_queue" --include=*.py --include=*.xml --include=*.js --exclude-dir=migrations --exclude-dir='purchase_request_approval*' .`
  over the modules this PR touches. Expected residuals: `docs/`, `CONTEXT*.md`,
  `accounting_kmitl_workflow`'s own `action_approve_batch` on `account.move`.
- `grep -rn "state = .approved." */tests` returns nothing.
- pyflakes, xmllint and `msgfmt -c` on every touched module.

**Acceptance:**

- The `state` selection has exactly six keys, and no module `selection_add`s to it.
- Approving a never-validated DR succeeds. A bill on a `signed` DR succeeds; a second
  bill is refused.
- The anchors `action_submit`, `action_sign`, `action_draft`,
  `//header/field[@name='state']`, filters `signed`/`state`/`done` and
  `//group[@id='other_information']` exist.
- Each act refuses a user without its role over RPC and refuses a draft DR.

**Risks:**

- This is the largest PR: review it module by module and revert it as one unit.
- `approval_state` tracking history is erased on `-u` unless section A ran.
- Orphan raw state values remain until section B runs.
- Several consumers (the demo) have no tests: read the warning log.

---

### PR7: budget is its own act

- **Branch:** `16.0-imp-disbursement_budget-consume-act`. **Title:**
  `[16.0][IMP] disbursement_budget: consuming budget is its own act, gated by a per-DR flag`
- **Modules:** `disbursement`, `disbursement_budget`, `finance_kmitl_demo`,
  `procurement_plan_disbursement` (CONTEXT). Logical dependency PR6.
- **Goal (D16):** consumption leaves the rector's approval and becomes
  `disbursement.consume_budget`. The new flag `consumes_budget` is off for
  เงินรับฝากบุคคลที่สาม / เงินประกัน.
- **Installable after it:** yes. Budget is consumed only by the act, which stations
  offer and require (PR11's setup requires it at the rector station).

| File                                                                                       | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `disbursement/models/disbursement_request.py`, `docs/adr/0003-*.md`                        | Delete `_on_final_approval()` (L988-991) and its call in `action_approve`. ADR-0003 note: consumption is `disbursement_budget`'s own act.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `disbursement_budget/models/disbursement_request.py`                                       | `consumes_budget` Boolean("Consumes Budget", default True, tracking, copy). True is stamped on every existing row by design (today's behaviour). Help names the deposit and guarantee sources. `_disbursement_acts` adds `disbursement.consume_budget` (`disbursement.group_disbursement_rector_delegate`, §8 item 5). `_disbursement_act_applicable`: False for that code when not `consumes_budget`; the engine logs it as not applicable on the visit (ADR-0003 (a)). `action_consume_budget()`: check act; if `consumes_budget`, `_action_approve_budget()` (idempotent); act_done. `can_consume_budget` = offered and `consumes_budget` and `budget_consumed_amount in (0, False)`. Delete the `_on_final_approval` override (L306-308). `_check_commitment_obligable` runs only when `consumes_budget`; message "…required before consuming budget.". `consumes_budget` is covered by `can_edit_budget`. |
| `disbursement_budget/views/…`, `security/security.xml`, `i18n/th.po`                       | Delete the `action_approve` attributes xpath (L24-26). Add a "Consume Budget" button carrying that confirm text (invisible unless `can_consume_budget`). Add `consumes_budget` with readonly on `can_edit_budget`. Security comment: "consumed on the budget act". th.po: ใช้งบประมาณ, ตัดงบประมาณ, the confirm text, the act name (python) and the reworded error.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `disbursement_budget/tests/test_final_approval_budget.py`, `test_budget_ledger_consume.py` | In place, keeping the file name and the `TwoApproverCommon` import. **`test_final_approval_budget.py`:** the consume act without a commitment raises UserError when `consumes_budget` is True; with `consumes_budget` False it consumes nothing and the act is not applicable; `action_approve` no longer consumes. **`test_budget_ledger_consume.py`:** `_request` sets `consumes_budget=True` explicitly; the L68 comment says "after a divert back".                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `finance_kmitl_demo/hooks.py`, `procurement_plan_disbursement/CONTEXT.md`                  | Demo calls `action_consume_budget()` after `action_approve`. CONTEXT: "once the budget act consumed it".                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |

**Existing tests repaired (NEVER RUN):** both budget test files.

**Minimal tests for new modules:** none.

**Unguarded:** the consume act on a draft DR (an integrity check, but no test).

**Verify:** `grep -rn _on_final_approval .` returns only docs; pyflakes; `msgfmt -c`.

**Acceptance:**

- Pressing consume twice posts one consume.
- With `consumes_budget` False the act is never "missing" at forward and is listed as
  not applicable on the visit.

**Risks:** until a station requires `consume_budget`, nobody is forced to press it (the
PR11 setup makes it required).

---

### PR8: `disbursement_validation`

- **Branch:** `16.0-add-disbursement_validation`. **Title:**
  `[16.0][ADD] disbursement_validation: the ตรวจสอบ act leaves core`
- **Modules:** `disbursement_validation` (new), `disbursement`,
  `disbursement_assignment_kmitl` (test only), `finance_kmitl_demo`,
  `kmitl_depends_dev`, `CONTEXT-MAP.md`. Logical dependency PR6.
- **Goal:** move `action_validate`, `verifier_id` / `verify_date`, the button and the
  strings out of core. Behaviour is unchanged, and the act code `disbursement.validate`
  is unchanged, so station configuration survives. The sync rewrites the act row's
  `module` and unarchives it if a core-only window archived it.
- **Installable after it:** yes, provided `-u disbursement -i disbursement_validation`
  runs **in one command** (§3.0). A separate install drops the stamp columns.

| File                                                                                        | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `disbursement_validation/__manifest__.py`, `__init__.py`, `models/disbursement_request.py`  | depends `['disbursement']`, LGPL-3, `16.0.1.0.0`. Moved from core: `verifier_id`, `verify_date` (same column names), with the comment that distinguishes them from `assigned_to`. `action_validate`: check act → stamp → `_stamp_signature('verify')` → `_resolve_source_correction_todos()` → act_done. `_disbursement_acts` declares `disbursement.validate` (module `disbursement_validation`). `can_validate` flag. An `action_draft` override clears the stamp. |
| `disbursement_validation/views/disbursement_request_views.xml`, `i18n/th.po`, `README.rst`  | Validate button (confirm text, `attrs` on `can_validate`). The verifier pair goes in `//group[@id='other_information']`. th.po: the moved entries plus the act-name python entry, including `field_disbursement_request__verifier_id` under this module. README: act terms live in `disbursement_wc/CONTEXT.md`.                                                                                                                                                     |
| `disbursement/models/…`, `views/…`, `i18n/th.po`, version `16.0.15.0.0`                     | Remove `action_validate`, the stamps, `can_validate`, the declaration, the stamp clearing in `action_draft`, the button, the verifier pair and the moved th.po entries.                                                                                                                                                                                                                                                                                              |
| `disbursement/tests/test_signature_block.py`                                                | Move `test_validate_stamps_the_verifier_and_a_signature` out to the new suite (a move, not an addition). `test_reset_to_draft_archives_everything` drops L263.                                                                                                                                                                                                                                                                                                       |
| `disbursement_assignment_kmitl/tests/test_assignment_rule.py`                               | `test_validate_by_other_officer_closes_todo` calls `dr.with_user(self.officer_b)._disbursement_act_done('disbursement.validate')` instead of `action_validate()`, so the assignment suite no longer needs this module.                                                                                                                                                                                                                                               |
| `disbursement_validation/tests/__init__.py`, `tests/test_validation.py` (new suite)         | Under `_patch_circuit_entry`: an officer's validate sets the stamps and one `verify` row, and the state is unchanged; validating twice leaves one active `verify` row; a non-officer gets AccessError (`invalidate_all()` first); validate on a `draft` DR raises UserError; holds the moved signature test. **Written, NEVER RUN.**                                                                                                                                 |
| `finance_kmitl_demo/__manifest__.py`, `kmitl_depends_dev/__manifest__.py`, `CONTEXT-MAP.md` | Add the module to both manifests. CONTEXT-MAP entry: "ตรวจสอบ act on the DR; terms in disbursement_wc/CONTEXT.md".                                                                                                                                                                                                                                                                                                                                                   |

**Verify:**

- `grep -rn 'verifier_id\|action_validate' disbursement/` returns only docs.
- After the pilot install command, `\d disbursement_request` still has `verifier_id`,
  and existing stamps are filled.

**Acceptance:** core has no `action_validate`. Validate works from the module, and the
station's allowed act is unchanged.

**Risks:** forgetting `-i` in the same command loses the stamps and archives the act.

---

### PR9: `disbursement_approver_director`

- **Branch:** `16.0-add-disbursement_approver_director`. **Title:**
  `[16.0][ADD] disbursement_approver_director: the ผอ.กองคลัง act leaves core`
- **Modules:** `disbursement_approver_director` (new), `disbursement`,
  `finance_kmitl_demo`, `kmitl_depends_dev`, `CONTEXT-MAP.md`. Logical dependency PR6.
- **Goal:** move `action_approve_finance`, `finance_approver_id` /
  `finance_approve_date`, `FINANCE_DIRECTOR_GROUP`, the button and the strings out of
  core. The role group xmlid stays in core (§8 item 11).
- **Installable after it:** yes, with the same single-command rule.

| File                                                                                          | Change                                                                                                                                                                                                                                                                                                                   |
| --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `disbursement_approver_director/{__manifest__.py,__init__.py,models/disbursement_request.py}` | depends `['disbursement']`. Moved: the constant, the stamps, and `action_approve_finance` (check → stamps → `_stamp_signature('finance_approve')` → act_done). New: the `disbursement.approve_director` declaration, `can_approve_director`, `action_draft` stamp clearing.                                              |
| `…/views/disbursement_request_views.xml`, `i18n/th.po`, `README.rst`                          | Button with `groups="disbursement.group_disbursement_finance_director"`. Stamp pair in `//group[@id='other_information']`. th.po: Approve (Finance Director), Finance Director, Finance Approved On, the confirm text, the act name and the field xmlids under this module.                                              |
| `disbursement/…`, version `16.0.16.0.0`                                                       | Remove the moved pieces. The group-name entry and the `finance_approve` step label stay. `TwoApproverCommon` keeps the finance user.                                                                                                                                                                                     |
| `…/tests/__init__.py`, `tests/test_director.py` (new suite)                                   | Acting on a never-validated DR succeeds (ADR-0001), sets the stamps and one `finance_approve` row, and leaves `budget_consumed_amount` unset or 0. Acting on a `draft` DR raises. A non-member director is refused when the station has members (skipped unless `disbursement_wc` is installed). **Written, NEVER RUN.** |
| manifests, `CONTEXT-MAP.md`                                                                   | Add the module; CONTEXT-MAP entry.                                                                                                                                                                                                                                                                                       |

**Verify:** `grep -rn action_approve_finance disbursement/` returns nothing.

**Acceptance:** the director act works with no prior validation.

**Risks:** the deploy must include `-i` in the same command.

---

### PR10: `disbursement_approver_rector`

- **Branch:** `16.0-add-disbursement_approver_rector`. **Title:**
  `[16.0][ADD] disbursement_approver_rector: the ผู้รับมอบอำนาจอธิการบดี act leaves core`
- **Modules:** `disbursement_approver_rector` (new), `disbursement`,
  `finance_kmitl_demo`, `kmitl_depends_dev`, `CONTEXT-MAP.md`. Logical dependency PR7.
- **Goal:** move `action_approve`, `rector_approver_id` / `rector_approve_date`,
  `RECTOR_DELEGATE_GROUP`, the button and the strings out of core. After this PR, core
  declares no act.
- **Installable after it:** yes, with the same single-command rule. Budget was decoupled
  in PR7, and the accounting anchor was re-pointed in PR6.

| File                                                                                        | Change                                                                                                                                                                                                                                                                                                                                                          |
| ------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `disbursement_approver_rector/{__manifest__.py,__init__.py,models/disbursement_request.py}` | depends `['disbursement']`. Moved: the constant, the stamps, and `action_approve` (method name kept; check → stamps → `_stamp_signature('rector_approve')` → act_done). New: the `disbursement.approve_rector` declaration, `can_approve_rector`, `action_draft` stamp clearing.                                                                                |
| `…/views/disbursement_request_views.xml`, `i18n/th.po`, `README.rst`                        | Button with `groups="disbursement.group_disbursement_rector_delegate"`. **`rector_approver_id` / `rector_approve_date` re-added via `//group[@id='other_information']`**, with `invisible` attrs on `rector_approver_id`. th.po: Approve (Rector Delegate), Rector-delegated Approver, Rector Approved On, the confirm text, the act name and the field xmlids. |
| `disbursement/…`, version `16.0.17.0.0`                                                     | Remove the moved pieces; core `_disbursement_acts()` returns `[]`.                                                                                                                                                                                                                                                                                              |
| `…/tests/__init__.py`, `tests/test_rector.py` (new suite)                                   | The inversion of the deleted `test_cannot_skip_finance_step`: the rector acts without any director approval and succeeds, setting the stamps and one `rector_approve` row, while `budget_consumed_amount` stays unset or 0. Acting on a `draft` DR raises. **Written, NEVER RUN.**                                                                              |
| manifests, `CONTEXT-MAP.md`                                                                 | Add the module; CONTEXT-MAP entry.                                                                                                                                                                                                                                                                                                                              |

**Verify:** `grep -rn "name=.action_approve." --include=*.xml .` shows only this module
(excluding the `account.move` button in `accounting_kmitl_workflow`).

**Acceptance:** core hosts no approval act.

**Risks:** the deploy must include `-i`.

---

### PR11: `disbursement_wc` (PO trial gate, together with PR12)

- **Branch:** `16.0-add-disbursement_wc` (existing; rebased onto PR10). **Title:**
  `[16.0][ADD] disbursement_wc: route the DR through stations`
- **Modules:** `disbursement_wc`, `disbursement` (CONTEXT/ADR docs only),
  `kmitl_depends_dev`, `CONTEXT-MAP.md`. Logical dependencies PR1 and PR6-PR10.
- **Goal:** plug `disbursement.request` into the engine through the core seams:
  - `signed` → `in_progress` at station 1; resubmit re-enters at station 1 unsigned;
  - forward out of the last station → `done`;
  - send-back and cancel leave the circuit;
  - act, edit and send-back authority are keyed on the holding station;
  - the walk-back Todo after `done`;
  - seeded area, six central stations, route and counters.
- **Installable after it:** yes. With no active route, `_on_signed` logs a warning and
  the DR stays at `signed` (PR6 behaviour), so installing locks nobody out. Act, edit
  and member configuration is admin data, set by the setup snippet.

| File                                                                  | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `__manifest__.py`, `__init__.py`, `models/__init__.py`                | depends `['disbursement', 'work_center']`. data: `data/work_center_data.xml`, `data/mail_activity_type_data.xml`, `views/disbursement_request_views.xml`, `views/work_center_menus.xml`. `16.0.1.0.0`, LGPL-3.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `models/disbursement_request.py`                                      | `_name = 'disbursement.request'`; `_inherit = ['disbursement.request', 'work.center.mixin']` (the explicit `_name` is mandatory). **Acts:** `_work_center_acts()` = `super()` + `self._disbursement_acts()` (stamped with model and module) + five edit kinds: `disbursement.edit_header`, `disbursement.edit_lines`, `disbursement.edit_attachments`, `disbursement.edit_dimensions`, `disbursement.edit_budget` (`kind='edit'`, group `disbursement.group_disbursement_officer`, §8 item 7). `_work_center_act_applies(code)` → `_disbursement_act_applicable(code)`. `_disbursement_act_offered(code)`: when `in_progress` → `_work_center_offers(code)`, else `super()`. `_disbursement_check_act(code)`: `super()` (state and role), then `_work_center_check_act(code)` when `in_progress`. `_disbursement_act_done(code)`: `super()` then `_work_center_act_done(code)`. `_disbursement_check_send_back()`: when `in_progress` → `_work_center_check_move()`, else `super()`. **Entry:** `_on_signed()`: `super()`; if `self._work_center_route()` exists: **first write `state='in_progress'`, then** `self.sudo()._work_center_enter('resubmit' if context disbursement_resubmit else 'enter')`, so arrival hooks (assignment, PR12) see `in_progress`. sudo because the Saraban head may not read stations; `env.user` is still recorded as the mover. `_work_center_on_exit()`: `state='done'`. **Exits:** `action_draft()`: for records holding a station or an open visit, `_work_center_leave(context work_center_departure or 'send_back', reason from context)`, then `super()` (one shared exit for send-back, Saraban return and the exception wizard). `_action_return_for_edit(reason)`: `super()` under context `work_center_departure='send_back'` and the reason. `_return_to_source` does not leave. `action_cancel()`: `_work_center_leave('cancel')`, then `super()`. `_work_center_circuit_domain()` → `[('state','=','in_progress')]`. **Locks:** `_can_edit_open(kind)`: `super()` or (`state == 'in_progress'` and `_work_center_offers('disbursement.edit_' + kind)` and `settlement_stage == 'none'`); extend the `_compute_can_edit` depends with `work_center_id` and `settlement_stage` only. **Walk-back (D19):** `_on_settlement_walked_back(previous)`: for `done` records, `visit = _work_center_last_visit(('forward','exit'))` (the exit visit for a done DR, i.e. สถานีอนุมัติจ่าย); recipients = `visit.work_center_id.member_ids` (active), or its role holders when it has no members; schedule `mail_activity_dr_money_walked_back` for each; the DR stays `done`. |
| `data/work_center_data.xml`, `data/mail_activity_type_data.xml`       | `noupdate="0"`: `area_disbursement` ("Disbursement", model `disbursement.request`) and `mail_activity_dr_money_walked_back` (execution, `res_model` `disbursement.request`). `noupdate="1"` (admin data): six **central** stations, no OU (`disbursement_operating_unit` is uninstalled on the snapshot): `station_check` (สถานีหมวดตรวจ), `station_director` (สถานี ผอ.กองคลัง), `station_rector` (สถานีผู้รับมอบอำนาจอธิการบดี), `station_bill` (สถานีตั้งหนี้), `station_audit` (สถานีตรวจจ่าย), `station_authorize` (สถานีอนุมัติจ่าย). `route_disbursement` with six single-candidate lines (sequence 10-60). Counters "Waiting here" `[('state','=','in_progress')]` and "Not yet billed" `[('state','=','in_progress'),('settlement_stage','=','none')]`. No acts in XML. Seeded stations have neither acts nor members until the setup snippet runs, so the "act or member" constraint is checked only in the UI: give each seeded station one member placeholder? **No.** Instead the constraint skips records created with context `install_mode`; document this in the README.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `views/disbursement_request_views.xml`, `views/work_center_menus.xml` | **Form:** ส่งต่อ (Forward) and Divert buttons before `action_draft`, invisible `['                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | ',('state','!=','in_progress'),('work_center_can_move','=',False)]`, context `{'expected_station': work_center_id}`; the core Return button's attrs also require `work_center_can_move`; `work_center_id`, `work_center_next_id`and missing acts (tags) near the statusbar; page **สมุดเยี่ยม** ("Visit Log") embedding`work_center_visit_ids`; invisible `work_center_can_move`. The generic Send Back button is **not** shown, because the core Return wizard is the DR's send-back and keeps return-to-source. **Tree:** a `work_center_id` column. **Search:** "At My Stations" (`work_center_id.is_my_station`) and group by station. **Menu:** `menu_disbursement_stations`"Stations" kanban action scoped to`area_disbursement`, `parent="disbursement.menu_disbursement_root"`, `sequence="15"`, `groups="disbursement.group_disbursement_user"`. Template: `git show f5c38040:purchase_request_work_center/views/work_center_menus.xml`(closed branch`16.0-add-purchase_request_work_center`). |
| `i18n/th.po`                                                          | §5.4, including every mixin field under `disbursement_wc.field_disbursement_request__*`, the six route-line names (`model:work.center.route.line,name`), stations, area, route, counters, buttons, the page, filters, the menu, the walk-back type and the five edit-kind names.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `README.rst`                                                          | Hand-written: what entering the circuit means; configuration; D7 (ordering is recorded, not enforced); the deliberate D13 narrowings (draft bills and budget commitments also lock; §8 item 8); seeded stations start empty and must be configured; the pilot snippets.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `CONTEXT.md`, `docs/adr/`                                             | Close the Member flag (L89-95). Update the status banner. Add a short term "ส่วนที่แก้ไขได้ (Editable part)": a part of the DR a station lets its people edit; not an act, never required. Act terms (ตรวจสอบ, เห็นชอบ, อนุมัติ, ตั้งหนี้, ตรวจจ่าย, อนุมัติจ่าย, ตัดงบประมาณ) live here for every act module.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `disbursement/CONTEXT.md`                                             | Rewrite now (the banner commit `8b8afcd9` is on this branch): remove the banner and the approval_state, Two-approver step, Approver queue and Reject entries; point the act terms at `disbursement_wc/CONTEXT.md`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `CONTEXT-MAP.md`, `kmitl_depends_dev/__manifest__.py`                 | `disbursement_wc` entry: state = progress around the วงจร; ขั้นการชำระ = money. Add the module to the dev stack.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `tests/__init__.py`, `tests/test_disbursement_wc.py` (new suite)      | Fixtures: import `TwoApproverCommon`; reuse the seeded area and stations via `env.ref` (a second DR area trips `_check_model_in_one_area`); configure acts and explicit members in `setUpClass`; call `_reflect_acts()`. Tests: (1) sign → `in_progress` at `station_check`, one open visit (snapshot = members), one arrival Todo per member; (2) forward closes the visit (`departure_act='forward'`) and lands at station 2; forward out of the last station → departure `exit`, `done`, pointer False, stage `none`, Todos closed; (3) send-back via the Return wizard → `draft`, departure `send_back` with the reason; (4) resubmit → `in_progress` at station 1, arrival `resubmit`, no pass through `submitted`; (5) return-to-source keeps the station; (6) a non-member officer is refused send-back, `action_draft` and `action_cancel` on an `in_progress` DR (`invalidate_all()` first); (7) `can_edit_lines` is False at a station that does not allow `edit_lines`; (8) walk-back: call `_on_settlement_walked_back('billed')` directly on a done DR and assert the Todos go to the members of the **exit** station (`station_authorize`); (9) if `th_TH` is active, the `disbursement.validate` act name is Thai. **Written, NEVER RUN.**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `.context/disbursement_wc_pilot_setup.py` (new, local)                | 1. `_reflect_acts()`. 2. Per station, allowed / required: check = validate (required) + edits `edit_header`, `edit_lines`, `edit_attachments`, `edit_dimensions`, `edit_budget`; director = approve_director; rector = approve_rector + consume_budget; bill = create_bill; audit = audit_payment; authorize = authorize_payment. Required = every allowed `kind='act'`. 3. Seat members from a dict at the top of the file, **supplied by the PO** (the snippet refuses to run while the dict is empty). 4. Print a summary.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `.context/disbursement-station-pilot.py` section B (local)            | Run after the install and the setup snippet, as su. 1. SQL-map `paid`, `cleared`, `payment_authorized` → `done` (all three completed the อนุมัติจ่าย act; §8 item 13). 2. `bills_posted` → set `in_progress`, `_work_center_enter('enter')`, then `with_context(work_center_act_anywhere=True)._work_center_divert(station_audit, reason='pilot: legacy state bills_posted')`. 3. `payment_audited` → the same with `station_authorize`. 4. Any other orphan value (`verified`, `approved`) → print and stop. 5. `add_to_compute` `settlement_stage` on all DRs and `billing_status` on PAs and ARs, then `flush_all()` (reading is not enough). 6. Unlink open activities of the six retired types, then the types. 7. Print the counts.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |

**Verify:** pyflakes, xmllint, `msgfmt -c`; then the trial in §6.

**Acceptance:**

- Saraban completion (action_sign under sudo) lands the DR `in_progress` at
  สถานีหมวดตรวจ with a visit row whose mover is the head.
- After a divert, forward goes to the station after the last on-route visit.
- Only members of the holding station (or role holders when it has none) can ส่งต่อ,
  divert, send back, reset or cancel an `in_progress` DR.
- Each act is offered only where its station allows it.
- State moves only through `_on_signed`, exit, `action_draft` and `action_cancel`, and
  every move is in the สมุดเยี่ยม.

**Risks:**

- Core and assignment tests that sign a DR must stub `_on_signed` (done in PR6).
- A memberless seeded station fans Todos out to every role holder: the setup snippet
  seats members.

---

### PR12: assignment inside a station

- **Branch:** `16.0-imp-disbursement_assignment_kmitl-station`. **Title:**
  `[16.0][IMP] disbursement_assignment_kmitl: assign an officer inside the station the DR arrives at`
- **Modules:** `disbursement_assignment_kmitl`. Logical dependency PR11.
- **Goal (D19):** auto-assign on station arrival; rules scoped to a station; the Todo
  closed on any departure; assignment works at any station, not only for verification
  officers.
- **Installable after it:** yes. Assignment now requires `disbursement_wc`.

| File                                                               | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `__manifest__.py`                                                  | depends gains `disbursement_wc`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `models/disbursement_request.py`                                   | Remove the `action_sign`, `action_resubmit_verification` and `_disbursement_act_done` triggers. `_work_center_on_arrival(visit)`: `super()`; for `in_progress` records, `_assignment_auto_assign` with rules whose `work_center_id == visit.work_center_id`, or rules without a station when the visit is on route line 1. Keep the sudo rule search and the manual-assign guard. `_work_center_on_departure(visit)`: close the assignment Todo. Keep the `action_draft` / `action_cancel` closes. Summary renamed consistently to "Assigned as the responsible officer at this station" (it is the activity-matching key). |
| `models/assignment_rule.py`                                        | New `work_center_id` M2o (domain: DR area, not Unassigned; help "Station where this rule assigns; empty = the first station of the route"; no default). `user_id` domain widened from the officer group to `[('id','in',allowed_user_ids)]`, a computed m2m of the station's members, or its role holders when it has none. Constraint: when the station has members, `user_id` is one of them. Docstring: "when a request arrives at a station". `action_apply_to_pending`: `[('state','=','in_progress'),('assigned_to','=',False)]` plus the station match.                                                              |
| `wizards/assign_officer_wizard.py`, `security/ir.model.access.csv` | Wizard ACL → `group_disbursement_user`. `action_confirm` checks `_work_center_check_move()` on the DR (members of the holding station). `_description` "Assign Responsible Officer" (from "Assign Disbursement Verification Officer"); help and menu wording drop "Verification".                                                                                                                                                                                                                                                                                                                                           |
| `views/*.xml`, `i18n/th.po`                                        | Assign to me / Assign… / Unassign invisible unless `state == 'in_progress'` and `work_center_can_move`. Rule views show `work_center_id`. th.po: field, help, summary, wizard and menu strings.                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `tests/test_assignment_rule.py`                                    | `setUpClass`: replace the seeded route's lines (in the test transaction) with `station_check` whose members are `officer_a` and `officer_b`; `_reflect_acts()`. `_make_dr` stops stubbing `_on_signed`, so signing enters the station and fires arrival (this covers "Saraban completion → auto-assign", since completion is `action_sign`). `test_validate_by_other_officer_closes_todo` → "forwarding out of the station closes the assignment Todo". The `apply_to_pending` tests use `in_progress`. `test_manual_assign…` sends back via `action_draft` from `in_progress` as a member. NEVER RUN.                      |

**Verify:** `grep -n "'signed'" disbursement_assignment_kmitl/models` returns nothing;
§6 step 1.

**Acceptance:** the assignment Todo opens on arrival (enter, forward, divert, resubmit)
and closes on any departure. Rules at ตรวจจ่าย can pick that station's members.

**Risks:** summary-based Todo matching still breaks across user languages (pre-existing,
out of scope).

---

### PR13: demo drives the stations (after the trial)

- **Branch:** `16.0-imp-finance_kmitl_demo-stations`. **Title:**
  `[16.0][IMP] finance_kmitl_demo: drive demo requests through the station route`
- **Modules:** `finance_kmitl_demo`, `kmitl_depends_dev`. Logical dependencies PR7-PR11.
- **Goal:** the demo seed configures the station acts and members, then moves demo DRs
  around the circuit (act, then ส่งต่อ).
- **Installable after it:** yes (demo DBs only).

| File                                | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `__manifest__.py`                   | depends gains `disbursement_wc`, `disbursement_validation`, `disbursement_approver_director`, `disbursement_approver_rector`.                                                                                                                                                                                                                                                                                                                            |
| `hooks.py`                          | After `_reflect_acts`, configure the seeded stations with the same table as the setup snippet; members = the demo users. `_approve_dr` under su: `action_submit`, `action_sign` (enters หมวดตรวจ), then per station its act(s) and `_work_center_forward` (computed from the open visit, not the cached field) until `station_bill`. `_bill_dr`: `action_create_bill`, post the bills (stage billed), forward. Rewrite the docstrings (L1-13, L502-539). |
| `kmitl_depends_dev/__manifest__.py` | Confirm all four new modules are listed.                                                                                                                                                                                                                                                                                                                                                                                                                 |

**Tests:** none. **Verify:** only if asked, install on a scratch DB; the warning log is
empty and demo DRs sit at สถานีตรวจจ่าย with stage `billed`.

**Acceptance:** no demo DR stops silently before billing.

**Risks:** the savepoint-plus-warning wrapper hides failures, so read the log.

---

## 4. Touch list of dependents outside the new modules

| Module                                 | Path                                                                                                | Reads the old state / field today                                                                  | Replacement                                                            | PR                      |
| -------------------------------------- | --------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- | ----------------------- |
| disbursement_budget                    | `models/disbursement_request.py:6-8,37,48`                                                          | `DisbursementRequestBase.READONLY_STATES`                                                          | `can_edit_budget` / `_can_edit_blocked`                                | PR2                     |
| disbursement_budget                    | `views/disbursement_request_views.xml:44-58`                                                        | `state != 'draft'` attrs                                                                           | `can_edit_dimensions` / `can_edit_budget`                              | PR2                     |
| disbursement_budget                    | `models/disbursement_request.py:306-308`                                                            | `_on_final_approval`                                                                               | `disbursement.consume_budget` act + `consumes_budget`                  | PR7                     |
| disbursement_budget                    | `views/disbursement_request_views.xml:24-26`                                                        | `//button[@name='action_approve']` confirm                                                         | Consume Budget button                                                  | PR7                     |
| disbursement_budget                    | `tests/test_final_approval_budget.py:6-21`                                                          | `_make_verified_dr`, `verified`                                                                    | `_make_signed_dr`, the consume act                                     | PR6, PR7                |
| procurement_plan_disbursement          | `views/disbursement_request_views.xml:20-24`                                                        | `state != 'draft'`                                                                                 | `can_edit_dimensions`                                                  | PR2                     |
| procurement_plan_disbursement          | `models/procurement_plan.py:3-6,47-90`                                                              | `DISBURSEMENT_*_STATES`                                                                            | budget_consumed / settlement domains (NULL-safe)                       | PR5                     |
| kmitl_project_disbursement             | `models/kmitl_project.py:3-130`                                                                     | `DISBURSEMENT_*_STATES`                                                                            | same                                                                   | PR5                     |
| agx_approval_disbursement              | `models/approval_request.py:10-18,117-130`                                                          | `_DISBURSEMENT_NOT_BILLED_STATES`                                                                  | `budget_consumed_amount > 0` or stage `!= none` (+ `init` recompute)   | PR5                     |
| purchase_request_approval_disbursement | `models/purchase_request_approval.py:143-183`                                                       | `_DR_STATE_TO_BILLING_STATUS`                                                                      | `_dr_billing_status(dr)` (+ `init` recompute)                          | PR5                     |
| advance_payment_disbursement           | `models/advance_payment_usage_line.py:25-28`                                                        | related `pipeline_status`                                                                          | related `settlement_stage`                                             | PR5                     |
| purchase_order_disbursement            | `views/disbursement_request_views.xml:48-54`                                                        | `display_status` badge                                                                             | `state` + `settlement_stage` badges                                    | PR5                     |
| disbursement_operating_unit            | `views/disbursement_request_views.xml:50-68`                                                        | inherits the approved search view                                                                  | inherit deleted                                                        | PR5                     |
| disbursement_accounting_kmitl          | `models/disbursement_request.py:12-42,124-143`                                                      | state/pipeline/display `selection_add` + computes                                                  | bill leg of `settlement_stage`                                         | PR2, PR6                |
| disbursement_accounting_kmitl          | `models/disbursement_request.py:148-153,264-283,342-355`                                            | `state != 'approved'` guards; `bills_posted` write; return-to-verification                         | guards deleted; cancel refusal; `disbursement.create_bill` act         | PR6                     |
| disbursement_accounting_kmitl          | `models/account_move.py:45-65`                                                                      | `approved` filter, `bills_posted` write                                                            | `_on_bills_posted` seam; walk-back check                               | PR4, PR6                |
| disbursement_accounting_kmitl          | `models/accounting_kmitl_dashboard.py:7-28` + `tests/test_dashboard_card.py:23`                     | card domain `state == 'approved'`                                                                  | fact-based card domain                                                 | PR6                     |
| disbursement_accounting_kmitl          | `views/disbursement_request_views.xml:4-18,36-56`                                                   | `search_default_approved`; `display_status` xpath; `action_approve` anchor; return-to-verification | `awaiting_bill` filter; re-anchor on `action_draft`; `can_create_bill` | PR6                     |
| disbursement_finance_kmitl             | `models/disbursement_request.py:46-94,187-234`                                                      | late states, pipeline/display, `write()` on `bills_posted`                                         | voucher legs; `_on_bills_posted`; TO_AUDIT dropped                     | PR2, PR4, PR6           |
| disbursement_finance_kmitl             | `models/disbursement_request.py:417-461,498-723,748-761`                                            | audit/authorize/confirm/submit/cancel/create-payment state guards                                  | act checks + integrity; stage-keyed submit/cancel                      | PR6                     |
| disbursement_finance_kmitl             | `models/disbursement_request.py:558-604`                                                            | `_hand_over` filter `payment_authorized`, `paid` write                                             | stage `settled` + no open TO_BOOK                                      | PR4, PR6                |
| disbursement_finance_kmitl             | `models/account_move.py:60-99`                                                                      | `state not in (paid, cleared)`; `cleared` write                                                    | stage guard; walk-back via `payment_disbursement_request_id`           | PR4, PR6                |
| disbursement_finance_kmitl             | `models/account_payment.py:45-86,111`                                                               | hand-over seams; stale comment                                                                     | + `_settlement_check`; comment reworded                                | PR4                     |
| disbursement_finance_kmitl             | `models/disbursement_payment_line.py:278-295`                                                       | `_banking_editable` on `bills_posted` / `payment_authorized`                                       | `not payment_id and state != 'cancel'`                                 | PR4                     |
| disbursement_finance_kmitl             | `views/disbursement_queue_views.xml:20-172`                                                         | queues on `state`, `display_status` badges                                                         | integrity-only domains, `can_*` buttons                                | PR6                     |
| disbursement_finance_kmitl             | `views/disbursement_request_views.xml:9-332`                                                        | finance action, history, xpaths, buttons, page on states                                           | stage / flags / stamps                                                 | PR6                     |
| disbursement_finance_kmitl             | `data/mail_activity_type.xml:7-23`                                                                  | to_audit / to_authorize types                                                                      | deleted; snippet removes rows                                          | PR6, PR11               |
| disbursement_finance_kmitl             | `tests/test_payment_workflow.py` (see PR6)                                                          | `request.state = approved/paid/cleared`, state asserts                                             | stage asserts; bounce inverted                                         | PR6                     |
| disbursement_assignment_kmitl          | `models/disbursement_request.py:37-41,153-195`                                                      | `state == 'signed'`; `action_validate` override                                                    | arrival / departure hooks                                              | PR2, PR6, PR12          |
| disbursement_assignment_kmitl          | `models/assignment_rule.py:9-13,66-77,113-123`; wizard; ACL                                         | `signed`; officer-only domain and ACL                                                              | station-scoped rules, widened ACL                                      | PR12                    |
| disbursement_assignment_kmitl          | `views/disbursement_request_views.xml:9-31`                                                         | `state != 'signed'` attrs                                                                          | `in_progress` + `work_center_can_move`                                 | PR6, PR12               |
| disbursement_assignment_kmitl          | `tests/test_assignment_rule.py:106-362`                                                             | `action_validate`, `verified`, `signed`                                                            | act-done seam, arrival, `in_progress`                                  | PR6, PR8, PR12          |
| disbursement_sarabun                   | `models/disbursement_request.py:21-52`, views `action_sign` anchor                                  | `submitted` / `signed` / `action_sign` / `action_draft` / `action_cancel`                          | unchanged; entry via `_on_signed`                                      | none                    |
| purchase_work_acceptance_disbursement  | `models/disbursement_request.py:61-75`                                                              | `action_sign` override                                                                             | `_on_signed` override                                                  | PR3                     |
| disbursement_cash_movement_kmitl       | `tests/test_cash_movement.py:94-120`                                                                | `request.state = 'approved'`                                                                       | line deleted                                                           | PR6                     |
| disbursement_cash_revenue_handover     | `tests/test_cash_revenue_handover.py:173,376-388`; `models/account_move.py:10-15`; `docs/adr/0001*` | `approved` fixture; `bills_posted` wording                                                         | stage asserts; reworded; ADR note                                      | PR2, PR6                |
| finance_kmitl                          | `docs/adr/0006*`, `0007*`                                                                           | request stays `paid` after a bounce                                                                | superseding note                                                       | PR4                     |
| finance_kmitl_demo                     | `hooks.py:1-13,502-581`                                                                             | validate/approve ×2/post_bills; `bills_posted` wording                                             | stations route                                                         | PR6, PR7, PR13          |
| accounting_kmitl_workflow              | `models/account_move.py:83`                                                                         | docstring cites `display_status`                                                                   | reworded                                                               | PR6                     |
| kmitl_depends_dev                      | `__manifest__.py:23-84`                                                                             | n/a                                                                                                | new modules added                                                      | PR8-PR11, PR13          |
| CONTEXT-MAP.md                         | L82-86, L103-107, L165-168                                                                          | `signed`, audit→…→clear, ศูนย์งาน                                                                  | station wording                                                        | PR1, PR5, PR6, PR8-PR11 |

---

## 5. i18n

### 5.1 Term table (use these msgstrs, matching the glossary)

| English source                                 | Thai msgstr                                                    | Notes                                                |
| ---------------------------------------------- | -------------------------------------------------------------- | ---------------------------------------------------- |
| Station / Stations                             | สถานี                                                          | `ศูนย์งาน` is retired.                               |
| Unassigned (card)                              | ยังไม่มีสถานี                                                  | "Unassigned Card" → การ์ดยังไม่มีสถานี               |
| Station Members / Members                      | สมาชิกสถานี                                                    |                                                      |
| Route                                          | เส้นทางมาตรฐาน                                                 | Route lines are not "steps".                         |
| Act / Acts                                     | การกระทำ                                                       |                                                      |
| Allowed Acts / Required Acts                   | การกระทำที่ทำได้ / การกระทำที่ต้องทำ                           |                                                      |
| Editable Parts                                 | ส่วนที่แก้ไขได้                                                | Not การกระทำ.                                        |
| Forward                                        | ส่งต่อ                                                         |                                                      |
| Divert                                         | เบี่ยงเส้นทาง                                                  | Never ตีกลับ.                                        |
| Send Back                                      | ส่งคืนผู้จัดทำ                                                 | Never ตีกลับ.                                        |
| Visit Log / Station Visits                     | สมุดเยี่ยม                                                     |                                                      |
| Circuit                                        | วงจร                                                           |                                                      |
| Settlement Stage                               | ขั้นการชำระ                                                    |                                                      |
| Not Billed / Billed / Settled / Booked         | ยังไม่ตั้งหนี้ / ตั้งหนี้แล้ว / จ่ายแล้ว / บันทึกบัญชีแล้ว     |                                                      |
| In Progress                                    | อยู่ระหว่างดำเนินการ                                           |                                                      |
| Done                                           | เสร็จสิ้น                                                      | Reuse the existing entry, retargeting its `#:` line. |
| My Stations / At My Stations                   | สถานีของฉัน / อยู่ที่สถานีของฉัน                               |                                                      |
| Station Administrator                          | ผู้ดูแลสถานี                                                   |                                                      |
| Responsible on Arrival                         | ผู้รับผิดชอบเมื่อมาถึง                                         | Frozen snapshot.                                     |
| Not Applicable Acts / Skipped Acts / Done Acts | การกระทำที่ไม่เกี่ยวข้อง / การกระทำที่ข้าม / การกระทำที่ทำแล้ว |                                                      |
| Arrived at your station                        | มีเอกสารมาถึงสถานีของคุณ                                       | Activity type.                                       |

**Rules:**

- Hand-edit only, with `#:` reference lines. An entry with no `#:` is skipped on import.
- For a shared msgid, delete only the dead `#:` line.
- Multi-line view help msgids must match the XML indentation exactly.
- Act names written from Python need `#. odoo-python` /
  `#: code:addons/<module>/<file>:0` / `#, python-format`.
- `msgfmt -c` on every touched file.

### 5.2 `work_center/i18n/th.po` (PR1): ศูนย์งาน → สถานี

- Bump POT-Creation-Date and PO-Revision-Date.
- **All 30 msgstrs containing ศูนย์งาน move to สถานี** (lines 34-39, 41-50, 52-64,
  104-108, 115-118, 162-172, 194-197, 212-219, 221-234, 236-243, 262-270, 272-298,
  305-308, 317-329, 346-353, 355-374, 381-396, 398-408).
- **Split the "Work Center" entry (L346-353):**
  - `msgid "Station"` → สถานี, with the `#:` lines for the model,
    `field_work_center_mixin__work_center_id` and
    `field_work_center_rule__work_center_id`;
  - the category and root-menu `#:` lines move under `msgid "Stations"` → สถานี, merged
    with the former "Work Centers" entry (L381-396), which also carries
    `work_center_action`.
  - Every source is relabelled in the same commit.
- **Rewritten msgids** (meaning changed):
  - member help;
  - rule action help (exact indentation);
  - `is_unassigned` help;
  - group comment;
  - `operating_unit_id` help (mentions divert);
  - "My Work Centers" → "My Stations";
  - "Work Center Routing Rule(s)" → "Station Routing Rule(s)";
  - "Work Center Counter(s)" → "Station Counter(s)";
  - "Work Center Administrator" → "Station Administrator";
  - "Work Center Mixin" → "Station Mixin";
  - the placeholder → "e.g. Verification Station" → "เช่น สถานีหมวดตรวจ".
- **Deleted:** the `work_center_manual` entries (L253-260, L376-379).
- **New entries:**
  - model descriptions: route, route line, visit, act, move wizard;
  - field labels and helps from §2.1;
  - both visit selections and `kind`;
  - Forward / Divert / Send Back / Confirm / Sync acts;
  - Routes / Acts / Visit Log menus and actions;
  - the activity type;
  - every UserError and ValidationError: not a member, no role, missing acts need a
    reason, different area, no route, already moved, immutable log, station has history,
    act not allowed here, route constraints, pointer written outside the engine, forward
    from the Unassigned card, station needs an act or a member, an edit permission
    cannot be required, act without a role.

### 5.3 `disbursement*` th.po (PR2-PR10)

**`disbursement` (PR2, PR3, PR6, PR8-PR10).**

- Add: ขั้นการชำระ and its four values; the stage filters and group-by; the five
  `can_edit_*` labels; `can_validate` / `can_approve_director` / `can_approve_rector`;
  In Progress; Open; the AccessError and "not in the circuit" messages; the rekeyed
  `action_draft`, send-back and return-source msgids; the three act names (python,
  moving out with their modules).
- Delete:
  - the `display_status` `#:` lines (L227, 397, 756, 840, 1137);
  - "Verified" and "Approved";
  - pipeline/display (L1193-1214);
  - bill/payment filters (reusing "Done" for `state__done` and the done filter);
  - `approval_state` (L1534-1558) and "Approval Reject Reason";
  - reject/queue/JS/batch/menu (L1601-1811);
  - return-to-verification (L1362-1391, 1444-1449, 1470-1473, 1505-1517);
  - the dead "Only verified requests can be approved.";
  - **"Only signed requests can be validated." (L629)**;
  - **"Request Approval Again" (L1599)**.
- Move with their modules: Validate / Approve (Finance Director) / Approve (Rector
  Delegate), the confirm texts, and the stamp labels (Verified By/On, Finance Director,
  Finance Approved On, Rector-delegated Approver, Rector Approved On). Group names and
  step labels stay.

**`disbursement_accounting_kmitl` (PR6).**

- Delete: Bill Draft, Bill Posted, Bills Posted, **"Only approved requests can be used
  to create bills." (L141)**, the **"Return to Verification" view entry (L170)**.
- Add: the cancel refusal for create-bill, the card label, the `awaiting_bill` filter,
  the act name, `can_create_bill`.

**`disbursement_finance_kmitl` (PR4, PR6).**

- Delete: Payment Audited, Authorized for Disbursement, Paid, Cleared, Payment Draft,
  Payment Posted, the pipeline "Done", **"Only bills-posted requests can be audited."
  (L319)**, **"Only audited requests can be authorized for payment." (L325)**, **"Only
  authorized requests can be confirmed as paid." (L331)**, **"Only a request the finance
  office has paid can be booked." (L337)**.
- Add: the stage-keyed submit, cancel and booking messages; "Post the bills first."; the
  banking-freeze message; the two act names; the three flags; the renamed queue actions;
  the settlement filters.

**Other modules.**

- `disbursement_budget` (PR7): Consume Budget, Consumes Budget, the confirm text, the
  act name, the reworded commitment error.
- `kmitl_project_disbursement`, `procurement_plan_disbursement`,
  `advance_payment_disbursement` (PR5): stat-button labels and the new field label.
- `disbursement_assignment_kmitl` (PR12): `work_center_id` label and help, the new
  summary, the wizard description and the menu wording.
- Act modules (PR8-PR10): the moved entries plus `field_disbursement_request__<stamp>`
  under their own module.

### 5.4 `disbursement_wc/i18n/th.po` (PR11)

- **Mixin fields on the DR, under this module's xmlid:**
  `#: model:ir.model.fields,field_description:disbursement_wc.field_disbursement_request__work_center_id`
  ("Station" → สถานี), and the same for `work_center_visit_ids` (สมุดเยี่ยม),
  `work_center_next_id` (สถานีถัดไป), `work_center_missing_act_ids`
  (การกระทำที่ยังไม่ได้ทำ), `work_center_open_visit_id`, `work_center_can_move`, plus
  their help texts. work_center's own th.po never translates these.
- **Seeded records:** area, six stations, route, six route lines
  (`model:work.center.route.line,name`) and two counters.
- **UI strings:** ส่งต่อ / เบี่ยงเส้นทาง buttons, the สมุดเยี่ยม page, filters, the
  Stations menu and action, the walk-back activity type.
- **Python strings:** the five edit-kind names (python-format entries).

### 5.5 Repo-wide check for the retired word

```bash
grep -rn 'ศูนย์งาน' --include='*.po' --include='*.xml' --include='*.py' --include='*.rst' --include='*.md' . \
  | grep -v '^./.git/' | grep -v 'work_center/docs/adr/0001' | grep -v 'work_center/docs/adr/0002'
```

- Expected residuals: `disbursement_wc/CONTEXT.md` (its _Avoid_ line and the closed flag
  history), `.context/plans/*` (local history).
- `.context/wc_bridge_seed.py` belongs to the closed bridge (#1576): delete it locally,
  or leave it marked obsolete.
- PR1 acceptance is that this grep shows nothing else.

---

## 6. Verification on the pilot DB, end to end

Run this only when the user asks. It uses the `odoo-real-db-test` recipe. Nothing
touches UAT.

**Preparation**

1. Confirm the PO has supplied the member list per station, and fill the dict in
   `.context/disbursement_wc_pilot_setup.py`.
2. Clone the DB: `createdb -T snapshot-2610220031 pilot_stations_<yyyymmdd>`.
3. **Section A, old code.** Check out the code the snapshot was built with:
   `select latest_version from ir_module_module where name='disbursement'` must read
   `16.0.12.0.0`. `origin/16.0` (`c82bb8fd` at time of writing) qualifies when versions
   match. Then run
   `odoo shell -d pilot_stations_<date> < .context/disbursement-station-pilot.py` with
   `SECTION='A'`.
4. Check out `16.0-pilot-stations` (= the PR12 head) and run **one** command:
   ```bash
   odoo -d pilot_stations_<date> --stop-after-init \
     -u disbursement,disbursement_budget,disbursement_accounting_kmitl,disbursement_finance_kmitl,disbursement_assignment_kmitl,disbursement_cash_movement_kmitl,disbursement_cash_revenue_handover,procurement_plan_disbursement,kmitl_project_disbursement,agx_approval_disbursement,purchase_request_approval_disbursement,advance_payment_disbursement,purchase_order_disbursement,purchase_work_acceptance_disbursement,disbursement_operating_unit,finance_kmitl \
     -i work_center,disbursement_validation,disbursement_approver_director,disbursement_approver_rector,disbursement_wc
   ```
   Only installed modules are upgraded. Check:
   - no view-validation errors;
   - `verifier_id`, `finance_approver_id` and `rector_approver_id` still exist and still
     hold their stamps;
   - the act sync appears once in the log.
5. Run `odoo shell … < .context/disbursement_wc_pilot_setup.py`, then section B of the
   pilot snippet. Check the printed counts: legacy `bills_posted` DRs sit at
   สถานีตรวจจ่าย, `payment_audited` DRs at สถานีอนุมัติจ่าย, both with a visit carrying
   the "pilot: legacy state" reason. Paid DRs read `done` / `settled`.
6. Start a throwaway HTTP server on the clone.

**Click-through, DR-A (consumes budget), as the users named in the member dict**

| #   | Who                                  | Action                                                                                                                       | Expected                                                                                                                                                                                                                                                    |
| --- | ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Maker                                | Create a DR with lines, dimensions and a commitment; Submit to Saraban. Head signs in Saraban.                               | Completion runs `action_sign` under sudo. The DR is `in_progress` at **สถานีหมวดตรวจ**. The สมุดเยี่ยม has one open row (arrival `enter`, mover = head, responsible = members). One arrival Todo per member. The assignment rule assigns an officer (PR12). |
| 2   | Member officer                       | ส่งต่อ without validating                                                                                                    | The wizard opens and lists "Validate" as missing; Confirm with an empty or whitespace reason is refused. Cancel the wizard.                                                                                                                                 |
| 3   | Same officer                         | Return (send-back) with the reason "wrong payee"                                                                             | `draft`, `returned_for_edit`. The visit closes with `send_back` and the reason. All arrival Todos and the assignment Todo are closed. Pointer empty.                                                                                                        |
| 4   | Maker                                | Fix the payee; Resubmit to Verification                                                                                      | `in_progress` at สถานีหมวดตรวจ, arrival `resubmit`, no Saraban circulation, no new head signature.                                                                                                                                                          |
| 5   | Officer                              | Validate, then ส่งต่อ                                                                                                        | One active `verify` signature row. The visit closes as `forward`. Arrives at **สถานี ผอ.กองคลัง**; Todos go to its members.                                                                                                                                 |
| 6   | Director (member)                    | Divert to สถานีหมวดตรวจ, reason "attachment missing"                                                                         | Visit `divert` with the reason. The DR is at หมวดตรวจ; "Next" shows สถานี ผอ.กองคลัง (the last on-route visit is now หมวดตรวจ).                                                                                                                             |
| 7   | Officer                              | Add the attachment (edit allowed here); ส่งต่อ **without** re-validating, reason "checked in visit 2; only attachment added" | Forward succeeds. The visit's `skipped_act_ids` = Validate, with the reason. Arrives at ผอ.กองคลัง.                                                                                                                                                         |
| 8   | Non-member holding the director role | Open the DR                                                                                                                  | Approve, ส่งต่อ and Divert are hidden. The same call over RPC (shell `with_user`) raises AccessError.                                                                                                                                                       |
| 9   | Director                             | Approve, ส่งต่อ                                                                                                              | `finance_approve` row. Arrives at the rector station.                                                                                                                                                                                                       |
| 10  | Rector delegate                      | Approve, Consume Budget, ส่งต่อ                                                                                              | `rector_approve` row; budget consumed once. Arrives at **สถานีตั้งหนี้**. Line fields are read-only (station does not allow edits).                                                                                                                         |
| 11  | Accounting maker                     | Create Bill, post it, ส่งต่อ                                                                                                 | Stage `billed`; payment lines exist. Arrives at **สถานีตรวจจ่าย**.                                                                                                                                                                                          |
| 12  | Auditor                              | Audit, ส่งต่อ                                                                                                                | `payment_audit` row. Arrives at **สถานีอนุมัติจ่าย**.                                                                                                                                                                                                       |
| 13  | Authorizer                           | Authorize, ส่งต่อ                                                                                                            | Vouchers raised. Visit closes with **`exit`**. State **เสร็จสิ้น (`done`)**, stage `billed`. No open arrival Todo.                                                                                                                                          |
| 14  | Finance office / accounting          | Confirm paid; post the vouchers                                                                                              | Stage `settled`, then `booked`. State stays `done`.                                                                                                                                                                                                         |
| 15  | Accounting                           | Reset one voucher's posted entry to draft (or bounce its cheque)                                                             | Stage walks back (`settled` or `billed`) with no hand write. State stays `done`. A walk-back Todo goes to the **members of สถานีอนุมัติจ่าย**.                                                                                                              |
| 16  | Auditor persona (non-developer)      | Open the สมุดเยี่ยม tab                                                                                                      | Every arrival, departure, mover, act, the divert reason, the send-back reason and the skipped Validate are readable without developer mode.                                                                                                                 |

**DR-B (deposit or guarantee money).** Set `consumes_budget` False in draft and walk it
through. At the rector station, ส่งต่อ succeeds without a reason, and the visit lists
Consume Budget under not-applicable acts. `budget_consumed_amount` stays empty.

**Negative checks in odoo shell** (each preceded by `env.invalidate_all()`):

- each act on a `draft` DR raises UserError;
- a station member without the act's role is refused;
- `action_draft` / `action_cancel` by a non-member on an `in_progress` DR raises.

**Overview.** The Disbursement > Stations kanban shows six cards whose counters match
the DRs at each station. The Unassigned card counts 0. The project and procurement-plan
stat buttons and the accounting "awaiting bill" card show sensible numbers.

**Behaviours this click-through covers that no test guards:**

- act-sync idempotence (start Odoo twice; the log shows one sync);
- unarchiving on re-declaration;
- Thai act names;
- a live route edit (move a line and check "Next" on an in-flight DR);
- a stale `expected_station` (two browser tabs pressing ส่งต่อ: the second gets "already
  moved");
- the finance queues;
- the readers' stat buttons.

---

## 7. Accepted risks, and what to tell auditors

| Risk                                                                                                               | Source                       | Mitigation / what remains                                                                                                                                                                                                                                                                                                                                                |
| ------------------------------------------------------------------------------------------------------------------ | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **No hard ordering.** Nothing prevents approving a DR หมวดตรวจ never checked, or billing before approval.          | D7, disbursement_wc ADR-0001 | The route says what normally happens; required acts can be skipped only with a logged reason; the สมุดเยี่ยม records what happened. Integrity checks remain: no second bill, no partial-bill payment, payee classification, no cancel once money moved, a voucher paid before posting, audit only after bills are posted, every act only while the DR is in the circuit. |
| **No new head signature on edited content.** A DR sent back, edited and resubmitted is not re-signed in e-Saraban. | D9                           | The resubmit visit (`arrival_act='resubmit'`) and chatter show it was corrected. It re-enters at หมวดตรวจ and is checked again from the start.                                                                                                                                                                                                                           |
| **Audit evidence lives only in the visit log.** If the log is incomplete, nothing can reconstruct custody.         | D4, ADR-0001                 | Single writer; pointer writes outside the engine raise; rows are append-only (no write or unlink for users); deletion only with the document; ordered by id. The remaining gap is direct SQL.                                                                                                                                                                            |
| Visits are readable by every internal user, with no record rule (a polymorphic `res_id`).                          | §2.5                         | Reasons and responsible names of DRs in other OUs are readable over RPC. The menu is manager-only; `document_display` reads under sudo. Revisit if OU segregation of DRs is turned on (`disbursement_operating_unit`).                                                                                                                                                   |
| `can_edit_*` is UI-only.                                                                                           | D13                          | Fields are writable over RPC. `_banking_editable` is the one enforced lock.                                                                                                                                                                                                                                                                                              |
| Approval history in `approval_state` tracking is cascade-deleted on `-u`.                                          | PR6                          | Section A converts it to plain chatter notes first.                                                                                                                                                                                                                                                                                                                      |
| Memberless stations notify every implied role holder, admin and root included.                                     | D14 / D15                    | Pilot stations get explicit members.                                                                                                                                                                                                                                                                                                                                     |
| Act modules must be installed in the same command as `-u disbursement`.                                            | §3.0                         | Deploy note in each act module's README and in the checklist.                                                                                                                                                                                                                                                                                                            |
| A memberless, act-less station or the Unassigned card falls back to Station Administrators.                        | §2.4                         | Only where nobody else is responsible. Pending PO sign-off (§8 item 2).                                                                                                                                                                                                                                                                                                  |

**What to tell auditors.** "Control over the order of work on a ใบขอเบิก is now
evidential, not preventive. Each desk (สถานี) is configured with the acts it must
perform. Skipping one requires the mover to type a reason, which is stored permanently.
Every hand-over records when the DR arrived and left, who moved it, by which act, and
who was responsible on arrival. To review a DR, open its สมุดเยี่ยม tab. To review all
out-of-order handling, filter the Visit Log (Settings > Stations > Visit Log) on
'Skipped Acts is set' or 'Departure = Divert'. Signatures remain on the printed DR, one
row per act. Money progress (ขั้นการชำระ) is computed from the actual bills and vouchers
and cannot be edited."

---

## 8. Open items NOT decided

Each row says what the plan builds if nobody answers, which PR it blocks, and how to
reverse the default.

| #   | Question                                                                                                                                                                                                                                                                 | Blocks                           | Default the plan builds                                                                         | How to reverse                                                                                                                                                    |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------- | ----------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **Amendment to D16:** `in_progress`/`done`, `settlement_stage` and `can_edit_*` are declared in core, not in `disbursement_wc` (readers that depend only on core or budget must not crash without the engine).                                                           | PR2                              | Core placement, recorded in `disbursement/docs/adr/0005`.                                       | Move the `selection_add`, the stage and the flags into `disbursement_wc` and make the five readers depend on it (pulls `work_center` into every budget consumer). |
| 2   | **Escape hatch (D14/D15 extension):** a `fallback` responsible source plus manager move authority, **only** where nobody else is responsible (the Unassigned card, or a station whose roles have no active holders). Real stations must have at least one act or member. | PR1 (ADR-0003 status "proposed") | Built as described.                                                                             | Drop `fallback`; a DR on the Unassigned card is then freed only by a shell snippet.                                                                               |
| 3   | Required acts count only when done **in the current visit**.                                                                                                                                                                                                             | PR1                              | Current visit. After a divert back, re-act or skip with a reason.                               | Compute "done" over all visits of the document.                                                                                                                   |
| 4   | **Not-applicable acts (D6 extension):** a required act the document declares not applicable (consume_budget with `consumes_budget` False) is not missing, and is logged in `not_applicable_act_ids`.                                                                     | PR1, PR7                         | Logged exception (ADR-0003).                                                                    | Remove `_work_center_act_applies`; users then skip with a typed reason.                                                                                           |
| 5   | Which role holds `consume_budget`, and at which station it is required. (Consumption is its own act per D16; only the role and the station are open.)                                                                                                                    | PR7, PR11 setup                  | Rector-delegate role, required at the rector station.                                           | Change the declaration's group and the setup table.                                                                                                               |
| 6   | Who turns `consumes_budget` off for เงินรับฝากบุคคลที่สาม / เงินประกัน.                                                                                                                                                                                                  | PR7                              | Default True; the maker in draft (or wherever `edit_budget` is allowed).                        | A rule on the source dimension (out of scope now).                                                                                                                |
| 7   | Edit permissions: their role, and which stations enable them in the pilot.                                                                                                                                                                                               | PR11 setup                       | Officer role; enabled at สถานีหมวดตรวจ only (today's "draft-only" lock is otherwise preserved). | Edit the setup table or the declaration's group.                                                                                                                  |
| 8   | **Narrowings of D13:** besides station + `settlement_stage == 'none'`, a draft bill locks lines, dimensions and budget, and a budget commitment locks dimensions and budget.                                                                                             | PR2                              | Built; documented in the `disbursement_wc` README.                                              | Drop `_can_edit_blocked` in the accounting and budget bridges.                                                                                                    |
| 9   | Booking after a bounced cheque: the request-level guard (`settled`/`booked`) blocks booking the other paid payees until the replacement is paid.                                                                                                                         | PR4                              | Guard kept.                                                                                     | Drop it and rely on finance_kmitl's per-voucher paid check.                                                                                                       |
| 10  | `disbursement_finance_kmitl` is the act family for ตรวจจ่าย / อนุมัติจ่าย (D16 does not name it).                                                                                                                                                                        | PR6                              | Yes.                                                                                            | Split into a new module (no data impact; act codes stay).                                                                                                         |
| 11  | Approver groups stay as `disbursement.group_disbursement_finance_director` / `_rector_delegate` in core, so membership survives `-u`.                                                                                                                                    | PR9, PR10                        | Stay in core.                                                                                   | Move them with a member re-seat snippet.                                                                                                                          |
| 12  | Readers' "approved" bucket keys on `budget_consumed_amount > 0`, so DRs with `consumes_budget` False never land there.                                                                                                                                                   | PR5                              | As built.                                                                                       | Add `or state == 'done'` for non-consuming DRs.                                                                                                                   |
| 13  | Pilot mapping: `paid`/`cleared`/**`payment_authorized`** → `done` (the อนุมัติจ่าย act was already performed); `bills_posted` → at สถานีตรวจจ่าย; `payment_audited` → at สถานีอนุมัติจ่าย.                                                                               | PR11 snippet                     | As described.                                                                                   | Move `payment_authorized` to section B step 2 with `station_authorize`.                                                                                           |
| 14  | Who may pull an `in_progress` DR out (reset or cancel): station members only, with no manager override; a `done` DR cannot be reset.                                                                                                                                     | PR6, PR11                        | Members only; `done` excluded.                                                                  | Add a manager branch to `action_draft` / `action_cancel` and show the reset button for `in_progress` / `done`.                                                    |
| 15  | Accounting "awaiting bill" card is fact-based, so it also counts DRs still at หมวดตรวจ.                                                                                                                                                                                  | PR6                              | Fact-based card.                                                                                | Replace it with the `station_bill` "Waiting here" counter.                                                                                                        |
| 16  | `create_bill` is allowed on a `done` DR, so a bill can be re-raised after money walks back.                                                                                                                                                                              | PR6                              | Allowed.                                                                                        | Remove `done` from the act's states.                                                                                                                              |
| 17  | Repurposing the eight deleted owning-unit test methods as engine tests (same count) under the "no new tests" preference.                                                                                                                                                 | PR1                              | Repurposed.                                                                                     | Delete them instead; the engine is then guarded only by the `disbursement_wc` suite and §6.                                                                       |
| 18  | Finance audit and authorize menus stay as fact lists next to the station kanban.                                                                                                                                                                                         | PR6, PR11                        | Kept and renamed; the station card is the desk's worklist.                                      | Hide the two menus when `disbursement_wc` is installed.                                                                                                           |

---

## 9. Hand-off checklist

- [ ] Read the authoritative sources, §0.4 and §1-§2.
- [ ] Get PO sign-off on §8 items 1 and 2 (they shape PR1 and PR2), and ask the PO for
      the pilot member list per station.
- [ ] Comment on PR #1510 to @n3n: ADR-0001 is superseded by ADR-0002, and the branch
      will be force-pushed. Wait for the acknowledgement.
- [ ] Move ADR-0002 onto `16.0-add-work_center` (§3.0 step 1); skip `bcc56539`.
- [ ] Build PR1 and push; retitle #1510. Commits carry no `Co-Authored-By`.
- [ ] Build PR2-PR10 as a linear stack (§3.0), opening each PR against the previous
      branch. Mark every PR "do not merge before pilot acceptance"; mark PR6 "never
      merge without PR11".
- [ ] Rebase `16.0-add-disbursement_wc` onto PR10 and build PR11; build PR12.
- [ ] For each PR: pyflakes, xmllint, `msgfmt -c` and the PR's greps. Do **not** run
      tests or pre-commit unless the user asks. State "tests written, never run" in each
      PR description.
- [ ] Attach the local `.context/` snippets (`disbursement-station-pilot.py`,
      `disbursement_wc_pilot_setup.py`, `work_center_refresh_unassigned_name.py`) to the
      PR6 / PR11 descriptions.
- [ ] Run the repo-wide ศูนย์งาน grep (§5.5); delete `.context/wc_bridge_seed.py`
      locally.
- [ ] Create `16.0-pilot-stations` at the PR12 head and tag it `pilot-stations-<date>`.
- [ ] Run the pilot (§6) on a copy of `snapshot-2610220031`: section A with the old code
      → the single install command → the setup snippet → section B → the click-through.
      Do not touch UAT.
- [ ] Record the pilot result and the PO's answers to §8. Fold any changes into the
      stack and re-run §6 if code changed.
- [ ] After PO acceptance only: merge PR1-PR12 into `16.0` in stack order in one window.
      On UAT, run section A (old image), then the deploy with `-u disbursement` plus
      `-i` of all five new modules **in one command**, then the setup snippet with UAT
      members, then section B.
- [ ] Build and merge PR13 (demo) afterwards.
- [ ] Update the `CONTEXT-MAP.md` entries and close the Member flag in
      `disbursement_wc/CONTEXT.md` if anything changed during the pilot.
