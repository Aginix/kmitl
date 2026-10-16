# ADR-0018 — Admin route edit while circulating

**Status:** Accepted **Date:** 2026-10-16 **Module:** `agx_sarabun_route_edit` (optional
extension of `agx_sarabun`)

---

## Context

Once a หนังสือ is `circulating` its Route is read-only for everyone, managers included.
Two common situations need an admin to change it:

- **The Route was built wrong** — a wrong person / Position / verb on a later step, a
  missing step.
- **An executive changed** (new คณบดี / ผอ.กอง). A _waiting_ Position step already
  follows the Position's current holders, because holders resolve at activation
  (ADR-0003). But an **active** step has its actors snapshotted, and a บุคลากร (Person)
  step is pinned to one employee.

None of the existing moves fits:

- **ดึงกลับ** is sender-only and closed once anyone has signed (ADR-0006).
- **Reset** throws the signatures away and restarts the whole route (ADR-0011).
- **มอบหมาย** can only be done by the step's own actor, who may be the person who has
  left.

## Decision

A **separate, optional module** `agx_sarabun_route_edit` lets a **Sarabun Route Editor**
(`group_sarabun_route_edit`) edit the live Route of a circulating หนังสือ directly in
the Route list.

- **Access.** The group is category-less, so it shows as an independent checkbox like
  Reset (ADR-0011), and it implies Manager.
- **Waiting step.** Verb, ลำดับ, CC and target may change, or the step may be deleted.
- **Active step.** Only the **target** may change. Its to-dos are cleared and the new
  holders are snapshotted and get fresh to-dos. This is the engine half of มอบหมาย, with
  no disposition stamped.
  - An active step may also be deleted. Its to-dos are cleared first.
- **People taken off the Route lose access.** This covers re-targeting an active step,
  deleting it, and the holder refresh below. For each person removed:
  - Their recipient row on that step is deleted. That row is the reach ledger that
    keys read (ADR-0013), so they can no longer open the หนังสือ and it leaves their
    Incoming box.
  - They are unfollowed, since their to-do had subscribed them, so chatter stops
    notifying them.
  - They keep access only if the หนังสือ still reaches them some other way: another
    step, a prior attempt, or being its sender. Managers still see everything.
- **Done / skipped / originator step.** Locked. Signatures are never rewritten.
- **Added step.** Created `waiting` with `created_by_disposition='direct'`, so a later
  Reset drops it like any runtime insertion (ADR-0011).
- **Frontier.** Steps may only be added or moved at or after the first Stage not yet
  passed.
- **After each save** the Route is validated the way ส่ง validates it:
  - at least one gating step remains;
  - while unnumbered, a step that issues the number remains (ADR-0017).
  - Then the engine advances: a step added to the current Stage activates at once, and
    removing the Stage's last pending gating step moves the หนังสือ on, completing it if
    nothing is left.
- **Holder change.** This is a **manual per-document button**,
  ดึงผู้ดำรงตำแหน่งปัจจุบัน. It re-resolves the active Position / unit-clerk steps to
  their current holders. Editing a Position never silently moves in-flight documents.
- **Audit.** Every edit is logged to the document chatter (who, step, field old → new).
  There is no mandatory reason.

The guards apply only to **user** edits. Engine writes are untouched: they run `sudo`
(act_on_step, ตีกลับ, Reset) or, for the sender's ดึงกลับ, carry the
`sarabun_route_engine` context.

## Considered alternatives

- **An edit wizard holding a copy of the Route.** Rejected. The copy would miss
  extension fields on the step (e.g. `agx_sarabun_person_capacity`'s capacity), and it
  would need a diff/apply layer. Editing the real rows keeps every extension working.
- **Auto re-resolve active steps when a Position's holders change.** Rejected for v1.
  One holder edit would silently move every in-flight หนังสือ.
- **Keep a removed active step as `skipped`**, so the people it reached keep their
  read. Rejected: when a route is wrong or an executive changes, the person taken off
  must not keep seeing the หนังสือ.

## Consequences

- A circulating Route is no longer frozen for a route editor. It is still frozen for
  everyone else, and the original actors' signed steps are never changed.
- **Refines ADR-0013's "the reach ledger only grows".** An admin route edit is the
  one place a recipient row is removed. Every other move (ตีกลับ / ดึงกลับ / Reset /
  มอบหมาย) still keeps it.
- A removed person's read status on that step (วันที่เปิดอ่าน) is gone with the row.
  The chatter log of the edit is the remaining audit.
- **position_id in the step dialog** keeps its own attrs (owned by
  `agx_sarabun_person_capacity` when installed). Changing it on a done step is refused
  by the server guard, not by the form.
