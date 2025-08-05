# -*- coding: utf-8 -*-
import logging
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestSubmit(models.Model):
    _name = 'purchase.request.submit'
    _description = 'PurchaseRequestSubmit'
    _rec_name = 'ref'

    _STATES = [
        ("draft", "Draft"),
        ("submit", "Submit"),
        ("approve", "approved"),
        ("reject", "reject"),
    ]
    state = fields.Selection(
        selection=_STATES,
        string="Status",
        index=True,
        tracking=True,
        required=True,
        copy=False,
        default="draft",
    )
    ref = fields.Char('ref')
    payment_type = fields.Selection(
        [("direct", "จ่ายตรง"),("loan", "เงินยืม"),("prepaid", "สำรองจ่าย")],
        string="Payment Type",states={"submit": [("readonly", True)],
        "approve": [("readonly", True)]}
    )
    request_by = fields.Many2one(
        'res.users',
        string='Requested By',
        default=lambda self: self.env.user,
        readonly=True,
        states={"submit": [("readonly", True)],
        "approve": [("readonly", True)]}
    )
    approve_by = fields.Many2one(
        'res.users',
        string='Approved By',
        states={"submit": [("readonly", True)],
        "approve": [("readonly", True)]}
    )
    approve_date = fields.Datetime(
        string='Approved Date',
    )
    line_ids = fields.One2many('purchase.request.submit.line', 'submitted_id', states={"submit": [("readonly", True)],"approve": [("readonly", True)]}, string="PR2 Forms")

    def button_submit(self):
        return self.write({"state": "submit"})

    def button_approve(self):
        self.ensure_one()

        self.write({
            'state': 'approve',
            'approve_by': self.env.user.id,
            'approve_date': datetime.now(),
        })

        for line in self.line_ids:
            if line.pr2_form_id and line.pr2_form_id.state != 'approve':
                line.pr2_form_id.state = 'approve'
                line.pr2_form_id.approve_by = self.env.user.id
                line.pr2_form_id.approve_date = datetime.now()

    def button_reject(self):
        return self.write({"state": "reject"})

    def button_reset(self):
        return self.write({"state": "draft"})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('ref'):
                vals['ref'] = self.env['ir.sequence'].next_by_code('purchase.request.submit')
        return super().create(vals_list)
