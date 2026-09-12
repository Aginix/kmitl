# -*- coding: utf-8 -*-
from odoo import api, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.ondelete(at_uninstall=False)
    def _unlink_except_purchase_or_done(self):
        """Allow unlinking a confirmed PO line when called from an applied
        contract revision.

        The base guard blocks any deletion once the PO is in ``purchase`` or
        ``done``. Contract revisions legitimately drop line items when the
        agreed scope shrinks, so we bypass the guard when the caller sets the
        ``from_contract_revision_apply`` context flag."""
        if self.env.context.get("from_contract_revision_apply"):
            return
        return super()._unlink_except_purchase_or_done()
