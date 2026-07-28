# -*- coding: utf-8 -*-
from odoo import fields, models


class PurchaseRequestApprovalLine(models.Model):
    _inherit = "purchase.request.approval.line"

    # tracking metadata for the sarabun-sync branch's write() override.
    product_qty = fields.Float(string="Quantity", tracking=True)
    price_unit = fields.Float(string="Unit Price", tracking=True)

    # Related helpers so the editable-tree `attrs` can reference parent state
    # and the current user's God Mode flag without a `parent.` prefix.
    approval_state = fields.Selection(related="approval_id.state")
    approval_user_has_godmode = fields.Boolean(
        related="approval_id.user_has_godmode",
    )
