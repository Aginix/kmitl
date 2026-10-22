import json

from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    """Relabel ``assigned_to`` in every language (ADR-0011).

    Odoo merges a changed field string into the existing label jsonb as
    ``en_US`` only, so the old Thai label ("ผู้แทนฝ่ายจัดซื้อ" /
    "เจ้าหน้าที่ผู้รับผิดชอบ") would keep showing. Existing translations win
    on later non-overwrite loads, so setting them once here sticks."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    label = env["purchase.request"]._fields["assigned_to"].string
    field = env["ir.model.fields"]._get("purchase.request", "assigned_to")
    cr.execute(
        "SELECT field_description FROM ir_model_fields WHERE id = %s", [field.id]
    )
    labels = {lang: label for lang in cr.fetchone()[0] or {}}
    labels["en_US"] = label
    cr.execute(
        "UPDATE ir_model_fields SET field_description = %s::jsonb WHERE id = %s",
        [json.dumps(labels), field.id],
    )
