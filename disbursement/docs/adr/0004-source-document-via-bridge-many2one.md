# The source document is a bridge-owned Many2one, not a generic `fields.Reference`

A request used to carry `reference` (a `fields.Reference` whose selection each
source bridge extended), its derived `reference_model` / `reference_model_name`,
a free-text `ref`, and a header `partner_id` computed from `reference`. The PO and
PA bridges in turn computed their own stored `purchase_id` /
`purchase_request_approval_id` from `reference`, and the PO bridge hung its
analytic prefill on the same compute.

## Decision

The request has **no generic source field**. Each source bridge owns a plain,
stored, readonly Many2one set when it creates the request (`purchase_id`,
`purchase_request_approval_id`, `approval_request_id`) and overrides one core
hook, `_get_source_document()`, which returns that record (or nothing for a
stand-alone request). The hook feeds the printed อ้างอิง line, the bill's `ref`
and nothing else; search goes through each bridge's own field. The bridges write
their dimensions into the create values instead of piggy-backing on a compute.

`reference`, `reference_model`, `reference_model_name`, `ref` and the header
`partner_id` / `partner_bank_id` / `partner_type` are dropped. Old `ref` text is
not migrated.

## Considered options

- **Keep `fields.Reference` (rejected)** — every reader had to test
  `reference._name`, the stored per-bridge fields were computed off it anyway,
  and the "pick any document" widget invited users to link documents by hand.
- **Keep `ref` as free text for stand-alone requests (rejected)** — users asked
  for it to go; a stand-alone request's context belongs in its note.

## Consequences

- The bridges' Many2one columns already existed as stored computes, so no data
  moves; they simply stop being computed.
- A bridge raising a request from a single-vendor document stamps the vendor's
  payee type (`_get_payee_type`), and a multi-recipient source (approval
  request) raises one request per payee type.
- The 16.0.12.0.0 pre-migration fills the new required `partner_type_id` from the
  most common line-payee type (else the old header partner's, else อื่น ๆ) before
  the header partner columns are dropped.
