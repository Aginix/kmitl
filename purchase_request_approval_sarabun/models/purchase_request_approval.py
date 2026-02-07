# -*- coding: utf-8 -*-
import logging
from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class PurchaseRequestApproval(models.Model):
    _inherit = 'purchase.request.approval'

    def _prepare_sarabun_document_vals(self):
        """Override to add Thai subject formatting."""
        vals = super()._prepare_sarabun_document_vals()
        vals.update({
            "subject": f"ขออนุมัติจัดซื้อจัดจ้าง: {self.name}",
        })
        return vals
