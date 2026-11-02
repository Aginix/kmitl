# The printed request moves to `disbursement_pdf`; the portal is deleted

The core shipped the standalone ใบขอเบิก PDF (paperformat, report action, the
QWeb template and its signature-block sub-template) and a portal
(`/my/disbursement…`) whose only job was to frame that report, reached from a
"Preview" smart button. Once `disbursement_sarabun` is installed the report is
unbound from the Print menu: the หนังสือ is the official document, so the core
carried a print and a portal most deployments hide.

## Decision

- The print moves to a new module, **`disbursement_pdf`**, with
  `_get_report_base_filename` and the `l10n_th_fonts` / `l10n_th_amount_to_text`
  dependencies. It is not auto-installed: `disbursement_budget`,
  `kmitl_project_disbursement` (which add rows to the template) and
  `disbursement_sarabun` (which unbinds it) depend on it and pull it in.
- The **portal is deleted**: controller, templates, frontend JS, the Preview
  smart button, `open_preview`, `_compute_access_url` and `portal.mixin`.
- The signature model and its snapshots (ADR 0002), `thai.date.mixin` and
  `_get_masked_acc_number` stay in the core: they are request data, not layout.
- The 16.0.14.0.0 pre-migration re-points the four xmlids
  (`paperformat_disbursement_request_report`, `action_report_disbursement_request`,
  `report_disbursement_request`, `report_disbursement_request_signature`) to
  `disbursement_pdf`, so the update does not delete them and the record ids — and
  the inheriting views — are kept.

## Considered options

- **Keep the portal (rejected)** — no external user reaches it; it was a frame
  around the backend report, and its access token on every request was unused.
- **Glue modules for the budget and project rows (rejected)** — both already
  inherit the template, so a direct dependency on `disbursement_pdf` is enough.

## Consequences

- Deploy with `-u disbursement,disbursement_budget,kmitl_project_disbursement,disbursement_sarabun -i disbursement_pdf`.
- `disbursement_budget` and `kmitl_project_disbursement` list their
  `auto_install` triggers explicitly, so the new dependency is pulled in rather
  than blocking the auto-install.
- The Thai translations of the report move to `disbursement_pdf/i18n`.
