# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequestReport(models.Model):
    _name = 'purchase.request.report'
    _description = 'Purchase Request Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "date desc, id desc"
    _check_company_auto = True

    _STATES = [
        ("draft", "Draft"),
        ('submit', 'Submit'),
        ('done', 'Done'),
        ('cancel', 'Cancel')
    ]

    name = fields.Char('Name', tracking=True)
    is_editable = fields.Boolean("Is Editable", default=True, compute='_compute_is_editable')
    date = fields.Datetime('Date', default=fields.Datetime.now, tracking=True)
    approval_date = fields.Datetime('Approval Date', tracking=True)
    state = fields.Selection(selection=_STATES, string='Status', default='draft', tracking=True)
    payment_type = fields.Selection([
        ("direct", "Direct paid"),
        ("loan", "Loan"),
        ("prepaid", "Prepaid")
    ])
    operating_unit_id = fields.Many2one('operating.unit', string='Operating Unit', tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.company, tracking=True
    )
    currency_id = fields.Many2one('res.currency', string='Currency', states={'draft': [('readonly', False)]})
    request_ids = fields.Many2many(
        'purchase.request',
        'purchase_request_report_rel',
        'report_id', 'request_id',
        string='Requests',
        domain="[('payment_type', '=', payment_type), ('state', '=', 'to_verify'), ('report_id', '=', False)]",
    )

    def _compute_is_editable(self):
        for rec in self:
            rec.is_editable = rec.state in ['draft']

    def action_save_changes(self):
        for rec in self:
            rec.write({})
        return {'type': 'ir.actions.act_window_close'}

    @api.onchange('payment_type')
    def _onchange_payment_type_clear_requests(self):
        if self.request_ids:
            self.request_ids = [(5, 0, 0)]
