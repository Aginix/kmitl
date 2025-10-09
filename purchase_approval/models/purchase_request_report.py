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
        ('normal', 'Normal'),
        ('cash_advance', 'Cash Advance')
    ], string='Payment Type', default='normal', required=True, tracking=True)
    operating_unit_id = fields.Many2one('operating.unit', string='Operating Unit', tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.company, tracking=True
    )
    currency_id = fields.Many2one('res.currency', string='Currency', states={'draft': [('readonly', False)]})
    request_ids = fields.One2many('purchase.request', 'report_id', string='Request Lines', copy=False)

    def _compute_is_editable(self):
        for rec in self:
            rec.is_editable = rec.state in ['draft']
