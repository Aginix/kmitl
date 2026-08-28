# -*- coding: utf-8 -*-
from odoo import _, api, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    @api.model
    def _get_default_name(self):
        # Bypass the base's next_by_code("purchase.request") so records keep the
        # _("New") placeholder until the workflow draws our KMITL-format number
        # (see purchase_request_approval_kmitl.button_to_verify).
        return _("New")
