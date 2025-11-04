# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseInvoicePlan(models.Model):
    _inherit = 'purchase.invoice.plan'

    def action_view_linked_invoices(self):
        print("Custom action_view_linked_invoices called")
