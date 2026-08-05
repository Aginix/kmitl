# Integration adapter: hardened callback-push, atomic, 1:N

Five in-repo modules (`purchase_request_sarabun`, `purchase_request_approval`, `disbursement_sarabun`, `agx_approval_sarabun`, and `agx_construction` transitively) integrate through `sarabun.document.mixin` — overriding `_on_sarabun_*` callbacks, calling `action_create_sarabun_document()`, and each re-declaring a `main_sarabun_document_id`. We keep the **callback-push** pattern (Odoo-idiomatic, right-sized for in-repo consumers — not an event bus) but harden it: the mixin **owns** the origin↔document relation, callbacks map to the new lifecycle (`_on_sarabun_completed` / `_rejected` / `_returned` / `_cancelled` plus a generic `_on_sarabun_step(step, disposition)`) and pass a **`sarabun.routing.step`** rather than the old recipient, and semantic helpers replace hardcoded `state == "sent"` checks. Callbacks run **in the same transaction as the actor's action and a failure rolls the action back** (no silent swallow) — correctness over availability, because the integrations are financial (PR→budget, disbursement) where "approved in saraban but not in the origin" is a data-integrity disaster.

The origin↔document relation is **1:N**: the linkage lives on the document (`origin_model` + `origin_res_id`) so many documents per origin is free, and ADR-0002's reject→duplicate produces it immediately. The mixin exposes `sarabun_document_ids` (all) and `active_sarabun_document_id` (current live one), replacing the per-consumer `main_sarabun_document_id`.

## Consequences

- All five consumers must be updated to the new contract (no backward-compat — the module is not yet in production).
- A failing origin callback surfaces as an error to the approver; origins that should "proceed even if the callback fails" must opt in explicitly (deferred).
