from odoo import models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    def _prepare_approval_vals(self):
        # The base resets ``assigned_to`` to False; an explicit value in the
        # create vals would stop the พจ.1's compute from defaulting the
        # Assigned Officer from the Buddy settings. On a ตีกลับ/แก้ไข resync it
        # also keeps the officer already on the พจ.1.
        vals = super()._prepare_approval_vals()
        vals.pop("assigned_to", None)
        return vals
