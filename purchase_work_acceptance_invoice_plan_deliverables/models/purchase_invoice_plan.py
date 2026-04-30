# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseInvoicePlan(models.Model):
    _inherit = 'purchase.invoice.plan'

    deliverables=fields.Text(
        string='Deliverables'
    )

    deliverables_short = fields.Char(
        string='Description',
        compute='_compute_deliverables_short',
        store=False,
    )

    @api.depends('deliverables')
    def _compute_deliverables_short(self):
        for rec in self:
            if rec.deliverables:
                text = rec.deliverables.replace('\n', ' ')
                rec.deliverables_short = (
                    text[:50] + '...' if len(text) > 50 else text
                )
            else:
                rec.deliverables_short = False

    def action_open_deliverables_dialog(self):
        self.ensure_one()
        return {
            'name': _('รายละเอียดการส่งมอบงาน - งวดที่ %s') % self.installment,
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.invoice.plan',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('purchase_work_acceptance_invoice_plan_deliverables.view_purchase_invoice_plan_deliverables_form').id,
            'target': 'new',
        }
