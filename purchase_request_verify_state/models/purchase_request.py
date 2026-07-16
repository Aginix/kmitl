# -*- coding: utf-8 -*-
# Deprecated: to_examine/to_verify states removed in new 11-state machine.
# This module is kept as a stub to avoid breaking installed dependencies.
# The verification logic has been absorbed into purchase_request_kmitl.button_confirm_data.

from odoo import models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"
