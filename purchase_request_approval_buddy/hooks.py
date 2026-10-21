from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    """Relabel ``assigned_to`` in every language: install loads translations
    without overwrite, so the base module's th_TH "ผู้อนุมัติ" (Approver)
    would otherwise win over this module's "เจ้าหน้าที่ผู้รับผิดชอบ"."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["ir.module.module"].search(
        [("name", "=", "purchase_request_approval_buddy")]
    )._update_translations(overwrite=True)
