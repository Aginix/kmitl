# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class WorkAcceptance(models.Model):
    _name = 'work.acceptance'
    _inherit = ['work.acceptance', 'thai.date.mixin']

    evaluation_result_ids = fields.One2many(
        groups="purchase_work_acceptance_evaluation.group_enable_eval_on_wa"
    )

    requested_delivery_date = fields.Date(
        string="Requested Delivery Date",
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    price_subtotal = fields.Monetary(
        compute="_compute_price_subtotal",
        string="Project value",
        store=True,
    )

    fines_total = fields.Monetary(
        string="Total",
        compute="_compute_fines_total",
        store=True,
    )

    fines_late = fields.Monetary(
        compute="_compute_fines_late",
        store=True
    )

    @api.onchange("late_days")
    def _onchange_late_days(self):
        if self.late_days < 0:
            self.late_days = 0

    @api.onchange("fines_rate")
    def _onchange_fines_rate(self):
        if self.fines_rate < 0:
            self.fines_rate = 0
    
    @api.depends("late_days", "fines_rate")
    def _compute_fines_late(self):
        for rec in self:
            rec.fines_late = rec.late_days * rec.fines_rate

    @api.depends("price_subtotal", "fines_late")
    def _compute_fines_total(self):
        for rec in self:
            result = rec.price_subtotal - rec.fines_late
            rec.fines_total = max(result, 0)

    @api.depends("wa_line_ids", "wa_line_ids.price_subtotal")
    def _compute_price_subtotal(self):
        for rec in self:
            rec.price_subtotal = sum(rec.wa_line_ids.mapped("price_subtotal"))

    def action_view_purchase_order(self):
        self.ensure_one()
        if not self.purchase_id:
            return

        return {
            'name': _('Purchase Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': self.purchase_id.id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
            'context': self.env.context,
        }
