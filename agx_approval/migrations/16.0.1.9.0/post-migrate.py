from odoo.addons.agx_approval.hooks import set_approval_ok_on_non_purchase_codes


def migrate(cr, version):
    """Backfill the new approval_ok flag so every code selectable today (the
    non-procurement baseline) stays selectable once the flag becomes the gate
    (ADR-0004, amended)."""
    if not version:
        return
    set_approval_ok_on_non_purchase_codes(cr)
