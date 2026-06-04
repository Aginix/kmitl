# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    READONLY_STATES = {
        'purchase': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    invoice_plan_ids = fields.One2many(
        comodel_name="purchase.invoice.plan",
        inverse_name="purchase_id",
        states=READONLY_STATES,
    )

    use_invoice_plan = fields.Boolean(
        states=READONLY_STATES,
    )
    
    attachment_ids = fields.One2many(
        'ir.attachment',
        'res_id',
        string='Document Attachments',
        tracking=True,
    )

    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal year",
        tracking=True,
        states=READONLY_STATES,
    )

    date_planned = fields.Datetime(
        string="Date End"
    )

    department_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Department",
        domain=[("root_plan_id.code", "=", "departments")],
        states=READONLY_STATES,
        tracking=True,
    )

    payment_type = fields.Selection(
        [
            ("direct", "Direct paid"),
            ("advance", "Advance"),
            ("prepaid", "Prepaid"),
        ],
        tracking=True,
        string="Payment Type",
        states=READONLY_STATES,
    )

    state = fields.Selection(selection_add=[
        ("purchase", "Open"),
        ("done", "Done")
    ])

    def action_view_purchase_request(self):
        self.ensure_one()
        if not self.request_id:
            return

        return {
            'name': _('Purchase Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.request',
            'res_id': self.request_id.id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
        }
